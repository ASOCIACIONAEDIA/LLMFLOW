import logging
from typing import List, Optional, Dict, Any
from fastapi import BackgroundTasks
from app.repositories.user_repo import UserRepository
from app.core.security import hash_password, password_meets_policy
from app.core.exceptions import ConflictError, NotFoundError, AppError
from app.models import User, Organization
from app.domain.types import Role
from app.services.auth_services import AuthService

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.auth_service = AuthService()

    async def create_user(
        self, 
        name: str, 
        email: str, 
        password: str,
        organization_id: Optional[int] = None,
        organization_name: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> User:
        """
        Creates a new user with organization handling.
        """
        # Check if user already exists
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"User with email {email} already exists")
        
        if organization_id:
            # Verify organization exists
            organization = await self.user_repo.get_organization_by_id(organization_id)
            if not organization:
                raise NotFoundError(f"Organization with ID {organization_id} not found")
            final_org_id = organization_id
        elif organization_name:
            # Create new organization
            organization = await self.user_repo.create_organization(name=organization_name, email=email)
            final_org_id = organization.id
            logger.info(f"Created new organization '{organization_name}' with ID {organization.id}")
        else:
            final_org_id = None
        
        # Create user
        hashed_password = hash_password(password)
        user = await self.user_repo.create_user(
            name=name,
            email=email,
            hashed_password=hashed_password,
            organization_id=final_org_id,
            role=Role.ADMIN if organization_name else Role.USER,  # Creator of org becomes admin
            is_active=False,  # Requires email verification
            is_verified=False
        )
        
        # Send verification email if background tasks available
        if background_tasks:
            await self.auth_service.send_email_verification(
                self.user_repo, user.id, background_tasks
            )
        
        logger.info(f"Created user {user.id} for organization {final_org_id}")
        return user

    async def create_initial_organization_and_admin(self, name: str, email: str, password: str) -> User:
        """
        Creates the first organization and its corporate admin user.
        """
        logger.info(f"Creating initial organization '{name}' with admin {email}")

        # Check if admin already exists
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"User with email {email} already exists")
        
        # Create the organization
        organization = await self.user_repo.create_organization(name=name, email=email)

        # Create the admin user for that organization
        hashed_password = hash_password(password)
        admin_user = await self.user_repo.create_user(
            name=name,
            email=email,
            hashed_password=hashed_password,
            organization_id=organization.id,
            role=Role.CORPORATE_ADMIN,
            is_active=True,  # Admin users are active by default
            is_verified=True  # Admin users are verified by default
        )
        
        logger.info(f"Successfully created organization ID {organization.id} with admin user ID {admin_user.id}")
        return admin_user
    
    async def create_user_for_organization(self, org_id: int, user_data: Dict[str, Any]) -> User:
        """
        Creates a new user (standard or admin) within an existing organization.
        """
        email = user_data["email"]
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"User with email {email} already exists")
        
        # Enforce password policy here (not at schema) so permission checks can run first
        password_meets_policy(user_data["password"])

        hashed_password = hash_password(user_data["password"])

        new_user = await self.user_repo.create_user(
            name=user_data["name"],
            email=email,
            hashed_password=hashed_password,
            organization_id=org_id,
            unit_id=user_data.get("unit_id"),
            role=Role.ADMIN if user_data.get("is_admin") else Role.USER,
            is_active=True,  # Organization users are active by default
            is_verified=True  # Organization users are verified by default
        )
        
        logger.info(f"Successfully created user ID {new_user.id} for organization ID {org_id}")
        return new_user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID with organization details.
        """
        return await self.user_repo.get_user_with_organization(user_id)
    
    async def get_users_by_organization(self, organization_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Retrieves all users belonging to an organization with pagination.
        """
        return await self.user_repo.get_users_by_organization(organization_id, skip=skip, limit=limit)
    
    async def get_available_organizations(self) -> List[Organization]:
        """
        Retrieves all organizations available for user registration.
        """
        return await self.user_repo.get_all_organizations()
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> User:
        """
        Updates a user's information.
        """
        # Don't allow password updates through this method
        if "password" in update_data:
            update_data.pop("password")
            logger.warning(f"Password update attempted through update_user for user {user_id}")
        
        updated_user = await self.user_repo.update_user(user_id, **update_data)
        if not updated_user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        logger.info(f"Updated user {user_id}")
        return updated_user
    
    async def toggle_user_status(self, user_id: int) -> User:
        """
        Toggles a user's active status.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        new_status = not user.is_active
        updated_user = await self.user_repo.update_user(user_id, is_active=new_status)
        
        logger.info(f"User {user_id} status changed to {'active' if new_status else 'inactive'}")
        return updated_user
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Soft deletes a user by deactivating them.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        await self.user_repo.update_user(user_id, is_active=False)
        logger.info(f"User {user_id} deactivated")
        return True
    
    async def search_users(
        self, 
        organization_id: Optional[int] = None,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Searches users with various filters.
        """
        return await self.user_repo.search_users(
            organization_id=organization_id,
            query=query,
            is_active=is_active,
            skip=skip,
            limit=limit
        )