import logging 
from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.organization import Organization
from app.models.unit import Unit
from app.models.token import RefreshToken
from app.models.twofa import TwoFactorCode

from app.domain.types import Role, TokenType
from app.core.exceptions import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_organization(self, name: str, email: Optional[str] = None) -> Organization:
        """
        Creates a new organization.
        """
        organization = Organization(name=name, email=email)
        self.session.add(organization)
        await self.session.flush()
        return organization

    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
        organization_id: int,
        role: Role = Role.USER,
        unit_id: Optional[int] = None,
        is_active: bool = True,
        is_2fa_enabled: bool = False,
    ) -> User:
        """
        Creates a new user.
        """
        user = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            organization_id=organization_id,
            unit_id=unit_id,
            role=role,
            is_active=is_active,
            is_2fa_enabled=is_2fa_enabled,
        )
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError as e:
            await self.session.rollback()
            if "user_email_key" in str(e):
                raise ConflictError(f"User with email {email} already exists") from e
            raise 
        
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieves a user by their email.
        """
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_users(self, organization_id: Optional[int] = None) -> List[User]:
        """
        Retrieves all users, optionally filtered by organization.
        """
        stmt = select(User)
        if organization_id:
            stmt = stmt.where(User.organization_id == organization_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Updates a user's fields.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user by their id
        """
        stmt = delete(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    # --- Token operations ---
    async def create_refresh_token(
        self, user_id: int, token_hash: str, expires_at: datetime, token_uuid: UUID
    ) -> RefreshToken:
        """
        Creates a new refresh token
        """
        refresh_token = RefreshToken(
            id=str(token_uuid),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token
    
    async def get_refresh_token(self, token_uuid: UUID) -> Optional[RefreshToken]:
        """
        Retrieves a refresh token by its UUID.
        """
        stmt = select(RefreshToken).where(RefreshToken.id == str(token_uuid))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_uuid: UUID) -> Optional[RefreshToken]:
        """
        Revokes a refresh token by marking it as used
        """
        stmt = select(RefreshToken).where(RefreshToken.id == str(token_uuid), RefreshToken.revoked_at.is_(None))
        result = await self.session.execute(stmt)
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
            refresh_token.revoked_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(refresh_token)
        return refresh_token
    
    async def revoke_all_user_refresh_tokens(self, user_id: int) -> int:
        """
        Revokes all refresh tokens for a user.
        """
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None)
        ).values(revoked_at=datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # --- Two-factor operations ---
    async def create_2fa_code(self, user_id: int, code_hash: str, expires_at: datetime) -> TwoFactorCode:
        """
        Creates and stores a new 2FA code for a user.
        """
        # Invalidate any existing codes first pls
        await self.session.execute(
            update(TwoFactorCode).where(
                TwoFactorCode.user_id == user_id,
                TwoFactorCode.used_at.is_(None),
                TwoFactorCode.expires_at > datetime.now(timezone.utc)
            ).values(used_at=datetime.now(timezone.utc))
        )

        twofa_code = TwoFactorCode(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(twofa_code)
        await self.session.commit()
        await self.session.refresh(twofa_code)
        return twofa_code
    
    async def get_active_2fa_code(self, user_id: int, code_hash: str) -> Optional[TwoFactorCode]:
        """
        Fetches an active, unused 2FA code for an user
        """
        stmt = select(TwoFactorCode).where(
            TwoFactorCode.user_id == user_id,
            TwoFactorCode.code_hash == code_hash,
            TwoFactorCode.expires_at > datetime.now(timezone.utc),
            TwoFactorCode.used_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def mark_2fa_code_as_used(self, twofa_code: TwoFactorCode) -> TwoFactorCode:
        """
        Marks a 2FA code as used
        """
        twofa_code.used_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(twofa_code)
        return twofa_code
    
