"""Helpers for building generation context from pack data."""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainNotFoundError
from app.modules.brand_os.services import get_active_for_pack
from app.modules.packs.models import Pack
from app.modules.packs.onboarding.artifact_store import get_artifact
from app.modules.packs.onboarding.artifacts import (
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_BRAND_OS,
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
)
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


def _coalesce_text(*values: object) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _as_string_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    return []


def build_generation_brand_context(
    pack: Pack,
    brand_os=None,
    *,
    artifacts_only: bool = False,
) -> GenerationBrandContext:
    onboarding = _as_dict(getattr(pack, "onboarding_answers", None)) if not artifacts_only else {}
    normalized_profile = get_artifact(pack, ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE)
    brand_os_artifact = get_artifact(pack, ARTIFACT_TYPE_BRAND_OS)
    brand_identity = get_artifact(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE)
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
    artifact_palette = _as_dict(getattr(brand_identity, "palette", None))
    palette_dict = artifact_palette or _json_dict(onboarding.get("palette"))
    palette = GenerationColorPalette(
        primary=str(palette_dict.get("primary") or "").strip() or None,
        secondary=str(palette_dict.get("secondary") or "").strip() or None,
        accent=str(palette_dict.get("accent") or "").strip() or None,
    )

    logo_raw = (
        getattr(brand_identity, "primary_logo_url", None)
        or onboarding.get("wordmark_svg_or_url")
        or onboarding.get("wordmark_result")
    )
    logo_url: str | None = None
    logo_markup: str | None = None
    if isinstance(logo_raw, str) and logo_raw.strip():
        cleaned_logo = logo_raw.strip()
        if cleaned_logo.lstrip().startswith("<"):
            logo_markup = cleaned_logo
        else:
            logo_url = cleaned_logo

    audience_personas: list[GenerationAudiencePersona] = []
    artifact_audience_personas = getattr(brand_os_artifact, "audience_personas", None)
    audience_personas_raw = artifact_audience_personas if artifact_audience_personas else strategy.get("audience_personas")
    if isinstance(audience_personas_raw, list):
        for persona in audience_personas_raw:
            if isinstance(persona, dict):
                persona_name = str(persona.get("persona") or "").strip()
                needs = [
                    str(item).strip()
                    for item in persona.get("needs") or []
                    if str(item).strip()
                ]
                pain_points = [
                    str(item).strip()
                    for item in persona.get("pain_points") or []
                    if str(item).strip()
                ]
            else:
                persona_name = str(getattr(persona, "persona", "") or "").strip()
                needs = [str(item).strip() for item in getattr(persona, "needs", []) or [] if str(item).strip()]
                pain_points = [
                    str(item).strip()
                    for item in getattr(persona, "pain_points", []) or []
                    if str(item).strip()
                ]
            if not persona_name:
                continue
            audience_personas.append(
                GenerationAudiencePersona(
                    persona=persona_name,
                    needs=needs,
                    pain_points=pain_points,
                )
            )

    proof_points = _as_string_list(getattr(normalized_profile, "proof_points", None)) or _as_string_list(
        getattr(brand_os_artifact, "proof_points", None)
    ) or [
        str(item).strip()
        for item in messaging.get("proof_points") or []
        if str(item).strip()
    ]
    brand_purpose = _as_string_list(getattr(brand_os_artifact, "brand_purpose", None)) or [
        str(item).strip()
        for item in foundation.get("brand_purpose") or []
        if str(item).strip()
    ]
    main_audience = _as_string_list(getattr(brand_os_artifact, "main_audience", None)) or [
        str(item).strip()
        for item in foundation.get("main_audience") or []
        if str(item).strip()
    ]
    design_cues = _as_string_list(getattr(brand_os_artifact, "design_cues", None)) or _as_string_list(
        getattr(brand_identity, "visual_keywords", None)
    ) or [
        str(item).strip()
        for item in style.get("design_cues") or []
        if str(item).strip()
    ]
    style_palette = _as_string_list(getattr(brand_os_artifact, "style_palette", None)) or _as_string_list(
        getattr(brand_identity, "palette_direction", None)
    ) or [
        str(item).strip()
        for item in style.get("palette") or []
        if str(item).strip()
    ]
    voice_traits = _as_string_list(getattr(brand_os_artifact, "tone_attributes", None)) or _as_string_list(
        getattr(brand_identity, "personality_traits", None)
    ) or [
        str(item).strip()
        for item in voice.get("profile") or []
        if str(item).strip()
    ]
    fonts = _as_string_list(getattr(brand_identity, "fonts", None)) or _json_list(onboarding.get("fonts"))

    color_palette = None
    if palette.primary or palette.secondary or palette.accent:
        color_palette = palette

    return GenerationBrandContext(
        brand_name=_coalesce_text(
            getattr(normalized_profile, "business_name", None),
            getattr(brand_os_artifact, "brand_name", None),
            getattr(pack, "brand_name", None) if not artifacts_only else None,
            foundation.get("brand_name"),
        ),
        industry=_coalesce_text(
            getattr(normalized_profile, "industry", None),
            getattr(brand_os_artifact, "industry", None),
            foundation.get("brand_industry"),
        ),
        target_audience=_coalesce_text(
            getattr(normalized_profile, "target_audience", None),
            getattr(pack, "target_audience", None) if not artifacts_only else None,
        ),
        main_audience=main_audience or None,
        core_offer=_coalesce_text(
            getattr(normalized_profile, "core_offer", None),
            getattr(brand_os_artifact, "one_line_offer", None),
            getattr(pack, "offer_one_liner", None) if not artifacts_only else None,
            foundation.get("one_line_offer"),
        ),
        primary_cta=_coalesce_text(
            getattr(normalized_profile, "primary_cta", None),
            getattr(pack, "primary_cta", None) if not artifacts_only else None,
        ),
        primary_pain=_coalesce_text(
            getattr(normalized_profile, "problem_solved", None),
            getattr(pack, "primary_pain", None) if not artifacts_only else None,
        ),
        primary_outcome=_coalesce_text(
            getattr(normalized_profile, "primary_outcome", None),
            getattr(pack, "primary_outcome", None) if not artifacts_only else None,
        ),
        hero_angle=getattr(pack, "hero_angle", None) if not artifacts_only else None,
        usp_statement=_coalesce_text(
            getattr(brand_os_artifact, "unique_advantage", None),
            getattr(pack, "usp_statement", None) if not artifacts_only else None,
            _as_string_list(getattr(normalized_profile, "differentiators", None))[0] if normalized_profile and _as_string_list(getattr(normalized_profile, "differentiators", None)) else None,
        ),
        usp_proof=_coalesce_text(
            getattr(pack, "usp_proof", None) if not artifacts_only else None,
            _as_string_list(getattr(normalized_profile, "proof_points", None))[0] if normalized_profile and _as_string_list(getattr(normalized_profile, "proof_points", None)) else None,
            proof_points[0] if proof_points else None,
        ),
        logo_url=logo_url,
        logo_markup=logo_markup,
        color_palette=color_palette,
        fonts=fonts or None,
        brand_purpose=brand_purpose or None,
        mission=_coalesce_text(getattr(brand_os_artifact, "mission", None), mission_vision.get("mission")),
        vision=_coalesce_text(getattr(brand_os_artifact, "vision", None), mission_vision.get("vision")),
        promise=_coalesce_text(getattr(brand_os_artifact, "promise", None), mission_vision.get("promise")),
        elevator_pitch=_coalesce_text(
            getattr(brand_os_artifact, "elevator_pitch", None),
            messaging.get("elevator_pitch"),
        ),
        proof_points=proof_points or None,
        audience_personas=audience_personas or None,
        voice_archetype=_coalesce_text(
            getattr(brand_os_artifact, "voice_archetype", None),
            voice.get("archetype"),
        ),
        voice_traits=voice_traits or None,
        design_cues=design_cues or None,
        style_palette=style_palette or None,
        typography_direction=_coalesce_text(
            getattr(brand_identity, "typography_direction", None),
            getattr(brand_os_artifact, "typography_direction", None),
            str(style.get("typography") or "").strip() or None,
        ),
    )


def load_generation_brand_context(
    db: Session,
    pack_id: UUID,
    pack: Pack | None = None,
    *,
    artifacts_only: bool = False,
) -> GenerationBrandContext:
    pack_row = pack
    if pack_row is None:
        from app.modules.packs.models import Pack as PackModel

        pack_row = db.query(PackModel).filter(PackModel.id == pack_id).first()
        if pack_row is None:
            raise DomainNotFoundError("Pack not found")

    active_brand_os = get_active_for_pack(db, pack_id)
    return build_generation_brand_context(
        pack_row,
        brand_os=active_brand_os,
        artifacts_only=artifacts_only,
    )
