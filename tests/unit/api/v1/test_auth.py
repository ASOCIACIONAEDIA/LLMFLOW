"""Test authentication endpoints."""
import pytest
import secrets
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.organization import Organization
from app.models.email_verification import EmailVerification
from app.core.security import hash_token, create_token
from app.domain.types import Role, TokenType
from tests.utils.factories import UserFactory, OrganizationFactory, EmailVerificationFactory


class TestAuthEndpoints:
    """Test authentication endpoints."""

    async def test_get_organizations(self, client: AsyncClient, test_organization: Organization):
        """Test getting available organizations."""
        # Create another organization
        org2 = Organization(name="Another Org", email="another@example.com")
        
        response = await client.get("/api/v1/auth/organizations")
        assert response.status_code == 200
        
        organizations = response.json()
        assert len(organizations) >= 1
        assert any(org["name"] == "Test Organization" for org in organizations)

    async def test_register_with_new_organization(
        self, 
        client: AsyncClient, 
        db_session: AsyncSession,
        mock_email_service
    ):
        """Test user registration with new organization creation."""
        register_data = {
            "name": "John Doe",
            "email": "john@neworg.com",
            "password": "SecurePass123!",
            "organization_name": "New Organization"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["message"] == "User registered successfully. Please check your email to verify your account."
        assert result["requires_verification"] is True
        assert "user_id" in result
        
        # Verify user was created
        user = await db_session.get(User, result["user_id"])
        assert user is not None
        assert user.email == "john@neworg.com"
        assert user.name == "John Doe"
        assert user.role == Role.ADMIN  # Creator becomes admin
        assert user.is_active is False
        assert user.is_verified is False
        
        # Verify organization was created
        assert user.organization is not None
        assert user.organization.name == "New Organization"

    async def test_register_with_existing_organization(
        self, 
        client: AsyncClient, 
        test_organization: Organization,
        db_session: AsyncSession,
        mock_email_service
    ):
        """Test user registration with existing organization."""
        register_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass123!",
            "organization_id": test_organization.id
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["requires_verification"] is True
        
        # Verify user was created with correct organization
        user = await db_session.get(User, result["user_id"])
        assert user.organization_id == test_organization.id
        assert user.role == Role.USER  # Joining existing org as user

    async def test_register_duplicate_email(
        self, 
        client: AsyncClient, 
        test_user: User
    ):
        """Test registration with duplicate email fails."""
        register_data = {
            "name": "Duplicate User",
            "email": test_user.email,
            "password": "SecurePass123!",
            "organization_name": "Some Org"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 409

    async def test_register_invalid_data(self, client: AsyncClient):
        """Test registration with invalid data."""
        # Missing organization info
        register_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 422

    async def test_email_verification(
        self, 
        client: AsyncClient, 
        unverified_user: User,
        db_session: AsyncSession
    ):
        """Test email verification."""
        # Create verification token
        verification = await EmailVerificationFactory.create(
            db_session, 
            user_id=unverified_user.id
        )
        
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification.token}
        )
        assert response.status_code == 200
        assert "verified successfully" in response.json()["message"]
        
        # Verify user is now active and verified
        await db_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        assert unverified_user.is_active is True

    async def test_email_verification_invalid_token(self, client: AsyncClient):
        """Test email verification with invalid token."""
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token"}
        )
        assert response.status_code == 400

    async def test_resend_verification_email(
        self, 
        client: AsyncClient, 
        unverified_user: User,
        mock_email_service
    ):
        """Test resending verification email."""
        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": unverified_user.email}
        )
        assert response.status_code == 200
        assert "verification email sent" in response.json()["message"]

    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert "refresh_token" not in result  # remember_me is False

    async def test_login_with_remember_me(self, client: AsyncClient, test_user: User):
        """Test login with remember me enabled."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": True
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_login_with_2fa(
        self, 
        client: AsyncClient, 
        user_with_2fa: User,
        mock_email_service
    ):
        """Test login with 2FA enabled."""
        login_data = {
            "email": user_with_2fa.email,
            "password": "password123",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 202  # 2FA required
        
        result = response.json()
        assert result["detail"]["requires_2fa"] is True
        assert "user_id" in result["detail"]

    async def test_login_unverified_user(self, client: AsyncClient, unverified_user: User):
        """Test login with unverified user fails."""
        login_data = {
            "email": unverified_user.email,
            "password": "password123",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "verify your email" in response.json()["detail"]

    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: User):
        """Test login with invalid credentials."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_2fa_verification(
        self, 
        client: AsyncClient, 
        user_with_2fa: User,
        db_session: AsyncSession
    ):
        """Test 2FA code verification."""
        from tests.utils.factories import TwoFactorCodeFactory
        
        # Create 2FA code
        code = "123456"
        tfa_code = await TwoFactorCodeFactory.create(
            db_session,
            user_id=user_with_2fa.id,
            code=code
        )
        
        response = await client.post(
            "/api/v1/auth/verify-2fa",
            json={"user_id": user_with_2fa.id, "code": code}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "refresh_token" in result  # 2FA login gets refresh token

    async def test_2fa_verification_invalid_code(
        self, 
        client: AsyncClient, 
        user_with_2fa: User
    ):
        """Test 2FA verification with invalid code."""
        response = await client.post(
            "/api/v1/auth/verify-2fa",
            json={"user_id": user_with_2fa.id, "code": "invalid"}
        )
        assert response.status_code == 400

    async def test_refresh_token(
        self, 
        client: AsyncClient, 
        test_user: User,
        db_session: AsyncSession
    ):
        """Test token refresh."""
        from tests.utils.factories import RefreshTokenFactory
        
        # Create refresh token
        token = secrets.token_urlsafe(32)
        refresh_token = await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token
        )
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "refresh_token" not in result  # New refresh token not issued

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )
        assert response.status_code == 401

    async def test_logout(
        self, 
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test logout (revoke refresh token)."""
        from tests.utils.factories import RefreshTokenFactory
        
        token = secrets.token_urlsafe(32)
        refresh_token = await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token
        )
        
        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": token}
        )
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    async def test_logout_all_devices(
        self, 
        authenticated_client: AsyncClient
    ):
        """Test logout from all devices."""
        response = await authenticated_client.post("/api/v1/auth/logout-all")
        assert response.status_code == 200
        assert "all devices" in response.json()["message"]

    async def test_enable_2fa(
        self, 
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
        mock_email_service
    ):
        """Test enabling 2FA."""
        response = await authenticated_client.post(
            "/api/v1/auth/2fa/enable",
            json={"password": "testpassword123", "enable": True}
        )
        assert response.status_code == 200
        assert "2FA has been enabled" in response.json()["message"]
        
        # Verify 2FA is enabled
        await db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is True

    async def test_disable_2fa(
        self, 
        client: AsyncClient,
        user_with_2fa: User,
        db_session: AsyncSession
    ):
        """Test disabling 2FA."""
        # Create authenticated client for 2FA user
        access_token = create_token(
            subject=user_with_2fa.id,
            role=user_with_2fa.role,
            token_type=TokenType.ACCESS,
            extra_claims={"org_id": user_with_2fa.organization_id}
        )
        client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        response = await client.post(
            "/api/v1/auth/2fa/disable",
            json={"password": "password123", "enable": False}
        )
        assert response.status_code == 200
        assert "2FA has been disabled" in response.json()["message"]
        
        # Verify 2FA is disabled
        await db_session.refresh(user_with_2fa)
        assert user_with_2fa.is_2fa_enabled is False

    async def test_change_password(
        self, 
        authenticated_client: AsyncClient,
        test_user: User,
        mock_email_service
    ):
        """Test password change."""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePass123!"
            }
        )
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    async def test_change_password_invalid_current(
        self, 
        authenticated_client: AsyncClient
    ):
        """Test password change with invalid current password."""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass123!"
            }
        )
        assert response.status_code == 401

    async def test_get_current_user_info(
        self, 
        authenticated_client: AsyncClient,
        test_user: User
    ):
        """Test getting current user info."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        
        result = response.json()
        assert result["email"] == test_user.email
        assert result["name"] == test_user.name
        assert result["role"] == test_user.role.value
        assert result["is_verified"] is True
