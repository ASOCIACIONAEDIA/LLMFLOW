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
from app.api.deps import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.email_verification import EmailVerification
from app.core.security import create_token, hash_password
from app.domain.types import Role, TokenType


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
    settings.JWT_SECRET_KEY = "test-secret-key-for-user-management"
    settings.ENV = "test"
    settings.DEBUG = True
    settings.SMTP_HOST = None  # Disable email sending in tests


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
        echo=False  # Set to True for debugging
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
        # Start a transaction that will be rolled back after the test
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()


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


# Test data fixtures
@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        email="org@example.com"
    )
    
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a test user."""
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        role=Role.USER,
        is_active=True,
        is_verified=True,
        organization_id=test_organization.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a test admin user."""
    user = User(
        name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        role=Role.ADMIN,
        is_active=True,
        is_verified=True,
        organization_id=test_organization.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def corporate_admin_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a test corporate admin user."""
    user = User(
        name="Corporate Admin",
        email="corp.admin@example.com",
        hashed_password=hash_password("corppassword123"),
        role=Role.CORPORATE_ADMIN,
        is_active=True,
        is_verified=True,
        organization_id=test_organization.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create an unverified test user."""
    user = User(
        name="Unverified User",
        email="unverified@example.com",
        hashed_password=hash_password("password123"),
        role=Role.USER,
        is_active=False,
        is_verified=False,
        organization_id=test_organization.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_2fa(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a user with 2FA enabled."""
    user = User(
        name="2FA User",
        email="2fa@example.com",
        hashed_password=hash_password("password123"),
        role=Role.USER,
        is_active=True,
        is_verified=True,
        is_2fa_enabled=True,
        organization_id=test_organization.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Create authenticated HTTP client."""
    access_token = create_token(
        subject=test_user.id,
        role=test_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": test_user.organization_id}
    )
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


@pytest_asyncio.fixture
async def admin_authenticated_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    """Create authenticated HTTP client for admin user."""
    access_token = create_token(
        subject=admin_user.id,
        role=admin_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": admin_user.organization_id}
    )
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


@pytest_asyncio.fixture
async def corp_admin_authenticated_client(client: AsyncClient, corporate_admin_user: User) -> AsyncClient:
    """Create authenticated HTTP client for corporate admin user."""
    access_token = create_token(
        subject=corporate_admin_user.id,
        role=corporate_admin_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": corporate_admin_user.organization_id}
    )
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


# Mock fixtures for external services
@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service for testing."""
    emails_sent = []
    
    async def mock_send_email(recipient, subject, content):
        emails_sent.append({
            "recipient": recipient,
            "subject": subject,
            "content": content
        })
    
    monkeypatch.setattr("app.services.mailer.mailer_service._send_email", mock_send_email)
    return emails_sent


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