"""Durable onboarding orchestration backed by Redis queue workers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db.observability import (
    get_db_query_count,
    get_db_query_duration_ms,
    reset_db_query_stats,
)
from app.core.logging import get_logger
from app.core.db.session import SessionLocal
from app.modules.packs.models import Pack, utc_now
from app.modules.packs.onboarding_queue import dispatch_onboarding_job, redis_queue_enabled
from app.modules.packs.services import append_suggested_logo, merge_onboarding_answers

ONBOARDING_JOB_KEY = "_onboarding_job"
ONBOARDING_JOB_MAX_ATTEMPTS = 3

STAGE_STARTER_BRAND = "starter_brand"
STAGE_BRAND_OS = "brand_os"
STAGE_LOGO = "logo"
ONBOARDING_JOB_STAGES = (
    STAGE_STARTER_BRAND,
    STAGE_BRAND_OS,
    STAGE_LOGO,
)

logger = get_logger("klarnow.onboarding_jobs")


@dataclass(slots=True)
class OnboardingRunResult:
    retry: bool
    attempt: int
    clear_dispatch: bool


def _iso_now() -> str:
    return utc_now().isoformat()


def _default_stage_state() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "data": {},
    }


def _default_job_stages() -> dict[str, dict[str, Any]]:
    return {stage: _default_stage_state() for stage in ONBOARDING_JOB_STAGES}


def _normalize_stage_state(raw: Any) -> dict[str, Any]:
    state = _default_stage_state()
    if isinstance(raw, dict):
        if raw.get("status"):
            state["status"] = str(raw["status"])
        state["started_at"] = raw.get("started_at")
        state["completed_at"] = raw.get("completed_at")
        state["last_error"] = raw.get("last_error")
        if isinstance(raw.get("data"), dict):
            state["data"] = dict(raw["data"])
    return state


def _normalize_job_data(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    normalized = dict(raw)
    normalized["job_id"] = str(raw.get("job_id") or "")
    normalized["status"] = str(raw.get("status") or "queued")
    normalized["attempt"] = int(raw.get("attempt") or 0)
    normalized["max_attempts"] = int(raw.get("max_attempts") or ONBOARDING_JOB_MAX_ATTEMPTS)
    normalized["queued_at"] = raw.get("queued_at")
    normalized["started_at"] = raw.get("started_at")
    normalized["completed_at"] = raw.get("completed_at")
    normalized["last_error"] = raw.get("last_error")
    current_stage = raw.get("current_stage")
    normalized["current_stage"] = str(current_stage) if current_stage else None
    raw_stages = raw.get("stages") if isinstance(raw.get("stages"), dict) else {}
    normalized["stages"] = {
        stage: _normalize_stage_state(raw_stages.get(stage))
        for stage in ONBOARDING_JOB_STAGES
    }
    return normalized


def _get_job_data(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    return _normalize_job_data(answers.get(ONBOARDING_JOB_KEY))


def _set_job_data(pack: Pack, job_data: dict[str, Any]) -> None:
    answers = dict(pack.onboarding_answers or {})
    answers[ONBOARDING_JOB_KEY] = _normalize_job_data(job_data)
    pack.onboarding_answers = answers


def _public_stage_summary(stage_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": stage_state.get("status"),
        "started_at": stage_state.get("started_at"),
        "completed_at": stage_state.get("completed_at"),
        "last_error": stage_state.get("last_error"),
    }


def _set_stage_state(
    job: dict[str, Any],
    stage_name: str,
    status: str,
    *,
    error: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    stages = job.get("stages") if isinstance(job.get("stages"), dict) else _default_job_stages()
    stage = _normalize_stage_state(stages.get(stage_name))
    if status == "running" and not stage.get("started_at"):
        stage["started_at"] = _iso_now()
    if status in {"completed", "skipped"}:
        stage["completed_at"] = _iso_now()
        stage["last_error"] = None
    elif error is not None:
        stage["last_error"] = error[:2000]
    elif status == "running":
        stage["last_error"] = None
    stage["status"] = status
    if data:
        stage["data"].update(data)
    stages[stage_name] = stage
    job["stages"] = stages
    job["current_stage"] = stage_name if status == "running" else None


def _load_pack_and_job(
    db: Session,
    pack_id: UUID,
    job_id: str,
) -> tuple[Pack | None, dict[str, Any] | None]:
    pack = db.get(Pack, pack_id)
    if not pack:
        return None, None
    job = _get_job_data(pack)
    if not job or str(job.get("job_id") or "") != str(job_id):
        return pack, None
    return pack, job


def _persist_job(db: Session, pack: Pack, job: dict[str, Any]) -> Pack:
    _set_job_data(pack, job)
    db.commit()
    return pack


def _mark_stage(
    db: Session,
    pack_id: UUID,
    job_id: str,
    stage_name: str,
    status: str,
    *,
    error: str | None = None,
    data: dict[str, Any] | None = None,
) -> Pack:
    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    _set_stage_state(job, stage_name, status, error=error, data=data)
    return _persist_job(db, pack, job)


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


def _get_existing_onboarding_brand_os(db: Session, pack: Pack, job_id: str):
    from app.modules.brand_os.services import get_by_id_and_pack, get_by_source_job_id

    existing = get_by_source_job_id(db, pack.id, job_id)
    if existing:
        return existing

    answers = pack.onboarding_answers or {}
    brand_os_id = answers.get("onboarding_brand_os_id")
    if not brand_os_id:
        return None
    try:
        return get_by_id_and_pack(db, UUID(str(brand_os_id)), pack.id)
    except (TypeError, ValueError):
        return None


def _sync_pack_core_concept(pack: Pack, brand_os) -> None:
    from app.modules.brand_os.services import get_summary_fields

    mission, _, _ = get_summary_fields(brand_os)
    if mission:
        pack.core_concept = (mission.strip() or "")[:500]


def _run_starter_brand_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    from app.modules.packs.onboarding_services import generate_starter_brand

    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][STAGE_STARTER_BRAND]
    answers = pack.onboarding_answers or {}

    if stage["status"] == "completed" or _has_starter_brand_outputs(pack):
        return _mark_stage(
            db,
            pack_id,
            job_id,
            STAGE_STARTER_BRAND,
            "completed",
            data={"wordmark": answers.get("wordmark_svg_or_url")},
        )

    pack = _mark_stage(db, pack_id, job_id, STAGE_STARTER_BRAND, "running")
    brand_name = _resolve_brand_name(pack)
    vibe_chips = _resolve_vibe_chips(pack)
    onboarding_context = _build_onboarding_context(pack)
    result = generate_starter_brand(
        brand_name,
        vibe_chips,
        onboarding_context,
        pack_id=str(pack_id),
    )
    wordmark_to_use = result["wordmark_svg_or_url"]
    pack = append_suggested_logo(db, pack, wordmark_to_use, commit=False)
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "wordmark_svg_or_url": wordmark_to_use,
            "palette": result["palette"],
            "starter_brand_job_id": job_id,
            "starter_brand_completed_at": _iso_now(),
        },
        commit=False,
    )
    return _mark_stage(
        db,
        pack_id,
        job_id,
        STAGE_STARTER_BRAND,
        "completed",
        data={"wordmark": wordmark_to_use},
    )


def _run_brand_os_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    from app.modules.agents.orchestrator import handle_onboarding_complete

    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][STAGE_BRAND_OS]

    existing_brand_os = _get_existing_onboarding_brand_os(db, pack, job_id)
    if stage["status"] == "completed" or existing_brand_os:
        if existing_brand_os:
            pack = merge_onboarding_answers(
                db,
                pack,
                {
                    "onboarding_brand_os_id": str(existing_brand_os.id),
                    "onboarding_brand_os_job_id": job_id,
                    "onboarding_brand_os_completed_at": _iso_now(),
                },
                commit=False,
            )
            _sync_pack_core_concept(pack, existing_brand_os)
        return _mark_stage(
            db,
            pack_id,
            job_id,
            STAGE_BRAND_OS,
            "completed",
            data={"brand_os_id": str(existing_brand_os.id)} if existing_brand_os else None,
        )

    _mark_stage(db, pack_id, job_id, STAGE_BRAND_OS, "running")
    handle_onboarding_complete(pack_id, db, source_job_id=job_id)
    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    brand_os = _get_existing_onboarding_brand_os(db, pack, job_id)
    if not brand_os:
        raise RuntimeError("Brand OS generation did not produce a result")
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "onboarding_brand_os_id": str(brand_os.id),
            "onboarding_brand_os_job_id": job_id,
            "onboarding_brand_os_completed_at": _iso_now(),
        },
        commit=False,
    )
    _sync_pack_core_concept(pack, brand_os)
    return _mark_stage(
        db,
        pack_id,
        job_id,
        STAGE_BRAND_OS,
        "completed",
        data={"brand_os_id": str(brand_os.id), "version": brand_os.version},
    )


def _run_logo_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    from app.modules.brand_os.services import get_active_for_pack, get_summary_fields
    from app.modules.packs.logo_generation import generate_logo

    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][STAGE_LOGO]

    if stage["status"] == "skipped":
        return pack
    if stage["status"] == "completed" or _has_final_logo_output(pack):
        return _mark_stage(db, pack_id, job_id, STAGE_LOGO, "completed")

    palette = _extract_palette(pack.onboarding_answers or {})
    brand_os = _get_existing_onboarding_brand_os(db, pack, job_id) or get_active_for_pack(db, pack_id)
    if not palette or not brand_os:
        return _mark_stage(db, pack_id, job_id, STAGE_LOGO, "skipped")

    _mark_stage(db, pack_id, job_id, STAGE_LOGO, "running")
    mission, vision, _ = get_summary_fields(brand_os)
    foundation = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
    one_line = (foundation.get("one_line_offer") or "").strip()
    industry = (foundation.get("brand_industry") or "").strip()
    audience = (foundation.get("main_audience") or "").strip()
    summary_parts = [part for part in [mission, vision, one_line, industry, audience] if part]
    brand_os_summary = " ".join(summary_parts)[:1500] if summary_parts else None
    logo_result = generate_logo(
        brand_name=(pack.brand_name or pack.name or "My Brand"),
        prompt="distinctive, creative logo, professional and memorable, not generic",
        pack_id=str(pack_id),
        color_scheme="use the provided palette",
        brand_os_summary=brand_os_summary,
        color_palette=palette,
        strict=False,
    )
    logo_url = logo_result.get("logo_url") or logo_result.get("wordmark_svg_or_url")
    if not logo_url:
        return _mark_stage(db, pack_id, job_id, STAGE_LOGO, "skipped")

    pack = append_suggested_logo(db, pack, logo_url, commit=False)
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "wordmark_svg_or_url": logo_url,
            "final_logo_job_id": job_id,
            "final_logo_completed_at": _iso_now(),
        },
        commit=False,
    )
    return _mark_stage(
        db,
        pack_id,
        job_id,
        STAGE_LOGO,
        "completed",
        data={"logo_url": logo_url},
    )


def _run_onboarding_pipeline(db: Session, pack_id: UUID, job_id: str) -> None:
    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        return

    answers = pack.onboarding_answers or {}
    is_existing_brand = answers.get("has_existing_brand") == "yes"
    if is_existing_brand:
        _mark_stage(db, pack_id, job_id, STAGE_STARTER_BRAND, "skipped")
    else:
        _run_starter_brand_stage(db, pack_id, job_id)

    _run_brand_os_stage(db, pack_id, job_id)

    if is_existing_brand:
        _mark_stage(db, pack_id, job_id, STAGE_LOGO, "skipped")
    else:
        _run_logo_stage(db, pack_id, job_id)

    pack, job = _load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        return
    pack.onboarding_background_completed_at = utc_now()
    db.commit()


def enqueue_onboarding_job(db: Session, pack_id: UUID) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise ValueError("Pack not found")
    job = {
        "job_id": str(uuid.uuid4()),
        "status": "queued",
        "attempt": 0,
        "max_attempts": ONBOARDING_JOB_MAX_ATTEMPTS,
        "queued_at": _iso_now(),
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "current_stage": None,
        "stages": _default_job_stages(),
    }
    _set_job_data(pack, job)
    pack.onboarding_background_completed_at = None
    db.flush()
    return job


def get_onboarding_job_status(pack: Pack) -> dict[str, Any]:
    job = _get_job_data(pack)
    if not job:
        return {
            "status": "not_started",
            "job_id": None,
            "attempt": 0,
            "max_attempts": ONBOARDING_JOB_MAX_ATTEMPTS,
            "queued_at": None,
            "started_at": None,
            "completed_at": None,
            "last_error": None,
            "current_stage": None,
            "stages": None,
        }
    return {
        "status": str(job.get("status") or "queued"),
        "job_id": str(job.get("job_id") or ""),
        "attempt": int(job.get("attempt") or 0),
        "max_attempts": int(job.get("max_attempts") or ONBOARDING_JOB_MAX_ATTEMPTS),
        "queued_at": job.get("queued_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "last_error": job.get("last_error"),
        "current_stage": job.get("current_stage"),
        "stages": {
            stage_name: _public_stage_summary(stage_state)
            for stage_name, stage_state in job["stages"].items()
        },
    }


def dispatch_onboarding_job_from_api(
    pack_id: UUID,
    job_id: str,
    *,
    delay_seconds: int = 0,
    force: bool = False,
) -> bool:
    if not redis_queue_enabled():
        raise RuntimeError("REDIS_URL is not configured")
    return dispatch_onboarding_job(
        str(pack_id),
        str(job_id),
        delay_seconds=delay_seconds,
        force=force,
    )


def run_onboarding_job(pack_id: UUID, job_id: str) -> OnboardingRunResult:
    db = SessionLocal()
    reset_db_query_stats()
    try:
        pack, job = _load_pack_and_job(db, pack_id, job_id)
        if not pack or not job:
            return OnboardingRunResult(retry=False, attempt=0, clear_dispatch=True)
        if job["status"] == "completed":
            return OnboardingRunResult(
                retry=False,
                attempt=int(job.get("attempt") or 0),
                clear_dispatch=True,
            )

        attempt = int(job.get("attempt") or 0) + 1
        job["attempt"] = attempt
        job["status"] = "running"
        job["started_at"] = job.get("started_at") or _iso_now()
        job["last_error"] = None
        _set_job_data(pack, job)
        db.commit()

        try:
            _run_onboarding_pipeline(db, pack_id, job_id)
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            pack, job = _load_pack_and_job(db, pack_id, job_id)
            if not pack or not job:
                return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
            should_retry = attempt < int(job.get("max_attempts") or ONBOARDING_JOB_MAX_ATTEMPTS)
            job["status"] = "queued" if should_retry else "failed"
            job["last_error"] = str(exc)[:2000]
            job["current_stage"] = None
            _set_job_data(pack, job)
            db.commit()
            return OnboardingRunResult(
                retry=should_retry,
                attempt=attempt,
                clear_dispatch=not should_retry,
            )

        pack, job = _load_pack_and_job(db, pack_id, job_id)
        if not pack or not job:
            return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
        job["status"] = "completed"
        job["completed_at"] = _iso_now()
        job["last_error"] = None
        job["current_stage"] = None
        _set_job_data(pack, job)
        db.commit()
        return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
    finally:
        logger.info(
            "onboarding_job_db_usage | pack_id=%s | job_id=%s | queries=%s | query_time_ms=%.2f",
            pack_id,
            job_id,
            get_db_query_count(),
            get_db_query_duration_ms(),
        )
        db.close()
