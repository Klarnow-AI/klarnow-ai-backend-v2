"""Application configuration from environment."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    frontend_url: str = "http://localhost:3000"
    google_oauth_client_id: str = ""
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
    # Optional: Pack image context retrieval (pgvector-backed)
    image_context_enabled: bool = False
    image_context_top_k: int = 3
    image_context_min_score: float = 0.2
    image_context_embedding_model: str = "text-embedding-3-small"
    image_context_caption_model: str = "gpt-4o-mini"
    image_context_job_poll_seconds: int = 2
    image_context_job_max_attempts: int = 3
    image_context_preview_url_ttl_seconds: int = 900
    image_context_chat_enabled: bool = True
    image_context_poster_enabled: bool = True

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
