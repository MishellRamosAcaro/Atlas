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
    env: Literal["dev", "prod"]

    # Database
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int

    # Session
    max_sessions_per_user: int
    idle_timeout_days: int

    # Login lockout (brute-force protection)
    max_failed_login_attempts: int
    lockout_minutes: int

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str  # Frontend callback URL (SPA)

    # CORS - comma-separated origins for prod (e.g. https://app.example.com)
    cors_origins: list[str]

    # Email (Resend)
    resend_api_key: str

    # Uploads (dev: local dir; prod: GCS bucket)
    uploads_storage_path: str
    uploads_gcs_bucket: str | None  # Set in prod for Google Cloud Storage
    # Antivirus: in prod a scanner must run; dev can use mock
    uploads_antivirus_enabled: bool

    # Cookie
    cookie_domain: str | None
    cookie_secure: bool
    cookie_same_site: Literal["lax", "strict", "none"]

    # LLM preset (required in .env as LLM_PRESET)
    llm_preset: list[str]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (dotenv_settings, env_settings)

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
