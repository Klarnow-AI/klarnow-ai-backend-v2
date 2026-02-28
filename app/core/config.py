"""Application configuration from environment."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    secret_key: str = ""
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    access_token_expiry_time: int = 60  # minutes
    frontend_url: str = "http://localhost:3000"
    # Optional: when set, published sites use subdomains (e.g. sites.klarnow.com → acme.sites.klarnow.com)
    sites_domain: str = ""

    # Database
    database_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30

    # Optional: onboarding∑
    onboarding_session_expiry_days: int = 1

    # Optional: Resend
    resend_api_key: str = ""
    resend_from_email: str = "noreply@example.com"
    support_email: str = "sooreoluwa@klarnow.co.uk"

    # Optional: Storage (S3)
    storage_provider: str = "s3"
    storage_region: str = "us-east-1"
    storage_bucket: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_cdn_url: str = ""

    # Optional: OpenAI
    openai_api_key: str = ""

    # Optional: Kling API (official - api-singapore.klingai.com, JWT auth)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api-singapore.klingai.com"

    # Optional: Black Forest Labs (FLUX.2 Pro)
    bfl_api_key: str = ""

    # Optional: Stripe (Connect + Invoicing)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Orchestrator cost/safety (Phase 7)
    max_tool_chain_length: int = 5
    retry_cap_per_tool: int = 2

    @model_validator(mode="after")
    def validate_required_settings(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

        if self.app_env in {"production", "staging"}:
            missing: list[str] = []
            if not self.secret_key:
                missing.append("SECRET_KEY")
            if not self.cors_allow_origins:
                missing.append("CORS_ALLOW_ORIGINS")
            if missing:
                raise ValueError(
                    f"Missing required settings for {self.app_env}: {', '.join(missing)}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
