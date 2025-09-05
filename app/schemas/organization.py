from pydantic import BaseModel, Field
from typing import Optional
from pydantic import EmailStr

class OrganizationBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: Optional[EmailStr] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: int

    class Config:
        from_attributes = True

class OrganizationListResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True