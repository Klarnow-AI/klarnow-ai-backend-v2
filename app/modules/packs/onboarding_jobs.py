"""Durable onboarding job queue with DB-backed status and retries."""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db.session import SessionLocal
from app.modules.packs.models import Pack, utc_now
from app.modules.packs.services import append_suggested_logo, merge_onboarding_answers

ONBOARDING_JOB_KEY = "_onboarding_job"
ONBOARDING_JOB_MAX_ATTEMPTS = 3

_active_pack_workers: set[UUID] = set()
_worker_lock = threading.Lock()


def _iso_now() -> str:
    return utc_now().isoformat()


def _get_job_data(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    job = answers.get(ONBOARDING_JOB_KEY)
    return job if isinstance(job, dict) else None


def _set_job_data(pack: Pack, job_data: dict[str, Any]) -> None:
    answers = dict(pack.onboarding_answers or {})
    answers[ONBOARDING_JOB_KEY] = job_data
    pack.onboarding_answers = answers


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
    }


def _run_onboarding_pipeline(db: Session, pack_id: UUID) -> None:
    from app.modules.agents.orchestrator import handle_onboarding_complete
    from app.modules.brand_os.services import get_active_for_pack, get_summary_fields
    from app.modules.packs.logo_generation import generate_logo
    from app.modules.packs.onboarding_services import generate_starter_brand

    pack = db.get(Pack, pack_id)
    if not pack:
        return

    answers = pack.onboarding_answers or {}
    is_existing_brand = answers.get("has_existing_brand") == "yes"
    new_brand_palette = None
    if not is_existing_brand:
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
        if not brand_name:
            brand_name = (pack.brand_name or pack.name or "My Brand") or "My Brand"
        raw_vibe = answers.get("vibe_chips")
        if isinstance(raw_vibe, str):
            try:
                vibe_chips = json.loads(raw_vibe) if raw_vibe else []
            except (json.JSONDecodeError, TypeError):
                vibe_chips = ["professional", "modern"]
        else:
            vibe_chips = raw_vibe if isinstance(raw_vibe, list) else ["professional", "modern"]
        onboarding_context = {}
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
                ext = json.loads(answers["extracted_brand"])
                if isinstance(ext, dict) and (ext.get("industry") or "").strip():
                    onboarding_context["industry"] = (ext.get("industry") or "").strip()
            except (json.JSONDecodeError, TypeError):
                pass
        result = generate_starter_brand(
            brand_name, vibe_chips, onboarding_context or None, pack_id=str(pack_id),
        )
        new_brand_palette = result.get("palette")
        wordmark_to_use = result["wordmark_svg_or_url"]
        pack = append_suggested_logo(db, pack, wordmark_to_use)
        pack = merge_onboarding_answers(
            db,
            pack,
            {
                "wordmark_svg_or_url": wordmark_to_use,
                "palette": result["palette"],
            },
        )
        db.flush()
        db.refresh(pack)

    handle_onboarding_complete(pack_id, db)
    db.refresh(pack)
    brand_os = get_active_for_pack(db, pack_id)
    if brand_os:
        mission, _, _ = get_summary_fields(brand_os)
        if mission:
            pack.core_concept = (mission.strip() or "")[:500]
        db.flush()
        db.refresh(pack)

    if not is_existing_brand and brand_os and new_brand_palette:
        mission, vision, _ = get_summary_fields(brand_os)
        foundation = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
        one_line = (foundation.get("one_line_offer") or "").strip()
        industry = (foundation.get("brand_industry") or "").strip()
        audience = (foundation.get("main_audience") or "").strip()
        summary_parts = [p for p in [mission, vision, one_line, industry, audience] if p]
        brand_os_summary = " ".join(summary_parts)[:1500] if summary_parts else None
        logo_result = generate_logo(
            brand_name=(pack.brand_name or pack.name or "My Brand"),
            prompt="distinctive, creative logo—professional and memorable, not generic",
            pack_id=str(pack_id),
            color_scheme="use the provided palette",
            brand_os_summary=brand_os_summary,
            color_palette=new_brand_palette,
            strict=False,
        )
        logo_url = logo_result.get("logo_url") or logo_result.get("wordmark_svg_or_url")
        if logo_url:
            pack = append_suggested_logo(db, pack, logo_url)
            pack = merge_onboarding_answers(db, pack, {"wordmark_svg_or_url": logo_url})
            db.flush()
            db.refresh(pack)

    pack = db.get(Pack, pack_id)
    if pack:
        pack.onboarding_background_completed_at = utc_now()
        db.flush()


def _run_worker(pack_id: UUID) -> None:
    try:
        while True:
            db = SessionLocal()
            should_retry = False
            retry_attempt = 0
            try:
                pack = db.get(Pack, pack_id)
                if not pack:
                    return
                job = _get_job_data(pack)
                if not job:
                    return
                if job.get("status") == "completed":
                    return
                attempt = int(job.get("attempt") or 0) + 1
                max_attempts = int(job.get("max_attempts") or ONBOARDING_JOB_MAX_ATTEMPTS)
                job["attempt"] = attempt
                job["status"] = "running"
                job["started_at"] = _iso_now()
                job["last_error"] = None
                _set_job_data(pack, job)
                db.commit()

                try:
                    _run_onboarding_pipeline(db, pack_id)
                except Exception as exc:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    pack = db.get(Pack, pack_id)
                    if not pack:
                        return
                    job = _get_job_data(pack) or job
                    job["last_error"] = str(exc)[:2000]
                    retry_attempt = attempt
                    should_retry = attempt < max_attempts
                    job["status"] = "queued" if should_retry else "failed"
                    _set_job_data(pack, job)
                    db.commit()
                    if not should_retry:
                        return
                else:
                    job = _get_job_data(pack) or job
                    job["status"] = "completed"
                    job["completed_at"] = _iso_now()
                    _set_job_data(pack, job)
                    db.commit()
                    return
            finally:
                db.close()
            if should_retry:
                # Basic in-process backoff; queued state remains durable in DB.
                time.sleep(min(8, 2 ** retry_attempt))
    finally:
        with _worker_lock:
            _active_pack_workers.discard(pack_id)


def start_onboarding_job_worker(pack_id: UUID) -> bool:
    with _worker_lock:
        if pack_id in _active_pack_workers:
            return False
        _active_pack_workers.add(pack_id)
    thread = threading.Thread(
        target=_run_worker,
        args=(pack_id,),
        daemon=False,
        name=f"onboarding-job-{pack_id}",
    )
    thread.start()
    return True


def recover_pending_onboarding_jobs() -> int:
    db = SessionLocal()
    started = 0
    try:
        packs = db.query(Pack).all()
        for pack in packs:
            status = get_onboarding_job_status(pack).get("status")
            if status in {"queued", "running"}:
                if start_onboarding_job_worker(pack.id):
                    started += 1
        return started
    finally:
        db.close()
