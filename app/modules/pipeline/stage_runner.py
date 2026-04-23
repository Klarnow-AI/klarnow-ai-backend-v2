"""Base stage runner — common logic for loading inputs, persisting artifacts, updating status."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Artifact, GenerationRun, StageRun
from app.modules.projects.services import create_artifact, update_artifact_payload
from app.schemas import ARTIFACT_SCHEMA_VERSION
from app.schemas.enums import ArtifactType, StageStatus

from .config import STAGE_MAP

# Agents receive this callable when they want to publish partial work (e.g.
# brand identity colours + typography before the logo image has finished
# rendering, or individual poster PNGs as each one comes back). The
# orchestrator wires it up so that the first call *creates* a draft artifact
# row and subsequent calls *update it in place*, so the frontend can poll
# the same artifact id and watch fields fill in.
ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]

logger = logging.getLogger(__name__)


def load_input_artifacts(
    db: Session,
    project_id: UUID,
    stage_name: str,
) -> dict[str, dict[str, Any]]:
    """Load the latest approved or draft artifacts required by this stage.

    Returns a dict of artifact_type -> json_payload.
    """
    stage_def = STAGE_MAP.get(stage_name)
    if not stage_def:
        raise ValueError(f"Unknown stage: {stage_name}")

    inputs: dict[str, dict[str, Any]] = {}
    for dep_name in stage_def.depends_on:
        dep_def = STAGE_MAP.get(dep_name)
        if not dep_def:
            continue
        # Get the latest version of the required artifact type (prefer approved, fall back to draft)
        artifact = db.scalars(
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .where(Artifact.artifact_type == dep_def.artifact_type)
            .order_by(
                # approved first, then by version desc
                (Artifact.status == "approved").desc(),
                Artifact.version_number.desc(),
            )
            .limit(1)
        ).first()
        if artifact:
            inputs[dep_def.artifact_type] = artifact.json_payload
    return inputs


def mark_stage_running(db: Session, stage_run: StageRun) -> None:
    stage_run.status = StageStatus.RUNNING
    stage_run.started_at = datetime.now(timezone.utc)
    db.flush()


def mark_stage_completed(
    db: Session,
    stage_run: StageRun,
    output_artifact_id: UUID,
    metadata: dict[str, Any] | None = None,
) -> None:
    stage_run.status = StageStatus.COMPLETED
    stage_run.output_artifact_id = output_artifact_id
    stage_run.completed_at = datetime.now(timezone.utc)
    if metadata:
        stage_run.model_id = metadata.get("model_id")
        stage_run.latency_ms = metadata.get("latency_ms")
        stage_run.token_usage = metadata.get("token_usage")
    db.flush()


def mark_stage_failed(db: Session, stage_run: StageRun, error: str) -> None:
    stage_run.status = StageStatus.FAILED
    stage_run.error_message = error[:2000]
    stage_run.completed_at = datetime.now(timezone.utc)
    db.flush()


def mark_stage_needs_review(db: Session, stage_run: StageRun, output_artifact_id: UUID, metadata: dict[str, Any] | None = None) -> None:
    """Mark a stage as needing review (approval gate)."""
    stage_run.status = StageStatus.NEEDS_REVIEW
    stage_run.output_artifact_id = output_artifact_id
    stage_run.completed_at = datetime.now(timezone.utc)
    if metadata:
        stage_run.model_id = metadata.get("model_id")
        stage_run.latency_ms = metadata.get("latency_ms")
        stage_run.token_usage = metadata.get("token_usage")
    db.flush()


def persist_artifact(
    db: Session,
    project_id: UUID,
    artifact_type: str,
    payload: dict[str, Any],
    stage_name: str,
) -> Artifact:
    """Create a new versioned artifact."""
    return create_artifact(
        db,
        project_id=project_id,
        artifact_type=artifact_type,
        json_payload=payload,
        created_by_stage=stage_name,
        schema_version=ARTIFACT_SCHEMA_VERSION,
    )


def build_progress_callback(
    db: Session,
    *,
    project_id: UUID,
    artifact_type: str,
    stage_name: str,
    holder: dict[str, Artifact | None],
) -> ProgressCallback:
    """Return an ``on_progress`` callable agents can invoke mid-stage.

    The first call creates a DRAFT artifact row at the next version number
    and stashes it in ``holder["artifact"]``. Every subsequent call just
    rewrites ``json_payload`` on that same row. Each call commits so that
    the frontend — which polls ``GET /projects/{id}/artifacts`` at ~1.5 s —
    can see partially-filled work (e.g. colours and typography before the
    logo image is ready).

    ``execute_stage`` looks at ``holder["artifact"]`` after the agent returns
    to decide whether to create a fresh artifact (no progress was emitted)
    or finalise the existing draft with the agent's final payload.
    """

    async def _on_progress(payload: dict[str, Any]) -> None:
        try:
            existing = holder.get("artifact")
            if existing is None:
                artifact = persist_artifact(
                    db,
                    project_id=project_id,
                    artifact_type=artifact_type,
                    payload=payload,
                    stage_name=stage_name,
                )
                holder["artifact"] = artifact
            else:
                update_artifact_payload(db, existing, payload)
            db.commit()
        except Exception:  # pragma: no cover - progress updates are best-effort
            # A failed progress write must never crash the agent: the final
            # artifact at stage end is still the source of truth. Roll back
            # the partial write and keep going.
            logger.warning(
                "progress callback failed for stage=%s; continuing", stage_name,
                exc_info=True,
            )
            db.rollback()

    return _on_progress
