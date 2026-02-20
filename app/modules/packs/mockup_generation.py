"""Brand mockup image generation via BFL FLUX.2 Pro with actual brand logo as input reference."""

import time
import uuid

import requests

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger, log_service_action
from app.core.storage import upload_file, get_presigned_url

BFL_FLUX2_PRO_URL = "https://api.bfl.ai/v1/flux-2-pro"
BFL_POLL_INTERVAL = 3
BFL_POLL_TIMEOUT = 120
BFL_PROMPT_MAX_LENGTH = 1000

logger = get_logger("klarnow.services.mockup_generation")

# Fixed, ordered scenes sized for the bento layout to match:
# Hero(2×2), PortraitProduct(1×2), Product(2×2), Product(2×1), Product(2×1)
MOCKUP_SCENES = [
    {
        "id": "hero_billboard",
        "prompt": (
            "Professional marketing mockup: outdoor billboard in a modern urban setting "
            "prominently displaying the logo from the provided image. "
            "Clean design, high quality, photorealistic"
        ),
        "size_api": "1536x1024",
        "width": 1536,
        "height": 1024,
        "size": "large",
    },
    {
        "id": "portrait_product",
        "prompt": (
            "Professional product photography mockup: a single hero product photographed in portrait orientation "
            "on a clean studio background with soft lighting, with tasteful brand placement using the logo from the provided image. "
            "Photorealistic, premium e-commerce style"
        ),
        "size_api": "1024x1536",
        "width": 1024,
        "height": 1536,
        "size": "tall",
    },
    {
        "id": "product_court_scene",
        "prompt": (
            "Professional brand mockup: an in-situ venue or court scene (e.g., sports court surface, wall, or banner) "
            "showing the brand identity applied in a realistic way, prominently featuring the logo from the provided image. "
            "Clean composition, photorealistic"
        ),
        "size_api": "1024x1024",
        "width": 1024,
        "height": 1024,
        "size": "large",
    },
    {
        "id": "product_apparel",
        "prompt": (
            "Professional apparel mockup: a branded t-shirt or hoodie flat-lay in a clean studio setup, "
            "showing the logo from the provided image clearly on the garment. "
            "Photorealistic, modern"
        ),
        "size_api": "1536x1024",
        "width": 1536,
        "height": 1024,
        "size": "medium",
    },
    {
        "id": "product_packaging_lifestyle",
        "prompt": (
            "Professional packaging lifestyle mockup: a product box, bag, or bottle in a realistic lifestyle scene "
            "(e.g., on a shelf, counter, or in a minimal environment), incorporating the brand identity and logo from the provided image. "
            "Photorealistic, premium"
        ),
        "size_api": "1536x1024",
        "width": 1536,
        "height": 1024,
        "size": "medium",
    },
]


# ---------------------------------------------------------------------------
# Image generation helpers
# ---------------------------------------------------------------------------

def _generate_one_bfl(
    *,
    prompt_text: str,
    pack_id: str,
    scene: dict,
    logo_url: str,
) -> dict | None:
    """Generate one mockup via BFL FLUX.2 Pro with logo as input_image reference."""
    settings = get_settings()
    if not settings.bfl_api_key:
        return None

    headers = {
        "x-key": settings.bfl_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "prompt": prompt_text[:BFL_PROMPT_MAX_LENGTH],
        "input_image": logo_url,
        "output_format": "png",
        "width": int(scene["width"]),
        "height": int(scene["height"]),
        "safety_tolerance": 2,
    }

    try:
        resp = requests.post(BFL_FLUX2_PRO_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("mockup_generation: BFL submit failed: %s", e, exc_info=True)
        return None

    task_id = data.get("id")
    polling_url = data.get("polling_url")
    if not task_id or not polling_url:
        logger.warning("mockup_generation: BFL response missing id or polling_url: %s", data)
        return None

    deadline = time.monotonic() + BFL_POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            poll_resp = requests.get(polling_url, headers=headers, timeout=30)
            poll_resp.raise_for_status()
            result_data = poll_resp.json()
        except Exception as e:
            logger.warning("mockup_generation: BFL poll failed: %s", e, exc_info=True)
            return None

        status = result_data.get("status")
        if status == "Ready":
            break
        if status in ("Error", "Request Moderated", "Content Moderated", "Task not found"):
            logger.warning("mockup_generation: BFL task ended with status=%s", status)
            return None
        time.sleep(BFL_POLL_INTERVAL)
    else:
        logger.warning("mockup_generation: BFL poll timed out after %ss", BFL_POLL_TIMEOUT)
        return None

    result = result_data.get("result")
    if not result:
        logger.warning("mockup_generation: BFL result missing 'result'")
        return None

    image_url = result.get("sample") or result.get("image_url") or result.get("url")
    if not image_url:
        logger.warning("mockup_generation: BFL result has no image URL; keys=%s", list(result.keys()))
        return None

    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        image_bytes = img_resp.content
    except Exception as e:
        logger.warning("mockup_generation: image download failed: %s", e, exc_info=True)
        return None

    if not image_bytes:
        return None

    key = f"mockups/{pack_id}/{uuid.uuid4().hex}.png"
    uploaded = upload_file(key, image_bytes, content_type="image/png")
    if not uploaded:
        return None

    url = get_presigned_url(key, expires_in=86400 * 7) or f"key:{key}"
    return {"url": url, "width": scene["width"], "height": scene["height"]}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

@log_service_action()
def generate_mockups(
    pack_id: str,
    brand_name: str,
    logo_url: str,
    brand_os_summary: str | None = None,
) -> list[dict]:
    """
    Generate mockup images using fixed bento-sized scenes and the brand's actual
    logo as a gpt-image-1 input reference.

    Requires BFL_API_KEY. Raises BadRequestError when not configured.
    Returns list of {"id", "url", "width", "height", "size"}.
    """
    settings = get_settings()
    if not settings.bfl_api_key:
        raise BadRequestError(
            "Brand mockup generation requires BFL_API_KEY. "
            "Set it in your environment to generate mockups."
        )

    context = (brand_os_summary or "").strip()
    prefix = f"Brand: {brand_name}. " if brand_name else ""
    if context:
        prefix = prefix + f"Brand context: {context[:800]}. "

    results: list[dict] = []
    for scene in MOCKUP_SCENES:
        prompt_text = prefix + scene["prompt"]
        out = _generate_one_bfl(
            prompt_text=prompt_text,
            pack_id=pack_id,
            scene=scene,
            logo_url=logo_url,
        )
        if out:
            results.append({
                "id": f"mockup-{scene['id']}-{uuid.uuid4().hex[:8]}",
                "url": out["url"],
                "width": out.get("width", scene["width"]),
                "height": out.get("height", scene["height"]),
                "size": scene["size"],
            })
        else:
            logger.warning(
                "mockup_generation: skipped scene %s (generation failed)",
                scene["id"],
            )

    return results
