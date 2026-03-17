"""Logo generation via Gemini image models."""

from __future__ import annotations

import json
import threading
import time
import uuid

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger, log_service_action
from app.core.storage import get_asset_url, upload_file

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - dependency is part of project deps.
    genai = None
    genai_types = None

GEMINI_IMAGE_ASPECT_RATIO = "1:1"
GEMINI_IMAGE_SIZE = "1K"
DEFAULT_GEMINI_LOGO_MODEL = "gemini-2.5-flash-image"
LOGO_PROMPT_MAX_LENGTH = 1000
PROVIDER_COOLDOWN_SECONDS = 600
_IMAGE_EXTENSION_BY_MIME_TYPE = {
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

logger = get_logger("klarnow.services.logo_generation")
_GEMINI_FAILURE_LOCK = threading.Lock()
_GEMINI_FAILURE_STATE: dict[str, float | str] = {"until": 0.0, "reason": ""}


def _set_gemini_cooldown(reason: str) -> None:
    """Temporarily suppress provider calls after known auth/quota failures."""
    with _GEMINI_FAILURE_LOCK:
        _GEMINI_FAILURE_STATE["until"] = time.monotonic() + PROVIDER_COOLDOWN_SECONDS
        _GEMINI_FAILURE_STATE["reason"] = reason


def _get_gemini_cooldown_reason() -> str | None:
    """Return active cooldown reason for provider, or None when provider is callable."""
    with _GEMINI_FAILURE_LOCK:
        until = float(_GEMINI_FAILURE_STATE["until"] or 0.0)
        if until <= 0:
            return None
        if until <= time.monotonic():
            _GEMINI_FAILURE_STATE["until"] = 0.0
            _GEMINI_FAILURE_STATE["reason"] = ""
            return None
        reason = str(_GEMINI_FAILURE_STATE["reason"] or "").strip()
        return reason or "temporarily unavailable"


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
            try:
                parts.append(json.dumps(value, sort_keys=True, default=str))
            except TypeError:
                parts.append(str(value))
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts).lower()


def _is_gemini_auth_or_quota_error(exc: Exception) -> bool:
    """True for auth and quota failures that are unlikely to self-resolve quickly."""
    text = _build_error_text(exc)
    auth_markers = (
        "api key",
        "authentication",
        "invalid key",
        "permission denied",
        "unauthenticated",
        "unauthorized",
    )
    quota_markers = (
        "billing",
        "quota",
        "rate limit",
        "resource_exhausted",
        "too many requests",
    )
    if any(marker in text for marker in auth_markers + quota_markers):
        return True
    try:
        code = int(getattr(exc, "code", 0) or 0)
    except (TypeError, ValueError):
        code = 0
    return code in {401, 403, 429}


def _build_gemini_failure_reason(exc: Exception) -> str:
    text = _build_error_text(exc)
    if any(
        marker in text
        for marker in ("billing", "quota", "rate limit", "resource_exhausted", "too many requests")
    ):
        return "Gemini image generation quota or rate limit reached. Check your Gemini API plan and quota."
    return (
        "Gemini image generation authentication failed. "
        "Set GEMINI_API_KEY (or GOOGLE_API_KEY) with access to Gemini image generation."
    )


def _build_logo_prompt(
    brand_name: str,
    prompt: str | None,
    color_scheme: str | None,
    brand_os_summary: str | None,
    color_palette: dict | None = None,
) -> str:
    """Build the text prompt for logo generation."""
    style_description = (prompt or "").strip() or "simple and professional"
    scheme = (color_scheme or "").strip() or "versatile, modern color scheme"
    context = (brand_os_summary or "").strip()
    user_content = (
        f"Create a logo for {brand_name}. "
        f"The design should be {style_description}, with a {scheme}."
    )
    if context:
        user_content = f"Brand context: {context}. " + user_content
    if color_palette and isinstance(color_palette, dict):
        parts = [
            f"{key} {value}"
            for key, value in color_palette.items()
            if value and isinstance(value, str) and str(value).strip()
        ]
        if parts:
            user_content += (
                " Infuse these exact brand colors into the logo as the dominant visual system: "
                + ", ".join(parts)
                + ". Keep these hues clearly visible in the main mark, preserve an on-brand feel, "
                  "and do not swap them for unrelated accent colors except neutral black, white, "
                  "or transparent space when needed for contrast."
            )
    user_content += " Simple, clean logo image with no text overlay."
    return user_content


def _truncate_logo_prompt(prompt_text: str) -> str:
    if len(prompt_text) <= LOGO_PROMPT_MAX_LENGTH:
        return prompt_text
    logger.info(
        "logo_generation: Gemini prompt truncated from %s to %s chars",
        len(prompt_text),
        LOGO_PROMPT_MAX_LENGTH,
    )
    return prompt_text[:LOGO_PROMPT_MAX_LENGTH]


