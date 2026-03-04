"""Background worker for image context indexing jobs."""

from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.session import SessionLocal
from app.core.logging import get_logger
from app.modules.image_context.models import ImageContextJob, utc_now
from app.modules.image_context.services import process_image_context_job

logger = get_logger("klarnow.image_context.jobs")

_worker_lock = threading.Lock()
_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _claim_next_job(db: Session) -> ImageContextJob | None:
    job = (
        db.query(ImageContextJob)
        .filter(ImageContextJob.status == "queued")
        .order_by(ImageContextJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not job:
        return None

    job.status = "running"
    job.attempt = int(job.attempt or 0) + 1
    job.started_at = utc_now()
    job.last_error = None
    db.commit()
    db.refresh(job)
    return job


def _mark_job_completed(db: Session, job_id) -> None:
    job = db.get(ImageContextJob, job_id)
    if not job:
        return
    job.status = "completed"
    job.completed_at = utc_now()
    job.last_error = None
    db.commit()


def _mark_job_failed(db: Session, job_id, error_message: str) -> None:
    job = db.get(ImageContextJob, job_id)
    if not job:
        return

    max_attempts = max(1, int(job.max_attempts or 1))
    if int(job.attempt or 0) >= max_attempts:
        job.status = "failed"
    else:
        job.status = "queued"
    job.last_error = error_message[:2000]
    db.commit()


def _worker_loop() -> None:
    settings = get_settings()
    idle_sleep_seconds = max(1, settings.image_context_job_poll_seconds)

    logger.info("image_context_worker_started | idle_sleep_seconds=%s", idle_sleep_seconds)
    while not _stop_event.is_set():
        db = SessionLocal()
        try:
            job = _claim_next_job(db)
            if not job:
                db.close()
                _stop_event.wait(idle_sleep_seconds)
                continue

            job_id = job.id
            try:
                process_image_context_job(db, job)
                _mark_job_completed(db, job_id)
            except Exception as e:
                db.rollback()
                logger.warning(
                    "image_context_job_failed | job_id=%s | source_type=%s | operation=%s | error=%s",
                    job_id,
                    job.source_type,
                    job.operation,
                    e,
                )
                _mark_job_failed(db, job_id, str(e))
                # Basic exponential backoff per failed job attempt.
                backoff_seconds = min(8, 2 ** max(1, int(job.attempt or 1)))
                _stop_event.wait(backoff_seconds)
        except Exception as e:
            logger.warning("image_context_worker_tick_error | error=%s", e)
            time.sleep(1)
        finally:
            try:
                db.close()
            except Exception:
                pass

    logger.info("image_context_worker_stopped")


def start_image_context_worker() -> bool:
    global _worker_thread

    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return False
        _stop_event.clear()
        _worker_thread = threading.Thread(
            target=_worker_loop,
            daemon=True,
            name="image-context-worker",
        )
        _worker_thread.start()
        return True


def recover_pending_image_context_jobs() -> int:
    """Return running jobs to queued state on startup."""
    db = SessionLocal()
    try:
        count = (
            db.query(ImageContextJob)
            .filter(ImageContextJob.status == "running")
            .update({"status": "queued"}, synchronize_session=False)
        )
        db.commit()
        return int(count or 0)
    finally:
        db.close()


def stop_image_context_worker() -> None:
    _stop_event.set()
