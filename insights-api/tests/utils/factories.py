"""Data factories for creating test objects."""
import secrets
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.job import Job
from app.models.product import DiscoveredProduct
from app.models.review import Review
from app.models.organization import Organization
from app.models.email_verification import EmailVerification
from app.models.twofa import TwoFactorCode
from app.models.token import RefreshToken
from app.core.security import hash_password, hash_token
from app.domain.types import JobType, JobStatus, Role


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        email: str = "test@example.com",
        name: str = "Test User",
        password: str = "testpassword123",
        role: Role = Role.USER,
        is_active: bool = True,
        is_verified: bool = True,
        is_2fa_enabled: bool = False,
        organization_id: Optional[int] = None,
        **kwargs
    ) -> User:
        """Create a test user."""
        user_data = {
            "name": name,
            "email": email,
            "hashed_password": hash_password(password),
            "role": role,
            "is_active": is_active,
            "is_verified": is_verified,
            "is_2fa_enabled": is_2fa_enabled,
            "organization_id": organization_id,
            **kwargs
        }
        
        user = User(**user_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


class OrganizationFactory:
    """Factory for creating test organizations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        name: str = "Test Organization",
        email: Optional[str] = None,
        **kwargs
    ) -> Organization:
        """Create a test organization."""
        # FIXED: Generate unique email if not provided
        if email is None:
            unique_id = secrets.token_hex(4)
            email = f"org-{unique_id}@example.com"
            
        org_data = {
            "name": name,
            "email": email,
            **kwargs
        }
        
        org = Organization(**org_data)
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return org


class JobFactory:
    """Factory for creating test jobs."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        organization_id: int,
        job_type: JobType = JobType.REVIEW_SCRAPING,
        status: JobStatus = JobStatus.PENDING,
        sources_data: Optional[list] = None,
        **kwargs
    ) -> Job:
        """Create a test job."""
        if sources_data is None:
            sources_data = [{"name": "test_source", "url": "https://example.com"}]
        
        job_data = {
            "user_id": user_id,
            "organization_id": organization_id,
            "job_type": job_type,
            "status": status,
            "sources_data": sources_data,
            **kwargs
        }
        
        job = Job(**job_data)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


class EmailVerificationFactory:
    """Factory for creating email verification tokens."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        token: Optional[str] = None,
        expires_hours: int = 24,
        **kwargs
    ) -> EmailVerification:
        """Create an email verification token."""
        if token is None:
            token = secrets.token_urlsafe(32)
        
        verification_data = {
            "user_id": user_id,
            "token": token,
            "token_hash": hash_token(token),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
            **kwargs
        }
        
        verification = EmailVerification(**verification_data)
        session.add(verification)
        await session.commit()
        await session.refresh(verification)
        return verification


class TwoFactorCodeFactory:
    """Factory for creating 2FA codes."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        code: str = "123456",
        expires_minutes: int = 5,
        used_at: Optional[datetime] = None,
        **kwargs
    ) -> TwoFactorCode:
        """Create a 2FA code."""
        code_data = {
            "user_id": user_id,
            "code_hash": hash_token(code),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
            "used_at": used_at,
            **kwargs
        }
        
        tfa_code = TwoFactorCode(**code_data)
        session.add(tfa_code)
        await session.commit()
        await session.refresh(tfa_code)
        return tfa_code


class RefreshTokenFactory:
    """Factory for creating refresh tokens."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        token: Optional[str] = None,
        expires_days: int = 7,
        revoked_at: Optional[datetime] = None,
        **kwargs
    ) -> RefreshToken:
        """Create a refresh token."""
        if token is None:
            token = secrets.token_urlsafe(32)
        
        token_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "token_hash": hash_token(token),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=expires_days),
            "created_at": datetime.now(timezone.utc),
            "revoked_at": revoked_at,
            **kwargs
        }
        
        refresh_token = RefreshToken(**token_data)
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)
        return refresh_token


