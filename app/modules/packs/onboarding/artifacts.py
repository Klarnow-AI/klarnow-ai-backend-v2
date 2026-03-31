"""Typed artifact contracts for the onboarding pipeline."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE = "normalized_business_profile"
ARTIFACT_TYPE_BRAND_OS = "brand_os"
ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE = "brand_identity_profile"
ARTIFACT_TYPE_WEBSITE_BLUEPRINT = "website_blueprint"
ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE = "creative_brief_bundle"
ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE = "video_brief_bundle"
ARTIFACT_TYPE_VIDEO_RENDER_RESULT = "video_render_result"
ARTIFACT_TYPE_QA_REPORT = "qa_report"
ARTIFACT_SCHEMA_VERSION = 1

ArtifactType = Literal[
    "normalized_business_profile",
    "brand_os",
    "brand_identity_profile",
    "website_blueprint",
    "creative_brief_bundle",
    "video_brief_bundle",
    "video_render_result",
    "qa_report",
]


def _text_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        cleaned: list[str] = []
        for item in value:
            text = _text_or_none(item)
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned
    return []


def _coalesce_text(*values: Any) -> str | None:
    for value in values:
        text = _text_or_none(value)
        if text:
            return text
    return None


def _dedupe_strings(*groups: Any) -> list[str]:
    values: list[str] = []
    for group in groups:
        for item in _string_list(group):
            if item not in values:
                values.append(item)
    return values


def _parse_palette(value: Any) -> dict[str, str]:
    palette = _json_dict(value)
    normalized: dict[str, str] = {}
    for key in ("primary", "secondary", "accent", "background", "surface"):
        text = _text_or_none(palette.get(key))
        if text:
            normalized[key] = text
    return normalized


def _parse_fonts(value: Any) -> list[str]:
    fonts = _string_list(value)
    return [font for font in fonts if font]


def _logo_assets(onboarding: dict[str, Any]) -> list[str]:
    assets = _dedupe_strings(
        onboarding.get("wordmark_svg_or_url"),
        onboarding.get("transparent_logo_url"),
        onboarding.get("generated_logo_url"),
    )
    suggested_raw = onboarding.get("suggested_logos")
    suggested = suggested_raw
    if isinstance(suggested_raw, str):
        try:
            suggested = json.loads(suggested_raw)
        except (TypeError, json.JSONDecodeError):
            suggested = []
    for item in _string_list(suggested):
        if item not in assets:
            assets.append(item)
    return assets


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ArtifactEvidence(ArtifactModel):
    field: str
    source: str
    value: str


class ArtifactAudiencePersona(ArtifactModel):
    persona: str
    needs: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)


class NormalizedBusinessProfile(ArtifactModel):
    business_name: str | None = None
    industry: str | None = None
    target_audience: str | None = None
    core_offer: str | None = None
    problem_solved: str | None = None
    differentiators: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    tone_preferences: list[str] = Field(default_factory=list)
    geographic_focus: list[str] = Field(default_factory=list)
    competitor_signals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    available_channels: list[str] = Field(default_factory=list)
    source_evidence: list[ArtifactEvidence] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    primary_cta: str | None = None
    primary_outcome: str | None = None
    why_started: str | None = None
    pack_type: str | None = None
    business_type: str | None = None
    has_existing_brand: bool | None = None
    brand_url: str | None = None
    vibe_chips: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)

    def to_brand_os_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "brand_name": self.business_name,
            "offer_one_liner": self.core_offer,
            "target_audience": self.target_audience,
            "primary_cta": self.primary_cta,
            "primary_pain": self.problem_solved,
            "primary_outcome": self.primary_outcome,
            "why_started": self.why_started,
            "pack_type": self.pack_type,
            "business_type": self.business_type,
            "brand_url": self.brand_url,
            "vibe_chips": self.vibe_chips or self.tone_preferences,
            "industry": self.industry,
            "differentiators": self.differentiators,
            "goals": self.goals,
            "tone_preferences": self.tone_preferences,
            "geographic_focus": self.geographic_focus,
            "competitor_signals": self.competitor_signals,
            "constraints": self.constraints,
            "available_channels": self.available_channels,
            "proof_points": self.proof_points,
            "missing_fields": self.missing_fields,
            "source_evidence": [item.model_dump(mode="json") for item in self.source_evidence],
        }
        if self.has_existing_brand is not None:
            payload["has_existing_brand"] = "yes" if self.has_existing_brand else "no"
        if self.differentiators:
            payload["usp_statement"] = self.differentiators[0]
        if self.proof_points:
            payload["proof_text"] = "\n".join(self.proof_points)
        return {key: value for key, value in payload.items() if value not in (None, [], {}, "")}


class BrandOSArtifact(ArtifactModel):
    brand_name: str | None = None
    industry: str | None = None
    mission: str | None = None
    vision: str | None = None
    promise: str | None = None
    brand_purpose: list[str] = Field(default_factory=list)
    main_audience: list[str] = Field(default_factory=list)
    audience_personas: list[ArtifactAudiencePersona] = Field(default_factory=list)
    positioning_statement: str | None = None
    unique_advantage: str | None = None
    one_line_offer: str | None = None
    value_proposition: str | None = None
    elevator_pitch: str | None = None
    messaging_pillars: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    voice_archetype: str | None = None
    tone_attributes: list[str] = Field(default_factory=list)
    design_cues: list[str] = Field(default_factory=list)
    style_palette: list[str] = Field(default_factory=list)
    typography_direction: str | None = None
    cta_framework: str | None = None
    strategic_summary: str | None = None
    source_version: str | None = None


class BrandIdentityProfile(ArtifactModel):
    personality_traits: list[str] = Field(default_factory=list)
    visual_keywords: list[str] = Field(default_factory=list)
    palette_direction: list[str] = Field(default_factory=list)
    palette: dict[str, str] = Field(default_factory=dict)
    typography_direction: str | None = None
    fonts: list[str] = Field(default_factory=list)
    logo_direction: str | None = None
    primary_logo_url: str | None = None
    logo_assets: list[str] = Field(default_factory=list)
    image_style: list[str] = Field(default_factory=list)
    voice_rules: list[str] = Field(default_factory=list)
    design_dos: list[str] = Field(default_factory=list)
    design_donts: list[str] = Field(default_factory=list)
    tagline_options: list[str] = Field(default_factory=list)


class WebsiteBlueprint(ArtifactModel):
    page_list: list[str] = Field(default_factory=list)
    page_goals: dict[str, str] = Field(default_factory=dict)
    section_hierarchy: dict[str, list[str]] = Field(default_factory=dict)
    copy_blocks: dict[str, str] = Field(default_factory=dict)
    trust_elements: list[str] = Field(default_factory=list)
    faq: list[str] = Field(default_factory=list)
    cta_map: dict[str, str] = Field(default_factory=dict)
    funnel_logic: list[str] = Field(default_factory=list)
    project_id: str | None = None
    summary: str | None = None


class CreativeBriefBundle(ArtifactModel):
    campaign_objective: str | None = None
    asset_audience: str | None = None
    headline_options: list[str] = Field(default_factory=list)
    support_copy: list[str] = Field(default_factory=list)
    cta: str | None = None
    design_briefs: list[str] = Field(default_factory=list)
    visual_prompts: list[str] = Field(default_factory=list)
    format_variants: list[str] = Field(default_factory=list)
    asset_names: list[str] = Field(default_factory=list)


class VideoBriefBundle(ArtifactModel):
    concept_summary: list[str] = Field(default_factory=list)
    hook: list[str] = Field(default_factory=list)
    storyboard: list[str] = Field(default_factory=list)
    voiceover_script: list[str] = Field(default_factory=list)
    captions: list[str] = Field(default_factory=list)
    end_frame_cta: str | None = None
    render_prompts: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)


class VideoRenderResult(ArtifactModel):
    asset_ids: list[str] = Field(default_factory=list)
    requested_count: int = Field(default=1, ge=1)
    rendered_count: int = Field(default=0, ge=0)
    end_frame_cta: str | None = None


class QAReport(ArtifactModel):
    overall_status: Literal["passed", "warning", "failed"] = "passed"
    consistency_score: int = Field(default=100, ge=0, le=100)
    passed_checks: list[str] = Field(default_factory=list)
    warning_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    repair_actions: list[str] = Field(default_factory=list)
    recommended_repair_stage: str | None = None
    recommended_repair_reason: str | None = None
    auto_repairable: bool = False
    artifact_versions: dict[str, int] = Field(default_factory=dict)


class ArtifactEnvelope(ArtifactModel):
    artifact_type: ArtifactType
    schema_version: int = ARTIFACT_SCHEMA_VERSION
    version: int = 1
    source_stage: str
    job_id: str | None = None
    input_fingerprint: str | None = None
    created_at: str
    updated_at: str
    data: dict[str, Any] = Field(default_factory=dict)


ARTIFACT_MODEL_BY_TYPE: dict[str, type[ArtifactModel]] = {
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE: NormalizedBusinessProfile,
    ARTIFACT_TYPE_BRAND_OS: BrandOSArtifact,
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE: BrandIdentityProfile,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT: WebsiteBlueprint,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE: CreativeBriefBundle,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE: VideoBriefBundle,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT: VideoRenderResult,
    ARTIFACT_TYPE_QA_REPORT: QAReport,
}


def validate_artifact_model(artifact_type: str, data: Any) -> ArtifactModel:
    model_type = ARTIFACT_MODEL_BY_TYPE.get(str(artifact_type))
    if not model_type:
        raise ValueError(f"Unsupported onboarding artifact type: {artifact_type}")
    if isinstance(data, model_type):
        return data
    return model_type.model_validate(data)


def build_brand_os_artifact(brand_os: Any) -> BrandOSArtifact:
    foundation = brand_os.foundation if isinstance(getattr(brand_os, "foundation", None), dict) else {}
    strategy = brand_os.brand_strategy if isinstance(getattr(brand_os, "brand_strategy", None), dict) else {}
    positioning = strategy.get("positioning_differentiation") if isinstance(strategy, dict) else {}
    messaging = strategy.get("core_messaging_hierarchy") if isinstance(strategy, dict) else {}
    voice = strategy.get("voice_personality") if isinstance(strategy, dict) else {}
    mission_vision = strategy.get("mission_vision") if isinstance(strategy, dict) else {}
    style = strategy.get("style_direction_seeds") if isinstance(strategy, dict) else {}
    strategic_parts = [
        _text_or_none(mission_vision.get("mission")) if isinstance(mission_vision, dict) else None,
        _text_or_none(mission_vision.get("vision")) if isinstance(mission_vision, dict) else None,
        _text_or_none(positioning.get("unique_advantage")) if isinstance(positioning, dict) else None,
    ]
    audience_personas: list[ArtifactAudiencePersona] = []
    for raw_persona in strategy.get("audience_personas") if isinstance(strategy, dict) else []:
        if not isinstance(raw_persona, dict):
            continue
        persona_name = _text_or_none(raw_persona.get("persona"))
        if not persona_name:
            continue
        audience_personas.append(
            ArtifactAudiencePersona(
                persona=persona_name,
                needs=_string_list(raw_persona.get("needs")),
                pain_points=_string_list(raw_persona.get("pain_points")),
            )
        )
    return BrandOSArtifact(
        brand_name=_text_or_none(foundation.get("brand_name")),
        industry=_text_or_none(foundation.get("brand_industry")),
        mission=_text_or_none(mission_vision.get("mission")) if isinstance(mission_vision, dict) else None,
        vision=_text_or_none(mission_vision.get("vision")) if isinstance(mission_vision, dict) else None,
        promise=_text_or_none(mission_vision.get("promise")) if isinstance(mission_vision, dict) else None,
        brand_purpose=_string_list(foundation.get("brand_purpose")),
        main_audience=_string_list(foundation.get("main_audience")),
        audience_personas=audience_personas,
        positioning_statement=_text_or_none(positioning.get("statement")) if isinstance(positioning, dict) else None,
        unique_advantage=_text_or_none(positioning.get("unique_advantage")) if isinstance(positioning, dict) else None,
        one_line_offer=_text_or_none(foundation.get("one_line_offer")),
        value_proposition=_text_or_none(messaging.get("elevator_pitch")) if isinstance(messaging, dict) else None,
        elevator_pitch=_text_or_none(messaging.get("elevator_pitch")) if isinstance(messaging, dict) else None,
        messaging_pillars=_string_list(messaging.get("proof_points")) if isinstance(messaging, dict) else [],
        proof_points=_string_list(messaging.get("proof_points")) if isinstance(messaging, dict) else [],
        voice_archetype=_text_or_none(voice.get("archetype")) if isinstance(voice, dict) else None,
        tone_attributes=_string_list(voice.get("profile")) if isinstance(voice, dict) else [],
        design_cues=_string_list(style.get("design_cues")) if isinstance(style, dict) else [],
        style_palette=_string_list(style.get("palette")) if isinstance(style, dict) else [],
        typography_direction=_text_or_none(style.get("typography")) if isinstance(style, dict) else None,
        cta_framework=_text_or_none(mission_vision.get("promise")) if isinstance(mission_vision, dict) else None,
        strategic_summary=" ".join(part for part in strategic_parts if part) or None,
        source_version=_text_or_none(getattr(brand_os, "version", None)),
    )


def _default_typography_direction(
    tone_traits: list[str],
    fonts: list[str],
    brand_os_artifact: BrandOSArtifact | None = None,
) -> str | None:
    if fonts:
        if len(fonts) == 1:
            return f"Use {fonts[0]} as the core typeface."
        return f"Use {fonts[0]} for headlines and {fonts[1]} for body copy."
    if brand_os_artifact and brand_os_artifact.typography_direction:
        return brand_os_artifact.typography_direction
    lowered = {item.lower() for item in tone_traits}
    if {"luxury", "premium", "editorial"} & lowered:
        return "High-contrast editorial headlines with a refined sans-serif body."
    if {"playful", "friendly", "approachable"} & lowered:
        return "Rounded modern sans-serif typography with bold friendly display moments."
    return "Modern sans-serif typography with confident headline contrast."


def build_brand_identity_profile(
    pack: Any,
    normalized_profile: NormalizedBusinessProfile | None = None,
    brand_os_artifact: BrandOSArtifact | None = None,
) -> BrandIdentityProfile:
    onboarding = dict(getattr(pack, "onboarding_answers", None) or {})
    palette = _parse_palette(onboarding.get("palette"))
    fonts = _parse_fonts(onboarding.get("fonts"))
    logo_assets = _logo_assets(onboarding)
    primary_logo_url = _coalesce_text(
        onboarding.get("wordmark_svg_or_url"),
        onboarding.get("transparent_logo_url"),
        onboarding.get("generated_logo_url"),
    )
    personality_traits = _dedupe_strings(
        getattr(normalized_profile, "tone_preferences", None),
        getattr(normalized_profile, "vibe_chips", None),
        getattr(brand_os_artifact, "tone_attributes", None),
    )
    visual_keywords = _dedupe_strings(
        getattr(brand_os_artifact, "design_cues", None),
        getattr(brand_os_artifact, "style_palette", None),
        getattr(normalized_profile, "tone_preferences", None),
    )
    palette_direction = _dedupe_strings(
        getattr(brand_os_artifact, "style_palette", None),
        [f"{key}:{value}" for key, value in palette.items()],
    )
    typography_direction = _default_typography_direction(
        personality_traits,
        fonts,
        brand_os_artifact,
    )
    voice_rules = _dedupe_strings(
        [f"Write in a {trait} voice." for trait in personality_traits[:4]],
        [f"Stay anchored in the {brand_os_artifact.voice_archetype} archetype."] if brand_os_artifact and brand_os_artifact.voice_archetype else [],
    )
    design_dos = _dedupe_strings(
        [f"Lean into {cue}." for cue in visual_keywords[:4]],
        [f"Preserve the {key} color {value}." for key, value in palette.items()],
    )
    design_donts = _dedupe_strings(
        ["Avoid generic clip-art styling."] if logo_assets else [],
        ["Avoid drifting away from the defined CTA and offer language."] if brand_os_artifact and brand_os_artifact.one_line_offer else [],
        ["Avoid visual clutter that hides the main offer."] if normalized_profile and normalized_profile.core_offer else [],
    )
    tagline_options = _dedupe_strings(
        [getattr(brand_os_artifact, "one_line_offer", None)],
        [getattr(brand_os_artifact, "value_proposition", None)],
        [getattr(brand_os_artifact, "positioning_statement", None)],
        [getattr(brand_os_artifact, "unique_advantage", None)],
    )
    image_style = _dedupe_strings(
        [getattr(pack, "business_type", None)],
        getattr(brand_os_artifact, "design_cues", None),
        getattr(normalized_profile, "tone_preferences", None),
    )
    logo_direction = _coalesce_text(
        "Wordmark-led identity with supporting logo assets." if primary_logo_url else None,
        getattr(brand_os_artifact, "positioning_statement", None),
    )

    return BrandIdentityProfile(
        personality_traits=personality_traits,
        visual_keywords=visual_keywords,
        palette_direction=palette_direction,
        palette=palette,
        typography_direction=typography_direction,
        fonts=fonts,
        logo_direction=logo_direction,
        primary_logo_url=primary_logo_url,
        logo_assets=logo_assets,
        image_style=image_style,
        voice_rules=voice_rules,
        design_dos=design_dos,
        design_donts=design_donts,
        tagline_options=tagline_options,
    )


_SECTION_HINTS: tuple[tuple[str, str], ...] = (
    ("hero", "hero"),
    ("offer", "offer"),
    ("proof", "proof"),
    ("testimonial", "proof"),
    ("process", "process"),
    ("faq", "faq"),
    ("contact", "contact"),
    ("cta", "cta"),
)


def _extract_section_labels(app_code: str) -> list[str]:
    lowered = app_code.lower()
    sections: list[str] = []
    for needle, label in _SECTION_HINTS:
        if needle in lowered and label not in sections:
            sections.append(label)
    if not sections:
        sections = ["hero", "offer", "proof", "cta"]
    return sections


def build_website_blueprint(
    project: Any,
    brand_context: Any | None = None,
    *,
    summary: str | None = None,
) -> WebsiteBlueprint:
    files = getattr(project, "files", None) if project is not None else {}
    files_dict = files if isinstance(files, dict) else {}
    app_code = _coalesce_text(files_dict.get("/App.tsx"), files_dict.get("App.tsx")) or ""
    sections = _extract_section_labels(app_code)
    primary_cta = _text_or_none(getattr(brand_context, "primary_cta", None))
    trust_elements = _dedupe_strings(getattr(brand_context, "proof_points", None))
    faq = ["FAQ section included in the website draft."] if "faq" in sections else []
    funnel_logic = [f"Lead with {sections[0]}"] if sections else []
    if "proof" in sections:
        funnel_logic.append("Reinforce trust before the CTA.")
    if primary_cta:
        funnel_logic.append(f"Close with {primary_cta}.")
    return WebsiteBlueprint(
        page_list=["home"],
        page_goals={"home": f"Drive {primary_cta or 'qualified conversions'}."},
        section_hierarchy={"home": sections},
        copy_blocks={"home": app_code[:800]} if app_code else {},
        trust_elements=trust_elements,
        faq=faq,
        cta_map={"primary": primary_cta} if primary_cta else {},
        funnel_logic=funnel_logic,
        project_id=str(getattr(project, "id", "") or "") or None,
        summary=_text_or_none(summary),
    )


def build_creative_brief_bundle(
    pack: Any,
    brand_context: Any | None = None,
    website_blueprint: WebsiteBlueprint | None = None,
    *,
    asset_names: list[str] | None = None,
) -> CreativeBriefBundle:
    primary_cta = _coalesce_text(
        getattr(brand_context, "primary_cta", None),
    )
    headline_options = _dedupe_strings(
        [getattr(brand_context, "core_offer", None)],
        [getattr(brand_context, "elevator_pitch", None)],
        [getattr(brand_context, "promise", None)],
        [getattr(brand_context, "usp_statement", None)],
    )
    support_copy = _dedupe_strings(
        getattr(brand_context, "proof_points", None),
        getattr(website_blueprint, "trust_elements", None) if website_blueprint else None,
        [getattr(brand_context, "primary_outcome", None)],
    )
    design_briefs = _dedupe_strings(
        getattr(brand_context, "design_cues", None),
        [getattr(brand_context, "typography_direction", None)],
        [getattr(brand_context, "voice_archetype", None)],
    )
    visual_prompts = _dedupe_strings(
        getattr(brand_context, "style_palette", None),
        getattr(brand_context, "design_cues", None),
    )
    format_variants = asset_names or []
    if not format_variants:
        format_variants = ["4x5", "9x16", "16x9", "1x1"]
    return CreativeBriefBundle(
        campaign_objective=_coalesce_text(primary_cta, "Generate starter demand"),
        asset_audience=_coalesce_text(
            getattr(brand_context, "target_audience", None),
            _string_list(getattr(brand_context, "main_audience", None))[0] if _string_list(getattr(brand_context, "main_audience", None)) else None,
        ),
        headline_options=headline_options,
        support_copy=support_copy,
        cta=primary_cta,
        design_briefs=design_briefs,
        visual_prompts=visual_prompts,
        format_variants=format_variants,
        asset_names=asset_names or [],
    )


def build_video_brief_bundle(
    pack: Any,
    brand_context: Any | None = None,
    creative_brief: CreativeBriefBundle | None = None,
    website_blueprint: WebsiteBlueprint | None = None,
    *,
    count: int = 4,
    asset_ids: list[str] | None = None,
) -> VideoBriefBundle:
    desired_count = max(1, count)
    offer = _coalesce_text(
        getattr(brand_context, "core_offer", None),
        "A clear founder-friendly offer.",
    )
    pain = _coalesce_text(
        getattr(brand_context, "primary_pain", None),
        "A frustrating problem your buyer already feels.",
    )
    outcome = _coalesce_text(
        getattr(brand_context, "primary_outcome", None),
        "A better end state for the customer.",
    )
    cta = _coalesce_text(
        getattr(brand_context, "primary_cta", None),
        "Take the next step",
    )
    proof = _coalesce_text(
        _string_list(getattr(brand_context, "proof_points", None))[0] if _string_list(getattr(brand_context, "proof_points", None)) else None,
        _string_list(getattr(creative_brief, "support_copy", None))[0] if creative_brief and _string_list(getattr(creative_brief, "support_copy", None)) else None,
    )
    headlines = _string_list(getattr(creative_brief, "headline_options", None)) if creative_brief else []
    if not headlines:
        headlines = [offer]
    concept_summary: list[str] = []
    hooks: list[str] = []
    storyboards: list[str] = []
    scripts: list[str] = []
    captions: list[str] = []
    render_prompts = _dedupe_strings(
        getattr(brand_context, "design_cues", None),
        getattr(brand_context, "style_palette", None),
        getattr(creative_brief, "visual_prompts", None) if creative_brief else None,
    )
    funnel_hint = _string_list(getattr(website_blueprint, "funnel_logic", None))[0] if website_blueprint and _string_list(getattr(website_blueprint, "funnel_logic", None)) else None
    for index in range(desired_count):
        headline = headlines[index % len(headlines)]
        concept = headline or offer
        hook = (
            f"Still dealing with {pain}?"
            if index % 2 == 0
            else f"What if {outcome.lower()} started with one simple shift?"
        )
        storyboard = "Hook -> offer -> proof -> CTA"
        script_parts = [hook, concept, offer]
        if proof:
            script_parts.append(f"Proof: {proof}")
        if funnel_hint:
            script_parts.append(funnel_hint)
        script_parts.append(cta)
        script = " ".join(part for part in script_parts if part)
        concept_summary.append(concept)
        hooks.append(hook)
        storyboards.append(storyboard)
        scripts.append(script)
        captions.append(script)
    return VideoBriefBundle(
        concept_summary=concept_summary,
        hook=hooks,
        storyboard=storyboards,
        voiceover_script=scripts,
        captions=captions,
        end_frame_cta=cta,
        render_prompts=render_prompts,
        asset_ids=asset_ids or [],
    )


def build_video_render_result(
    video_assets: list[Any] | None = None,
    *,
    requested_count: int,
    end_frame_cta: str | None = None,
) -> VideoRenderResult:
    asset_ids = _dedupe_strings(
        [str(getattr(asset, "id", "") or "") for asset in (video_assets or [])],
    )
    return VideoRenderResult(
        asset_ids=asset_ids,
        requested_count=max(1, requested_count),
        rendered_count=len(asset_ids),
        end_frame_cta=_text_or_none(end_frame_cta),
    )
