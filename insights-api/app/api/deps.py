import logging
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import ArqRedis

from app.core import security
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import User
from app.repositories.user_repo import UserRepository
from app.repositories.job_repo import JobRepository
from app.schemas.auth import TokenPayload
from app.services.user_service import UserService
from app.services.job_service import JobService
from app.domain.types import TokenType

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_job_repo(db: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(db)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserService:
    return UserService(user_repo)


def get_arq_pool(request: Request) -> ArqRedis:
    """Get the ARQ pool from app state"""
    return request.app.state.arq_worker


def get_job_service(
    job_repo: JobRepository = Depends(get_job_repo),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> JobService:
    return JobService(job_repo, arq_pool)


async def get_current_user(
    user_repo: UserRepository = Depends(get_user_repo),
    token: str = Depends(oauth2_scheme),
) -> User:
    try:
        # Use our security module's decode_token function
        payload = security.decode_token(token, expected_type=TokenType.ACCESS)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = int(user_id)
        
    except (ValueError, ValidationError) as e:
        logger.error(f"Error decoding token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Inactive user"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Unverified user"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (redundant check, but kept for compatibility)"""
    return current_user


async def get_arq_client() -> ArqRedis:
    """
    Dependency to get the ArqRedis client.
    """
    return ArqRedis.from_url(settings.ARQ_REDIS_URL)