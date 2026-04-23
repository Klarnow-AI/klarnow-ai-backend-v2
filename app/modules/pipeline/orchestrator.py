"""Pipeline orchestrator — creates runs, manages stage lifecycle, triggers agents."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Artifact, GenerationRun, Project, StageRun
from app.schemas.enums import RunStatus, StageStatus

from .config import PIPELINE_VERSION, STAGE_MAP, STAGES
from app.modules.projects.services import update_artifact_payload

from .stage_runner import (
    build_progress_callback,
    load_input_artifacts,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_needs_review,
    mark_stage_running,
    persist_artifact,
)

logger = logging.getLogger(__name__)


def initialize_run(db: Session, run: GenerationRun) -> list[StageRun]:
    """Ensure a run has one StageRun per pipeline stage.

    Idempotent: if the run already has stage runs (e.g. we're resuming after
    an approval gate), existing rows are returned untouched. We only create
    missing stages so a fresh run gets seeded with `PENDING` rows, while a
    resumed run keeps its real history (completed, needs_review, …).
    """
    existing_by_name = {sr.stage_name: sr for sr in run.stage_runs}

    stage_runs: list[StageRun] = []
    created_any = False
    for stage_def in STAGES:
        sr = existing_by_name.get(stage_def.name)
        if sr is None:
            sr = StageRun(
                generation_run_id=run.id,
                stage_name=stage_def.name,
                status=StageStatus.PENDING,
                depends_on_stage_names=list(stage_def.depends_on) if stage_def.depends_on else [],
            )
            db.add(sr)
            created_any = True
        stage_runs.append(sr)

    # Only stamp "started" metadata for a truly fresh run.
    if not existing_by_name:
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.pipeline_version = PIPELINE_VERSION
    else:
        # Resuming: flip the run back to RUNNING so the timeline UI reflects
        # that work is in progress again.
        run.status = RunStatus.RUNNING

    if created_any or not existing_by_name:
        db.flush()
    return stage_runs


def get_ready_stages(db: Session, run: GenerationRun) -> list[StageRun]:
    """Find stages whose dependencies are all completed and that are still pending."""
    completed_stages = {
        sr.stage_name
        for sr in run.stage_runs
        if sr.status in (StageStatus.COMPLETED, StageStatus.NEEDS_REVIEW)
    }
    ready = []
    for sr in run.stage_runs:
        if sr.status != StageStatus.PENDING:
            continue
        stage_def = STAGE_MAP.get(sr.stage_name)
        if not stage_def:
            continue
        deps_met = all(dep in completed_stages for dep in stage_def.depends_on)
        # If any dependency is at an approval gate and needs_review, don't proceed
        blocked_by_approval = False
        for dep in stage_def.depends_on:
            dep_sr = next((s for s in run.stage_runs if s.stage_name == dep), None)
            if dep_sr and dep_sr.status == StageStatus.NEEDS_REVIEW:
                blocked_by_approval = True
                break
        if deps_met and not blocked_by_approval:
            ready.append(sr)
    return ready


async def execute_stage(
    db: Session,
    run: GenerationRun,
    stage_run: StageRun,
) -> None:
    """Execute a single stage: load inputs, run agent, persist artifact."""
    stage_def = STAGE_MAP.get(stage_run.stage_name)
    if not stage_def:
        mark_stage_failed(db, stage_run, f"Unknown stage: {stage_run.stage_name}")
        return

    mark_stage_running(db, stage_run)
    db.commit()

    try:
        project = db.get(Project, run.project_id)
        if not project:
            mark_stage_failed(db, stage_run, "Project not found")
            db.commit()
            return

        # Load input artifacts from dependencies
        inputs = load_input_artifacts(db, project.id, stage_run.stage_name)

        # Progressive-render plumbing: agents that support it (brand_identity,
        # creative_asset) call ``on_progress`` to publish partial work so the
        # UI can light up the logo page / posters page as each image lands
        # instead of waiting for the whole stage to finish.
        progress_holder: dict[str, Artifact | None] = {"artifact": None}
        on_progress = build_progress_callback(
            db,
            project_id=project.id,
            artifact_type=stage_def.artifact_type,
            stage_name=stage_run.stage_name,
            holder=progress_holder,
        )

        # Import and run the agent
        agent_fn = _get_agent_function(stage_run.stage_name)
        result_payload, metadata = await agent_fn(
            project=project,
            inputs=inputs,
            on_progress=on_progress,
        )

        # Finalise the artifact. If the agent published progress along the
        # way we already have a draft row — update it so downstream consumers
        # still see a single artifact version for this stage. Otherwise
        # create a fresh row from the final payload.
        progress_artifact = progress_holder.get("artifact")
        if progress_artifact is not None:
            artifact = update_artifact_payload(db, progress_artifact, result_payload)
        else:
            artifact = persist_artifact(
                db,
                project_id=project.id,
                artifact_type=stage_def.artifact_type,
                payload=result_payload,
                stage_name=stage_run.stage_name,
            )

        # Mark stage completed or needs_review (if approval gate)
        if stage_def.approval_gate:
            mark_stage_needs_review(db, stage_run, artifact.id, metadata)
        else:
            mark_stage_completed(db, stage_run, artifact.id, metadata)

        db.commit()

    except Exception as exc:
        logger.exception("Stage %s failed: %s", stage_run.stage_name, exc)
        db.rollback()
        mark_stage_failed(db, stage_run, str(exc))
        db.commit()


def _has_failed_stage(run: GenerationRun) -> bool:
    """True if any stage in the run has failed.

    The pipeline DAG has parallel branches downstream of `brand_identity`
    (website_builder and creative_asset), so a naive
    "ready stages" check would keep advancing the sibling branch after one
    branch failed. That wastes tokens and confuses the user who's trying
    to fix a single broken stage. We treat ANY stage failure as a full-run
    stop so the retry UX is predictable: fix the one stage, resume the whole
    pipeline from there.
    """
    return any(sr.status == StageStatus.FAILED for sr in run.stage_runs)


async def run_pipeline(db: Session, run: GenerationRun) -> None:
    """Execute the full pipeline, advancing through stages as dependencies resolve.

    Pause semantics: between stage iterations we refresh the run and check
    if the user has flipped its status to ``PAUSED`` via ``POST /runs/{id}/pause``.
    The in-flight stage (if any) always completes first — we only break before
    starting the *next* batch of ready stages. This gives a clean snapshot:
    no stages are left half-written, and ``resume_run`` can safely pick up
    from the next pending stage.

    Fail-fast semantics: a single stage failure halts the entire run even
    when other branches of the DAG are still technically ready. See
    ``_has_failed_stage`` for the rationale.
    """
    initialize_run(db, run)
    db.commit()

    max_iterations = len(STAGES) * 2  # safety limit
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        # Refresh run state so we see external status changes (pause/cancel).
        db.refresh(run)

        # Honour an external pause/cancel request before starting any more work.
        if run.status in (RunStatus.PAUSED, RunStatus.CANCELLED):
            logger.info(
                "Pipeline run %s stopping loop — status=%s", run.id, run.status
            )
            return

        # Fail-fast: if any stage failed, stop the whole run before starting
        # the next batch of ready stages (prevents sibling branches from
        # running past a known failure).
        if _has_failed_stage(run):
            logger.info(
                "Pipeline run %s halting — a stage has failed; marking run FAILED",
                run.id,
            )
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        ready = get_ready_stages(db, run)
        if not ready:
            # Check if we're done or blocked
            all_statuses = {sr.status for sr in run.stage_runs}
            if StageStatus.RUNNING in all_statuses:
                # Still executing — shouldn't happen in sync mode but be safe
                break
            if all_statuses <= {StageStatus.COMPLETED, StageStatus.NEEDS_REVIEW, StageStatus.SKIPPED}:
                # All done
                run.status = RunStatus.COMPLETED
                if StageStatus.NEEDS_REVIEW in all_statuses:
                    run.status = RunStatus.NEEDS_REVIEW
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return
            if StageStatus.FAILED in all_statuses:
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return
            # Blocked by approval gates
            run.status = RunStatus.NEEDS_REVIEW
            db.commit()
            return

        # Execute ready stages (could be parallelized in the future).
        for stage_run in ready:
            await execute_stage(db, run, stage_run)
            # Check again after each stage so a pause request issued mid-loop
            # doesn't start another stage on the same batch.
            db.refresh(run)
            if run.status in (RunStatus.PAUSED, RunStatus.CANCELLED):
                logger.info(
                    "Pipeline run %s stopping mid-batch — status=%s",
                    run.id,
                    run.status,
                )
                return
            # Same fail-fast check mid-batch: if the stage we just ran
            # (or a sibling started earlier in this batch) failed, don't
            # start the next stage in this batch.
            if _has_failed_stage(run):
                logger.info(
                    "Pipeline run %s halting mid-batch — a stage failed",
                    run.id,
                )
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

    # Safety: if we exhausted iterations
    logger.error("Pipeline run %s hit max iterations", run.id)
    run.status = RunStatus.FAILED
    run.completed_at = datetime.now(timezone.utc)
    db.commit()


def resume_after_approval(db: Session, run: GenerationRun) -> None:
    """Resume pipeline execution after an artifact is approved at a gate.

    Called when an approval gate stage has its artifact approved.
    Advances any stages that were blocked by the approval.
    """
    # Mark needs_review stages as completed if their artifact is now approved
    for sr in run.stage_runs:
        if sr.status == StageStatus.NEEDS_REVIEW and sr.output_artifact_id:
            artifact = db.get(Artifact, sr.output_artifact_id)
            if artifact and artifact.status == "approved":
                sr.status = StageStatus.COMPLETED
                db.flush()

    # Continue pipeline
    asyncio.get_event_loop().run_until_complete(run_pipeline(db, run))


def _get_agent_function(stage_name: str):
    """Lazy import of agent functions to avoid circular imports."""
    if stage_name == "input_normalizer":
        from .agents.input_normalizer import run as fn
    elif stage_name == "strategy":
        from .agents.strategy import run as fn
    elif stage_name == "brand_identity":
        from .agents.brand_identity import run as fn
    elif stage_name == "website_builder":
        from .agents.website_builder import run as fn
    elif stage_name == "creative_asset":
        from .agents.creative_asset import run as fn
    elif stage_name == "qa":
        from .agents.qa import run as fn
    else:
        raise ValueError(f"No agent for stage: {stage_name}")
    return fn
