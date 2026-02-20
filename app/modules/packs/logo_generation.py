"""Logo generation via BFL FLUX.2 Pro (primary) and OpenAI DALL-E 2 (fallback)."""

import base64
import time
import uuid

import requests

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger, log_service_action
from app.core.storage import upload_file, get_presigned_url

OPENAI_IMAGE_MODEL = "dall-e-2"
OPENAI_PROMPT_MAX_LENGTH = 1000  # Images API limit
BFL_FLUX2_PRO_URL = "https://api.bfl.ai/v1/flux-2-pro"
BFL_POLL_INTERVAL = 3
BFL_POLL_TIMEOUT = 120

logger = get_logger("klarnow.services.logo_generation")


def _build_logo_prompt(
    brand_name: str,
    prompt: str | None,
    color_scheme: str | None,
    brand_os_summary: str | None,
    color_palette: dict | None = None,
) -> str:
    """Build shared text prompt for logo generation (BFL and DALL-E)."""
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


def _generate_logo_bfl(
    prompt_text: str,
    pack_id: str,
) -> dict | None:
    """
    Generate logo via BFL FLUX.2 Pro. Returns {"logo_url", "wordmark_svg_or_url"} on success.
    Returns None on any failure (logs reason); does not raise.
    """
    settings = get_settings()
    if not settings.bfl_api_key:
        return None

    headers = {
        "x-key": settings.bfl_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "prompt": prompt_text,
        "output_format": "png",
        "width": 1024,
        "height": 1024,
        "safety_tolerance": 2,
    }

    try:
        resp = requests.post(BFL_FLUX2_PRO_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("logo_generation: BFL submit failed: %s", e, exc_info=True)
        return None

    task_id = data.get("id")
    polling_url = data.get("polling_url")
    if not task_id or not polling_url:
        logger.warning("logo_generation: BFL response missing id or polling_url: %s", data)
        return None

    # Poll until Ready or terminal state
    deadline = time.monotonic() + BFL_POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            poll_resp = requests.get(polling_url, headers=headers, timeout=30)
            poll_resp.raise_for_status()
            result_data = poll_resp.json()
        except Exception as e:
            logger.warning("logo_generation: BFL poll failed: %s", e, exc_info=True)
            return None

        status = result_data.get("status")
        if status == "Ready":
            break
        if status in ("Error", "Request Moderated", "Content Moderated", "Task not found"):
            logger.warning("logo_generation: BFL task ended with status=%s", status)
            return None
        time.sleep(BFL_POLL_INTERVAL)

    else:
        logger.warning("logo_generation: BFL poll timed out after %ss", BFL_POLL_TIMEOUT)
        return None

    result = result_data.get("result")
    if not result:
        logger.warning("logo_generation: BFL result missing 'result'")
        return None

    # BFL returns image URL in result.sample (or similar)
    image_url = result.get("sample") or result.get("image_url") or result.get("url")
    if not image_url:
        logger.warning("logo_generation: BFL result has no image URL; keys=%s", list(result.keys()))
        return None

    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        image_bytes = img_resp.content
    except Exception as e:
        logger.warning("logo_generation: BFL image download failed: %s", e, exc_info=True)
        return None

    if not image_bytes:
        logger.warning("logo_generation: BFL image download empty")
        return None

    key = f"logos/{pack_id}/{uuid.uuid4().hex}.png"
    uploaded = upload_file(key, image_bytes, content_type="image/png")
    if not uploaded:
        logger.warning("logo_generation: BFL upload_file returned falsy")
        return None

    url = get_presigned_url(key, expires_in=86400 * 7) or f"key:{key}"
    return {"logo_url": url, "wordmark_svg_or_url": None}


def _generate_logo_dalle(
    prompt_text: str,
    pack_id: str,
) -> dict:
    """
    Generate logo via OpenAI DALL-E 2. Returns {"logo_url", "wordmark_svg_or_url"}.
    Raises BadRequestError on failure.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise BadRequestError(
            "Logo image generation is not configured. Set OPENAI_API_KEY (or BFL_API_KEY) in your environment to generate logos."
        )

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt_for_dalle = prompt_text[:OPENAI_PROMPT_MAX_LENGTH] if len(prompt_text) > OPENAI_PROMPT_MAX_LENGTH else prompt_text
    if len(prompt_text) > OPENAI_PROMPT_MAX_LENGTH:
        logger.info("logo_generation: DALL-E prompt truncated from %s to %s chars", len(prompt_text), OPENAI_PROMPT_MAX_LENGTH)
    try:
        response = client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=prompt_for_dalle,
            n=1,
            size="256x256",
            response_format="b64_json",
        )
    except Exception as e:
        logger.warning("logo_generation: OpenAI Images API call failed: %s", e, exc_info=True)
        raise BadRequestError(
            f"Logo generation failed: {e!s}. Check OPENAI_API_KEY and that your account has access to image models."
        ) from e

    if not response.data or len(response.data) == 0:
        logger.warning("logo_generation: OpenAI response had no data")
        raise BadRequestError("Logo generation did not return an image.")
    b64_data = getattr(response.data[0], "b64_json", None)
    if not b64_data:
        logger.warning("logo_generation: no b64_json in response")
        raise BadRequestError("Logo generation did not return image data.")
    image_bytes = base64.b64decode(b64_data)
    logger.info("logo_generation: DALL-E image decoded (%s bytes), uploading to storage", len(image_bytes))
    key = f"logos/{pack_id}/{uuid.uuid4().hex}.png"
    uploaded = upload_file(key, image_bytes, content_type="image/png")
    if not uploaded:
        logger.warning("logo_generation: upload_file returned falsy")
        raise BadRequestError("Logo was generated but storage upload failed. Check storage configuration.")
    url = get_presigned_url(key, expires_in=86400 * 7) or f"key:{key}"
    return {"logo_url": url, "wordmark_svg_or_url": None}


@log_service_action()
def generate_logo_with_gemini(
    brand_name: str,
    prompt: str | None,
    pack_id: str,
    color_scheme: str | None = None,
    brand_os_summary: str | None = None,
    color_palette: dict | None = None,
) -> dict:
    """
    Generate a logo image using BFL FLUX.2 Pro (if BFL_API_KEY set), then DALL-E 2 as fallback.
    On success returns {"logo_url": str, "wordmark_svg_or_url": str | None}.
    On failure raises BadRequestError with a clear message.
    """
    settings = get_settings()
    prompt_text = _build_logo_prompt(
        brand_name, prompt, color_scheme, brand_os_summary, color_palette
    )

    # 1) Try BFL FLUX.2 Pro first when configured
    if settings.bfl_api_key:
        logger.info("logo_generation: trying BFL FLUX.2 Pro first")
        result = _generate_logo_bfl(prompt_text, pack_id)
        if result is not None:
            logger.info("logo_generation: BFL FLUX.2 Pro succeeded")
            return result
        logger.info("logo_generation: BFL failed or unavailable, falling back to DALL-E")

    # 2) Fallback to DALL-E when configured
    if settings.openai_api_key:
        logger.info("logo_generation: using DALL-E 2")
        try:
            return _generate_logo_dalle(prompt_text, pack_id)
        except BadRequestError:
            if settings.bfl_api_key:
                raise BadRequestError(
                    "Logo generation failed with both FLUX.2 Pro (BFL) and DALL-E. Check BFL_API_KEY and OPENAI_API_KEY and try again."
                ) from None
            raise

    # 3) Neither provider configured
    raise BadRequestError(
        "Logo image generation is not configured. Set BFL_API_KEY and/or OPENAI_API_KEY in your environment to generate logos."
    )
