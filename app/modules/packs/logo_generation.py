"""Logo generation via OpenRouter image-capable models."""

from __future__ import annotations

import base64
import json
import threading
import time
import uuid

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger, log_service_action
from app.core.storage import get_asset_url, upload_file
from app.shared.services.openai_compatible import (
    create_sync_openai_client,
    get_image_generation_extra_body_attempts,
    get_logo_model,
    has_openai_compatible_provider,
    is_unsupported_output_modalities_error,
)

OPENROUTER_IMAGE_ASPECT_RATIO = "1:1"
OPENROUTER_IMAGE_SIZE = "1K"
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
_PROVIDER_FAILURE_LOCK = threading.Lock()
_PROVIDER_FAILURE_STATE: dict[str, float | str] = {"until": 0.0, "reason": ""}


def _set_provider_cooldown(reason: str) -> None:
    """Temporarily suppress provider calls after known auth/quota failures."""
    with _PROVIDER_FAILURE_LOCK:
        _PROVIDER_FAILURE_STATE["until"] = time.monotonic() + PROVIDER_COOLDOWN_SECONDS
        _PROVIDER_FAILURE_STATE["reason"] = reason


def _get_provider_cooldown_reason() -> str | None:
    """Return active cooldown reason for provider, or None when provider is callable."""
    with _PROVIDER_FAILURE_LOCK:
        until = float(_PROVIDER_FAILURE_STATE["until"] or 0.0)
        if until <= 0:
            return None
        if until <= time.monotonic():
            _PROVIDER_FAILURE_STATE["until"] = 0.0
            _PROVIDER_FAILURE_STATE["reason"] = ""
            return None
        reason = str(_PROVIDER_FAILURE_STATE["reason"] or "").strip()
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


def _is_provider_auth_or_quota_error(exc: Exception) -> bool:
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
        "payment required",
    )
    if any(marker in text for marker in auth_markers + quota_markers):
        return True
    try:
        code = int(getattr(exc, "code", 0) or 0)
    except (TypeError, ValueError):
        code = 0
    return code in {401, 402, 403, 429}


def _build_provider_failure_reason(exc: Exception) -> str:
    text = _build_error_text(exc)
    if any(
        marker in text
        for marker in ("billing", "quota", "rate limit", "resource_exhausted", "too many requests", "payment required")
    ):
        return "OpenRouter image generation quota or billing limit reached. Check your OpenRouter credits and limits."
    return (
        "OpenRouter image generation authentication failed. "
        "Set OPENROUTER_API_KEY with access to image-capable models."
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
        "logo_generation: OpenRouter prompt truncated from %s to %s chars",
        len(prompt_text),
        LOGO_PROMPT_MAX_LENGTH,
    )
    return prompt_text[:LOGO_PROMPT_MAX_LENGTH]


def _get_attr_or_key(value: object, *names: str) -> object | None:
    if value is None:
        return None
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    model_extra = getattr(value, "model_extra", None)
    if isinstance(model_extra, dict):
        for name in names:
            if name in model_extra:
                return model_extra[name]
    return None


def _extract_generated_image_data_url(response: object) -> str | None:
    choices = _get_attr_or_key(response, "choices")
    if not isinstance(choices, list):
        return None
    for choice in choices:
        message = _get_attr_or_key(choice, "message")
        images = _get_attr_or_key(message, "images")
        if not isinstance(images, list):
            continue
        for image in images:
            image_url = _get_attr_or_key(image, "image_url", "imageUrl")
            url = _get_attr_or_key(image_url, "url")
            if isinstance(url, str) and url.startswith("data:image/"):
                return url
    return None


def _decode_data_url_image(data_url: str) -> tuple[bytes, str]:
    header, _, data = data_url.partition(",")
    if not header.startswith("data:image/") or ";base64" not in header or not data:
        raise BadRequestError("Logo generation returned an unsupported image payload.")
    mime_type = header[5:].split(";", 1)[0].strip().lower()
    try:
        image_bytes = base64.b64decode(data)
    except Exception as exc:  # pragma: no cover - defensive
        raise BadRequestError("Logo generation returned invalid base64 image data.") from exc
    return image_bytes, mime_type


def _extension_for_mime_type(mime_type: str) -> str:
    normalized = str(mime_type or "").split(";", 1)[0].strip().lower()
    return _IMAGE_EXTENSION_BY_MIME_TYPE.get(normalized, "png")


