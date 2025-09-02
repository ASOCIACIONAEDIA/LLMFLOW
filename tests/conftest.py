import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.db.redis import get_redis_client
from app.api.deps import get_current_active_user
from app.models.user import User
from app.core.security import create_access_token


# Test database URL - using SQLite for fast tests, but you can use PostgreSQL if preferred
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_insights"
)

# Test Redis settings
TEST_REDIS_SETTINGS = RedisSettings(
    host="localhost",
    port=6379,
    database=1  # Use a different database for tests
)

# Override settings for testing
@pytest.fixture(scope="session", autouse=True)
def override_settings():
    """Override application settings for testing."""
    settings.DB_URL = TEST_DATABASE_URL
    settings.REDIS_URL = "redis://localhost:6379/1"  # Test database
    settings.ARQ_REDIS_URL = "redis://localhost:6379/1"
    settings.JWT_SECRET_KEY = "test-secret-key"
    settings.ENV = "test"
    settings.DEBUG = True


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=True  # Set to False to reduce test output
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_redis():
    """Create test Redis client."""
    client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    # Clear the test database
    await client.flushdb()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest_asyncio.fixture
async def arq_pool():
    """Create ARQ Redis pool for testing background jobs."""
    pool = await create_pool(TEST_REDIS_SETTINGS)
    yield pool
    await pool.aclose()


@pytest_asyncio.fixture
async def client(db_session, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database and Redis override."""
    
    # Override dependencies
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Create authenticated HTTP client."""
    access_token = create_access_token(subject=str(test_user.id))
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


# Test data fixtures
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from app.models.user import User
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        role="USER",
        is_active=True,
        is_verified=True,
        organization_id=1
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    from app.models.user import User
    from app.core.security import hash_password
    
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        role="ADMIN",
        is_active=True,
        is_verified=True,
        organization_id=1
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession):
    """Create a test organization."""
    from app.models.organization import Organization
    
    org = Organization(
        name="Test Organization",
        description="A test organization",
        is_active=True
    )
    
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_job(db_session: AsyncSession, test_user: User):
    """Create a test job."""
    from app.models.job import Job
    from app.domain.types import JobType, JobStatus
    
    job = Job(
        user_id=test_user.id,
        organization_id=test_user.organization_id,
        job_type=JobType.REVIEW_SCRAPING,
        status=JobStatus.PENDING,
        sources_data=[{"name": "test_source", "url": "https://example.com"}]
    )
    
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


# Mock fixtures for external services
@pytest.fixture
def mock_external_api(monkeypatch):
    """Mock external API calls."""
    async def mock_api_call(*args, **kwargs):
        return {"status": "success", "data": "mocked"}
    
    # Add monkeypatch logic here for specific external APIs
    return mock_api_call


# Event loop fixture for proper async test handling
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Utility fixtures
@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"


# Test data cleanup
@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """Automatically clean up test data after each test."""
    yield
    await db_session.rollback()