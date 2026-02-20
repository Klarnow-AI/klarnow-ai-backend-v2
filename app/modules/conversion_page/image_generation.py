"""Hero image generation for conversion pages using BFL FLUX.2 Pro."""

import time
import uuid

import requests

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.core.storage import upload_file, get_presigned_url

BFL_FLUX2_PRO_URL = "https://api.bfl.ai/v1/flux-2-pro"
BFL_POLL_INTERVAL = 3
BFL_POLL_TIMEOUT = 120

logger = get_logger("klarnow.conversion_page.image_generation")


def _build_hero_image_prompt(
    brand_name: str,
    offer: str,
    hero_angle: str,
    business_type: str,
    target_audience: str | None = None,
) -> str:
    """
    Build prompt for hero image generation based on business context.
    
    Args:
        brand_name: Brand name
        offer: Offer one-liner
        hero_angle: speed | quality | specialist | value
        business_type: product | service | coach
        target_audience: Optional target audience description
    """
    # Base style for professional marketing imagery
    base_style = "Professional marketing hero image, high quality, modern, clean composition"
    
    # Business type specific imagery
    type_guidance = {
        "product": "product showcase, lifestyle photography, premium product presentation",
        "service": "professional team environment, people collaborating, modern office or service setting",
        "coach": "professional consultant or expert, authoritative presence, inspirational setting",
    }
    type_spec = type_guidance.get(business_type, type_guidance["service"])
    
    # Hero angle specific mood and emphasis
    angle_guidance = {
        "speed": "dynamic, energetic composition with sense of movement and progress, vibrant colors",
        "quality": "premium aesthetic, attention to detail, luxurious materials, sophisticated lighting",
        "specialist": "focused expertise visualization, precision tools or workspace, professional depth",
        "value": "practical and accessible feel, approachable composition, smart solution visualization",
    }
    angle_mood = angle_guidance.get(hero_angle, angle_guidance["quality"])
    
    # Audience context if provided
    audience_context = ""
    if target_audience:
        audience_context = f"tailored for {target_audience}, "
    
    prompt = (
        f"{base_style}. {type_spec}. Context: {offer} for {brand_name}. "
        f"{audience_context}{angle_mood}. Photorealistic, marketing-grade quality, "
        f"suitable for conversion page hero section. No text overlays, no brand logos in image. "
        f"Focus on conveying professionalism and trust."
    )
    
    return prompt


