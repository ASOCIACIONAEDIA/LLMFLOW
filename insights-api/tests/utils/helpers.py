"""Test helper functions."""
from typing import Dict, Any, Optional
from httpx import Response, AsyncClient

from app.core.security import create_token
from app.domain.types import Role, TokenType
from app.models.user import User


def assert_response(
    response: Response,
    expected_status: int,
    expected_keys: Optional[list] = None,
    expected_data: Optional[Dict[str, Any]] = None
):
    """Assert API response structure and data."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    
    if expected_keys:
        response_data = response.json()
        for key in expected_keys:
            assert key in response_data, f"Expected key '{key}' not found in response"
    
    if expected_data:
        response_data = response.json()
        for key, value in expected_data.items():
            assert response_data.get(key) == value, f"Expected {key}={value}, got {response_data.get(key)}"


def create_auth_headers(user: User) -> Dict[str, str]:
    """Create authorization headers for user."""
    access_token = create_token(
        subject=user.id,
        role=user.role,
        token_type=TokenType.ACCESS,
        extra_claims={"org_id": user.organization_id}
    )
    return {"Authorization": f"Bearer {access_token}"}


async def login_user(client: AsyncClient, email: str, password: str) -> Dict[str, Any]:
    """Login user and return response."""
    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    return response.json()
