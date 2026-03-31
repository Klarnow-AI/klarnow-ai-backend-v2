"""Route-facing onboarding job API.

This module is the public entrypoint for packs routes and other callers that
need to enqueue, inspect, pause, resume, or run onboarding jobs.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack
from app.modules.packs.onboarding.common import OnboardingRunResult
from app.modules.packs.onboarding import service as _service


def enqueue_onboarding_job(db: Session, pack_id: UUID) -> dict:
    return _service.enqueue_onboarding_job(db, pack_id)


def get_onboarding_job_status(pack: Pack) -> dict:
    return _service.get_onboarding_job_status(pack)


def dispatch_onboarding_job_from_api(
    pack_id: UUID,
    job_id: str,
    *,
    delay_seconds: int = 0,
    force: bool = False,
) -> bool:
    return _service.dispatch_onboarding_job_from_api(
        pack_id,
        job_id,
        delay_seconds=delay_seconds,
        force=force,
    )


def request_onboarding_job_pause(db: Session, pack_id: UUID) -> dict:
    return _service.request_onboarding_job_pause(db, pack_id)


def resume_onboarding_job(db: Session, pack_id: UUID) -> dict:
    return _service.resume_onboarding_job(db, pack_id)


def enqueue_onboarding_stage_repair(
    db: Session,
    pack_id: UUID,
    *,
    stage_name: str,
    include_downstream: bool = True,
    reason: str | None = None,
) -> dict:
    return _service.enqueue_onboarding_stage_repair(
        db,
        pack_id,
        stage_name=stage_name,
        include_downstream=include_downstream,
        reason=reason,
    )


def enqueue_onboarding_qa_repair(
    db: Session,
    pack_id: UUID,
    *,
    include_downstream: bool = True,
    reason: str | None = None,
) -> dict:
    return _service.enqueue_onboarding_qa_repair(
        db,
        pack_id,
        include_downstream=include_downstream,
        reason=reason,
    )


def get_onboarding_artifact_lineage(pack: Pack) -> list[dict]:
    return _service.get_onboarding_artifact_lineage(pack)


def run_onboarding_job(pack_id: UUID, job_id: str) -> OnboardingRunResult:
    return _service.run_onboarding_job(pack_id, job_id)


__all__ = [
    "dispatch_onboarding_job_from_api",
    "enqueue_onboarding_job",
    "enqueue_onboarding_qa_repair",
    "enqueue_onboarding_stage_repair",
    "get_onboarding_artifact_lineage",
    "get_onboarding_job_status",
    "request_onboarding_job_pause",
    "resume_onboarding_job",
    "run_onboarding_job",
]
