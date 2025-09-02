"""Data factories for creating test objects."""
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.job import Job
from app.models.product import Product
from app.models.review import Review
from app.models.organization import Organization
from app.core.security import hash_password
from app.domain.types import JobType, JobStatus, Role


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        email: str = "test@example.com",
        username: str = "testuser",
        password: str = "testpassword123",
        role: Role = Role.USER,
        is_active: bool = True,
        is_verified: bool = True,
        organization_id: int = 1,
        **kwargs
    ) -> User:
        """Create a test user."""
        user_data = {
            "email": email,
            "username": username,
            "hashed_password": hash_password(password),
            "full_name": kwargs.get("full_name", "Test User"),
            "role": role,
            "is_active": is_active,
            "is_verified": is_verified,
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
        description: str = "A test organization",
        is_active: bool = True,
        **kwargs
    ) -> Organization:
        """Create a test organization."""
        org_data = {
            "name": name,
            "description": description,
            "is_active": is_active,
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


class ProductFactory:
    """Factory for creating test products."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        name: str = "Test Product",
        description: str = "A test product",
        **kwargs
    ) -> Product:
        """Create a test product."""
        product_data = {
            "name": name,
            "description": description,
            **kwargs
        }
        
        product = Product(**product_data)
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


class ReviewFactory:
    """Factory for creating test reviews."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        product_id: int,
        rating: float = 4.5,
        content: str = "This is a test review",
        **kwargs
    ) -> Review:
        """Create a test review."""
        review_data = {
            "product_id": product_id,
            "rating": rating,
            "content": content,
            **kwargs
        }
        
        review = Review(**review_data)
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review


class PlaceFactory:
    """Factory for creating test discovered places."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: int,
        job_id: str,
        name: str = "Test Place",
        google_place_id: str = "ChIJTest123456789",
        full_address: str = "123 Test Street, Test City, Test Country",
        postal_code: str = "12345",
        country: str = "Test Country",
        typical_time_spent: int = 60,
        rating: float = 4.0,
        num_reviews: int = 100,
        created_by: Optional[int] = None,
        extra: Optional[dict] = None,
        **kwargs
    ):
        """Create a test discovered place."""
        if extra is None:
            extra = {
                "category": "Test Category",
                "phone": "+1 123 456 7890"
            }
        
        place_data = {
            "organization_id": organization_id,
            "job_id": job_id,
            "name": name,
            "google_place_id": google_place_id,
            "full_address": full_address,
            "postal_code": postal_code,
            "country": country,
            "typical_time_spent": typical_time_spent,
            "rating": rating,
            "num_reviews": num_reviews,
            "created_by": created_by,
            "extra": extra,
            **kwargs
        }
        
        from app.models.places import DiscoveredPlaces
        place = DiscoveredPlaces(**place_data)
        session.add(place)
        await session.commit()
        await session.refresh(place)
        return place