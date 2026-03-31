"""Public onboarding job API helpers."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID


@dataclass(frozen=True)
class OnboardingJobApiRuntime:
    get_job_data: Callable[[Any], dict[str, Any] | None]
    set_job_data: Callable[[Any, dict[str, Any]], None]
    append_job_event: Callable[..., None]
    default_job_stages: Callable[[], dict[str, Any]]
    default_job_events: Callable[[], list[dict[str, Any]]]
    iso_now: Callable[[], str]
    compute_onboarding_input_fingerprint: Callable[[Any], str]
    build_public_job_stages: Callable[[dict[str, Any]], dict[str, dict[str, Any]]]
    public_stage_summary: Callable[[dict[str, Any]], dict[str, Any]]
    map_internal_stage_to_public: Callable[[str | None], str | None]
    pause_job: Callable[..., None]
    onboarding_job_max_attempts: int
    active_statuses: Collection[str]
    redis_queue_enabled: Callable[[], bool]
    dispatch_onboarding_job: Callable[..., bool]


def enqueue_onboarding_job(pack: Any, runtime: OnboardingJobApiRuntime) -> dict[str, Any]:
    input_fingerprint = runtime.compute_onboarding_input_fingerprint(pack)
    existing_job = runtime.get_job_data(pack)
    if existing_job:
        existing_status = str(existing_job.get("status") or "").strip()
        if existing_status in runtime.active_statuses:
            if existing_status == "queued":
                existing_job["input_fingerprint"] = input_fingerprint
            runtime.append_job_event(
                existing_job,
                "Reusing the existing onboarding job already in the queue.",
                level="info",
            )
            runtime.set_job_data(pack, existing_job)
            pack.onboarding_background_completed_at = None
            return existing_job

    job = {
        "job_id": str(uuid.uuid4()),
        "status": "queued",
        "input_fingerprint": input_fingerprint,
        "attempt": 0,
        "max_attempts": runtime.onboarding_job_max_attempts,
        "queued_at": runtime.iso_now(),
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "pause_requested": False,
        "paused_at": None,
        "current_stage": None,
        "stages": runtime.default_job_stages(),
        "events": runtime.default_job_events(),
    }
    runtime.append_job_event(job, "Queued onboarding automation.", level="info")
    runtime.set_job_data(pack, job)
    pack.onboarding_background_completed_at = None
    return job


def get_onboarding_job_status(pack: Any, runtime: OnboardingJobApiRuntime) -> dict[str, Any]:
    job = runtime.get_job_data(pack)
    if not job:
        return {
            "status": "not_started",
            "job_id": None,
            "attempt": 0,
            "max_attempts": runtime.onboarding_job_max_attempts,
            "queued_at": None,
            "started_at": None,
            "completed_at": None,
            "last_error": None,
            "pause_requested": False,
            "paused_at": None,
            "current_stage": None,
            "stages": None,
        }
    public_stages = runtime.build_public_job_stages(job)
    if str(job.get("status") or "") == "completed":
        for stage_state in public_stages.values():
            if stage_state.get("status") == "pending":
                stage_state["status"] = "completed"
                stage_state["started_at"] = stage_state.get("started_at") or job.get("started_at")
                stage_state["completed_at"] = stage_state.get("completed_at") or job.get("completed_at")
    return {
        "status": str(job.get("status") or "queued"),
        "job_id": str(job.get("job_id") or ""),
        "attempt": int(job.get("attempt") or 0),
        "max_attempts": int(job.get("max_attempts") or runtime.onboarding_job_max_attempts),
        "queued_at": job.get("queued_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "last_error": job.get("last_error"),
        "pause_requested": bool(job.get("pause_requested") or False),
        "paused_at": job.get("paused_at"),
        "current_stage": runtime.map_internal_stage_to_public(job.get("current_stage")),
        "stages": {
            stage_name: runtime.public_stage_summary(stage_state)
            for stage_name, stage_state in public_stages.items()
        },
        "events": list(job.get("events") or []),
    }


def dispatch_onboarding_job_from_api(
    *,
    pack_id: UUID,
    job_id: str,
    runtime: OnboardingJobApiRuntime,
    delay_seconds: int = 0,
    force: bool = False,
) -> bool:
    if not runtime.redis_queue_enabled():
        raise RuntimeError("REDIS_URL is not configured")
    return runtime.dispatch_onboarding_job(
        str(pack_id),
        str(job_id),
        delay_seconds=delay_seconds,
        force=force,
    )


def request_onboarding_job_pause(db: Any, pack: Any, runtime: OnboardingJobApiRuntime) -> dict[str, Any]:
    job = runtime.get_job_data(pack)
    if not job:
        return get_onboarding_job_status(pack, runtime)

    status = str(job.get("status") or "").strip()
    if status == "queued":
        runtime.pause_job(job, message="Paused onboarding automation.")
        runtime.set_job_data(pack, job)
        db.commit()
        db.refresh(pack)
        return get_onboarding_job_status(pack, runtime)
    if status == "running" and not bool(job.get("pause_requested")):
        job["pause_requested"] = True
        runtime.append_job_event(
            job,
            "Stop requested. Generation will pause after the current step.",
        )
        runtime.set_job_data(pack, job)
        db.commit()
        db.refresh(pack)
        return get_onboarding_job_status(pack, runtime)
    return get_onboarding_job_status(pack, runtime)


def resume_onboarding_job(db: Any, pack: Any, runtime: OnboardingJobApiRuntime) -> dict[str, Any]:
    job = runtime.get_job_data(pack)
    if not job:
        return get_onboarding_job_status(pack, runtime)

    status = str(job.get("status") or "").strip()
    if status == "paused":
        job["status"] = "queued"
        job["pause_requested"] = False
        job["paused_at"] = None
        job["last_error"] = None
        job["queued_at"] = runtime.iso_now()
        job["current_stage"] = None
        runtime.append_job_event(job, "Resumed onboarding automation.")
        runtime.set_job_data(pack, job)
        db.commit()
        db.refresh(pack)
        return get_onboarding_job_status(pack, runtime)
    if status == "running" and bool(job.get("pause_requested")):
        job["pause_requested"] = False
        runtime.append_job_event(
            job,
            "Continue requested. Generation will keep running.",
        )
        runtime.set_job_data(pack, job)
        db.commit()
        db.refresh(pack)
        return get_onboarding_job_status(pack, runtime)
    return get_onboarding_job_status(pack, runtime)
