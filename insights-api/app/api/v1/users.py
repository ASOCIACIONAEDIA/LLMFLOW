from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api import deps
from app.schemas.user import (
    UserResponse, UserProfileResponse, UserListResponse, 
    UserUpdate, UserCreate
)
from app.schemas.organization import OrganizationResponse
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.models import User
from app.domain.types import Role
from app.core.exceptions import NotFoundError, ConflictError, AppError
from app.core.security import require_role

router = APIRouter()

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_info(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> UserProfileResponse:
    """
    Get current user's detailed profile
    """
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)

    user = await user_service.get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    response = UserProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        organization_id=user.organization_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        organization_name=user.organization.name if user.organization else None,
        unit_name=user.unit.name if user.unit else None
    )
    return response

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> UserResponse:
    """
    Update current user's profile
    """
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)

    try:
        update_data = user_update.model_dump(exclude_unset=True)
        update_data.pop("is_active", None)
        update_data.pop("is_2fa_enabled", None)

        updated_user = await user_service.update_user(current_user.id, update_data)
        return updated_user
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.get("/", response_model=List[UserListResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    query: Optional[str] = Query(None, description="Search by name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> List[UserListResponse]:
    """
    List users with filtering and pagination. Requires admin role.
    """
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    # Corporate admins can only see users in their organization
    if current_user.role == Role.CORPORATE_ADMIN:
        organization_id = current_user.organization_id
    
    users = await user_service.search_users(
        organization_id=organization_id,
        query=query,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return users

@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Get user by ID. Requires admin role or self-access."""
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    # Users can view their own profile, admins can view any
    if (current_user.id != user_id and 
        current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        # Corporate admins can only see users in their organization
        if (current_user.role == Role.CORPORATE_ADMIN and 
            user.organization_id != current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in your organization"
            )
        
        response = UserProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_2fa_enabled=user.is_2fa_enabled,
            organization_id=user.organization_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
            organization_name=user.organization.name if user.organization else None,
            unit_name=user.unit.name if user.unit else None
        )
        
        return response
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Update user by ID. Requires admin role."""
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    try:
        # Check if user exists and is in same organization (for corporate admins)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        if (current_user.role == Role.CORPORATE_ADMIN and 
            user.organization_id != current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in your organization"
            )
        
        update_data = user_update.model_dump(exclude_unset=True)
        updated_user = await user_service.update_user(user_id, update_data)
        return updated_user
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Create a new user. Requires admin role."""
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    try:
        # Corporate admins can only create users in their organization
        organization_id = user_create.organization_id
        if current_user.role == Role.CORPORATE_ADMIN:
            organization_id = current_user.organization_id
        
        user_data = {
            "name": user_create.name,
            "email": user_create.email,
            "password": user_create.password,
            "is_admin": user_create.role == Role.ADMIN
        }
        
        new_user = await user_service.create_user_for_organization(
            organization_id, user_data
        )
        return new_user
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Toggle user active status. Requires admin role."""
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    try:
        # Check if user exists and is in same organization (for corporate admins)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        if (current_user.role == Role.CORPORATE_ADMIN and 
            user.organization_id != current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in your organization"
            )
        
        # Prevent self-deactivation
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own status"
            )
        
        updated_user = await user_service.toggle_user_status(user_id)
        status_text = "activated" if updated_user.is_active else "deactivated"
        
        return {"message": f"User {status_text} successfully"}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Soft delete user. Requires admin role."""
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    try:
        # Check if user exists and is in same organization (for corporate admins)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        if (current_user.role == Role.CORPORATE_ADMIN and 
            user.organization_id != current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in your organization"
            )
        
        # Prevent self-deletion
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        await user_service.delete_user(user_id)
        return {"message": "User deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/organization/{organization_id}", response_model=List[UserListResponse])
async def get_organization_users(
    organization_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Get users by organization. Requires admin role or same organization."""
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    
    # Check permissions
    if (current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN] and
        current_user.organization_id != organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    users = await user_service.get_users_by_organization(
        organization_id, skip=skip, limit=limit
    )
    
    return users