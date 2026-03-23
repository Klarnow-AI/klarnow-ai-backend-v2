"""Logo generation via OpenRouter image-capable models."""

from __future__ import annotations

import asyncio
import base64
import inspect
import json
import threading
import time
import uuid
from collections import deque
from io import BytesIO
from typing import Mapping

from PIL import Image

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


def _clean_logo_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def get_logo_primary_asset_url(result: Mapping[str, object] | None) -> str | None:
    """Prefer the reusable transparent asset and fall back to the default image."""
    if result is None:
        return None
    for key in ("wordmark_svg_or_url", "transparent_logo_url", "logo_url"):
        candidate = _clean_logo_url(result.get(key))
        if candidate:
            return candidate
    return None


def get_logo_variant_urls(result: Mapping[str, object] | None) -> list[str]:
    """Return distinct generated asset URLs in display order."""
    if result is None:
        return []
    urls: list[str] = []
    for key in ("logo_url", "transparent_logo_url", "wordmark_svg_or_url"):
        candidate = _clean_logo_url(result.get(key))
        if candidate and candidate not in urls:
            urls.append(candidate)
    return urls


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
    user_content += (
        " Present a single isolated logo mark on a flat, plain background with generous clear space, "
        "no text overlay, no mockup, no paper texture, no scenery, and no cast shadows."
    )
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


def _upload_logo_variant(
    *,
    pack_id: str,
    asset_id: str,
    image_bytes: bytes,
    mime_type: str,
    extension: str,
    variant_name: str | None = None,
) -> str:
    suffix = f"_{variant_name}" if variant_name else ""
    key = f"logos/{pack_id}/{asset_id}{suffix}.{extension}"
    upload_result = upload_file(key, image_bytes, content_type=mime_type)
    uploaded = asyncio.run(upload_result) if inspect.isawaitable(upload_result) else upload_result
    if not uploaded:
        logger.warning(
            "logo_generation: upload_file returned falsy for variant %s",
            variant_name or "default",
        )
        raise BadRequestError("Logo was generated but storage upload failed. Check storage configuration.")
    return get_asset_url(key, expires_in=86400 * 7) or f"key:{key}"


def _image_has_transparency(image: Image.Image) -> bool:
    if "A" not in image.getbands():
        return False
    alpha_extrema = image.getchannel("A").getextrema()
    if alpha_extrema is None:
        return False
    return alpha_extrema[0] < 255


def _background_seed_colors(image: Image.Image) -> list[tuple[int, int, int]]:
    width, height = image.size
    sample_points = {
        (0, 0),
        (max(width - 1, 0), 0),
        (0, max(height - 1, 0)),
        (max(width - 1, 0), max(height - 1, 0)),
        (width // 2, 0),
        (width // 2, max(height - 1, 0)),
        (0, height // 2),
        (max(width - 1, 0), height // 2),
    }
    seed_colors: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for x, y in sample_points:
        rgb = tuple(image.getpixel((x, y))[:3])
        if rgb not in seen:
            seen.add(rgb)
            seed_colors.append(rgb)
    return seed_colors or [(255, 255, 255)]


def _max_channel_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]), abs(left[2] - right[2]))


def _candidate_background_thresholds(
    seed_colors: list[tuple[int, int, int]],
) -> list[int]:
    if len(seed_colors) < 2:
        return [20, 32, 48]
    spread = 0
    for index, seed_color in enumerate(seed_colors):
        for other_color in seed_colors[index + 1 :]:
            spread = max(spread, _max_channel_distance(seed_color, other_color))
    base = max(20, min(42, spread + 10))
    return sorted({base, min(64, base + 12), min(84, base + 24)})


def _matches_background(
    rgb: tuple[int, int, int],
    *,
    seed_colors: list[tuple[int, int, int]],
    threshold: int,
) -> bool:
    return any(
        _max_channel_distance(rgb, seed_color) <= threshold
        for seed_color in seed_colors
    )


def _build_background_mask(
    image: Image.Image,
    *,
    seed_colors: list[tuple[int, int, int]],
    threshold: int,
) -> tuple[list[list[bool]], int]:
    width, height = image.size
    pixels = image.load()
    mask = [[False] * width for _ in range(height)]
    queue: deque[tuple[int, int]] = deque()

    def maybe_enqueue(x: int, y: int) -> None:
        if mask[y][x]:
            return
        rgba = pixels[x, y]
        if rgba[3] == 0 or _matches_background(
            rgba[:3],
            seed_colors=seed_colors,
            threshold=threshold,
        ):
            mask[y][x] = True
            queue.append((x, y))

    for x in range(width):
        maybe_enqueue(x, 0)
        maybe_enqueue(x, height - 1)
    for y in range(height):
        maybe_enqueue(0, y)
        maybe_enqueue(width - 1, y)

    removed = 0
    while queue:
        x, y = queue.popleft()
        removed += 1
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                continue
            if mask[next_y][next_x]:
                continue
            rgba = pixels[next_x, next_y]
            if rgba[3] == 0 or _matches_background(
                rgba[:3],
                seed_colors=seed_colors,
                threshold=threshold,
            ):
                mask[next_y][next_x] = True
                queue.append((next_x, next_y))

    return mask, removed


def _create_transparent_png_variant(image_bytes: bytes) -> bytes:
    """Remove connected edge background and encode the result as PNG."""
    with Image.open(BytesIO(image_bytes)) as opened:
        image = opened.convert("RGBA")

    if _image_has_transparency(image):
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    width, height = image.size
    total_pixels = max(width * height, 1)
    seed_colors = _background_seed_colors(image)
    chosen_mask: list[list[bool]] | None = None

    for threshold in _candidate_background_thresholds(seed_colors):
        mask, removed = _build_background_mask(
            image,
            seed_colors=seed_colors,
            threshold=threshold,
        )
        removal_ratio = removed / total_pixels
        if 0.02 <= removal_ratio < 1.0:
            chosen_mask = mask
            break

    if chosen_mask is not None:
        pixels = image.load()
        for y, row in enumerate(chosen_mask):
            for x, is_background in enumerate(row):
                if not is_background:
                    continue
                red, green, blue, _alpha = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


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

    Returns the default logo asset plus a transparent PNG variant.
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
    asset_id = uuid.uuid4().hex
    default_logo_url = _upload_logo_variant(
        pack_id=pack_id,
        asset_id=asset_id,
        image_bytes=image_bytes,
        mime_type=mime_type,
        extension=extension,
    )
    transparent_logo_url = _upload_logo_variant(
        pack_id=pack_id,
        asset_id=asset_id,
        image_bytes=_create_transparent_png_variant(image_bytes),
        mime_type="image/png",
        extension="png",
        variant_name="transparent",
    )
    return {
        "logo_url": default_logo_url,
        "wordmark_svg_or_url": transparent_logo_url,
        "transparent_logo_url": transparent_logo_url,
    }


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

    On success returns the default logo plus a transparent PNG variant.
    On failure raises BadRequestError with a clear message when strict=True.
    When strict=False, returns empty logo fields.
    """
    settings = get_settings()
    prompt_text = _build_logo_prompt(
        brand_name, prompt, color_scheme, brand_os_summary, color_palette
    )
    no_logo_result: dict[str, str | None] = {
        "logo_url": None,
        "wordmark_svg_or_url": None,
        "transparent_logo_url": None,
    }

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
