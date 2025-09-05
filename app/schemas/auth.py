from dataclasses import field
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.core.security import password_meets_policy
from app.core.exceptions import AppError

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8) # We perform a basic validation here, more detailed below
    organization_id: Optional[int] = None
    organization_name: Optional[str] = Field(None, min_length=3, max_length=255)

    @field_validator('password')
    @classmethod
    def validate_password_policy(cls, password: str) -> str:
        try:
            password_meets_policy(password)
        except ValueError as e:
            raise AppError(str(e), status_code=422, code="password_policy_violation") # We raise our coool custom error :D
        return password

class TokenResponse(BaseModel):
    access_token: str
    refresh_tokem: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 3600

class TokenPayload(BaseModel):
    sub: Optional[int] = None

class TwoFactorCodeRequest(BaseModel):
    user_id: int
    code: str

class EmailVerificationRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TwoFactorSetupRequest(BaseModel):
    password: str  # Current password for verification
    enable: bool = True

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_policy(cls, password: str) -> str:
        try:
            password_meets_policy(password)
        except ValueError as e:
            raise AppError(str(e), status_code=422, code="password_policy_violation")
        return password

class UserRegistrationResponse(BaseModel):
    message: str
    user_id: int
    requires_verification: bool = True