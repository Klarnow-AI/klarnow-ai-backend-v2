"""Brand identity AI suggestions: typography and palette for packs."""

import json
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.brand_os.services import get_active_for_pack
from app.modules.packs.models import Pack

logger = get_logger("klarnow.packs.brand_identity_suggestions")


def _brand_identity_ai_unavailable_reason() -> str | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return "Brand identity AI suggestions need OPENAI_API_KEY to be set."
    if not settings.ai_brand_identity_suggestions_enabled:
        return (
            "Brand identity AI suggestions are disabled. Set "
            "AI_BRAND_IDENTITY_SUGGESTIONS_ENABLED=true and restart the backend."
        )
    return None


def _pack_context_for_suggestions(db: Session, pack: Pack) -> str:
    """Build context string from pack and optional Brand OS for LLM prompts."""
    parts = []
    if pack.brand_name:
        parts.append(f"Brand name: {pack.brand_name}")
    if pack.usp_statement:
        parts.append(f"USP: {pack.usp_statement}")
    if pack.primary_cta:
        parts.append(f"Primary CTA: {pack.primary_cta}")
    if pack.offer_one_liner:
        parts.append(f"Offer: {pack.offer_one_liner}")
    if pack.hero_angle:
        parts.append(f"Hero angle: {pack.hero_angle}")
    if pack.business_type:
        parts.append(f"Business type: {pack.business_type}")

    active = get_active_for_pack(db, pack.id)
    if active and active.brand_strategy and isinstance(active.brand_strategy, dict):
        bs = active.brand_strategy
        mv = bs.get("mission_vision") or {}
        if mv.get("mission"):
            parts.append(f"Mission: {mv['mission'][:300]}")
        voice = bs.get("voice_personality") or {}
        if voice.get("archetype"):
            parts.append(f"Voice: {voice['archetype']}")
        msg = bs.get("core_messaging_hierarchy") or {}
        if msg.get("elevator_pitch"):
            parts.append(f"Elevator pitch: {msg['elevator_pitch'][:300]}")
        style = bs.get("style_direction_seeds") or {}
        if style.get("design_cues"):
            parts.append(f"Design cues: {', '.join(style['design_cues'][:5])}")

    return "\n".join(parts) if parts else "No brand context yet."


def suggest_typography(
    db: Session,
    pack_id: UUID,
    current_headline: str | None = None,
    current_body: str | None = None,
) -> dict:
    """
    Suggest headline and body font names for the pack using OpenAI.
    Returns {"headline_font": str, "body_font": str}.
    Uses only web-safe or Google Fonts that are free and widely available.
    """
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {"headline_font": "Inter", "body_font": "Inter"}

    context = _pack_context_for_suggestions(db, pack)
    refine = current_headline or current_body
    instruction = (
        "Refine the following typography to better match the brand."
        if refine
        else "Suggest an initial typography pair that fits the brand."
    )
    current_line = ""
    if current_headline or current_body:
        current_line = f"Current: headline={current_headline or 'none'}, body={current_body or 'none'}."

    prompt = f"""You are a brand and UI designer. Given the brand context below, {instruction}

Brand context:
{context}
{current_line}

Respond with ONLY a valid JSON object with exactly two keys: "headline_font" and "body_font".
Each value must be a single font family name (e.g. "Playfair Display", "Inter", "Lato").
Use only web-safe or Google Fonts that are free and widely available. No markdown, no explanation."""

    unavailable_reason = _brand_identity_ai_unavailable_reason()
    if unavailable_reason:
        return {
            "headline_font": current_headline or "Inter",
            "body_font": current_body or "Open Sans",
            "source": "fallback",
            "reason": unavailable_reason,
        }

    try:
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )
        text = (r.choices[0].message.content or "{}").strip()
        text = text.removeprefix("```json").removeprefix("```").strip()
        data = json.loads(text)
        headline = (data.get("headline_font") or "Inter").strip()
        body = (data.get("body_font") or "Open Sans").strip()
        return {
            "headline_font": headline,
            "body_font": body,
            "source": "ai",
            "reason": None,
        }
    except Exception as e:
        logger.warning("suggest_typography failed: %s", e)
        return {
            "headline_font": current_headline or "Inter",
            "body_font": current_body or "Open Sans",
            "source": "fallback",
            "reason": "Brand identity AI suggestions are temporarily unavailable. Please try again.",
        }


def suggest_palette(
    db: Session,
    pack_id: UUID,
    current_palette: dict | None = None,
) -> dict:
    """
    Suggest primary, secondary, accent (and optionally background, surface) hex colors.
    Returns {"primary": "#hex", "secondary": "#hex", "accent": "#hex", ...}.
    """
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {"primary": "#2563eb", "secondary": "#64748b", "accent": "#f59e0b"}

    context = _pack_context_for_suggestions(db, pack)
    refine = current_palette and any(
        v for k, v in (current_palette or {}).items() if v and k in ("primary", "secondary", "accent")
    )
    instruction = (
        "Refine the following color palette to better match the brand (keep hex format)."
        if refine
        else "Suggest a distinctive, memorable color palette—not generic."
    )
    current_line = ""
    if current_palette:
        parts = [f"{k}: {v}" for k, v in current_palette.items() if v]
        if parts:
            current_line = "Current palette: " + ", ".join(parts)

    prompt = f"""You are a brand designer. Given the brand context below, {instruction}

Brand context:
{context}
{current_line}

Return ONLY a valid JSON object with keys: "primary", "secondary", "accent".
Each value must be a hex color (e.g. "#2563eb"). Optionally add "background" and "surface" (hex).
Ensure colors work well together and are accessible. No markdown, no explanation."""

    unavailable_reason = _brand_identity_ai_unavailable_reason()
    if unavailable_reason:
        fallback_palette = {
            "primary": (current_palette or {}).get("primary") or "#2563eb",
            "secondary": (current_palette or {}).get("secondary") or "#64748b",
            "accent": (current_palette or {}).get("accent") or "#f59e0b",
            "source": "fallback",
            "reason": unavailable_reason,
        }
        background = (current_palette or {}).get("background")
        surface = (current_palette or {}).get("surface")
        if background:
            fallback_palette["background"] = background
        if surface:
            fallback_palette["surface"] = surface
        return fallback_palette

    try:
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        text = (r.choices[0].message.content or "{}").strip()
        text = text.removeprefix("```json").removeprefix("```").strip()
        data = json.loads(text)
        out = {
            "primary": (data.get("primary") or "#2563eb").strip(),
            "secondary": (data.get("secondary") or "#64748b").strip(),
            "accent": (data.get("accent") or "#f59e0b").strip(),
            "source": "ai",
            "reason": None,
        }
        if data.get("background"):
            out["background"] = data["background"].strip()
        if data.get("surface"):
            out["surface"] = data["surface"].strip()
        return out
    except Exception as e:
        logger.warning("suggest_palette failed: %s", e)
        fallback_palette = {
            "primary": (current_palette or {}).get("primary") or "#2563eb",
            "secondary": (current_palette or {}).get("secondary") or "#64748b",
            "accent": (current_palette or {}).get("accent") or "#f59e0b",
            "source": "fallback",
            "reason": "Brand identity AI suggestions are temporarily unavailable. Please try again.",
        }
        background = (current_palette or {}).get("background")
        surface = (current_palette or {}).get("surface")
        if background:
            fallback_palette["background"] = background
        if surface:
            fallback_palette["surface"] = surface
        return fallback_palette