def _call_bfl_flux(prompt: str, pack_id: str) -> str | None:
    """
    Call BFL FLUX 2 Pro API and poll for result.
    
    Args:
        prompt: Image generation prompt
        pack_id: Pack ID for file naming
        
    Returns:
        S3 URL of generated image, or None if generation fails
    """
    settings = get_settings()
    if not settings.bfl_api_key:
        logger.warning("BFL API key not configured")
        return None
    
    try:
        # Submit generation request
        logger.info("Submitting hero image generation to BFL FLUX")
        response = requests.post(
            BFL_FLUX2_PRO_URL,
            headers={"X-Key": settings.bfl_api_key},
            json={
                "prompt": prompt[:1000],  # BFL limit
                "width": 1536,
                "height": 1024,  # 3:2 ratio good for hero sections
                "prompt_upsampling": False,
                "safety_tolerance": 2,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        request_id = result.get("id")
        
        if not request_id:
            logger.error("No request ID returned from BFL")
            return None
        
        # Poll for completion
        logger.info(f"Polling BFL for completion (request_id: {request_id})")
        start_time = time.time()
        get_url = f"https://api.bfl.ai/v1/get_result?id={request_id}"
        
        while time.time() - start_time < BFL_POLL_TIMEOUT:
            time.sleep(BFL_POLL_INTERVAL)
            
            poll_response = requests.get(
                get_url,
                headers={"X-Key": settings.bfl_api_key},
                timeout=30,
            )
            poll_response.raise_for_status()
            poll_data = poll_response.json()
            
            status = poll_data.get("status")
            
            if status == "Ready":
                image_url = poll_data.get("result", {}).get("sample")
                if not image_url:
                    logger.error("No image URL in BFL result")
                    return None
                
                # Download and upload to S3
                logger.info("Downloading generated image from BFL")
                img_response = requests.get(image_url, timeout=60)
                img_response.raise_for_status()
                
                # Upload to S3
                filename = f"conversion_page/{pack_id}/hero_{uuid.uuid4().hex[:12]}.jpg"
                s3_key = upload_file(filename, img_response.content, "image/jpeg")
                
                if not s3_key:
                    logger.warning("S3 upload failed, returning BFL URL directly")
                    return image_url
                
                # Get presigned URL
                s3_url = get_presigned_url(s3_key, expiration=31536000)  # 1 year
                logger.info(f"Hero image uploaded to S3: {s3_key}")
                return s3_url or image_url
            
            elif status in ["Error", "Request Moderated"]:
                error_msg = poll_data.get("error") or status
                logger.error(f"BFL generation failed: {error_msg}")
                return None
        
        logger.error("BFL generation timed out")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"BFL API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during BFL generation: {e}")
        return None


def generate_hero_image(
    pack_id: str,
    brand_name: str,
    offer: str,
    hero_angle: str,
    business_type: str,
    target_audience: str | None = None,
) -> str | None:
    """
    Generate hero image for conversion page using BFL FLUX 2 Pro.
    
    Args:
        pack_id: Pack UUID as string
        brand_name: Brand name
        offer: Offer one-liner
        hero_angle: speed | quality | specialist | value
        business_type: product | service | coach
        target_audience: Optional target audience description
        
    Returns:
        S3 URL of generated hero image, or None if generation fails
        
    Note:
        This function can take 10-30 seconds to complete due to image generation time.
        Callers should handle this asynchronously or show loading states.
    """
    prompt = _build_hero_image_prompt(
        brand_name=brand_name,
        offer=offer,
        hero_angle=hero_angle,
        business_type=business_type,
        target_audience=target_audience,
    )
    
    logger.info(f"Generating hero image for pack {pack_id}: {brand_name}")
    return _call_bfl_flux(prompt, pack_id)


def _generate_gradient_fallback(hero_angle: str, business_type: str) -> dict:
    """
    Generate CSS gradient data as fallback when image generation fails.
    
    Returns:
        Dict with gradient_from, gradient_to hex colors
    """
    # Angle-specific gradient palettes
    gradients = {
        "speed": {"from": "#f97316", "to": "#dc2626"},  # Orange to red (energy)
        "quality": {"from": "#7c3aed", "to": "#4f46e5"},  # Purple to indigo (premium)
        "specialist": {"from": "#0891b2", "to": "#0e7490"},  # Cyan to teal (expertise)
        "value": {"from": "#16a34a", "to": "#15803d"},  # Green to darker green (value)
    }
    
    # Business type adjustments
    if business_type == "coach":
        # More professional, trust-building colors
        gradients = {
            "speed": {"from": "#0891b2", "to": "#0369a1"},
            "quality": {"from": "#4338ca", "to": "#3730a3"},
            "specialist": {"from": "#1e40af", "to": "#1e3a8a"},
            "value": {"from": "#059669", "to": "#047857"},
        }
    
    return gradients.get(hero_angle, gradients["quality"])


def get_hero_background_data(
    pack_id: str,
    brand_name: str,
    offer: str,
    hero_angle: str,
    business_type: str,
    target_audience: str | None = None,
    skip_image_generation: bool = False,
) -> dict:
    """
    Get hero background data with fallback to gradient if image generation fails.
    
    Args:
        pack_id: Pack UUID as string
        brand_name: Brand name
        offer: Offer one-liner
        hero_angle: speed | quality | specialist | value
        business_type: product | service | coach
        target_audience: Optional target audience description
        skip_image_generation: If True, skip image generation and use gradient
        
    Returns:
        Dict with either:
        - {"type": "image", "url": "https://..."} or
        - {"type": "gradient", "from": "#...", "to": "#..."}
    """
    if skip_image_generation:
        gradient = _generate_gradient_fallback(hero_angle, business_type)
        return {"type": "gradient", **gradient}
    
    image_url = generate_hero_image(
        pack_id=pack_id,
        brand_name=brand_name,
        offer=offer,
        hero_angle=hero_angle,
        business_type=business_type,
        target_audience=target_audience,
    )
    
    if image_url:
        return {"type": "image", "url": image_url}
    
    # Fallback to gradient
    logger.warning(f"Image generation failed for pack {pack_id}, using gradient fallback")
    gradient = _generate_gradient_fallback(hero_angle, business_type)
    return {"type": "gradient", **gradient}
