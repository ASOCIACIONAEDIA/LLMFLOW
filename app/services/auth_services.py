import logging 
import uuid 
from fastapi import BackgroundTasks
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.security import hash_password, verify_password, create_token, generate_2fa_code, burn_time_for_unknown_user
from app.core.config import settings
from app.domain.types import Role, TokenType
from app.repositories.user_repo import UserRepository
from app.core.exceptions import NotFoundError, ConflictError, AppError, UnauthorizedError
from app.services.mailer import mailer_service
from app.db.redis import get_redis_client

class AuthService:
    async def _get_user_and_handle_not_found(self, user_repo: UserRepository, email: str) -> User:
        """
        Helper function to fetch user or raise UnauthorizedError, performing timing attack mitigation
        """   
        user = await user_repo.get_by_email(email)
        if not user:
            # Defend here!!
            burn_time_for_unknown_user("dummy_password")
            raise UnauthorizedError("Invalid credentials")
        return user
    
    async def login_user(self, user_repo: UserRepository, email: str, password: str, remembere_me: bool = False) -> Tuple[int, bool]:
        """
        Authenticates a user and prepares for 2FA or token issuance.
        Return (user_id, is_2fa_required)
        """
        user = await self._get_user_and_handle_not_found(user_repo, email)
        if not user.is_Active:
            raise UnauthorizedError("User account is inactive")
        
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")
        
        return user.id, user.is_2fa_enabled
    
    async def send_2fa_code(self, user_repo: UserRepository, user_id: int, background_tasks: BackgroundTasks) -> None:
        """
        Sends a 2FA code to the user's email.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        code = generate_2fa_code()
        redis_client = get_redis_client()
        await redis_client.set(f"2fa_code:{user_id}", timedelta(minutes=5), code)

        background_tasks.add_task(
            mailer_service.send_2fa_code,
            recipient_email=user.email,
            user_name=user.name,
            code=code
        )
    
    async def verify_2fa_code(self, user_id: int, code: str) -> bool:
        """
        Verifies a 2FA code, returns True if valid, False otherwise.
        """
        redis_client = get_redis_client()
        stored_code = await redis_client.get(f"2fa_code:{user_id}")
        if not stored_code or stored_code != code: # TODO: Should we encrpyt this code somethow? See send_2fa_code to implement this.
            return False
        
        await redis_client.delete(f"2fa_code:{user_id}")
        return True
    
    async def issue_token(self, user_repo: UserRepository, user_id: int) -> str:
        """
        Issues a new access token for a user.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        return create_token(
            subject=user_id,
            token_type=TokenType.ACCESS,
            role=user.role,
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            extra_claims={"org_id": user.organization_id}
        )
    