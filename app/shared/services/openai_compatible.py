"""Shared OpenAI-compatible client helpers for OpenRouter-backed AI calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.core.config import get_settings

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_IMAGE_ONLY_MODALITY_MODEL_PREFIXES = ("sourceful/",)


@dataclass(slots=True)
class OpenAICompatibleProvider:
    """Configuration for OpenRouter's OpenAI-compatible API."""

    api_key: str
    base_url: str

    def create_sync_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def create_async_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_model_slug(model: str | None) -> str:
    return _clean_text(model).lower()


def _read_model(setting_name: str, default: str) -> str:
    settings = get_settings()
    return _clean_text(getattr(settings, setting_name, "")) or default


def _build_error_text(exc: Exception) -> str:
    parts: list[str] = []
    for value in (
        getattr(exc, "status", None),
        getattr(exc, "message", None),
        getattr(exc, "details", None),
        str(exc),
    ):
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            parts.append(str(value))
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts).lower()


def get_openai_compatible_provider() -> OpenAICompatibleProvider | None:
    """Return the OpenRouter-backed provider when configured."""
    settings = get_settings()
    api_key = _clean_text(settings.openrouter_api_key)
    if not api_key:
        return None
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=_clean_text(settings.openrouter_base_url) or DEFAULT_OPENROUTER_BASE_URL,
    )


def has_openai_compatible_provider() -> bool:
    return get_openai_compatible_provider() is not None


def create_sync_openai_client() -> OpenAI | None:
    provider = get_openai_compatible_provider()
    return provider.create_sync_client() if provider else None


def create_async_openai_client() -> AsyncOpenAI | None:
    provider = get_openai_compatible_provider()
    return provider.create_async_client() if provider else None


def is_unsupported_output_modalities_error(exc: Exception) -> bool:
    text = _build_error_text(exc)
    return (
        "requested output modalities" in text
        or "support the requested output modalities" in text
        or "no endpoints found" in text and "modalities" in text
    )


def get_image_generation_extra_body_attempts(
    model: str,
    *,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    image_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    normalized = _normalize_model_slug(model)
    preferred_modalities: tuple[str, ...] = ("image", "text")
    if normalized.startswith(_IMAGE_ONLY_MODALITY_MODEL_PREFIXES) or "/flux" in normalized or normalized.startswith("flux"):
        preferred_modalities = ("image",)
    elif "gemini" in normalized:
        preferred_modalities = ("image", "text")

    fallback_modalities = ("image",) if preferred_modalities == ("image", "text") else ("image", "text")
    modalities_attempts = (preferred_modalities, fallback_modalities)

    resolved_image_config: dict[str, Any] = {}
    if image_config:
        resolved_image_config.update(image_config)
    if aspect_ratio:
        resolved_image_config["aspect_ratio"] = aspect_ratio
    if image_size:
        resolved_image_config["image_size"] = image_size

    attempts: list[dict[str, Any]] = []
    seen_modalities: set[tuple[str, ...]] = set()
    for modalities in modalities_attempts:
        if modalities in seen_modalities:
            continue
        seen_modalities.add(modalities)
        payload: dict[str, Any] = {"modalities": list(modalities)}
        if resolved_image_config:
            payload["image_config"] = dict(resolved_image_config)
        attempts.append(payload)
    return tuple(attempts)


def get_default_model() -> str:
    return _read_model("ai_default_model", "openai/gpt-4o")


def get_fast_model() -> str:
    return _read_model("ai_fast_model", "openai/gpt-4o-mini")


def get_reasoning_model() -> str:
    return _read_model("ai_reasoning_model", "anthropic/claude-sonnet-4.6")


def get_builder_model() -> str:
    return _read_model("ai_builder_model", "anthropic/claude-opus-4.6")


def get_extraction_model() -> str:
    return _read_model("ai_extraction_model", "openai/gpt-4o-mini")


def get_embedding_model() -> str:
    return _read_model("ai_embedding_model", "openai/text-embedding-3-small")


def get_logo_model() -> str:
    return _read_model("ai_logo_model", "google/gemini-2.5-flash-image-preview")


def get_poster_flyer_model() -> str:
    settings = get_settings()
    configured = _clean_text(getattr(settings, "ai_poster_flyer_model", ""))
    return configured or get_reasoning_model()


def resolve_model_name(model: str) -> str:
    """Pass through configured OpenRouter model slugs."""
    return model
