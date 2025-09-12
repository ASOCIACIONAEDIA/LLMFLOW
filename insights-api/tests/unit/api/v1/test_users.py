"""Test user management endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from app.domain.types import Role
from tests.utils.factories import UserFactory, OrganizationFactory


class TestUserEndpoints:
    """Test user management endpoints."""

    async def test_get_current_user_profile(
        self, 
        authenticated_client: AsyncClient,
        test_user: User
    ):
        """Test getting current user's profile."""
        response = await authenticated_client.get("/api/v1/users/me")
        assert response.status_code == 200
        
        result = response.json()
        assert result["email"] == test_user.email
        assert result["name"] == test_user.name
        assert result["organization_name"] == test_user.organization.name

    async def test_update_current_user_profile(
        self, 
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test updating current user's profile."""
        update_data = {
            "name": "Updated Name",
            "email": "updated@example.com"
        }
        
        response = await authenticated_client.put("/api/v1/users/me", json=update_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["name"] == "Updated Name"
        assert result["email"] == "updated@example.com"

    async def test_list_users_as_admin(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        admin_user: User,
        db_session: AsyncSession
    ):
        """Test listing users as admin."""
        # Create additional users
        await UserFactory.create(
            db_session,
            email="user2@example.com",
            name="User Two",
            organization_id=test_user.organization_id
        )
        
        response = await admin_authenticated_client.get("/api/v1/users/")
        assert response.status_code == 200
        
        result = response.json()
        assert len(result) >= 3  # admin, test_user, user2
        assert any(user["email"] == test_user.email for user in result)

    async def test_list_users_with_filters(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test listing users with filters."""
        # Create inactive user
        await UserFactory.create(
            db_session,
            email="inactive@example.com",
            name="Inactive User",
            is_active=False,
            organization_id=test_user.organization_id
        )
        
        # Filter by active status
        response = await admin_authenticated_client.get(
            "/api/v1/users/?is_active=true"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert all(user["is_active"] for user in result)

    async def test_list_users_as_regular_user_forbidden(
        self, 
        authenticated_client: AsyncClient
    ):
        """Test that regular users cannot list users."""
        response = await authenticated_client.get("/api/v1/users/")
        assert response.status_code == 403

    async def test_list_users_as_corporate_admin(
        self, 
        corp_admin_authenticated_client: AsyncClient,
        corporate_admin_user: User,
        db_session: AsyncSession
    ):
        """Test corporate admin can only see users in their org."""
        # Create user in different organization
        other_org = await OrganizationFactory.create(
            db_session, 
            name="Other Org"
        )
        await UserFactory.create(
            db_session,
            email="other@example.com",
            organization_id=other_org.id
        )
        
        response = await corp_admin_authenticated_client.get("/api/v1/users/")
        assert response.status_code == 200
        
        result = response.json()
        # Should only see users from their organization
        assert all(
            user["organization_id"] == corporate_admin_user.organization_id 
            for user in result
        )

    async def test_get_user_by_id(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User
    ):
        """Test getting user by ID."""
        response = await admin_authenticated_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        
        result = response.json()
        assert result["email"] == test_user.email
        assert result["name"] == test_user.name

    async def test_get_user_by_id_as_self(
        self, 
        authenticated_client: AsyncClient,
        test_user: User
    ):
        """Test user can get their own profile by ID."""
        response = await authenticated_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200

    async def test_get_other_user_as_regular_user_forbidden(
        self, 
        authenticated_client: AsyncClient,
        admin_user: User
    ):
        """Test regular user cannot get other user's profile."""
        response = await authenticated_client.get(f"/api/v1/users/{admin_user.id}")
        assert response.status_code == 403

    async def test_update_user_as_admin(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test updating user as admin."""
        update_data = {
            "name": "Admin Updated Name",
            "is_active": False
        }
        
        response = await admin_authenticated_client.put(
            f"/api/v1/users/{test_user.id}", 
            json=update_data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["name"] == "Admin Updated Name"
        assert result["is_active"] is False

    async def test_update_user_as_regular_user_forbidden(
        self, 
        authenticated_client: AsyncClient,
        admin_user: User
    ):
        """Test regular user cannot update other users."""
        response = await authenticated_client.put(
            f"/api/v1/users/{admin_user.id}",
            json={"name": "Unauthorized Update"}
        )
        assert response.status_code == 403

    async def test_create_user_as_admin(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test creating user as admin."""
        user_data = {
            "name": "New Admin User",
            "email": "newadmin@example.com",
            "password": "SecurePass123!",  # Meets policy: 8+ chars, upper, lower, special
            "role": "ADMIN",
            "organization_id": test_user.organization_id
        }
        
        response = await admin_authenticated_client.post("/api/v1/users/", json=user_data)
        
        # Debug: Print response if it fails
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")
        
        assert response.status_code == 201
        
        result = response.json()
        assert result["email"] == "newadmin@example.com"
        assert result["name"] == "New Admin User"

    async def test_create_user_as_regular_user_forbidden(
        self, 
        authenticated_client: AsyncClient
    ):
        """Test regular user cannot create users."""
        user_data = {
            "name": "Unauthorized User",
            "email": "unauthorized@example.com",
            "password": "password123",
            "role": "USER"
        }
        
        response = await authenticated_client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 403

    async def test_create_user_as_corporate_admin(
        self, 
        corp_admin_authenticated_client: AsyncClient,
        corporate_admin_user: User
    ):
        """Test corporate admin creates user in their org."""
        user_data = {
            "name": "Corp User",
            "email": "corpuser@example.com",
            "password": "SecurePass123!",
            "role": "USER",
            "organization_id": 999  # This should be ignored
        }
        
        response = await corp_admin_authenticated_client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 201
        
        result = response.json()
        # Should be created in corporate admin's organization
        assert result["organization_id"] == corporate_admin_user.organization_id

    async def test_toggle_user_status(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test toggling user status."""
        original_status = test_user.is_active
        
        response = await admin_authenticated_client.post(
            f"/api/v1/users/{test_user.id}/toggle-status"
        )
        assert response.status_code == 200
        
        await db_session.refresh(test_user)
        assert test_user.is_active != original_status

    async def test_toggle_own_status_forbidden(
        self, 
        admin_authenticated_client: AsyncClient,
        admin_user: User
    ):
        """Test user cannot toggle their own status."""
        response = await admin_authenticated_client.post(
            f"/api/v1/users/{admin_user.id}/toggle-status"
        )
        assert response.status_code == 400
        assert "Cannot change your own status" in response.json()["detail"]

    async def test_delete_user(
        self, 
        admin_authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test soft deleting user."""
        response = await admin_authenticated_client.delete(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        
        # Verify user is deactivated (soft delete)
        await db_session.refresh(test_user)
        assert test_user.is_active is False

    async def test_delete_own_account_forbidden(
        self, 
        admin_authenticated_client: AsyncClient,
        admin_user: User
    ):
        """Test user cannot delete their own account."""
        response = await admin_authenticated_client.delete(f"/api/v1/users/{admin_user.id}")
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    async def test_get_organization_users(
        self, 
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test getting users by organization."""
        # Create more users in the same organization
        await UserFactory.create(
            db_session,
            email="orguser@example.com",
            organization_id=test_user.organization_id
        )
        
        response = await authenticated_client.get(
            f"/api/v1/users/organization/{test_user.organization_id}"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert len(result) >= 2  # test_user + orguser
        assert all(
            user["organization_id"] == test_user.organization_id 
            for user in result
        )

    async def test_get_other_organization_users_forbidden(
        self, 
        authenticated_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test user cannot get users from other organizations."""
        other_org = await OrganizationFactory.create(
            db_session, 
            name="Other Organization"
        )
        
        response = await authenticated_client.get(
            f"/api/v1/users/organization/{other_org.id}"
        )
        assert response.status_code == 403
