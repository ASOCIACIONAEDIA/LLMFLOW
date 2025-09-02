"""User test data fixtures."""
from typing import Dict, Any, List

# Sample user data for testing
SAMPLE_USERS = [
    {
        "email": "user1@example.com",
        "username": "user1",
        "full_name": "User One",
        "role": "USER",
        "is_active": True,
        "is_verified": True,
        "organization_id": 1
    },
    {
        "email": "user2@example.com",
        "username": "user2",
        "full_name": "User Two",
        "role": "USER",
        "is_active": True,
        "is_verified": False,
        "organization_id": 1
    },
    {
        "email": "admin@example.com",
        "username": "admin",
        "full_name": "Admin User",
        "role": "ADMIN",
        "is_active": True,
        "is_verified": True,
        "organization_id": 1
    }
]

# User creation data for API tests
USER_CREATE_DATA = {
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "securepassword123",
    "full_name": "New User",
    "role": "USER"
}

# User update data
USER_UPDATE_DATA = {
    "full_name": "Updated User Name",
    "is_active": False
}

# Invalid user data for testing validation
INVALID_USER_DATA = [
    {
        "email": "invalid-email",
        "username": "test",
        "password": "123"
    },
    {
        "email": "",
        "username": "",
        "password": ""
    },
    {
        "username": "test",
        "password": "password123"
        # Missing email
    }
]