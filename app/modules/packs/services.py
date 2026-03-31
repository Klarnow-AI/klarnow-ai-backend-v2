"""Pack service: list, create, archive, onboarding."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.packs.models import Pack, PACK_TYPE_ENQUIRIES


STEP_2_FINALIZATION_CACHE_KEY = "_step_2_finalization"
_STEP_2_FINALIZATION_IGNORED_ANSWER_KEYS = {
    STEP_2_FINALIZATION_CACHE_KEY,
    "_onboarding_job",
    "_onboarding_artifacts",
    "_normalize_input_fingerprint",
    "_starter_brand_input_fingerprint",
    "_brand_identity_input_fingerprint",
    "_onboarding_brand_os_input_fingerprint",
    "_final_logo_input_fingerprint",
    "_website_input_fingerprint",
    "_poster_flyers_input_fingerprint",
    "_video_briefs_input_fingerprint",
    "_video_render_input_fingerprint",
    "_qa_review_input_fingerprint",
    "generated_logo_url",
    "transparent_logo_url",
    "wordmark_svg_or_url",
    "palette",
    "starter_brand_job_id",
    "starter_brand_completed_at",
    "suggested_logos",
    "onboarding_brand_os_id",
    "onboarding_brand_os_job_id",
    "onboarding_brand_os_completed_at",
    "final_logo_job_id",
    "final_logo_completed_at",
    "onboarding_website_project_id",
    "onboarding_website_generated_at",
    "onboarding_poster_flyers_generated_at",
    "onboarding_videos_generated_at",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _text_or_none(value: Any, *, limit: int | None = None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if limit is not None:
        return text[:limit]
    return text


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


def fingerprint_payload(payload: Any) -> str:
    normalized = _normalize_hash_value(payload)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_step_2_finalization_cache(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    raw = answers.get(STEP_2_FINALIZATION_CACHE_KEY)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def set_step_2_finalization_cache(pack: Pack, payload: dict[str, Any]) -> Pack:
    return _merge_onboarding_answers(pack, {STEP_2_FINALIZATION_CACHE_KEY: payload})


def resolve_pack_target_audience(pack: Pack) -> str | None:
    audience = (pack.target_audience or "").strip()
    if audience:
        return audience

    answers = pack.onboarding_answers or {}
    for key in ("who_are_your_customers", "who_is_it_for", "target_audience", "q1"):
        raw = answers.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def sync_pack_target_audience(pack: Pack) -> str | None:
    audience = resolve_pack_target_audience(pack)
    if audience and not (pack.target_audience or "").strip():
        pack.target_audience = audience
    return audience


def resolve_pack_vibe_chips(pack: Pack) -> list[str]:
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


def extract_palette_from_answers(answers: dict | None) -> dict[str, str] | None:
    if not isinstance(answers, dict):
        return None
    raw = answers.get("palette")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items() if isinstance(v, str) and v.strip()}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(parsed, dict):
            return {
                str(k): str(v)
                for k, v in parsed.items()
                if isinstance(v, str) and str(v).strip()
            }
    return None


def _extract_brand_name_from_answers(answers: dict[str, Any] | None) -> str | None:
    if not isinstance(answers, dict):
        return None

    brand_name = _text_or_none(answers.get("brand_name"), limit=255)
    if brand_name:
        return brand_name

    raw_extracted = answers.get("extracted_brand")
    extracted: dict[str, Any] | None = None
    if isinstance(raw_extracted, dict):
        extracted = raw_extracted
    elif isinstance(raw_extracted, str):
        try:
            parsed = json.loads(raw_extracted)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        extracted = parsed if isinstance(parsed, dict) else None

    if isinstance(extracted, dict):
        return _text_or_none(extracted.get("brand_name"), limit=255)
    return None


def _generate_pack_name_from_business_description(raw_value: Any) -> str | None:
    text = _text_or_none(raw_value, limit=255)
    if not text:
        return None

    normalized = text.strip()
    lower = normalized.lower()
    prefixes = (
        "i run ",
        "we run ",
        "i own ",
        "we own ",
        "i'm ",
        "im ",
        "i am ",
        "we're ",
        "we are ",
        "i help ",
        "we help ",
        "i provide ",
        "we provide ",
    )
    for prefix in prefixes:
        if lower.startswith(prefix):
            normalized = normalized[len(prefix) :].strip(" .,-")
            break

    for article in ("a ", "an ", "the "):
        if normalized.lower().startswith(article):
            normalized = normalized[len(article) :].strip(" .,-")
            break

    normalized = normalized[:255].strip(" .,-")
    if not normalized:
        normalized = text

    return normalized[:1].upper() + normalized[1:]


def build_onboarding_context(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    onboarding_context: dict[str, Any] = {}
    if (pack.offer_one_liner or "").strip():
        onboarding_context["offer"] = (pack.offer_one_liner or "").strip()
    why_started = _text_or_none(answers.get("why_started"), limit=1000)
    if why_started:
        onboarding_context["why_started"] = why_started
    if (pack.usp_statement or "").strip():
        onboarding_context["usp"] = (pack.usp_statement or "").strip()
    audience = resolve_pack_target_audience(pack)
    if audience:
        onboarding_context["audience"] = audience
    if (pack.primary_cta or "").strip():
        onboarding_context["cta"] = (pack.primary_cta or "").strip()
    raw_extracted = answers.get("extracted_brand")
    if isinstance(raw_extracted, str):
        try:
            extracted = json.loads(raw_extracted)
        except (json.JSONDecodeError, TypeError):
            extracted = None
        if isinstance(extracted, dict) and isinstance(extracted.get("industry"), str):
            industry = extracted["industry"].strip()
            if industry:
                onboarding_context["industry"] = industry
    return onboarding_context or None


def build_step_2_finalization_payload(pack: Pack) -> dict[str, Any]:
    answers = pack.onboarding_answers or {}
    filtered_answers = {
        key: value
        for key, value in answers.items()
        if key not in _STEP_2_FINALIZATION_IGNORED_ANSWER_KEYS and value is not None
    }
    return {
        "pack_name": (pack.name or "").strip(),
        "pack_type": (pack.pack_type or "").strip(),
        "has_existing_brand": answers.get("has_existing_brand"),
        "brand_name": (pack.brand_name or "").strip(),
        "why_started": _text_or_none(answers.get("why_started")) or "",
        "primary_cta": (pack.primary_cta or "").strip(),
        "usp_category": (pack.usp_category or "").strip(),
        "usp_statement": (pack.usp_statement or "").strip(),
        "usp_proof": (pack.usp_proof or "").strip(),
        "proof_text": (pack.proof_text or "").strip(),
        "offer_one_liner": (pack.offer_one_liner or "").strip(),
        "target_audience": resolve_pack_target_audience(pack) or "",
        "primary_pain": (pack.primary_pain or "").strip(),
        "primary_outcome": (pack.primary_outcome or "").strip(),
        "brand_url": answers.get("brand_url"),
        "extracted_brand": answers.get("extracted_brand"),
        "vibe_chips": resolve_pack_vibe_chips(pack),
        "answers": filtered_answers,
    }


@log_service_action()
def list_packs_for_user(
    db: Session, user_id: UUID, include_archived: bool = False
) -> list[Pack]:
    q = db.query(Pack).filter(Pack.created_by_user_id == user_id)
    if not include_archived:
        q = q.filter(Pack.status != "archived")
    return q.order_by(Pack.created_at.desc()).all()


@log_service_action()
def get_pack_for_user(db: Session, pack_id: UUID, user_id: UUID) -> Pack | None:
    return (
        db.query(Pack)
        .filter(Pack.id == pack_id, Pack.created_by_user_id == user_id)
        .first()
    )


@log_service_action()
def create_pack(
    db: Session,
    user_id: UUID,
    name: str = "New Pack",
    pack_type: str = PACK_TYPE_ENQUIRIES,
    *,
    commit: bool = True,
) -> Pack:
    pack = Pack(
        name=name,
        status="draft",
        pack_type=pack_type,
        created_by_user_id=user_id,
    )
    db.add(pack)
    db.flush()
    if commit:
        db.commit()
    return pack


@log_service_action()
def archive_pack(db: Session, pack: Pack) -> Pack:
    pack.status = "archived"
    db.commit()
    return pack


@log_service_action()
def restore_pack(db: Session, pack: Pack) -> Pack:
    """Restore an archived pack back to draft status."""
    pack.status = "draft"
    db.commit()
    return pack


@log_service_action()
def delete_pack(db: Session, pack: Pack) -> None:
    """Permanently delete a pack and all related data (CASCADE)."""
    db.delete(pack)
    db.commit()


@log_service_action()
def submit_onboarding(db: Session, pack: Pack, answers: dict) -> Pack:
    cleaned_answers = dict(answers or {})
    pack.onboarding_answers = cleaned_answers
    pack.status = "onboarding"
    generated_name = _generate_pack_name_from_business_description(
        cleaned_answers.get("what_do_you_do")
    )
    if generated_name:
        pack.name = generated_name
    resolved_brand_name = _extract_brand_name_from_answers(cleaned_answers)
    if resolved_brand_name:
        pack.brand_name = resolved_brand_name
    elif generated_name and not (pack.brand_name or "").strip():
        pack.brand_name = generated_name

    offer_one_liner = _text_or_none(cleaned_answers.get("what_do_you_do"), limit=500)
    if offer_one_liner:
        pack.offer_one_liner = offer_one_liner

    target_audience = _text_or_none(
        cleaned_answers.get("who_are_your_customers"),
        limit=500,
    )
    if target_audience:
        pack.target_audience = target_audience

    primary_cta = _text_or_none(cleaned_answers.get("primary_cta"), limit=255)
    pack.primary_cta = primary_cta

    proof_text = _text_or_none(cleaned_answers.get("proof_text"))
    pack.proof_text = proof_text

    brand_url = _text_or_none(cleaned_answers.get("brand_url"), limit=512)
    if brand_url:
        pack.website_url = brand_url

    if cleaned_answers.get("pack_type") in {PACK_TYPE_ENQUIRIES, "quotes", "sales"}:
        pack.pack_type = str(cleaned_answers["pack_type"])
    db.commit()
    return pack


SUGGESTED_LOGOS_MAX = 20


def _merge_onboarding_answers(pack: Pack, partial: dict) -> Pack:
    current = dict(pack.onboarding_answers or {})
    for k, v in partial.items():
        if v is not None:
            current[k] = v
    pack.onboarding_answers = current
    return pack


def _append_suggested_logo(pack: Pack, logo_url_or_svg: str) -> Pack:
    import json

    current = dict(pack.onboarding_answers or {})
    raw = current.get("suggested_logos")
    if isinstance(raw, str):
        try:
            suggested = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            suggested = []
    elif isinstance(raw, list):
        suggested = list(raw)
    else:
        suggested = []
    if not isinstance(suggested, list):
        suggested = []
    suggested.append(logo_url_or_svg)
    current["suggested_logos"] = json.dumps(suggested[-SUGGESTED_LOGOS_MAX:])
    pack.onboarding_answers = current
    return pack


def _append_suggested_logos(pack: Pack, logo_urls_or_svgs: list[str]) -> Pack:
    for logo_url_or_svg in logo_urls_or_svgs:
        text = str(logo_url_or_svg or "").strip()
        if not text:
            continue
        _append_suggested_logo(pack, text)
    return pack


@log_service_action()
def merge_onboarding_answers(
    db: Session,
    pack: Pack,
    partial: dict,
    *,
    commit: bool = True,
) -> Pack:
    """Merge partial keys into pack.onboarding_answers and save. Preserves existing keys."""
    _merge_onboarding_answers(pack, partial)
    if commit:
        db.commit()
    return pack


def append_suggested_logo(
    db: Session,
    pack: Pack,
    logo_url_or_svg: str,
    *,
    commit: bool = True,
) -> Pack:
    """Append a logo URL (or SVG/data URL) to suggested_logos in onboarding_answers, cap at SUGGESTED_LOGOS_MAX."""
    _append_suggested_logo(pack, logo_url_or_svg)
    if commit:
        db.commit()
    return pack


def append_suggested_logos(
    db: Session,
    pack: Pack,
    logo_urls_or_svgs: list[str],
    *,
    commit: bool = True,
) -> Pack:
    """Append multiple logo assets to suggested_logos, skipping blank values."""
    _append_suggested_logos(pack, logo_urls_or_svgs)
    if commit:
        db.commit()
    return pack


@log_service_action()
def complete_onboarding(
    db: Session,
    pack: Pack,
    answers: dict | None = None,
    *,
    commit: bool = True,
) -> Pack:
    pack.onboarding_completed_at = utc_now()
    pack.status = "draft"
    if answers and answers.get("pack_type") in ("enquiries", "quotes", "sales"):
        pack.pack_type = answers["pack_type"]
    if commit:
        db.commit()
    return pack
