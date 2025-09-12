"""Integration tests for complete authentication flow."""
import pytest
import secrets
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from tests.utils.factories import EmailVerificationFactory


class TestCompleteAuthFlow:
    """Test complete authentication flows."""

    async def test_complete_registration_and_login_flow(
        self, 
        client: AsyncClient,
        db_session: AsyncSession,
        mock_email_service
    ):
        """Test complete flow: registration → email verification → login."""
        
        # Step 1: Register user
        register_data = {
            "name": "Integration Test User",
            "email": "integration@example.com",
            "password": "SecurePass123!",
            "organization_name": "Integration Test Org"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        
        result = response.json()
        user_id = result["user_id"]
        
        # Step 2: Try login before verification (should fail)
        login_data = {
            "email": "integration@example.com",
            "password": "SecurePass123!",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "verify your email" in response.json()["detail"]
        
        # Step 3: Verify email
        user = await db_session.get(User, user_id)
        verification = await EmailVerificationFactory.create(
            db_session,
            user_id=user.id
        )
        
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification.token}
        )
        assert response.status_code == 200
        
        # Step 4: Login after verification
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        assert "access_token" in tokens
        
        # Step 5: Use access token to get user info
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        user_info = response.json()
        assert user_info["email"] == "integration@example.com"
        assert user_info["name"] == "Integration Test User"
        assert user_info["is_verified"] is True

    async def test_2fa_enabled_login_flow(
        self, 
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
        mock_email_service
    ):
        """Test login flow with 2FA enabled."""
        
        # Step 1: Enable 2FA
        # First login normally
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Enable 2FA
        response = await client.post(
            "/api/v1/auth/2fa/enable",
            json={"password": "testpassword123", "enable": True},
            headers=headers
        )
        assert response.status_code == 200
        
        # Step 2: Login with 2FA (should require 2FA code)
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 202
        
        result = response.json()
        assert result["detail"]["requires_2fa"] is True
        user_id = result["detail"]["user_id"]
        
        # Step 3: Create and verify 2FA code
        from tests.utils.factories import TwoFactorCodeFactory
        
        code = "123456"
        await TwoFactorCodeFactory.create(
            db_session,
            user_id=user_id,
            code=code
        )
        
        response = await client.post(
            "/api/v1/auth/verify-2fa",
            json={"user_id": user_id, "code": code}
        )
        assert response.status_code == 200
        
        final_tokens = response.json()
        assert "access_token" in final_tokens
        assert "refresh_token" in final_tokens

    async def test_remember_me_and_refresh_flow(
        self, 
        client: AsyncClient,
        test_user: User
    ):
        """Test remember me and token refresh flow."""
        
        # Step 1: Login with remember me
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": True
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Step 2: Use access token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Step 3: Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        
        new_tokens = response.json()
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != access_token  # Should be different
        
        # Step 4: Use new access token
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Step 5: Logout (revoke refresh token)
        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        
        # Step 6: Try to use refresh token again (should fail)
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401

    async def test_password_change_invalidates_sessions(
        self, 
        client: AsyncClient,
        test_user: User,
        mock_email_service
    ):
        """Test that password change invalidates all sessions."""
        
        # Step 1: Login and get tokens
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": True
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        refresh_token = tokens["refresh_token"]
        
        # Step 2: Change password
        response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePass123!"
            },
            headers=headers
        )
        assert response.status_code == 200
        
        # Step 3: Try to use old refresh token (should fail)
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401
        
        # Step 4: Login with new password
        new_login_data = {
            "email": test_user.email,
            "password": "NewSecurePass123!",
            "remember_me": False
        }
        
        response = await client.post("/api/v1/auth/login", json=new_login_data)
        assert response.status_code == 200
