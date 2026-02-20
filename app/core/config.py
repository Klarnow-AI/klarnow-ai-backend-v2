"""Application configuration from environment."""

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
    access_token_expiry_time: int = 60  # minutes
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = ""

    # Optional: onboarding∑
    onboarding_session_expiry_days: int = 1

    # Optional: Resend
    resend_api_key: str = ""
    resend_from_email: str = "noreply@example.com"

    # Optional: Storage (S3)
    storage_provider: str = "s3"
    storage_region: str = "us-east-1"
    storage_bucket: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_cdn_url: str = ""

    # Optional: OpenAI
    openai_api_key: str = ""

    # Optional: Black Forest Labs (FLUX.2 Pro)
    bfl_api_key: str = ""

    # Orchestrator cost/safety (Phase 7)
    max_tool_chain_length: int = 5
    retry_cap_per_tool: int = 2

def get_settings() -> Settings:
    return Settings()