def _request_logo_image_generation(
    client: object,
    *,
    model_name: str,
    prompt_for_model: str,
) -> object:
    message_payload = [{"role": "user", "content": prompt_for_model}]
    extra_body_attempts = get_image_generation_extra_body_attempts(
        model_name,
        aspect_ratio=OPENROUTER_IMAGE_ASPECT_RATIO,
        image_size=OPENROUTER_IMAGE_SIZE,
    )

    last_exc: Exception | None = None
    for attempt_index, extra_body in enumerate(extra_body_attempts):
        try:
            return client.chat.completions.create(
                model=model_name,
                messages=message_payload,
                extra_body=extra_body,
            )
        except Exception as exc:
            last_exc = exc
            has_fallback = attempt_index < len(extra_body_attempts) - 1
            if not has_fallback or not is_unsupported_output_modalities_error(exc):
                raise
            attempted_modalities = extra_body.get("modalities")
            next_modalities = extra_body_attempts[attempt_index + 1].get("modalities")
            logger.info(
                "logo_generation: model %s rejected output modalities %s; retrying with %s",
                model_name,
                attempted_modalities,
                next_modalities,
            )

    if last_exc is not None:
        raise last_exc
    raise BadRequestError("Logo generation failed before any OpenRouter request was sent.")


def generate_logo_with_openrouter(
    prompt_text: str,
    pack_id: str,
) -> dict[str, str | None]:
    """
    Generate a logo via OpenRouter image generation.

    Returns {"logo_url", "wordmark_svg_or_url"}.
    Raises BadRequestError on failure.
    """
    settings = get_settings()
    if not has_openai_compatible_provider() or not settings.ai_logo_generation_enabled:
        raise BadRequestError(
            "Logo image generation is disabled. "
            "Set OPENROUTER_API_KEY and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    cooldown_reason = _get_provider_cooldown_reason()
    if cooldown_reason:
        raise BadRequestError(cooldown_reason)

    client = create_sync_openai_client()
    if not client:
        raise BadRequestError(
            "Logo image generation is disabled. "
            "Set OPENROUTER_API_KEY and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )

    model_name = get_logo_model()
    prompt_for_model = _truncate_logo_prompt(prompt_text)
    try:
        response = _request_logo_image_generation(
            client,
            model_name=model_name,
            prompt_for_model=prompt_for_model,
        )
    except Exception as exc:
        if _is_provider_auth_or_quota_error(exc):
            reason = _build_provider_failure_reason(exc)
            _set_provider_cooldown(reason)
            logger.warning(
                "logo_generation: %s Skipping image generation for %ss.",
                reason,
                PROVIDER_COOLDOWN_SECONDS,
            )
            raise BadRequestError(reason) from None
        logger.warning("logo_generation: OpenRouter image call failed: %s", exc, exc_info=True)
        raise BadRequestError(
            "Logo generation failed: "
            f"{exc!s}. Check OPENROUTER_API_KEY and that your selected model supports image generation."
        ) from exc

    data_url = _extract_generated_image_data_url(response)
    if not data_url:
        logger.warning("logo_generation: OpenRouter response had no image payload")
        raise BadRequestError("Logo generation did not return an image.")

    image_bytes, mime_type = _decode_data_url_image(data_url)
    extension = _extension_for_mime_type(mime_type)
    logger.info(
        "logo_generation: OpenRouter image decoded (%s bytes, %s), uploading to storage",
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
    Generate a logo image using OpenRouter image generation.

    On success returns {"logo_url": str, "wordmark_svg_or_url": str | None}.
    On failure raises BadRequestError with a clear message when strict=True.
    When strict=False, returns {"logo_url": None, "wordmark_svg_or_url": None}.
    """
    settings = get_settings()
    prompt_text = _build_logo_prompt(
        brand_name, prompt, color_scheme, brand_os_summary, color_palette
    )
    no_logo_result: dict[str, str | None] = {"logo_url": None, "wordmark_svg_or_url": None}

    if has_openai_compatible_provider() and settings.ai_logo_generation_enabled:
        logger.info("logo_generation: using OpenRouter model %s", get_logo_model())
        try:
            return generate_logo_with_openrouter(prompt_text, pack_id)
        except BadRequestError as exc:
            if strict:
                raise
            logger.info(
                "logo_generation: non-strict mode returning no logo after OpenRouter failure: %s",
                exc,
            )
            return no_logo_result

    if strict:
        raise BadRequestError(
            "Logo image generation is disabled. "
            "Set OPENROUTER_API_KEY and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    logger.info("logo_generation: non-strict mode returning no logo; provider not configured")
    return no_logo_result
