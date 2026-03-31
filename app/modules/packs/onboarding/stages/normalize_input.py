"""Input normalization onboarding stage implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import ArtifactEvidence, NormalizedBusinessProfile


@dataclass(frozen=True)
class NormalizeInputStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    get_artifact_envelope: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    resolve_brand_name: Callable[[Any], str]
    resolve_target_audience: Callable[[Any], str | None]
    resolve_vibe_chips: Callable[[Any], list[str]]
    text_or_none: Callable[..., str | None]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    artifact_type: str


def _parse_json_dict(value: Any) -> dict[str, Any]:
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


def _split_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except (TypeError, json.JSONDecodeError):
                parsed = None
            if isinstance(parsed, list):
                value = parsed
            else:
                parts = [part.strip() for part in text.replace(";", "\n").splitlines()]
                return [part for part in parts if part]
        else:
            parts = [part.strip() for part in text.replace(";", "\n").splitlines()]
            return [part for part in parts if part]
    if isinstance(value, (list, tuple, set)):
        cleaned: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned
    return []


def _append_unique(target: list[str], value: str | None) -> None:
    text = str(value or "").strip()
    if text and text not in target:
        target.append(text)


def _pick_text(
    evidence: list[ArtifactEvidence],
    field: str,
    candidates: list[tuple[str, Any]],
    *,
    limit: int | None = None,
) -> str | None:
    for source, raw_value in candidates:
        text = str(raw_value or "").strip()
        if not text:
            continue
        if limit is not None:
            text = text[:limit]
        evidence.append(ArtifactEvidence(field=field, source=source, value=text))
        return text
    return None


def _pick_list(
    evidence: list[ArtifactEvidence],
    field: str,
    candidates: list[tuple[str, Any]],
) -> list[str]:
    values: list[str] = []
    for source, raw_value in candidates:
        for item in _split_text_list(raw_value):
            if item in values:
                continue
            values.append(item)
            evidence.append(ArtifactEvidence(field=field, source=source, value=item))
    return values


def _build_goal_hints(pack: Any, primary_cta: str | None) -> list[str]:
    goals: list[str] = []
    pack_type = str(getattr(pack, "pack_type", "") or "").strip()
    if primary_cta:
        _append_unique(goals, f"Drive {primary_cta.lower()}.")
    if pack_type == "enquiries":
        _append_unique(goals, "Generate qualified enquiries.")
    elif pack_type == "quotes":
        _append_unique(goals, "Generate quote requests.")
    elif pack_type == "sales":
        _append_unique(goals, "Drive direct sales.")
    if getattr(pack, "has_existing_customers", None):
        _append_unique(goals, "Build repeatable growth from existing customer proof.")
    return goals


def _build_normalized_business_profile(pack: Any, runtime: NormalizeInputStageRuntime) -> NormalizedBusinessProfile:
    answers = pack.onboarding_answers or {}
    extracted = _parse_json_dict(answers.get("extracted_brand"))
    contact_info = extracted.get("contact_info") if isinstance(extracted.get("contact_info"), dict) else {}
    social_links = extracted.get("social_links") if isinstance(extracted.get("social_links"), list) else []
    offer_cues = _split_text_list(extracted.get("offer_cues"))
    evidence: list[ArtifactEvidence] = []

    business_name = _pick_text(
        evidence,
        "business_name",
        [
            ("pack.brand_name", getattr(pack, "brand_name", None)),
            ("onboarding_answers.brand_name", answers.get("brand_name")),
            ("onboarding_answers.extracted_brand.brand_name", extracted.get("brand_name")),
            ("pack.name", getattr(pack, "name", None)),
        ],
        limit=255,
    )
    industry = _pick_text(
        evidence,
        "industry",
        [
            ("onboarding_answers.extracted_brand.industry", extracted.get("industry")),
            ("pack.business_type", getattr(pack, "business_type", None)),
            ("onboarding_answers.industry", answers.get("industry")),
        ],
        limit=255,
    )
    target_audience = _pick_text(
        evidence,
        "target_audience",
        [
            ("pack.target_audience", getattr(pack, "target_audience", None)),
            ("onboarding_answers.who_are_your_customers", answers.get("who_are_your_customers")),
            ("onboarding_answers.who_is_it_for", answers.get("who_is_it_for")),
            ("onboarding_answers.target_audience", answers.get("target_audience")),
            ("resolved.target_audience", runtime.resolve_target_audience(pack)),
        ],
        limit=500,
    )
    core_offer = _pick_text(
        evidence,
        "core_offer",
        [
            ("pack.offer_one_liner", getattr(pack, "offer_one_liner", None)),
            ("onboarding_answers.what_do_you_do", answers.get("what_do_you_do")),
            ("onboarding_answers.extracted_brand.description", extracted.get("description")),
            ("onboarding_answers.extracted_brand.offer_cues", offer_cues[0] if offer_cues else None),
        ],
        limit=500,
    )
    problem_solved = _pick_text(
        evidence,
        "problem_solved",
        [
            ("pack.primary_pain", getattr(pack, "primary_pain", None)),
            ("onboarding_answers.primary_pain", answers.get("primary_pain")),
        ],
        limit=500,
    )
    primary_cta = _pick_text(
        evidence,
        "primary_cta",
        [
            ("pack.primary_cta", getattr(pack, "primary_cta", None)),
            ("onboarding_answers.primary_cta", answers.get("primary_cta")),
        ],
        limit=255,
    )
    primary_outcome = _pick_text(
        evidence,
        "primary_outcome",
        [
            ("pack.primary_outcome", getattr(pack, "primary_outcome", None)),
            ("onboarding_answers.primary_outcome", answers.get("primary_outcome")),
        ],
        limit=500,
    )
    why_started = _pick_text(
        evidence,
        "why_started",
        [
            ("onboarding_answers.why_started", answers.get("why_started")),
        ],
        limit=1000,
    )

    differentiators = _pick_list(
        evidence,
        "differentiators",
        [
            ("pack.usp_statement", getattr(pack, "usp_statement", None)),
            ("pack.usp_proof", getattr(pack, "usp_proof", None)),
            ("onboarding_answers.extracted_brand.offer_cues", offer_cues),
            ("onboarding_answers.extracted_brand.tagline", extracted.get("tagline")),
        ],
    )
    proof_points = _pick_list(
        evidence,
        "proof_points",
        [
            ("pack.usp_proof", getattr(pack, "usp_proof", None)),
            ("pack.proof_text", getattr(pack, "proof_text", None)),
        ],
    )
    tone_preferences = _pick_list(
        evidence,
        "tone_preferences",
        [
            ("onboarding_answers.vibe_chips", runtime.resolve_vibe_chips(pack)),
        ],
    )

    goals = _pick_list(
        evidence,
        "goals",
        [
            ("derived.primary_cta", _build_goal_hints(pack, primary_cta)),
            ("onboarding_answers.goals", answers.get("goals")),
        ],
    )
    geographic_focus = _pick_list(
        evidence,
        "geographic_focus",
        [
            ("pack.location_city", getattr(pack, "location_city", None)),
            ("pack.location_country", getattr(pack, "location_country", None)),
            ("onboarding_answers.service_area", answers.get("service_area")),
            ("onboarding_answers.where_do_you_serve", answers.get("where_do_you_serve")),
        ],
    )
    competitor_signals = _pick_list(
        evidence,
        "competitor_signals",
        [
            ("onboarding_answers.competitors", answers.get("competitors")),
            ("onboarding_answers.competitor_signals", answers.get("competitor_signals")),
        ],
    )

    available_channels: list[str] = []
    if str(getattr(pack, "website_url", None) or answers.get("brand_url") or "").strip():
        _append_unique(available_channels, "website")
    if str(answers.get("wordmark_svg_or_url") or answers.get("generated_logo_url") or "").strip():
        _append_unique(available_channels, "logo")
    if social_links:
        _append_unique(available_channels, "social")
    if str(answers.get("voice_notes_sent") or "").strip():
        _append_unique(available_channels, "voice_notes")

    constraints: list[str] = []
    has_existing_brand = answers.get("has_existing_brand") == "yes"
    if has_existing_brand:
        _append_unique(constraints, "Respect the existing brand assets and public-facing positioning.")
    brand_url = str(answers.get("brand_url") or getattr(pack, "website_url", None) or "").strip() or None
    if brand_url:
        _append_unique(constraints, "Stay aligned with the current website and public-facing messaging.")
    if not available_channels:
        _append_unique(constraints, "No existing public channels were detected from the onboarding inputs.")

    for value in constraints:
        evidence.append(ArtifactEvidence(field="constraints", source="derived", value=value))
    for value in available_channels:
        evidence.append(ArtifactEvidence(field="available_channels", source="derived", value=value))

    missing_fields: list[str] = []
    if not business_name:
        missing_fields.append("business_name")
    if not core_offer:
        missing_fields.append("core_offer")
    if not target_audience:
        missing_fields.append("target_audience")
    if not primary_cta:
        missing_fields.append("primary_cta")
    if not industry:
        missing_fields.append("industry")

    return NormalizedBusinessProfile(
        business_name=business_name or runtime.resolve_brand_name(pack),
        industry=industry,
        target_audience=target_audience,
        core_offer=core_offer,
        problem_solved=problem_solved,
        differentiators=differentiators,
        goals=goals,
        tone_preferences=tone_preferences,
        geographic_focus=geographic_focus,
        competitor_signals=competitor_signals,
        constraints=constraints,
        available_channels=available_channels,
        source_evidence=evidence,
        missing_fields=missing_fields,
        primary_cta=primary_cta,
        primary_outcome=primary_outcome,
        why_started=why_started,
        pack_type=str(getattr(pack, "pack_type", "") or "").strip() or None,
        business_type=str(getattr(pack, "business_type", "") or "").strip() or None,
        has_existing_brand=has_existing_brand if answers.get("has_existing_brand") in {"yes", "no"} else None,
        brand_url=brand_url,
        vibe_chips=runtime.resolve_vibe_chips(pack),
        proof_points=proof_points,
    )


def run_normalize_input_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: NormalizeInputStageRuntime,
):
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    existing_envelope = runtime.get_artifact_envelope(pack, runtime.artifact_type)
    existing_profile = runtime.get_artifact(pack, runtime.artifact_type)

    if stage["status"] == "completed" or (
        existing_envelope and str(existing_envelope.input_fingerprint or "") == input_fingerprint
    ):
        pack.onboarding_answers = dict(pack.onboarding_answers or {})
        pack.onboarding_answers[runtime.input_fingerprint_key] = input_fingerprint
        missing_count = len(getattr(existing_profile, "missing_fields", []) or [])
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={
                "artifact_type": runtime.artifact_type,
                "artifact_version": getattr(existing_envelope, "version", 0),
                "missing_fields": missing_count,
            },
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    profile = _build_normalized_business_profile(pack, runtime)
    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        profile,
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        (
            "Normalized onboarding inputs into a business profile."
            if not profile.missing_fields
            else "Normalized onboarding inputs and flagged missing business context."
        ),
        stage_name=runtime.stage_name,
    )
    pack.onboarding_answers = dict(pack.onboarding_answers or {})
    pack.onboarding_answers[runtime.input_fingerprint_key] = input_fingerprint
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={
            "artifact_type": runtime.artifact_type,
            "artifact_version": envelope.version,
            "missing_fields": len(profile.missing_fields),
        },
    )
