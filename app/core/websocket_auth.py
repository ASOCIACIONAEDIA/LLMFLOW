import logging 
from typing import Optional 
from fastapi import WebSocket, HTTPException, status
from jose import jwt, JWTError

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.db.session import AsyncSession

logger = logging.getLogger(__name__)

async def get_websocket_user(websocket: WebSocket) -> Optional[User]:
    """
    Extracts and validates a user from the WebSocket connection.
    Supports both query parameter and header based authentication.
    """
    try:
        token = websocket.query_params.get("token")
        if not token:
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            logger.warning("No token provided in query params or header of the websocket connection")
            return None
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: int = payload.get("sub")
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
        
    except Exception as e:
        logger.error(f"Error getting websocket user: {str(e)}")
        return None 

class WebSocketAuthDependency:
    """
    Dependency to authenticate the user for the WebSocket connection.
    """
    async def __call__(self, websocket: WebSocket) -> User:
        user = await get_websocket_user(websocket)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
        return user 

websocket_auth = WebSocketAuthDependency()