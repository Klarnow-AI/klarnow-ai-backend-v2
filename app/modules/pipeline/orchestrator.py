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
from .stage_runner import (
    load_input_artifacts,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_needs_review,
    mark_stage_running,
    persist_artifact,
)

logger = logging.getLogger(__name__)


def initialize_run(db: Session, run: GenerationRun) -> list[StageRun]:
    """Create StageRun records for every stage in the pipeline."""
    stage_runs = []
    for stage_def in STAGES:
        sr = StageRun(
            generation_run_id=run.id,
            stage_name=stage_def.name,
            status=StageStatus.PENDING,
            depends_on_stage_names=list(stage_def.depends_on) if stage_def.depends_on else [],
        )
        db.add(sr)
        stage_runs.append(sr)
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.pipeline_version = PIPELINE_VERSION
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

        # Import and run the agent
        agent_fn = _get_agent_function(stage_run.stage_name)
        result_payload, metadata = await agent_fn(
            project=project,
            inputs=inputs,
        )

        # Persist the output artifact
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


async def run_pipeline(db: Session, run: GenerationRun) -> None:
    """Execute the full pipeline, advancing through stages as dependencies resolve."""
    stage_runs = initialize_run(db, run)
    db.commit()

    max_iterations = len(STAGES) * 2  # safety limit
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        # Refresh run state
        db.refresh(run)

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

        # Execute ready stages (could be parallelized in the future)
        for stage_run in ready:
            await execute_stage(db, run, stage_run)

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
    elif stage_name == "identity":
        from .agents.identity import run as fn
    elif stage_name == "design_system":
        from .agents.design_system import run as fn
    elif stage_name == "website_planner":
        from .agents.website_planner import run as fn
    elif stage_name == "website_builder":
        from .agents.website_builder import run as fn
    elif stage_name == "creative_asset":
        from .agents.creative_asset import run as fn
    elif stage_name == "qa":
        from .agents.qa import run as fn
    else:
        raise ValueError(f"No agent for stage: {stage_name}")
    return fn
