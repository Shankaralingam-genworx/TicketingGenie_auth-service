"""Application settings loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


class Settings(BaseSettings):
    """All configuration values for the auth service."""

    # Database — must use async scheme
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # App
    APP_ENV: str
    APP_PORT: int

    # Email
    EMAIL_FROM: str
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    # Redis / Celery
    REDIS_URL: str
    RESET_TOKEN_EXPIRE_MINUTES: int

    # Frontend
    FRONTEND_URL: str

    # ── Validators ─────────────────────────────────────────────────────────────

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'postgresql+asyncpg://' scheme. "
                "The sync 'postgresql://' scheme will silently fail at runtime."
            )
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long. "
                "Use a strong random secret."
            )
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        if v not in _ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM must be one of {_ALLOWED_JWT_ALGORITHMS}. "
                f"'none' and asymmetric algorithms are not permitted here."
            )
        return v

    @field_validator("FRONTEND_URL")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        """Prevent double-slash URLs in emails e.g. https://app.example.com//login."""
        return v.rstrip("/")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()