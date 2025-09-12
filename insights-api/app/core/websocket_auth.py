import logging
from typing import Optional
from fastapi import WebSocket, HTTPException, status
from jose import jwt, JWTError
 
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.db.session import AsyncSession
 
logger = logging.getLogger(__name__)
 
async def authenticate_user_from_token(token: str) -> Optional[User]:
    """
    Authenticate user from JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("JWT token missing 'sub' claim (user ID)")
            return None
       
    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        return None
   
    async with AsyncSession() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
 
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            return None
       
        if not user.is_active:
            logger.warning(f"User with ID {user_id} is inactive")
            return None
       
        return user