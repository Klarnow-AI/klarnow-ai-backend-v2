"""Helpers for building generation context from pack data."""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.brand_os.services import get_active_for_pack
from app.modules.packs.models import Pack
from app.shared.generation_schemas import (
    GenerationAudiencePersona,
    GenerationBrandContext,
    GenerationColorPalette,
)


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _json_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _json_dict(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def build_generation_brand_context(pack: Pack, brand_os=None) -> GenerationBrandContext:
    onboarding = _as_dict(pack.onboarding_answers)
    if brand_os is None:
        foundation = {}
        strategy = {}
    else:
        foundation = _as_dict(getattr(brand_os, "foundation", None))
        strategy = _as_dict(getattr(brand_os, "brand_strategy", None))

    mission_vision = _as_dict(strategy.get("mission_vision"))
    messaging = _as_dict(strategy.get("core_messaging_hierarchy"))
    voice = _as_dict(strategy.get("voice_personality"))
    style = _as_dict(strategy.get("style_direction_seeds"))

    palette_dict = _json_dict(onboarding.get("palette"))
    palette = GenerationColorPalette(
        primary=str(palette_dict.get("primary") or "").strip() or None,
        secondary=str(palette_dict.get("secondary") or "").strip() or None,
        accent=str(palette_dict.get("accent") or "").strip() or None,
    )

    logo_raw = onboarding.get("wordmark_svg_or_url") or onboarding.get("wordmark_result")
    logo_url: str | None = None
    if isinstance(logo_raw, str) and logo_raw.strip() and not logo_raw.lstrip().startswith("<"):
        logo_url = logo_raw.strip()

    audience_personas_raw = strategy.get("audience_personas")
    audience_personas: list[GenerationAudiencePersona] = []
    if isinstance(audience_personas_raw, list):
        for persona in audience_personas_raw:
            if not isinstance(persona, dict):
                continue
            name = str(persona.get("persona") or "").strip()
            if not name:
                continue
            audience_personas.append(
                GenerationAudiencePersona(
                    persona=name,
                    needs=[
                        str(item).strip()
                        for item in persona.get("needs") or []
                        if str(item).strip()
                    ],
                    pain_points=[
                        str(item).strip()
                        for item in persona.get("pain_points") or []
                        if str(item).strip()
                    ],
                )
            )

    proof_points = [
        str(item).strip()
        for item in messaging.get("proof_points") or []
        if str(item).strip()
    ]
    design_cues = [
        str(item).strip()
        for item in style.get("design_cues") or []
        if str(item).strip()
    ]
    fonts = _json_list(onboarding.get("fonts"))

    color_palette = None
    if palette.primary or palette.secondary or palette.accent:
        color_palette = palette

    return GenerationBrandContext(
        brand_name=pack.brand_name or foundation.get("brand_name"),
        industry=foundation.get("brand_industry"),
        core_offer=pack.offer_one_liner or foundation.get("one_line_offer"),
        primary_cta=pack.primary_cta,
        primary_pain=pack.primary_pain,
        primary_outcome=pack.primary_outcome,
        hero_angle=pack.hero_angle,
        usp_statement=pack.usp_statement,
        usp_proof=pack.usp_proof,
        logo_url=logo_url,
        color_palette=color_palette,
        fonts=fonts or None,
        mission=mission_vision.get("mission"),
        vision=mission_vision.get("vision"),
        elevator_pitch=messaging.get("elevator_pitch"),
        proof_points=proof_points or None,
        audience_personas=audience_personas or None,
        voice_archetype=voice.get("archetype"),
        design_cues=design_cues or None,
    )


def load_generation_brand_context(db: Session, pack_id: UUID, pack: Pack | None = None) -> GenerationBrandContext:
    pack_row = pack
    if pack_row is None:
        from app.modules.packs.models import Pack as PackModel

        pack_row = db.query(PackModel).filter(PackModel.id == pack_id).first()
        if pack_row is None:
            raise ValueError("Pack not found")

    active_brand_os = get_active_for_pack(db, pack_id)
    return build_generation_brand_context(pack_row, brand_os=active_brand_os)