def _extract_generated_image(response: object) -> tuple[bytes, str] | None:
    parts = getattr(response, "parts", None) or []
    for part in parts:
        inline_data = getattr(part, "inline_data", None)
        image_bytes = getattr(inline_data, "data", None)
        mime_type = str(getattr(inline_data, "mime_type", "") or "").strip().lower()
        if isinstance(image_bytes, bytes) and image_bytes and mime_type.startswith("image/"):
            return image_bytes, mime_type
    return None


def _extension_for_mime_type(mime_type: str) -> str:
    normalized = str(mime_type or "").split(";", 1)[0].strip().lower()
    return _IMAGE_EXTENSION_BY_MIME_TYPE.get(normalized, "png")


def generate_logo_with_gemini(
    prompt_text: str,
    pack_id: str,
) -> dict[str, str | None]:
    """
    Generate a logo via Gemini image generation.

    Returns {"logo_url", "wordmark_svg_or_url"}.
    Raises BadRequestError on failure.
    """
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key or not settings.ai_logo_generation_enabled:
        raise BadRequestError(
            "Logo image generation is disabled. "
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    if genai is None or genai_types is None:
        raise BadRequestError(
            "Gemini logo generation is unavailable because the google-genai package is not installed."
        )
    cooldown_reason = _get_gemini_cooldown_reason()
    if cooldown_reason:
        raise BadRequestError(cooldown_reason)

    client = genai.Client(api_key=api_key)
    prompt_for_gemini = _truncate_logo_prompt(prompt_text)
    model_name = (settings.gemini_logo_model or "").strip() or DEFAULT_GEMINI_LOGO_MODEL
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_for_gemini,
            config=genai_types.GenerateContentConfig(
                responseModalities=["IMAGE"],
                imageConfig=genai_types.ImageConfig(
                    aspect_ratio=GEMINI_IMAGE_ASPECT_RATIO,
                    image_size=GEMINI_IMAGE_SIZE,
                ),
            ),
        )
    except Exception as exc:
        if _is_gemini_auth_or_quota_error(exc):
            reason = _build_gemini_failure_reason(exc)
            _set_gemini_cooldown(reason)
            logger.warning(
                "logo_generation: %s Skipping Gemini for %ss.",
                reason,
                PROVIDER_COOLDOWN_SECONDS,
            )
            raise BadRequestError(reason) from None
        logger.warning("logo_generation: Gemini API call failed: %s", exc, exc_info=True)
        raise BadRequestError(
            "Logo generation failed: "
            f"{exc!s}. Check GEMINI_API_KEY (or GOOGLE_API_KEY) and that your account has access to Gemini image generation."
        ) from exc
    finally:
        close_client = getattr(client, "close", None)
        if callable(close_client):
            close_client()

    image_payload = _extract_generated_image(response)
    if not image_payload:
        logger.warning("logo_generation: Gemini response had no image parts")
        raise BadRequestError("Logo generation did not return an image.")

    image_bytes, mime_type = image_payload
    extension = _extension_for_mime_type(mime_type)
    logger.info(
        "logo_generation: Gemini image decoded (%s bytes, %s), uploading to storage",
        len(image_bytes),
        mime_type,
    )
    key = f"logos/{pack_id}/{uuid.uuid4().hex}.{extension}"
    uploaded = upload_file(key, image_bytes, content_type=mime_type)
    if not uploaded:
        logger.warning("logo_generation: upload_file returned falsy")
        raise BadRequestError("Logo was generated but storage upload failed. Check storage configuration.")
    url = get_asset_url(key, expires_in=86400 * 7) or f"key:{key}"
    return {"logo_url": url, "wordmark_svg_or_url": None}


@log_service_action()
def generate_logo(
    brand_name: str,
    prompt: str | None,
    pack_id: str,
    color_scheme: str | None = None,
    brand_os_summary: str | None = None,
    color_palette: dict | None = None,
    strict: bool = True,
) -> dict[str, str | None]:
    """
    Generate a logo image using Gemini image generation.

    On success returns {"logo_url": str, "wordmark_svg_or_url": str | None}.
    On failure raises BadRequestError with a clear message when strict=True.
    When strict=False, returns {"logo_url": None, "wordmark_svg_or_url": None}.
    """
    settings = get_settings()
    prompt_text = _build_logo_prompt(
        brand_name, prompt, color_scheme, brand_os_summary, color_palette
    )
    no_logo_result: dict[str, str | None] = {"logo_url": None, "wordmark_svg_or_url": None}

    if settings.gemini_api_key and settings.ai_logo_generation_enabled:
        logger.info(
            "logo_generation: using Gemini model %s",
            (settings.gemini_logo_model or "").strip() or DEFAULT_GEMINI_LOGO_MODEL,
        )
        try:
            return generate_logo_with_gemini(prompt_text, pack_id)
        except BadRequestError as exc:
            if strict:
                raise
            logger.info(
                "logo_generation: non-strict mode returning no logo after Gemini failure: %s",
                exc,
            )
            return no_logo_result

    if strict:
        raise BadRequestError(
            "Logo image generation is disabled. "
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    logger.info("logo_generation: non-strict mode returning no logo; provider not configured")
    return no_logo_result
