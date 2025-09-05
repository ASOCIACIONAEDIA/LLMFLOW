from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.domain.types import Role
from app.core.security import password_meets_policy
from app.core.exceptions import AppError

class UserBase(BaseModel): # IDK If i like this or not
    name: str = Field(min_length=3, max_length=255)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    organization_id: Optional[int] = None
    role: Role = Role.USER

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_2fa_enabled: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    organization_id: Optional[int] = None
    role: Role
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserProfileResponse(UserResponse):
    organization_name: Optional[str] = None
    unit_name: Optional[str] = None

class UserListResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    