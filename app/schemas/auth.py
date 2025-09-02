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
    token_type: str = "Bearer"

class TokenPayoload(BaseModel):
    sub: Optional[int] = None

class TwoFactorCodeRequest(BaseModel):
    user_id: int
    code: str