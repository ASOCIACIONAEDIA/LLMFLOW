"""Test authentication services."""
import pytest
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_services import AuthService
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.core.exceptions import UnauthorizedError, NotFoundError, AppError
from app.core.security import hash_password, verify_password, hash_token
from tests.utils.factories import UserFactory, TwoFactorCodeFactory, RefreshTokenFactory, EmailVerificationFactory


class TestAuthService:
    """Test authentication service."""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    @pytest.fixture
    def user_repo(self, db_session):
        return UserRepository(db_session)

    async def test_login_user_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test successful user login."""
        user_id, is_2fa_enabled, remember_me = await auth_service.login_user(
            user_repo, 
            test_user.email, 
            "testpassword123", 
            remember_me=True
        )
        
        assert user_id == test_user.id
        assert is_2fa_enabled == test_user.is_2fa_enabled
        assert remember_me is True

    async def test_login_user_invalid_email(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository
    ):
        """Test login with invalid email."""
        with pytest.raises(UnauthorizedError) as exc_info:
            await auth_service.login_user(
                user_repo, 
                "nonexistent@example.com", 
                "password123"
            )
        assert "Invalid credentials" in str(exc_info.value)

    async def test_login_user_invalid_password(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test login with invalid password."""
        with pytest.raises(UnauthorizedError) as exc_info:
            await auth_service.login_user(
                user_repo, 
                test_user.email, 
                "wrongpassword"
            )
        assert "Invalid credentials" in str(exc_info.value)

    async def test_login_user_inactive(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        db_session: AsyncSession
    ):
        """Test login with inactive user."""
        inactive_user = await UserFactory.create(
            db_session,
            email="inactive@example.com",
            is_active=False,
            is_verified=True
        )
        
        with pytest.raises(UnauthorizedError) as exc_info:
            await auth_service.login_user(
                user_repo, 
                inactive_user.email, 
                "testpassword123"
            )
        assert "inactive" in str(exc_info.value).lower()

    async def test_login_user_unverified(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        unverified_user: User
    ):
        """Test login with unverified user."""
        with pytest.raises(UnauthorizedError) as exc_info:
            await auth_service.login_user(
                user_repo, 
                unverified_user.email, 
                "password123"
            )
        assert "verify your email" in str(exc_info.value).lower()

    async def test_verify_2fa_code_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        user_with_2fa: User,
        db_session: AsyncSession
    ):
        """Test successful 2FA verification."""
        code = "123456"
        await TwoFactorCodeFactory.create(
            db_session,
            user_id=user_with_2fa.id,
            code=code
        )
        
        result = await auth_service.verify_2fa_code(user_repo, user_with_2fa.id, code)
        assert result is True

    async def test_verify_2fa_code_invalid(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        user_with_2fa: User
    ):
        """Test 2FA verification with invalid code."""
        result = await auth_service.verify_2fa_code(user_repo, user_with_2fa.id, "wrong")
        assert result is False

    async def test_issue_tokens_without_remember_me(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test token issuance without remember me."""
        tokens = await auth_service.issue_tokens(user_repo, test_user.id, remember_me=False)
        
        assert "access_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert "refresh_token" not in tokens

    async def test_issue_tokens_with_remember_me(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test token issuance with remember me."""
        tokens = await auth_service.issue_tokens(user_repo, test_user.id, remember_me=True)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens

    async def test_refresh_access_token_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test successful token refresh."""
        token = secrets.token_urlsafe(32)
        await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token
        )
        
        new_tokens = await auth_service.refresh_access_token(user_repo, token)
        
        assert "access_token" in new_tokens
        assert "refresh_token" not in new_tokens

    async def test_refresh_access_token_invalid(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository
    ):
        """Test token refresh with invalid token."""
        with pytest.raises(UnauthorizedError):
            await auth_service.refresh_access_token(user_repo, "invalid-token")

    async def test_verify_email_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        unverified_user: User,
        db_session: AsyncSession
    ):
        """Test successful email verification."""
        verification = await EmailVerificationFactory.create(
            db_session,
            user_id=unverified_user.id
        )
        
        result = await auth_service.verify_email(user_repo, verification.token)
        assert result is True
        
        # Verify user is now verified and active
        await db_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        assert unverified_user.is_active is True

    async def test_verify_email_invalid_token(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository
    ):
        """Test email verification with invalid token."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.verify_email(user_repo, "invalid-token")
        assert "Invalid or expired" in str(exc_info.value)

    async def test_enable_2fa_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test enabling 2FA."""
        await auth_service.enable_2fa(user_repo, test_user.id, "testpassword123")
        
        await db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is True

    async def test_enable_2fa_wrong_password(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test enabling 2FA with wrong password."""
        with pytest.raises(UnauthorizedError):
            await auth_service.enable_2fa(user_repo, test_user.id, "wrongpassword")

    async def test_enable_2fa_already_enabled(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        user_with_2fa: User
    ):
        """Test enabling 2FA when already enabled."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.enable_2fa(user_repo, user_with_2fa.id, "password123")
        assert "already enabled" in str(exc_info.value)

    async def test_disable_2fa_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        user_with_2fa: User,
        db_session: AsyncSession
    ):
        """Test disabling 2FA."""
        await auth_service.disable_2fa(user_repo, user_with_2fa.id, "password123")
        
        await db_session.refresh(user_with_2fa)
        assert user_with_2fa.is_2fa_enabled is False

    async def test_change_password_success(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test successful password change."""
        new_password = "NewSecurePassword123!"
        
        await auth_service.change_password(
            user_repo, 
            test_user.id, 
            "testpassword123", 
            new_password
        )
        
        # Verify password was changed
        await db_session.refresh(test_user)
        assert verify_password(new_password, test_user.hashed_password)

    async def test_change_password_wrong_current(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User
    ):
        """Test password change with wrong current password."""
        with pytest.raises(UnauthorizedError):
            await auth_service.change_password(
                user_repo, 
                test_user.id, 
                "wrongpassword", 
                "NewPassword123!"
            )

    async def test_revoke_refresh_token(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test revoking refresh token."""
        token = secrets.token_urlsafe(32)
        refresh_token = await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token
        )
        
        await auth_service.revoke_refresh_token(user_repo, token)
        
        # Verify token is revoked
        await db_session.refresh(refresh_token)
        assert refresh_token.revoked_at is not None

    async def test_revoke_all_refresh_tokens(
        self, 
        auth_service: AuthService,
        user_repo: UserRepository,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test revoking all refresh tokens."""
        # Create multiple refresh tokens
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)
        
        rt1 = await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token1
        )
        rt2 = await RefreshTokenFactory.create(
            db_session,
            user_id=test_user.id,
            token=token2
        )
        
        count = await auth_service.revoke_all_refresh_tokens(user_repo, test_user.id)
        
        assert count == 2
        
        # Verify all tokens are revoked
        await db_session.refresh(rt1)
        await db_session.refresh(rt2)
        assert rt1.revoked_at is not None
        assert rt2.revoked_at is not None
