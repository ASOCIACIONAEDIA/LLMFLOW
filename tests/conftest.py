"""Test configuration and fixtures - Simple function-scoped approach."""
import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.db.redis import get_redis_client
from app.models.user import User
from app.models.organization import Organization
from app.core.security import create_token, hash_password
from app.domain.types import Role, TokenType


def _detect_docker_environment():
    """Detect if we're running inside a Docker container."""
    return (
        os.path.exists('/.dockerenv') or
        os.getenv('ENVIRONMENT') in ['development', 'test'] or
        os.getenv('DOCKER_ENV') == 'true'
    )

def _get_test_database_url():
    """Get test database URL based on environment."""
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    
    if _detect_docker_environment():
        # Use the same database as the main app
        return "postgresql+asyncpg://insights_user:insights_pass@postgres:5432/insights"
    else:
        return "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_insights"

def _get_test_redis_settings():
    """Get Redis settings based on environment."""
    if _detect_docker_environment():
        return RedisSettings(host="redis", port=6379, database=1)
    else:
        return RedisSettings(host="localhost", port=6379, database=1)

TEST_DATABASE_URL = _get_test_database_url()
TEST_REDIS_SETTINGS = _get_test_redis_settings()

@pytest.fixture(scope="session", autouse=True)
def override_settings():
    """Override settings for testing."""
    settings.DB_URL = TEST_DATABASE_URL
    settings.REDIS_URL = f"redis://{TEST_REDIS_SETTINGS.host}:{TEST_REDIS_SETTINGS.port}/{TEST_REDIS_SETTINGS.database}"
    settings.DEBUG = True
    settings.SMTP_HOST = None

# Fix asyncio loop issues by using session scope for engine and proper cleanup
@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a clean test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    async with async_session() as session:
        yield session
    
    # Clean up tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def test_redis():
    """Create test Redis client."""
    try:
        if _detect_docker_environment():
            redis_url = "redis://redis:6379/1"
        else:
            redis_url = "redis://localhost:6379/1"
            
        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        
        # Clean Redis before each test
        await client.flushdb()
        
        yield client
        await client.aclose()
    except Exception:
        # Mock Redis if connection fails
        import unittest.mock
        mock_redis = unittest.mock.AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        mock_redis.aclose.return_value = None
        yield mock_redis

@pytest_asyncio.fixture
async def client(db_session, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create test organization."""
    from tests.utils.factories import OrganizationFactory
    return await OrganizationFactory.create(db_session)

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create test user."""
    from tests.utils.factories import UserFactory
    return await UserFactory.create(
        db_session,
        email="test@example.com",
        organization_id=test_org.id
    )

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create admin user."""
    from tests.utils.factories import UserFactory
    return await UserFactory.create(
        db_session,
        email="admin@example.com",
        role=Role.ADMIN,
        organization_id=test_org.id
    )

@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Create authenticated HTTP client."""
    access_token = create_token(
        subject=test_user.id,
        role=test_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": test_user.organization_id}
    )
    
    # Return a new client with auth headers, but don't mess with dependency overrides
    return AsyncClient(
        transport=client._transport,
        base_url=client.base_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )

@pytest_asyncio.fixture
async def admin_authenticated_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    """Create admin authenticated HTTP client."""
    access_token = create_token(
        subject=admin_user.id,
        role=admin_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": admin_user.organization_id}
    )
    
    return AsyncClient(
        transport=client._transport,
        base_url=client.base_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )

@pytest_asyncio.fixture  
async def corp_admin_authenticated_client(client: AsyncClient, corporate_admin_user: User) -> AsyncClient:
    """Create corporate admin authenticated HTTP client."""
    access_token = create_token(
        subject=corporate_admin_user.id,
        role=corporate_admin_user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": corporate_admin_user.organization_id}
    )
    
    return AsyncClient(
        transport=client._transport,
        base_url=client.base_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )

@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create unverified user."""
    from tests.utils.factories import UserFactory
    return await UserFactory.create(
        db_session,
        email="unverified@example.com",
        is_verified=False,
        is_active=False,
        organization_id=test_org.id
    )

@pytest_asyncio.fixture
async def user_with_2fa(db_session: AsyncSession, test_org: Organization) -> User:
    """Create user with 2FA enabled."""
    from tests.utils.factories import UserFactory
    return await UserFactory.create(
        db_session,
        email="2fa@example.com",
        is_2fa_enabled=True,
        organization_id=test_org.id
    )

@pytest_asyncio.fixture
async def corporate_admin_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create corporate admin user."""
    from tests.utils.factories import UserFactory
    return await UserFactory.create(
        db_session,
        email="corporate_admin@example.com",
        role=Role.CORPORATE_ADMIN,
        organization_id=test_org.id
    )

# Add alias for backward compatibility
@pytest_asyncio.fixture
async def test_organization(test_org: Organization) -> Organization:
    """Alias for test_org for backward compatibility."""
    return test_org

@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service."""
    emails_sent = []
    
    async def mock_send_email(*args, **kwargs):
        # Handle different call signatures
        if len(args) >= 3:
            recipient, subject, content = args[0], args[1], args[2]
        else:
            recipient = kwargs.get('recipient', kwargs.get('to', 'test@example.com'))
            subject = kwargs.get('subject', 'Test Subject')
            content = kwargs.get('content', kwargs.get('body', 'Test Content'))
        
        emails_sent.append({
            "recipient": recipient,
            "subject": subject,
            "content": content
        })
    
    monkeypatch.setattr("app.services.mailer.mailer_service._send_email", mock_send_email)
    return emails_sent