"""Business logic for the projects v2 API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.schemas.enums import ArtifactStatus, ProjectStatus
from app.schemas.onboarding_form import OnboardingFormSubmission

from .models import (
    Approval,
    Artifact,
    ExportJob,
    GenerationRun,
    Project,
    SourceDocument,
    StageRun,
    Workspace,
)


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

def ensure_default_workspace(db: Session, user_id: UUID) -> Workspace:
    """Return the user's default workspace, creating one if none exists."""
    ws = db.scalars(
        select(Workspace).where(Workspace.owner_user_id == user_id).limit(1)
    ).first()
    if ws:
        return ws
    ws = Workspace(name="My Workspace", owner_user_id=user_id)
    db.add(ws)
    db.flush()
    return ws


def create_workspace(db: Session, user_id: UUID, name: str) -> Workspace:
    ws = Workspace(name=name, owner_user_id=user_id)
    db.add(ws)
    db.flush()
    return ws


def list_workspaces(db: Session, user_id: UUID) -> list[Workspace]:
    return list(
        db.scalars(
            select(Workspace).where(Workspace.owner_user_id == user_id).order_by(Workspace.created_at)
        ).all()
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

def create_project(
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    name: str,
    description: str | None = None,
    website_goal: str | None = None,
) -> Project:
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.owner_user_id != user_id:
        raise NotFoundError("Workspace not found")
    project = Project(
        workspace_id=workspace_id,
        name=name,
        description=description,
        website_goal=website_goal,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.flush()
    return project


def list_projects(db: Session, user_id: UUID, workspace_id: UUID | None = None) -> list[Project]:
    stmt = (
        select(Project)
        .join(Workspace)
        .where(Workspace.owner_user_id == user_id)
        .order_by(Project.updated_at.desc())
    )
    if workspace_id:
        stmt = stmt.where(Project.workspace_id == workspace_id)
    return list(db.scalars(stmt).all())


def get_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project not found")
    ws = db.get(Workspace, project.workspace_id)
    if not ws or ws.owner_user_id != user_id:
        raise NotFoundError("Project not found")
    return project


def update_project(db: Session, project: Project, patch: dict[str, Any]) -> Project:
    for key, value in patch.items():
        if value is not None:
            setattr(project, key, value)
    db.flush()
    return project


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

def submit_onboarding(db: Session, project: Project, form: OnboardingFormSubmission) -> Project:
    project.onboarding_answers = form.model_dump(mode="json")
    project.status = ProjectStatus.ONBOARDING
    db.flush()
    return project


# ---------------------------------------------------------------------------
# Source Documents
# ---------------------------------------------------------------------------

def add_source_document(
    db: Session,
    project_id: UUID,
    name: str,
    storage_path: str,
    source_type: str | None = None,
    mime_type: str | None = None,
    size_bytes: int | None = None,
) -> SourceDocument:
    doc = SourceDocument(
        project_id=project_id,
        name=name,
        storage_path=storage_path,
        source_type=source_type,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(doc)
    db.flush()
    return doc


def list_source_documents(db: Session, project_id: UUID) -> list[SourceDocument]:
    return list(
        db.scalars(
            select(SourceDocument)
            .where(SourceDocument.project_id == project_id)
            .order_by(SourceDocument.created_at)
        ).all()
    )


def delete_source_document(db: Session, document_id: UUID, project_id: UUID) -> None:
    doc = db.get(SourceDocument, document_id)
    if not doc or doc.project_id != project_id:
        raise NotFoundError("Document not found")
    db.delete(doc)
    db.flush()


# ---------------------------------------------------------------------------
# Generation Runs
# ---------------------------------------------------------------------------

def create_run(db: Session, project: Project, user_id: UUID) -> GenerationRun:
    if not project.onboarding_answers:
        raise BadRequestError("Complete onboarding before generating")
    project.status = ProjectStatus.GENERATING
    run = GenerationRun(
        project_id=project.id,
        triggered_by_user_id=user_id,
        status="queued",
        pipeline_version="1",
    )
    db.add(run)
    db.flush()
    return run


def list_runs(db: Session, project_id: UUID) -> list[GenerationRun]:
    return list(
        db.scalars(
            select(GenerationRun)
            .where(GenerationRun.project_id == project_id)
            .order_by(GenerationRun.created_at.desc())
        ).all()
    )


def get_run(db: Session, run_id: UUID) -> GenerationRun:
    run = db.get(GenerationRun, run_id)
    if not run:
        raise NotFoundError("Run not found")
    return run


def get_paused_run_for_project(db: Session, project_id: UUID) -> GenerationRun | None:
    """Find the most recent run that is paused at an approval gate."""
    return db.scalars(
        select(GenerationRun)
        .where(GenerationRun.project_id == project_id)
        .where(GenerationRun.status == "needs_review")
        .order_by(GenerationRun.created_at.desc())
        .limit(1)
    ).first()


def cancel_run(db: Session, run: GenerationRun) -> GenerationRun:
    if run.status in ("completed", "cancelled", "failed"):
        raise BadRequestError(f"Cannot cancel a run with status '{run.status}'")
    run.status = "cancelled"
    for stage in run.stage_runs:
        if stage.status in ("pending", "queued", "running"):
            stage.status = "skipped"
    db.flush()
    return run


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def list_artifacts(
    db: Session,
    project_id: UUID,
    artifact_type: str | None = None,
) -> list[Artifact]:
    stmt = (
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .order_by(Artifact.artifact_type, Artifact.version_number.desc())
    )
    if artifact_type:
        stmt = stmt.where(Artifact.artifact_type == artifact_type)
    return list(db.scalars(stmt).all())


def get_artifact(db: Session, artifact_id: UUID) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise NotFoundError("Artifact not found")
    return artifact


def approve_artifact(db: Session, artifact: Artifact, user_id: UUID, decision: str, reason: str | None = None) -> Approval:
    artifact.status = decision  # "approved" or "rejected"
    approval = Approval(
        artifact_id=artifact.id,
        user_id=user_id,
        decision=decision,
        reason=reason,
    )
    db.add(approval)
    db.flush()
    return approval


def update_artifact_payload(db: Session, artifact: Artifact, json_payload: dict[str, Any]) -> Artifact:
    artifact.json_payload = json_payload
    artifact.status = ArtifactStatus.DRAFT
    db.flush()
    return artifact


def next_artifact_version(db: Session, project_id: UUID, artifact_type: str) -> int:
    max_version = db.scalar(
        select(func.max(Artifact.version_number))
        .where(Artifact.project_id == project_id)
        .where(Artifact.artifact_type == artifact_type)
    )
    return (max_version or 0) + 1


def create_artifact(
    db: Session,
    project_id: UUID,
    artifact_type: str,
    json_payload: dict[str, Any],
    created_by_stage: str | None = None,
    schema_version: int = 1,
) -> Artifact:
    version = next_artifact_version(db, project_id, artifact_type)
    artifact = Artifact(
        project_id=project_id,
        artifact_type=artifact_type,
        version_number=version,
        status=ArtifactStatus.DRAFT,
        schema_version=schema_version,
        json_payload=json_payload,
        created_by_stage=created_by_stage,
    )
    db.add(artifact)
    db.flush()
    return artifact


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def create_export_job(db: Session, project_id: UUID, export_type: str) -> ExportJob:
    job = ExportJob(
        project_id=project_id,
        export_type=export_type,
        status="queued",
    )
    db.add(job)
    db.flush()
    return job


def list_export_jobs(db: Session, project_id: UUID) -> list[ExportJob]:
    return list(
        db.scalars(
            select(ExportJob)
            .where(ExportJob.project_id == project_id)
            .order_by(ExportJob.created_at.desc())
        ).all()
    )
