from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.types import Role

class Settings(BaseSettings):
    # --- app ---
    APP_NAME: str = "Insights API"
    ENV: str = "dev"  # dev | staging | prod
    DEBUG: bool = True 
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # --- frontend ---
    FRONTEND_URL: str = "http://localhost:3000"

    # --- database/cache ---
    DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/insights"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- arq ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    ARQ_REDIS_URL: str = "redis://localhost:6379/"

    # --- SMTP (optional; used by a mailer service, not core) ---
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # --- auth/security ---
    JWT_SECRET_KEY: str = Field(
        "CHANGE_ME",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    ) #TODO: change to a secure key
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "insights"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Added for refresh token expiry
    ALLOWED_ROLES: List[Role] = [Role.USER, Role.ADMIN, Role.CORPORATE_ADMIN]

    # --- Password policy ---
    PWD_MIN_LEN: int = 8
    PWD_REQUIRE_UPPER: bool = True
    PWD_REQUIRE_LOWER: bool = True
    PWD_REQUIRE_SPECIAL: bool = True

    # --- 2FA (numeric code) ---
    TWOFA_CODE_LENGTH: int = 6
    TWOFA_TTL_MINUTES: int = 5

    # --- CORS --- TODO: change to a more secure CORS policy
    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # --- logging/observability ---
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "100 MB"

    # Bright Data
    BRIGHTDATA_API_BASE: str = "https://api.brightdata.com"
    BRIGHTDATA_API_TOKEN: Optional[str] = None
    BRIGHTDATA_DATASET_ID: Optional[str] = None

    # Public API base for building webhook notify URLs
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"

    # Webhook security (Authorization: Bearer <secret>)
    WEBHOOK_SHARED_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, value: str | List[str]) -> List[str]:
        """
        Allows CORS_ORIGINS to be a comma separated string in .env or JSON list.
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


@lru_cache
def get_settings() -> Settings:
    """ 
    Returns the settings object. Cached for performance.
    """
    return Settings()

settings = get_settings()