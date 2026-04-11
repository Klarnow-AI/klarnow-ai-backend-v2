"""Base stage runner — common logic for loading inputs, persisting artifacts, updating status."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Artifact, GenerationRun, StageRun
from app.modules.projects.services import create_artifact
from app.schemas import ARTIFACT_SCHEMA_VERSION
from app.schemas.enums import ArtifactType, StageStatus

from .config import STAGE_MAP

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
