"""Custom assertion helpers for tests."""
from typing import Dict, Any, Optional
from httpx import Response


def assert_api_response(
    response: Response,
    expected_status: int,
    expected_keys: Optional[list] = None,
    expected_data: Optional[Dict[str, Any]] = None
):
    """Assert API response has expected structure and data."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    
    if expected_keys:
        response_data = response.json()
        for key in expected_keys:
            assert key in response_data, f"Expected key '{key}' not found in response"
    
    if expected_data:
        response_data = response.json()
        for key, value in expected_data.items():
            assert response_data.get(key) == value, f"Expected {key}={value}, got {response_data.get(key)}"


def assert_user_response(response_data: Dict[str, Any], expected_user_data: Dict[str, Any]):
    """Assert user response data matches expected format."""
    required_fields = ["id", "email", "username", "full_name", "role", "is_active"]
    
    for field in required_fields:
        assert field in response_data, f"Required field '{field}' missing from user response"
    
    # Assert password is not included in response
    assert "password" not in response_data
    assert "hashed_password" not in response_data
    
    # Assert specific expected data
    for key, value in expected_user_data.items():
        if key in response_data:
            assert response_data[key] == value, f"Expected {key}={value}, got {response_data[key]}"


def assert_job_response(response_data: Dict[str, Any]):
    """Assert job response data has correct format."""
    required_fields = ["id", "user_id", "organization_id", "job_type", "status", "created_at"]
    
    for field in required_fields:
        assert field in response_data, f"Required field '{field}' missing from job response"


def assert_pagination_response(response_data: Dict[str, Any]):
    """Assert paginated response has correct format."""
    required_fields = ["items", "total", "page", "size", "pages"]
    
    for field in required_fields:
        assert field in response_data, f"Required field '{field}' missing from pagination response"
    
    assert isinstance(response_data["items"], list), "Items should be a list"
    assert isinstance(response_data["total"], int), "Total should be an integer"
    assert isinstance(response_data["page"], int), "Page should be an integer"
    assert isinstance(response_data["size"], int), "Size should be an integer"
    assert isinstance(response_data["pages"], int), "Pages should be an integer"