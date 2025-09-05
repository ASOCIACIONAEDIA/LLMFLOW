from __future__ import annotations

import logging
import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import random

import jwt  # PyJWT
from passlib.context import CryptContext

from app.domain.types import Role, TokenType
from .config import settings
from .exceptions import UnauthorizedError, ForbiddenError

logger = logging.getLogger(__name__)

# Use bcrypt
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# LOL -> Used to equalize timing when the user/email doesn't exist
# We compute it once per process and ignore its return value
DUMMY_BCRYPT_HASH = _pwd.hash("dummy")


# --- Passwords ---
def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    return _pwd.hash(password)

def verify_password(plain: str, stored: str) -> bool:
    """
    Verify a password against a stored hash.
    """
    try:
        return _pwd.verify(plain, stored)
    except Exception:
        logger.exception("Error while verifying password")
        return False

def password_meets_policy(password: str) -> None:
    """
    Raise a ValueError if password fails our policy, passes otherwise.
    """
    if len(password) < settings.PWD_MIN_LEN:
        raise ValueError(f"Password must be at least {settings.PWD_MIN_LEN} characters")
    if settings.PWD_REQUIRE_UPPER and not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter")
    if settings.PWD_REQUIRE_LOWER and not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter")
    if settings.PWD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain a special character")

def burn_time_for_unknown_user(plain: str) -> None:
    """
    Call this when the email/username isn't found, to keep timing similar
    to a real bcrypt verify. Ignore the result.
    """
    try:
        _pwd.verify(plain, DUMMY_BCRYPT_HASH)
    except Exception:
        # Swallow any error; this is purely to equalize timing.
        pass

def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.
    We use SHA-256 instead of bcrypt for tokens as we need deterministic hashing.
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)

# --- JWT ---

def create_token(
    *, 
    subject: str|int,
    role: Role,
    token_type: TokenType = TokenType.ACCESS,
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    if role not in settings.ALLOWED_ROLES:
        raise ValueError(f"Role {role} is not allowed")
    
    now = datetime.now(timezone.utc)
    if expires_minutes is None:
        expires_minutes = (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES
            if token_type == TokenType.ACCESS
            else settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
    
    claims: dict[str, Any] = {
        "sub": str(subject),
        "role": role.value,
        "typ": token_type.value,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)
    
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_type: Optional[TokenType] = None) -> dict[str, Any]:
    """
    Decode a JWT token into a dictionary of claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "iss"]}
        )
    except jwt.PyJWTError as e:
        raise UnauthorizedError(f"Invalid or expired token") from e
    
    if expected_type and payload.get("typ") != expected_type.value:
        raise UnauthorizedError("Token type mismatch")
    
    role = payload.get("role")
    if role and role not in [r.value for r in settings.ALLOWED_ROLES]:
        raise UnauthorizedError("Role not recognized")
    return payload

def require_role(payload: dict[str, Any], *allowed: Role) -> None:
    """Raise ForbiddenError if the token's role is not allowed."""
    tok_role = payload.get("role")
    if tok_role is None:
        raise ForbiddenError("No role on token")
    if allowed and tok_role not in [r.value for r in allowed]:
        raise ForbiddenError("Insufficient role")


def get_bearer_from_header(authorization: Optional[str]) -> str:
    """Parse 'Authorization: Bearer <token>' or raise UnauthorizedError."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing bearer token")
    return authorization.split(" ", 1)[1]

def generate_2fa_code(length: Optional[int] = None) -> str:
    """Generate a 2FA code."""
    length = length or settings.TWOFA_CODE_LENGTH
    return "".join(random.choices("0123456789", k=length))