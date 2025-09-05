from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.schemas.auth import (
    UserLoginRequest, TokenResponse, TwoFactorCodeRequest, UserRegisterRequest,
    EmailVerificationRequest, ResendVerificationRequest, RefreshTokenRequest,
    TwoFactorSetupRequest, PasswordChangeRequest, UserRegistrationResponse
)
from app.schemas.organization import OrganizationListResponse
from app.services import user_service
from app.services.auth_services import AuthService
from app.repositories.user_repo import UserRepository
from app.models import User
from app.services.user_service import UserService
from app.core.exceptions import AppError, UnauthorizedError, NotFoundError, ConflictError

router = APIRouter()
auth_service = AuthService()

@router.get("/organizations", response_model=List[OrganizationListResponse])
async def get_available_organizations(
    db: AsyncSession = Depends(deps.get_db),
) -> List[OrganizationListResponse]:
    """
    Get all available organizations for user registration.
    """
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    organizations = await user_service.get_available_organizations()
    return organizations

@router.post("/register", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
) -> UserRegistrationResponse:
    """
    Register a user ith optional organization selection
    """
    user_repo = UserRepository(db)
    user_services = UserService(user_repo)

    try:
        new_user = await user_services.create_user(
            name=user_in.name,
            email=user_in.email,
            password=user_in.password,
            organization_id=user_in.organization_id,
            organization_name=user_in.organization_name,
            background_tasks=background_tasks
        )

        return UserRegistrationResponse(
            message="User registered successfully. Please check your email to verify your account.",
            user_id=new_user.id,
            requires_verification=True
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
@router.post("verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Verify a user's email address using a verification token
    """
    user_repo = UserRepository(db)
    try:
        await auth_service.verify_email(user_repo, request.token)
        user_id = await user_repo.verify_email_verification(request.email)
        if user_id:
            user = await user_repo.get_by_id(user_id)
            if user:
                background_tasks.add_task(
                    auth_service._send_welcome_email, #TODO:ASK
                    user.email,
                    user.name
                    )
        return {"message": "Email verified successfully. You can now login."}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/resend-verification")
async def resend_verification_email(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    """Resend email verification link."""
    user_repo = UserRepository(db)
    
    try:
        user = await user_repo.get_by_email(request.email)
        if not user:
            return {"message": "If the email exists, a verification link has been sent."}
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        await auth_service.send_email_verification(user_repo, user.id, background_tasks)
        return {"message": "Verification email sent successfully."}
    except AppError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    user_in: UserLoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Authenticate user and return tokens.
    """
    user_repo = UserRepository(db)
    
    try:
        user_id, is_2fa_enabled, remember_me = await auth_service.login_user(
            user_repo, user_in.email, user_in.password, user_in.remember_me
        )
        
        if is_2fa_enabled:
            await auth_service.send_2fa_code(user_repo, user_id, background_tasks)
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail={"message": "2FA required", "user_id": user_id, "requires_2fa": True},
            )
            
        tokens = await auth_service.issue_tokens(user_repo, user_id, remember_me)
        return TokenResponse(**tokens)
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/verify-2fa", response_model=TokenResponse)
async def verify_2fa(
    tfa_in: TwoFactorCodeRequest,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Verify 2FA code and return tokens.
    """
    user_repo = UserRepository(db)
    
    try:
        user = await user_repo.get_by_id(tfa_in.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )
        
        is_valid = await auth_service.verify_2fa_code(user_repo, user.id, tfa_in.code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid or expired 2FA code"
            )
        
        # Issue tokens after successful 2FA
        tokens = await auth_service.issue_tokens(user_repo, user.id, remember_me=True)
        return TokenResponse(**tokens)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """Refresh access token using refresh token."""
    user_repo = UserRepository(db)
    
    try:
        tokens = await auth_service.refresh_access_token(user_repo, request.refresh_token)
        return TokenResponse(**tokens)
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """Logout user by revoking refresh token."""
    user_repo = UserRepository(db)
    
    try:
        await auth_service.revoke_refresh_token(user_repo, request.refresh_token)
        return {"message": "Logged out successfully"}
    except Exception:
        # Even if token revocation fails, consider logout successful
        return {"message": "Logged out successfully"}


@router.post("/2fa/enable")
async def enable_2fa(
    request: TwoFactorSetupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Enable 2FA for the current user."""
    user_repo = UserRepository(db)
    
    try:
        await auth_service.enable_2fa(user_repo, current_user.id, request.password)
        
        # Send notification email
        background_tasks.add_task(
            auth_service._send_2fa_enabled_notification,
            current_user.email,
            current_user.name
        )
        
        return {"message": "2FA has been enabled successfully"}
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except AppError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

@router.post("/2fa/disable")
async def disable_2fa(
    request: TwoFactorSetupRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Disable 2FA for the current user."""
    user_repo = UserRepository(db)
    
    try:
        await auth_service.disable_2fa(user_repo, current_user.id, request.password)
        return {"message": "2FA has been disabled successfully"}
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except AppError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Change user password."""
    user_repo = UserRepository(db)
    
    try:
        await auth_service.change_password(
            user_repo, 
            current_user.id, 
            request.current_password, 
            request.new_password
        )
        
        # Send notification email
        background_tasks.add_task(
            auth_service._send_password_changed_notification,
            current_user.email,
            current_user.name
        )
        
        return {"message": "Password changed successfully. Please log in again."}
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Logout user from all devices by revoking all refresh tokens."""
    user_repo = UserRepository(db)
    
    await auth_service.revoke_all_refresh_tokens(user_repo, current_user.id)
    return {"message": "Logged out from all devices successfully"}

@router.get("/me")
async def get_current_user_info( # TODO: ASK ABOUT THIS
    current_user: User = Depends(deps.get_current_user),
):
    """Get current user information."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "organization_id": current_user.organization_id,
        "created_at": current_user.created_at,
    }
