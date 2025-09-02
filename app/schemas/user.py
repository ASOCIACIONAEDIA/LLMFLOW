from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from app.domain.types import Role
from app.core.security import password_meets_policy
from app.core.exceptions import AppError

class UserBase(BaseModel):
    name: str
    email: EmailStr
    is_active: bool
    is_2fa_enabled: bool
    role: Role

class UserResponse(UserBase):
    id: int
    organization_id: int
    unit_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_2fa_enabled: Optional[bool] = None
    role: Optional[Role] = None

    @field_validator('password')
    @classmethod
    def validate_password_policy(cls, password: str | None) -> str | None:
        try:
            password_meets_policy(password)
        except ValueError as e:
            raise AppError(str(e), status_code=422, code="password_policy_violation")
        return password
    
    