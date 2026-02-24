"""Onboarding: extract brand (URL/paste) and generate starter brand (wordmark + palette)."""

import json

from app.core.config import get_settings
from app.core.logging import log_service_action
from app.modules.packs.extraction.website_scraper import extract_brand_from_website
from app.shared.services.llm import get_llm


def _extract_offer_cues_from_profile(profile: dict) -> list[str]:
    """Extract offer cues from brand profile."""
    cues = []
    
    if profile.get("value_proposition"):
        cues.append(profile["value_proposition"])
    
    # Add top products/services as cues
    products = profile.get("products_or_services", [])
    if products:
        cues.extend(products[:3])
    
    return cues


@log_service_action()
async def extract_brand(
    input_type: str,
    url: str | None = None,
    pasted_text: str | None = None,
    logo_file_key: str | None = None,
) -> dict:
    """
    Extract brand profile from URL, pasted text, or logo.
    
    Returns a rich brand profile with name, description, colors, contacts, etc.
    """
    if input_type == "url" and url:
        # Use advanced website extraction
        llm = get_llm()
        try:
            profile, color_candidates = await extract_brand_from_website(url, llm)
            profile_dict = profile.model_dump()
            
            # Extract offer cues from the profile
            offer_cues = _extract_offer_cues_from_profile(profile_dict)
            
            return {
                "brand_name": profile_dict.get("brand_name") or "My Brand",
                "offer_cues": offer_cues,
                "tagline": profile_dict.get("tagline"),
                "description": profile_dict.get("description"),
                "industry": profile_dict.get("industry"),
                "contact_info": profile_dict.get("contact_info", {}),
                "social_links": profile_dict.get("social_links", []),
                "logo_url": profile_dict.get("logo_url"),
                "color_candidates": [c.hex if hasattr(c, 'hex') else c for c in color_candidates],
                "raw_extract": {"source": "url", "url": url},
            }
        except Exception as e:
            # Fallback to basic extraction on error
            return {
                "brand_name": "My Brand",
                "offer_cues": [],
                "raw_extract": {"url": url, "error": str(e), "source": "url"},
            }
    
    if input_type == "paste" and pasted_text:
        # For pasted text, use simple LLM extraction
        from openai import OpenAI
        
        settings = get_settings()
        if not settings.openai_api_key:
            return {"brand_name": "My Brand", "offer_cues": [], "raw_extract": {}}
        
        client = OpenAI(api_key=settings.openai_api_key)
        sys = (
            "You extract brand name and offer cues (value props, differentiators) from the given content. "
            "Return only valid JSON with keys: brand_name (string), offer_cues (array of strings). "
            "No markdown, no explanation."
        )
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"Pasted copy:\n\n{pasted_text[:8000]}"},
                ],
                temperature=0.1,
            )
            text = (r.choices[0].message.content or "{}").strip()
            text = text.removeprefix("```json").removeprefix("```").strip()
            out = json.loads(text)
            out.setdefault("raw_extract", {})["source"] = "paste"
            return out
        except Exception:
            return {"brand_name": "My Brand", "offer_cues": [], "raw_extract": {"source": "paste"}}
    
    if input_type == "logo" and logo_file_key:
        # Placeholder: no vision yet; return stub
        return {
            "brand_name": "My Brand",
            "offer_cues": [],
            "raw_extract": {"logo_file_key": logo_file_key, "source": "logo"},
        }
    
    return {"brand_name": "My Brand", "offer_cues": [], "raw_extract": {}}


def _call_openai_palette(
    brand_name: str,
    vibe_chips: list[str],
    onboarding_context: dict | None = None,
) -> dict:
    """Generate a colour palette from brand name, vibe chips, and optional onboarding context."""
    from openai import OpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        return {"primary": "#2563eb", "secondary": "#64748b", "accent": "#f59e0b"}
    client = OpenAI(api_key=settings.openai_api_key)
    chips = ", ".join(vibe_chips) if vibe_chips else "professional, modern"
    prompt = (
        f"Brand: {brand_name}. Vibe: {chips}. "
        "Create a distinctive, memorable color palette—not generic. "
        "Return only valid JSON with keys: primary, secondary, accent (hex, e.g. #2563eb). "
        "Optionally add 'surface' (hex) for backgrounds. No markdown."
    )
    if onboarding_context:
        parts = []
        for k, v in onboarding_context.items():
            if v and isinstance(v, str) and v.strip():
                parts.append(f"{k}: {v.strip()[:200]}")
        if parts:
            prompt += " Context: " + "; ".join(parts)
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        text = (r.choices[0].message.content or "{}").strip()
        text = text.removeprefix("```json").removeprefix("```").strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            data = {}
        return {
            "primary": data.get("primary", "#2563eb"),
            "secondary": data.get("secondary", "#64748b"),
            "accent": data.get("accent", "#f59e0b"),
            "surface": data.get("surface"),
        }
    except Exception:
        return {"primary": "#2563eb", "secondary": "#64748b", "accent": "#f59e0b"}


PLACEHOLDER_LOGO_URL = "/logos/logo_black.svg"


@log_service_action()
def generate_starter_brand(
    brand_name: str,
    vibe_chips: list[str],
    onboarding_context: dict | None = None,
    pack_id: str | None = None,
) -> dict:
    """
    Generate palette (AI) and an AI-generated logo image URL.
    Falls back to a static placeholder when no image provider is configured.
    """
    from app.core.logging import get_logger

    logger = get_logger("klarnow.services.onboarding")
    palette = _call_openai_palette(brand_name, vibe_chips, onboarding_context)

    logo_url: str | None = None
    if pack_id:
        chips_str = ", ".join(vibe_chips) if vibe_chips else "professional, modern"
        try:
            from app.modules.packs.logo_generation import generate_logo_with_gemini

            result = generate_logo_with_gemini(
                brand_name=brand_name,
                prompt=f"distinctive, memorable logo mark—{chips_str}, not generic or clipart",
                pack_id=pack_id,
                color_scheme="use the provided palette",
                brand_os_summary=None,
                color_palette=palette,
            )
            logo_url = result.get("logo_url") or result.get("wordmark_svg_or_url")
        except Exception as e:
            logger.warning("starter brand logo generation failed: %s", e, exc_info=True)

    wordmark = logo_url or PLACEHOLDER_LOGO_URL
    return {"wordmark_svg_or_url": wordmark, "palette": palette}
