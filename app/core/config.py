import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_DB_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


def _database_uses_remote_host(database_url: str) -> bool:
    try:
        parsed = urlparse(database_url)
    except ValueError:
        return False

    scheme = (parsed.scheme or "").split("+", 1)[0]
    if scheme == "sqlite":
        return False

    host = (parsed.hostname or "").strip().lower()
    return host not in _LOCAL_DB_HOSTS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Load backend env from repository root regardless of process working dir.
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    secret_key: str = ""
    cors_allow_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    access_token_expiry_time: int = 60  # minutes
    refresh_token_expiry_days: int = 30
    frontend_url: str = "http://localhost:3000"
    google_oauth_client_id: str = ""
    # Optional: when set, published sites use subdomains (e.g. sites.klarnow.com → acme.sites.klarnow.com)
    sites_domain: str = ""

    # Database
    database_url: str = ""
    # Keep conservative defaults for hosted Postgres providers like Supabase.
    db_pool_size: int = 5
    db_max_overflow: int = 0
    db_pool_timeout_seconds: int = 30
    # Leave unset to auto-enable for staging/production and remote databases.
    db_pool_pre_ping: bool | None = None
    # Recycle long-lived connections periodically to avoid stale remote sockets.
    db_pool_recycle_seconds: int = 1800
    # Reuse the hottest pooled connection first to reduce reconnect churn.
    db_pool_use_lifo: bool = True
    db_connect_timeout_seconds: int = 5

    # Optional: onboarding∑
    onboarding_session_expiry_days: int = 1

    # Optional: Resend
    resend_api_key: str = ""
    resend_from_email: str = ""
    support_email: str = "sooreoluwaa@gmail.com"
    failure_alert_to_email: str = ""

    # Optional: Storage (S3)
    storage_provider: str = "s3"
    storage_region: str = "us-east-1"
    storage_bucket: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_cdn_url: str = ""

    # Optional: OpenAI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    poster_max_output_tokens: int = 16384
    # Cost guards: keep non-essential AI features opt-in.
    ai_chat_prompt_suggestions_enabled: bool = False
    ai_sprint_today_tasks_enabled: bool = False
    ai_sprint_field_suggestions_enabled: bool = False
    ai_brand_identity_suggestions_enabled: bool = False
    ai_logo_generation_enabled: bool = False
    ai_brand_os_reasoning_enabled: bool = False

    # Optional: Redis-backed onboarding queue
    redis_url: str = ""
    onboarding_queue_stream_key: str = "klarnow:onboarding:stream"
    onboarding_queue_consumer_group: str = "onboarding-workers"
    onboarding_queue_delayed_key: str = "klarnow:onboarding:delayed"
    onboarding_queue_block_ms: int = 5000
    onboarding_queue_claim_idle_ms: int = 60000
    onboarding_queue_batch_size: int = 1
    onboarding_queue_stream_maxlen: int = 1000
    onboarding_queue_dispatch_ttl_seconds: int = 86400
    onboarding_queue_retry_base_delay_seconds: int = 5
    onboarding_queue_retry_max_delay_seconds: int = 300

    # Optional: Chat attachments
    chat_attachment_max_size_mb: int = 20
    chat_attachment_max_text_chars: int = 20000
    chat_attachment_prompt_max_chars: int = 12000
    chat_attachment_max_per_message: int = 8

    # Optional: Global reference markdown KB (RAG-lite for chat/proposals)
    reference_doc_enabled: bool = False
    reference_doc_path: str = "app/core/reference/100M-Leads.md"
    reference_doc_embedding_model: str = "text-embedding-3-small"
    reference_doc_chunk_chars: int = 1200
    reference_doc_chunk_overlap_chars: int = 200
    reference_doc_top_k: int = 5
    reference_doc_min_score: float = 0.2
    reference_doc_max_chars: int = 250000
    reference_doc_cache_ttl_seconds: int = 300

    # Optional: Kling API (official - api-singapore.klingai.com, JWT auth)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api-singapore.klingai.com"
    ad_factory_billing_enabled: bool = False
    ad_factory_default_credit_balance: int = 0
    ad_factory_credit_reservation_minutes: int = 30

    # Optional: Stripe (Connect + Invoicing)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Orchestrator cost/safety (Phase 7)
    max_tool_chain_length: int = 5
    retry_cap_per_tool: int = 2

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object):
        if value is None:
            return value
        if isinstance(value, (list, tuple, set)):
            return cls._normalize_cors_allow_origins(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    bracket_trimmed = raw[1:]
                    if bracket_trimmed.endswith("]"):
                        bracket_trimmed = bracket_trimmed[:-1]
                    return cls._split_and_normalize_cors_allow_origins(bracket_trimmed)
                if isinstance(parsed, list):
                    return cls._normalize_cors_allow_origins(parsed)
                raise ValueError("CORS_ALLOW_ORIGINS JSON value must be a list")
            if raw.startswith("{"):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "CORS_ALLOW_ORIGINS must be a JSON list, bracketed list, or comma-separated string"
                    ) from exc
                if isinstance(parsed, list):
                    return cls._normalize_cors_allow_origins(parsed)
                raise ValueError("CORS_ALLOW_ORIGINS JSON value must be a list")
            return cls._split_and_normalize_cors_allow_origins(raw)
        raise ValueError("CORS_ALLOW_ORIGINS must be a string or list of strings")

    @classmethod
    def _split_and_normalize_cors_allow_origins(cls, value: str) -> list[str]:
        return cls._normalize_cors_allow_origins(value.split(","))

    @classmethod
    def _normalize_cors_allow_origins(cls, values: object) -> list[str]:
        if not isinstance(values, (list, tuple, set)):
            raise ValueError("CORS_ALLOW_ORIGINS must be a list")
        normalized: list[str] = []
        for origin in values:
            text = str(origin).strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
                text = text[1:-1].strip()
            if text:
                normalized.append(text)
        return normalized

    @model_validator(mode="after")
    def validate_required_settings(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

        if self.db_pool_pre_ping is None:
            self.db_pool_pre_ping = (
                self.app_env in {"production", "staging"}
                or _database_uses_remote_host(self.database_url)
            )

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
