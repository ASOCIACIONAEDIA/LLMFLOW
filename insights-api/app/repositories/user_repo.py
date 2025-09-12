import logging 
import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.organization import Organization
from app.models.unit import Unit
from app.models.token import RefreshToken
from app.models.twofa import TwoFactorCode
from app.models.email_verification import EmailVerification

from app.domain.types import Role, TokenType
from app.core.exceptions import NotFoundError, ConflictError
from app.core.security import hash_token

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # --- Organization methods ---
    async def create_organization(self, name: str, email: Optional[str] = None) -> Organization:
        """
        Creates a new organization.
        """
        organization = Organization(name=name, email=email)
        self.session.add(organization)
        await self.session.flush()
        return organization

    async def get_organization_by_id(self, organization_id: int) -> Optional[Organization]:
        """
        Retrieves an organization by ID.
        """
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_organizations(self) -> List[Organization]:
        """
        Retrieves all organizations.
        """
        stmt = select(Organization).order_by(Organization.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # --- User methods ---
    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
        organization_id: Optional[int] = None,
        role: Role = Role.USER,
        unit_id: Optional[int] = None,
        is_active: bool = False,
        is_verified: bool = False,
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
            is_verified=is_verified,
            is_2fa_enabled=is_2fa_enabled,
        )
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError as e:
            await self.session.rollback()
            if "users_email_key" in str(e) or "user_email_key" in str(e):
                raise ConflictError(f"User with email {email} already exists") from e
            raise 
        
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_with_organization(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID with organization loaded.
        """
        stmt = select(User).options(selectinload(User.organization)).where(User.id == user_id)
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

    async def get_users_by_organization(self, organization_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Retrieves users by organization with pagination.
        """
        stmt = (
            select(User)
            .where(User.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_users(
        self, 
        organization_id: Optional[int] = None,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Search users with various filters.
        """
        stmt = select(User)
        
        conditions = []
        
        if organization_id is not None:
            conditions.append(User.organization_id == organization_id)
        
        if query:
            search_term = f"%{query}%"
            conditions.append(
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())
        
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
            return None
        
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
    
    # --- Refresh Token operations ---
    async def create_refresh_token(
        self, user_id: int, token_hash: str, expires_days: int = 7
    ) -> RefreshToken:
        """
        Creates a new refresh token
        """
        token_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        refresh_token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token
    
    async def verify_refresh_token(self, token_hash: str) -> Optional[int]:
        """
        Verifies a refresh token and returns the user_id if valid.
        """
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.expires_at > datetime.now(timezone.utc),
                RefreshToken.revoked_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        refresh_token = result.scalar_one_or_none()
        return refresh_token.user_id if refresh_token else None

    async def get_refresh_token(self, token_uuid: UUID) -> Optional[RefreshToken]:
        """
        Retrieves a refresh token by its UUID.
        """
        stmt = select(RefreshToken).where(RefreshToken.id == str(token_uuid))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str) -> bool:
        """
        Revokes a refresh token by marking it as revoked
        """
        stmt = (
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None)
                )
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
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
        # Invalidate any existing codes first
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

    async def verify_and_consume_2fa_code(self, user_id: int, code_hash: str) -> bool:
        """
        Verifies and consumes a 2FA code. Returns True if valid, False otherwise.
        """
        stmt = select(TwoFactorCode).where(
            TwoFactorCode.user_id == user_id,
            TwoFactorCode.code_hash == code_hash,
            TwoFactorCode.expires_at > datetime.now(timezone.utc),
            TwoFactorCode.used_at.is_(None)
        )
        result = await self.session.execute(stmt)
        twofa_code = result.scalar_one_or_none()
        
        if not twofa_code:
            return False
        
        # Mark as used
        twofa_code.used_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True
    
    async def get_active_2fa_code(self, user_id: int, code_hash: str) -> Optional[TwoFactorCode]:
        """
        Fetches an active, unused 2FA code for a user
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

    async def revoke_all_2fa_codes(self, user_id: int) -> int:
        """
        Revokes all active 2FA codes for a user.
        """
        stmt = update(TwoFactorCode).where(
            TwoFactorCode.user_id == user_id,
            TwoFactorCode.used_at.is_(None),
            TwoFactorCode.expires_at > datetime.now(timezone.utc)
        ).values(used_at=datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    # --- Email Verification operations ---
    async def create_email_verification(
        self, user_id: int, token: str, token_hash: str, expires_hours: int = 24
    ) -> EmailVerification:
        """
        Creates a new email verification token.
        """
        # Invalidate any existing verification tokens first
        await self.session.execute(
            update(EmailVerification).where(
                EmailVerification.user_id == user_id,
                EmailVerification.verified_at.is_(None),
                EmailVerification.expires_at > datetime.now(timezone.utc)
            ).values(verified_at=datetime.now(timezone.utc))  # Mark as "used"
        )

        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        
        verification = EmailVerification(
            user_id=user_id,
            token=token,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(verification)
        await self.session.commit()
        await self.session.refresh(verification)
        return verification

    async def verify_email_verification(self, token: str) -> Optional[int]:
        """
        Verifies an email verification token and returns the user_id if valid.
        """
        token_hash = hash_token(token)
        
        stmt = select(EmailVerification).where(
            EmailVerification.token_hash == token_hash,
            EmailVerification.expires_at > datetime.now(timezone.utc),
            EmailVerification.verified_at.is_(None)
        )
        result = await self.session.execute(stmt)
        verification = result.scalar_one_or_none()
        
        if not verification:
            return None
        
        # Mark as verified
        verification.verified_at = datetime.now(timezone.utc)
        await self.session.commit()
        return verification.user_id
    
