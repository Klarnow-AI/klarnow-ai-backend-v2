"""Onboarding pack normalization and fingerprint helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.packs.models import Pack
from app.modules.packs.onboarding.artifact_store import get_artifact_envelope
from app.modules.packs.onboarding.artifacts import (
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_BRAND_OS,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
)

from .common import _text_or_none
from .constants import (
    BRAND_IDENTITY_INPUT_FINGERPRINT_KEY,
    BRAND_OS_INPUT_FINGERPRINT_KEY,
    LOGO_INPUT_FINGERPRINT_KEY,
    NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY,
    POSTER_FLYERS_INPUT_FINGERPRINT_KEY,
    QA_REVIEW_INPUT_FINGERPRINT_KEY,
    STARTER_BRAND_INPUT_FINGERPRINT_KEY,
    VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY,
    VIDEO_RENDER_INPUT_FINGERPRINT_KEY,
    WEBSITE_INPUT_FINGERPRINT_KEY,
    _IGNORED_ONBOARDING_INPUT_KEYS,
)
from .state import _get_job_data


def _normalize_hash_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalize_hash_value(inner_value)
            for key, inner_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_hash_value(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if text and text[0] in {"{", "["}:
            try:
                return _normalize_hash_value(json.loads(text))
            except (json.JSONDecodeError, TypeError):
                return text
        return text
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _fingerprint_payload(payload: Any) -> str:
    normalized = _normalize_hash_value(payload)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _has_palette(palette: Any) -> bool:
    return isinstance(palette, dict) and all(
        isinstance(palette.get(key), str) and palette.get(key, "").strip()
        for key in ("primary", "secondary", "accent")
    )


def _extract_palette(answers: dict[str, Any]) -> dict[str, Any] | None:
    palette = answers.get("palette")
    if _has_palette(palette):
        return dict(palette)
    if isinstance(palette, str):
        try:
            decoded = json.loads(palette)
        except (json.JSONDecodeError, TypeError):
            return None
        if _has_palette(decoded):
            return dict(decoded)
    return None


def _has_starter_brand_outputs(pack: Pack) -> bool:
    answers = pack.onboarding_answers or {}
    wordmark = str(answers.get("wordmark_svg_or_url") or "").strip()
    return bool(wordmark) and _has_palette(_extract_palette(answers))


def _has_final_logo_output(pack: Pack) -> bool:
    answers = pack.onboarding_answers or {}
    return bool(str(answers.get("wordmark_svg_or_url") or "").strip()) and bool(
        answers.get("final_logo_job_id")
    )


def _resolve_brand_name(pack: Pack) -> str:
    answers = pack.onboarding_answers or {}
    brand_name = (answers.get("brand_name") or "").strip()
    if not brand_name and answers.get("extracted_brand"):
        try:
            extracted = json.loads(answers["extracted_brand"])
            if isinstance(extracted, dict):
                brand_name = (extracted.get("brand_name") or "").strip()
        except (json.JSONDecodeError, TypeError):
            pass
    if not brand_name and (pack.brand_name or "").strip():
        brand_name = (pack.brand_name or "").strip()
    if not brand_name and pack.name:
        brand_name = (pack.name or "").strip()
    return brand_name or (pack.brand_name or pack.name or "My Brand")


def _resolve_vibe_chips(pack: Pack) -> list[str]:
    answers = pack.onboarding_answers or {}
    raw_vibe = answers.get("vibe_chips")
    if isinstance(raw_vibe, str):
        try:
            vibe_chips = json.loads(raw_vibe) if raw_vibe else []
        except (json.JSONDecodeError, TypeError):
            vibe_chips = ["professional", "modern"]
    else:
        vibe_chips = raw_vibe if isinstance(raw_vibe, list) else ["professional", "modern"]
    return vibe_chips or ["professional", "modern"]


def _build_onboarding_context(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    onboarding_context: dict[str, Any] = {}
    if (pack.offer_one_liner or "").strip():
        onboarding_context["offer"] = (pack.offer_one_liner or "").strip()
    why_started = _text_or_none(answers.get("why_started"), limit=1000)
    if why_started:
        onboarding_context["why_started"] = why_started
    if (pack.usp_statement or "").strip():
        onboarding_context["usp"] = (pack.usp_statement or "").strip()
    if (pack.target_audience or "").strip():
        onboarding_context["audience"] = (pack.target_audience or "").strip()
    if (pack.primary_cta or "").strip():
        onboarding_context["cta"] = (pack.primary_cta or "").strip()
    if answers.get("extracted_brand"):
        try:
            extracted = json.loads(answers["extracted_brand"])
            if isinstance(extracted, dict) and (extracted.get("industry") or "").strip():
                onboarding_context["industry"] = (extracted.get("industry") or "").strip()
        except (json.JSONDecodeError, TypeError):
            pass
    return onboarding_context or None


def _build_brand_os_input_payload(pack: Pack) -> dict[str, Any]:
    answers = pack.onboarding_answers or {}
    filtered_answers = {
        key: value
        for key, value in answers.items()
        if key not in _IGNORED_ONBOARDING_INPUT_KEYS and value is not None
    }
    return {
        "pack_name": (pack.name or "").strip(),
        "pack_type": (pack.pack_type or "").strip(),
        "brand_name": (pack.brand_name or "").strip() or _resolve_brand_name(pack),
        "why_started": _text_or_none(answers.get("why_started")) or "",
        "primary_cta": (pack.primary_cta or "").strip(),
        "usp_statement": (pack.usp_statement or "").strip(),
        "usp_proof": (pack.usp_proof or "").strip(),
        "proof_text": (pack.proof_text or "").strip(),
        "offer_one_liner": (pack.offer_one_liner or "").strip(),
        "target_audience": (pack.target_audience or "").strip(),
        "primary_pain": (pack.primary_pain or "").strip(),
        "primary_outcome": (pack.primary_outcome or "").strip(),
        "hero_angle": (pack.hero_angle or "").strip(),
        "answers": filtered_answers,
    }


def _build_normalize_input_payload(pack: Pack) -> dict[str, Any]:
    answers = pack.onboarding_answers or {}
    return {
        "brand_os_payload": _build_brand_os_input_payload(pack),
        "pack_name": (pack.name or "").strip(),
        "website_url": (pack.website_url or "").strip(),
        "location_city": (pack.location_city or "").strip(),
        "location_country": (pack.location_country or "").strip(),
        "business_type": (pack.business_type or "").strip(),
        "proof_types": list(pack.proof_types or []),
        "has_existing_customers": pack.has_existing_customers,
        "answers": {
            key: value
            for key, value in answers.items()
            if key not in _IGNORED_ONBOARDING_INPUT_KEYS and value is not None
        },
    }


def _compute_normalize_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(_build_normalize_input_payload(pack))


def _compute_starter_brand_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "has_existing_brand": (pack.onboarding_answers or {}).get("has_existing_brand"),
            "brand_name": _resolve_brand_name(pack),
            "vibe_chips": _resolve_vibe_chips(pack),
            "onboarding_context": _build_onboarding_context(pack),
        }
    )


def _compute_brand_identity_input_fingerprint(pack: Pack) -> str:
    answers = pack.onboarding_answers or {}
    has_existing_brand = answers.get("has_existing_brand") == "yes"
    return _fingerprint_payload(
        {
            "has_existing_brand": has_existing_brand,
            "normalized_artifact": _artifact_marker(pack, ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE),
            "brand_os_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_OS),
            "starter_brand_inputs": None if has_existing_brand else {
                "brand_name": _resolve_brand_name(pack),
                "vibe_chips": _resolve_vibe_chips(pack),
                "onboarding_context": _build_onboarding_context(pack),
            },
            "logo_inputs": {
                "palette": _extract_palette(answers),
                "wordmark_svg_or_url": (answers.get("wordmark_svg_or_url") or "").strip(),
                "generated_logo_url": (answers.get("generated_logo_url") or "").strip(),
                "transparent_logo_url": (answers.get("transparent_logo_url") or "").strip(),
                "final_logo_job_id": (answers.get("final_logo_job_id") or "").strip(),
            },
        }
    )


def _compute_brand_os_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(_build_brand_os_input_payload(pack))


def _artifact_marker(pack: Pack, artifact_type: str) -> dict[str, Any] | None:
    envelope = get_artifact_envelope(pack, artifact_type)
    if not envelope:
        return None
    return {
        "version": envelope.version,
        "input_fingerprint": envelope.input_fingerprint,
        "source_stage": envelope.source_stage,
        "updated_at": envelope.updated_at,
    }


def _compute_logo_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "brand_name": (pack.brand_name or pack.name or "My Brand").strip(),
            "palette": _extract_palette(pack.onboarding_answers or {}),
            "brand_os_input_fingerprint": _compute_brand_os_input_fingerprint(pack),
            "brand_identity_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE),
        }
    )


def _compute_website_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "normalized_artifact": _artifact_marker(pack, ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE),
            "brand_os_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_OS),
            "brand_identity_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE),
            "brand_os_input_fingerprint": _compute_brand_os_input_fingerprint(pack),
            "brand_identity_input_fingerprint": _compute_brand_identity_input_fingerprint(pack),
            "pack_fallback": {
                "brand_name": _resolve_brand_name(pack),
                "offer_one_liner": (pack.offer_one_liner or "").strip(),
                "primary_cta": (pack.primary_cta or "").strip(),
                "target_audience": (pack.target_audience or "").strip(),
                "primary_pain": (pack.primary_pain or "").strip(),
                "primary_outcome": (pack.primary_outcome or "").strip(),
                "hero_angle": (pack.hero_angle or "").strip(),
            },
        }
    )


def _compute_poster_flyers_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "website_input_fingerprint": _compute_website_input_fingerprint(pack),
            "website_blueprint_artifact": _artifact_marker(pack, ARTIFACT_TYPE_WEBSITE_BLUEPRINT),
            "brand_os_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_OS),
            "brand_identity_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE),
            "pack_fallback": {
                "brand_name": _resolve_brand_name(pack),
                "offer_one_liner": (pack.offer_one_liner or "").strip(),
                "primary_cta": (pack.primary_cta or "").strip(),
                "primary_pain": (pack.primary_pain or "").strip(),
                "primary_outcome": (pack.primary_outcome or "").strip(),
                "hero_angle": (pack.hero_angle or "").strip(),
                "usp_statement": (pack.usp_statement or "").strip(),
                "usp_proof": (pack.usp_proof or "").strip(),
                "proof_text": (pack.proof_text or "").strip(),
            },
        }
    )


def _compute_video_briefs_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "poster_flyers_input_fingerprint": _compute_poster_flyers_input_fingerprint(pack),
            "website_blueprint_artifact": _artifact_marker(pack, ARTIFACT_TYPE_WEBSITE_BLUEPRINT),
            "creative_brief_artifact": _artifact_marker(pack, ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE),
            "brand_identity_artifact": _artifact_marker(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE),
            "pack_fallback": {
                "brand_name": _resolve_brand_name(pack),
                "offer_one_liner": (pack.offer_one_liner or "").strip(),
                "primary_cta": (pack.primary_cta or "").strip(),
                "primary_outcome": (pack.primary_outcome or "").strip(),
            },
        }
    )


def _compute_video_render_input_fingerprint(pack: Pack) -> str:
    return _fingerprint_payload(
        {
            "video_briefs_input_fingerprint": _compute_video_briefs_input_fingerprint(pack),
            "video_brief_artifact": _artifact_marker(pack, ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE),
            "video_render_artifact": _artifact_marker(pack, ARTIFACT_TYPE_VIDEO_RENDER_RESULT),
            "pack_fallback": {
                "brand_name": _resolve_brand_name(pack),
                "primary_cta": (pack.primary_cta or "").strip(),
                "primary_outcome": (pack.primary_outcome or "").strip(),
            },
        }
    )


def _compute_videos_input_fingerprint(pack: Pack) -> str:
    return _compute_video_render_input_fingerprint(pack)


def _compute_qa_review_input_fingerprint(pack: Pack) -> str:
    answers = pack.onboarding_answers or {}
    return _fingerprint_payload(
        {
            "normalize_input": _compute_normalize_input_fingerprint(pack),
            "brand_os": _compute_brand_os_input_fingerprint(pack),
            "brand_identity": _compute_brand_identity_input_fingerprint(pack),
            "website": _compute_website_input_fingerprint(pack),
            "poster_flyers": _compute_poster_flyers_input_fingerprint(pack),
            "video_briefs": _compute_video_briefs_input_fingerprint(pack),
            "video_render": _compute_video_render_input_fingerprint(pack),
            "markers": {
                NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY: answers.get(NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY),
                BRAND_OS_INPUT_FINGERPRINT_KEY: answers.get(BRAND_OS_INPUT_FINGERPRINT_KEY),
                BRAND_IDENTITY_INPUT_FINGERPRINT_KEY: answers.get(BRAND_IDENTITY_INPUT_FINGERPRINT_KEY),
                STARTER_BRAND_INPUT_FINGERPRINT_KEY: answers.get(STARTER_BRAND_INPUT_FINGERPRINT_KEY),
                LOGO_INPUT_FINGERPRINT_KEY: answers.get(LOGO_INPUT_FINGERPRINT_KEY),
                WEBSITE_INPUT_FINGERPRINT_KEY: answers.get(WEBSITE_INPUT_FINGERPRINT_KEY),
                POSTER_FLYERS_INPUT_FINGERPRINT_KEY: answers.get(POSTER_FLYERS_INPUT_FINGERPRINT_KEY),
                VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY: answers.get(VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY),
                VIDEO_RENDER_INPUT_FINGERPRINT_KEY: answers.get(VIDEO_RENDER_INPUT_FINGERPRINT_KEY),
                "onboarding_brand_os_id": answers.get("onboarding_brand_os_id"),
                "onboarding_website_project_id": answers.get("onboarding_website_project_id"),
                "onboarding_poster_flyers_generated_at": answers.get("onboarding_poster_flyers_generated_at"),
                "onboarding_videos_generated_at": answers.get("onboarding_videos_generated_at"),
                "final_logo_job_id": answers.get("final_logo_job_id"),
            },
        }
    )


def compute_onboarding_input_fingerprint(pack: Pack) -> str:
    answers = pack.onboarding_answers or {}
    return _fingerprint_payload(
        {
            "has_existing_brand": answers.get("has_existing_brand"),
            "normalize_input": _compute_normalize_input_fingerprint(pack),
            "brand_os": _compute_brand_os_input_fingerprint(pack),
            "brand_identity": _compute_brand_identity_input_fingerprint(pack),
        }
    )


def onboarding_job_matches_current_inputs(pack: Pack) -> bool:
    job = _get_job_data(pack)
    if not job:
        return False
    return str(job.get("input_fingerprint") or "") == compute_onboarding_input_fingerprint(pack)
