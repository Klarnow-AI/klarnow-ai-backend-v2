"""Shared pack/job state access helpers for onboarding orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class OnboardingJobStoreRuntime:
    pack_model: type[Any]
    get_job_data: Callable[[Any], dict[str, Any] | None]
    set_job_data: Callable[[Any, dict[str, Any]], None]


@dataclass(frozen=True)
class OnboardingJobControlRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    persist_job: Callable[[Session, Any, dict[str, Any]], Any]
    append_job_event: Callable[..., None]
    set_stage_state: Callable[..., None]
    pause_requested_exception: type[BaseException]


def load_pack_and_job(
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: OnboardingJobStoreRuntime,
) -> tuple[Any | None, dict[str, Any] | None]:
    pack = db.get(runtime.pack_model, pack_id)
    if not pack:
        return None, None
    job = runtime.get_job_data(pack)
    if not job or str(job.get("job_id") or "") != str(job_id):
        return pack, None
    return pack, job


def persist_job(
    db: Session,
    pack: Any,
    job: dict[str, Any],
    runtime: OnboardingJobStoreRuntime,
):
    runtime.set_job_data(pack, job)
    db.commit()
    return pack


def log_job_event(
    db: Session,
    pack_id: UUID,
    job_id: str,
    message: str,
    runtime: OnboardingJobControlRuntime,
    *,
    stage_name: str | None = None,
    level: str = "info",
):
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    runtime.append_job_event(job, message, stage_name=stage_name, level=level)
    return runtime.persist_job(db, pack, job)


def raise_if_pause_requested(
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: OnboardingJobControlRuntime,
) -> None:
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    if bool(job.get("pause_requested")) or str(job.get("status") or "") == "paused":
        raise runtime.pause_requested_exception("Onboarding automation paused.")


def mark_stage(
    db: Session,
    pack_id: UUID,
    job_id: str,
    stage_name: str,
    status: str,
    runtime: OnboardingJobControlRuntime,
    *,
    error: str | None = None,
    data: dict[str, Any] | None = None,
):
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    runtime.set_stage_state(job, stage_name, status, error=error, data=data)
    return runtime.persist_job(db, pack, job)
