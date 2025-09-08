import logging 
import uuid 
import secrets
from fastapi import BackgroundTasks
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.security import (
    hash_password, verify_password, create_token, generate_2fa_code, 
    burn_time_for_unknown_user, hash_token
)
from app.core.config import settings
from app.domain.types import Role, TokenType
from app.repositories.user_repo import UserRepository
from app.core.exceptions import NotFoundError, ConflictError, AppError, UnauthorizedError
from app.services.mailer import mailer_service

logger = logging.getLogger(__name__)

class AuthService:
    async def _get_user_and_handle_not_found(self, user_repo: UserRepository, email: str) -> User:
        """
        Helper function to fetch user or raise UnauthorizedError, performing timing attack mitigation
        """   
        user = await user_repo.get_by_email(email)
        if not user:
            # Defend against timing attacks
            burn_time_for_unknown_user("dummy_password")
            raise UnauthorizedError("Invalid credentials")
        return user
    
    async def _send_welcome_email(self, email: str, name: str) -> None:
        """Helper method to send welcome email"""
        await mailer_service.send_welcome_email(email, name)
    
    async def _send_password_changed_notification(self, email: str, name: str) -> None:
        """Helper method to send password change notification"""
        await mailer_service.send_password_changed_notification(email, name)
    
    async def _send_2fa_enabled_notification(self, email: str, name: str) -> None:
        """Helper method to send 2FA enabled notification"""
        await mailer_service.send_2fa_enabled_notification(email, name)
    
    async def login_user(self, user_repo: UserRepository, email: str, password: str, remember_me: bool = False) -> Tuple[int, bool, bool]:
        """
        Authenticates a user and prepares for 2FA or token issuance.
        Returns (user_id, is_2fa_required, remember_me)
        """
        user = await self._get_user_and_handle_not_found(user_repo, email)

        # Fixed: Check verification status before inactive status
        if not user.is_verified:
            raise UnauthorizedError("Please verify your email before logging in")
        
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")
        
        return user.id, user.is_2fa_enabled, remember_me
    
    async def send_2fa_code(self, user_repo: UserRepository, user_id: int, background_tasks: BackgroundTasks) -> None:
        """
        Sends a 2FA code to the user's email.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        code = generate_2fa_code()
        hashed_code = hash_token(code)

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.TWOFA_TTL_MINUTES)
        await user_repo.create_2fa_code(user_id, hashed_code, expires_at)

        background_tasks.add_task(
            mailer_service.send_2fa_code,
            recipient_email=user.email,
            user_name=user.name,
            code=code
        )
        logger.info(f"2FA code sent to user {user_id}")
    
    async def verify_2fa_code(self, user_repo: UserRepository, user_id: int, code: str) -> bool:
        """
        Verifies a 2FA code, returns True if valid, False otherwise.
        """
        hashed_code = hash_token(code)
        is_valid = await user_repo.verify_and_consume_2fa_code(user_id, hashed_code)
        
        if is_valid:
            logger.info(f"2FA verification successful for user {user_id}")
        else:
            logger.warning(f"2FA verification failed for user {user_id}")
            
        return is_valid

    async def issue_tokens(self, user_repo: UserRepository, user_id: int, remember_me: bool = False) -> Dict[str, Any]:
        """
        Issues access and optionally refresh tokens for a user.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Create access token
        access_token = create_token(
            subject=user_id,
            token_type=TokenType.ACCESS,
            role=user.role,
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            extra_claims={"org_id": user.organization_id}
        )

        result = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
        # Create refresh token if remember_me is enabled
        if remember_me:
            refresh_token = await self._create_refresh_token(user_repo, user_id)
            result["refresh_token"] = refresh_token
        
        logger.info(f"Tokens issued for user {user_id}, remember_me: {remember_me}")
        return result
    
    async def _create_refresh_token(self, user_repo: UserRepository, user_id: int) -> str:
        """
        Creates a refresh token for the user.
        """
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        await user_repo.create_refresh_token(
            user_id=user_id,
            token_hash=token_hash,
            expires_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

        return token

    async def refresh_access_token(self, user_repo: UserRepository, refresh_token: str) -> Dict[str, Any]:
        """
        Issues a new access token using a valid refresh token.
        """
        token_hash = hash_token(refresh_token)
        user_id = await user_repo.verify_refresh_token(token_hash)
        
        if not user_id:
            raise UnauthorizedError("Invalid or expired refresh token")

        # Issue new access token without refresh token
        tokens = await self.issue_tokens(user_repo, user_id, remember_me=False)

        logger.info(f"Access token refreshed for user {user_id}")
        return tokens
    
    async def revoke_refresh_token(self, user_repo: UserRepository, refresh_token: str) -> None:
        """
        Revokes a refresh token.
        """
        token_hash = hash_token(refresh_token)
        await user_repo.revoke_refresh_token(token_hash)
        logger.info("Refresh token revoked")
    
    async def revoke_all_refresh_tokens(self, user_repo: UserRepository, user_id: int) -> int:
        """
        Revokes all refresh tokens for a user.
        Returns the count of revoked tokens.
        """
        count = await user_repo.revoke_all_user_refresh_tokens(user_id)
        logger.info(f"All refresh tokens revoked for user {user_id}, count: {count}")
        return count
    
    async def send_email_verification(self, user_repo: UserRepository, user_id: int, background_tasks: BackgroundTasks) -> None:
        """
        Sends an email verification link to the user.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if user.is_verified:
            raise AppError("Email is already verified", status_code=400, code="already_verified")
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        # Store verification token in database
        await user_repo.create_email_verification(
            user_id=user_id,
            token=token,
            token_hash=token_hash,
            expires_hours=24
        )

        background_tasks.add_task(
            mailer_service.send_email_verification,
            recipient_email=user.email,
            user_name=user.name,
            token=token
        )
        logger.info(f"Email verification sent to user {user_id}")
    
    async def verify_email(self, user_repo: UserRepository, token: str) -> bool:
        """
        Verifies an email using the verification token.
        """
        user_id = await user_repo.verify_email_verification(token)

        if not user_id:
            return False  # Fixed: Return False instead of raising exception for service layer
        
        # Activate the user account
        await user_repo.update_user(user_id, is_verified=True, is_active=True)
        
        logger.info(f"Email verified for user {user_id}")
        return True

    async def enable_2fa(self, user_repo: UserRepository, user_id: int, password: str) -> None:
        """
        Enables 2FA for a user after password verification.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if user.is_2fa_enabled:
            raise AppError("2FA is already enabled", status_code=400, code="already_enabled")
        
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid password")
        
        await user_repo.update_user(user_id, is_2fa_enabled=True)
        logger.info(f"2FA enabled for user {user_id}")
    
    async def disable_2fa(self, user_repo: UserRepository, user_id: int, password: str) -> None:
        """
        Disables 2FA for a user after password verification.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if not user.is_2fa_enabled:
            raise AppError("2FA is not enabled", status_code=400, code="not_enabled")
        
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid password")
        
        await user_repo.update_user(user_id, is_2fa_enabled=False)
        # Revoke all existing 2FA codes
        await user_repo.revoke_all_2fa_codes(user_id)
        logger.info(f"2FA disabled for user {user_id}")
    
    async def change_password(self, user_repo: UserRepository, user_id: int, current_password: str, new_password: str) -> None:
        """
        Changes a user's password after verifying the current password.
        """
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Invalid current password")
        
        new_hashed_password = hash_password(new_password)
        await user_repo.update_user(user_id, hashed_password=new_hashed_password)
        
        # Revoke all refresh tokens for security
        await self.revoke_all_refresh_tokens(user_repo, user_id)
        
        logger.info(f"Password changed for user {user_id}")

    