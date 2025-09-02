"""Authentication testing utilities."""
from typing import Dict, Any
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User


def create_test_token(user: User) -> str:
    """Create a test JWT token for a user."""
    return create_access_token(subject=str(user.id))


def get_auth_headers(token: str) -> Dict[str, str]:
    """Get authorization headers with token."""
    return {"Authorization": f"Bearer {token}"}


async def login_user(client: AsyncClient, email: str, password: str) -> Dict[str, Any]:
    """Login a user and return token response."""
    login_data = {"email": email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()


def make_authenticated_client(client: AsyncClient, user: User) -> AsyncClient:
    """Add authentication headers to client."""
    token = create_test_token(user)
    client.headers.update(get_auth_headers(token))
    return client