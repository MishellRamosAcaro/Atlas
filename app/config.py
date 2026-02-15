"""Application configuration via Pydantic Settings v2."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: Literal["dev", "prod"] = "dev"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/atlas"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # Session
    max_sessions_per_user: int = 2
    idle_timeout_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""  # Frontend callback URL (SPA)

    # CORS - comma-separated origins for prod (e.g. https://app.example.com)
    cors_origins: list[str] = ["*"]

    # Cookie
    cookie_domain: str | None = None
    cookie_secure: bool = True
    cookie_same_site: Literal["lax", "strict", "none"] = "none"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, list):
            return v
        if isinstance(v, str) and (not v or v == "*"):
            return ["*"]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["*"]

    @property
    def is_production(self) -> bool:
        """Whether the application is running in production."""
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
