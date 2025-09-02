import logging
from typing import List, Optional, Dict, Any
from app.repositories.user_repo import UserRepository
from app.core.security import hash_password
from app.core.exceptions import ConflictError, NotFoundError
from app.models import User
from app.domain.types import Role

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_initial_organization_and_admin(self, name: str, email: str, password: str) -> User:
        """
        Creates the first organization and its corporate admin user.
        """
        logger.info(f"Creating initial organization '{name}' with admin {email}")

        # Check for admin if needed
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"User with email {email} already exists")
        
        # 1.- Create the org
        organization = await self.user_repo.create_organization(name=name, email=email)

        # 2.- Create the admin user for that organizatio
        hashed_password = hash_password(password)
        admin_user = await self.user_repo.create_user(
            name=name,
            email=email,
            organization_id=organization.id,
            role=Role.ADMIN,
            is_active=True,
        )
        logger.info(f"Succesfully created organization ID {organization.id} with admin user ID {admin_user.id}")
        return admin_user
    
    async def create_user_for_organization(self, org_id: int, user_data: Dict[str, Any]) -> User:
        """
        Creates a new user (stadard or admin) within an existing organization.
        """
        email = user_data["email"]
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"User with email {email} already exists")
        
        hashed_password = hash_password(user_data["password"])

        new_user = await self.user_repo.create_user(
            name=user_data["name"],
            email=email,
            hashed_password=hashed_password,
            organization_id=org_id,
            unit_id=user_data.get("unit_id"),
            role=Role.ADMIN if user_data.get("is_admin") else Role.USER,
            is_active=True,
        )
        logger.info(f"Succesfully created user ID {new_user.id} for organization ID {org_id}")
        return new_user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID
        """
        return await self.user_repo.get_by_id(user_id)
    
    async def get_users_by_organization(self, organization_id: int) -> List[User]:
        """
        Retrieves all users belonging to an organization
        """
        return self.user_repo.get_all_users(organization_id)
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """
        Updates a user's information
        """
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        
        updated_user = await self.user_repo.update_user(user_id, **update_data)
        if not updated_user:
            raise NotFoundError(f"User with ID {user_id} not found")
        return updated_user
    
    async def toggle_user_status(self, user_id: int) -> User:
        """
        Toggles a user's status between active and inactive
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        return await self.user_repo.update_user(user_id, is_active=not user.is_active)