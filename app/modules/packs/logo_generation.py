"""Logo generation via OpenAI DALL-E 3."""

import base64
import threading
import time
import uuid

import requests

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger, log_service_action
from app.core.storage import upload_file, get_asset_url

OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_IMAGE_SIZE = "1024x1024"
OPENAI_IMAGE_QUALITY = "standard"
OPENAI_IMAGE_STYLE = "natural"
OPENAI_PROMPT_MAX_LENGTH = 1000  # Conservative guard for long prompts.
PROVIDER_COOLDOWN_SECONDS = 600

logger = get_logger("klarnow.services.logo_generation")
_OPENAI_FAILURE_LOCK = threading.Lock()
_OPENAI_FAILURE_STATE: dict[str, float | str] = {"until": 0.0, "reason": ""}


def _set_openai_cooldown(reason: str) -> None:
    """Temporarily suppress provider calls after known billing/quota failures."""
    with _OPENAI_FAILURE_LOCK:
        _OPENAI_FAILURE_STATE["until"] = time.monotonic() + PROVIDER_COOLDOWN_SECONDS
        _OPENAI_FAILURE_STATE["reason"] = reason


def _get_openai_cooldown_reason() -> str | None:
    """Return active cooldown reason for provider, or None when provider is callable."""
    with _OPENAI_FAILURE_LOCK:
        until = float(_OPENAI_FAILURE_STATE["until"] or 0.0)
        if until <= 0:
            return None
        if until <= time.monotonic():
            _OPENAI_FAILURE_STATE["until"] = 0.0
            _OPENAI_FAILURE_STATE["reason"] = ""
            return None
        reason = str(_OPENAI_FAILURE_STATE["reason"] or "").strip()
        return reason or "temporarily unavailable"


def _is_openai_billing_or_quota_error(exc: Exception) -> bool:
    """True for OpenAI billing/quota exhaustion errors that are unlikely to self-resolve quickly."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error_obj = body.get("error")
        if isinstance(error_obj, dict):
            code = str(error_obj.get("code") or "").lower()
            message = str(error_obj.get("message") or "").lower()
            if code in {"billing_hard_limit_reached", "insufficient_quota"}:
                return True
            if "billing hard limit" in message or "insufficient quota" in message:
                return True
    text = str(exc).lower()
    return ("billing_hard_limit_reached" in text) or ("billing hard limit" in text) or ("insufficient_quota" in text)


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
        parts = [f"{k}: {v}" for k, v in color_palette.items() if v and isinstance(v, str) and str(v).strip()]
        if parts:
            user_content += " Use these brand colors: " + ", ".join(parts) + "."
    user_content += " Simple, clean logo image with no text overlay."
    return user_content


def generate_logo_with_openai(
    prompt_text: str,
    pack_id: str,
) -> dict[str, str | None]:
    """
    Generate a logo via OpenAI DALL-E 3.

    Returns {"logo_url", "wordmark_svg_or_url"}.
    Raises BadRequestError on failure.
    """
    settings = get_settings()
    if not settings.openai_api_key or not settings.ai_logo_generation_enabled:
        raise BadRequestError(
            "Logo image generation is disabled. Set OPENAI_API_KEY and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    cooldown_reason = _get_openai_cooldown_reason()
    if cooldown_reason:
        raise BadRequestError(cooldown_reason)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt_for_dalle = prompt_text[:OPENAI_PROMPT_MAX_LENGTH] if len(prompt_text) > OPENAI_PROMPT_MAX_LENGTH else prompt_text
    if len(prompt_text) > OPENAI_PROMPT_MAX_LENGTH:
        logger.info(
            "logo_generation: DALL-E prompt truncated from %s to %s chars",
            len(prompt_text),
            OPENAI_PROMPT_MAX_LENGTH,
        )
    try:
        response = client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=prompt_for_dalle,
            n=1,
            size=OPENAI_IMAGE_SIZE,
            quality=OPENAI_IMAGE_QUALITY,
            style=OPENAI_IMAGE_STYLE,
            response_format="b64_json",
        )
    except Exception as e:
        if _is_openai_billing_or_quota_error(e):
            reason = "OpenAI Images billing/quota limit reached. Add credits or raise your OpenAI hard limit."
            _set_openai_cooldown(reason)
            logger.warning(
                "logo_generation: %s Skipping OpenAI Images for %ss.",
                reason,
                PROVIDER_COOLDOWN_SECONDS,
            )
            raise BadRequestError(reason) from None
        logger.warning("logo_generation: OpenAI Images API call failed: %s", e, exc_info=True)
        raise BadRequestError(
            f"Logo generation failed: {e!s}. Check OPENAI_API_KEY and that your account has access to image models."
        ) from e

    if not response.data or len(response.data) == 0:
        logger.warning("logo_generation: OpenAI response had no data")
        raise BadRequestError("Logo generation did not return an image.")
    b64_data = getattr(response.data[0], "b64_json", None)
    image_url = getattr(response.data[0], "url", None)
    if b64_data:
        image_bytes = base64.b64decode(b64_data)
    elif image_url:
        try:
            image_resp = requests.get(image_url, timeout=30)
            image_resp.raise_for_status()
            image_bytes = image_resp.content
        except Exception as e:
            logger.warning("logo_generation: image download failed: %s", e, exc_info=True)
            raise BadRequestError("Logo generation returned an image URL but it could not be downloaded.") from e
    else:
        logger.warning("logo_generation: no image payload in response")
        raise BadRequestError("Logo generation did not return image data.")
    logger.info("logo_generation: DALL-E 3 image decoded (%s bytes), uploading to storage", len(image_bytes))
    key = f"logos/{pack_id}/{uuid.uuid4().hex}.png"
    uploaded = upload_file(key, image_bytes, content_type="image/png")
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
    Generate a logo image using OpenAI DALL-E 3.

    On success returns {"logo_url": str, "wordmark_svg_or_url": str | None}.
    On failure raises BadRequestError with a clear message when strict=True.
    When strict=False, returns {"logo_url": None, "wordmark_svg_or_url": None}.
    """
    settings = get_settings()
    prompt_text = _build_logo_prompt(
        brand_name, prompt, color_scheme, brand_os_summary, color_palette
    )
    no_logo_result: dict[str, str | None] = {"logo_url": None, "wordmark_svg_or_url": None}

    if settings.openai_api_key and settings.ai_logo_generation_enabled:
        logger.info("logo_generation: using DALL-E 3")
        try:
            return generate_logo_with_openai(prompt_text, pack_id)
        except BadRequestError as e:
            if strict:
                raise
            logger.info("logo_generation: non-strict mode returning no logo after OpenAI failure: %s", e)
            return no_logo_result

    if strict:
        raise BadRequestError(
            "Logo image generation is disabled. Set OPENAI_API_KEY and AI_LOGO_GENERATION_ENABLED=true to generate logos."
        )
    logger.info("logo_generation: non-strict mode returning no logo; providers not configured")
    return no_logo_result
