"""Projects v2 API routes."""

from __future__ import annotations

from uuid import UUID

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db, SessionLocal
from app.core.errors import BadRequestError, NotFoundError
from app.core.storage import upload_file as storage_upload_file

logger = logging.getLogger(__name__)

from . import services
from .schemas import (
    ApprovalCreate,
    ApprovalRead,
    ArtifactPatch,
    ArtifactRead,
    ArtifactRegenerateRequest,
    ExportJobCreate,
    ExportJobRead,
    OnboardingFormSubmission,
    ProjectCreate,
    ProjectListItem,
    ProjectPatch,
    ProjectRead,
    RunCreate,
    RunRead,
    SourceDocumentRead,
    StageRunRead,
    WorkspaceCreate,
    WorkspaceRead,
)

router = APIRouter()


# ── Background pipeline execution ───────────────────────────────────────────

def _run_pipeline_background(run_id: str) -> None:
    """Execute the generation pipeline in a background thread.

    Opens its own DB session since the request session is already closed.
    """
    from app.modules.pipeline.orchestrator import run_pipeline
    from app.modules.projects.models import GenerationRun

    db = SessionLocal()
    try:
        run = db.get(GenerationRun, run_id)
        if not run:
            logger.error("Background pipeline: run %s not found", run_id)
            return
        asyncio.run(run_pipeline(db, run))
        logger.info("Background pipeline: run %s finished with status %s", run_id, run.status)
    except Exception:
        logger.exception("Background pipeline: run %s failed", run_id)
    finally:
        db.close()


def _resume_pipeline_background(run_id: str) -> None:
    """Resume pipeline after an approval gate in a background thread."""
    from app.modules.pipeline.orchestrator import run_pipeline
    from app.modules.projects.models import Artifact, GenerationRun
    from app.schemas.enums import StageStatus

    db = SessionLocal()
    try:
        run = db.get(GenerationRun, run_id)
        if not run:
            return
        # Promote needs_review stages whose artifacts are now approved
        for sr in run.stage_runs:
            if sr.status == StageStatus.NEEDS_REVIEW and sr.output_artifact_id:
                artifact = db.get(Artifact, sr.output_artifact_id)
                if artifact and artifact.status == "approved":
                    sr.status = StageStatus.COMPLETED
        db.flush()
        db.commit()
        # Continue the pipeline
        asyncio.run(run_pipeline(db, run))
        logger.info("Background pipeline resume: run %s finished with status %s", run_id, run.status)
    except Exception:
        logger.exception("Background pipeline resume: run %s failed", run_id)
    finally:
        db.close()


# ── Workspaces ──────────────────────────────────────────────────────────────

@router.post("/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: WorkspaceCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = services.create_workspace(db, user.id, body.name)
    db.commit()
    return ws


@router.get("/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.list_workspaces(db, user.id)


# ── Projects ────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = services.create_project(
        db, body.workspace_id, user.id, body.name, body.description, body.website_goal,
    )
    db.commit()
    return project


@router.get("/projects", response_model=list[ProjectListItem])
def list_projects(
    workspace_id: UUID | None = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.list_projects(db, user.id, workspace_id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.get_project(db, project_id, user.id)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    body: ProjectPatch,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = services.get_project(db, project_id, user.id)
    patch = body.model_dump(exclude_unset=True)
    services.update_project(db, project, patch)
    db.commit()
    return project


@router.post("/projects/{project_id}/onboarding", response_model=ProjectRead)
def submit_onboarding(
    project_id: UUID,
    body: OnboardingFormSubmission,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = services.get_project(db, project_id, user.id)
    services.submit_onboarding(db, project, body)
    db.commit()
    return project


# ── Source Documents ────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/documents", response_model=SourceDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    source_type: str | None = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = services.get_project(db, project_id, user.id)
    content = await file.read()
    storage_key = await storage_upload_file(
        content,
        filename=file.filename or "upload",
        path_key=f"projects/{project.id}/documents",
    )
    doc = services.add_source_document(
        db,
        project_id=project.id,
        name=file.filename or "upload",
        storage_path=storage_key,
        source_type=source_type,
        mime_type=file.content_type,
        size_bytes=len(content),
    )
    db.commit()
    return doc


@router.get("/projects/{project_id}/documents", response_model=list[SourceDocumentRead])
def list_documents(
    project_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)  # auth check
    return services.list_source_documents(db, project_id)


@router.delete("/projects/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    project_id: UUID,
    document_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)  # auth check
    services.delete_source_document(db, document_id, project_id)
    db.commit()


# ── Generation Runs ─────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/runs", response_model=RunRead, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    body: RunCreate | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = services.get_project(db, project_id, user.id)
    run = services.create_run(db, project, user.id)
    db.commit()
    # Kick off pipeline in background
    background_tasks.add_task(_run_pipeline_background, str(run.id))
    return _run_with_stages(db, run)


@router.get("/projects/{project_id}/runs", response_model=list[RunRead])
def list_runs(
    project_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)  # auth check
    runs = services.list_runs(db, project_id)
    return [_run_with_stages(db, r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(
    run_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = services.get_run(db, run_id)
    # Auth: verify user owns the project
    services.get_project(db, run.project_id, user.id)
    return _run_with_stages(db, run)


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run(
    run_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = services.get_run(db, run_id)
    services.get_project(db, run.project_id, user.id)
    services.cancel_run(db, run)
    db.commit()
    return _run_with_stages(db, run)


def _run_with_stages(db: Session, run) -> dict:
    """Serialize a run with its stage runs attached."""
    stages = [StageRunRead.model_validate(s) for s in run.stage_runs]
    data = RunRead.model_validate(run).model_dump()
    data["stages"] = [s.model_dump() for s in stages]
    return data


# ── Artifacts ───────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    project_id: UUID,
    artifact_type: str | None = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)
    return services.list_artifacts(db, project_id, artifact_type)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(
    artifact_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    services.get_project(db, artifact.project_id, user.id)
    return artifact


@router.post("/artifacts/{artifact_id}/approve", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
def approve_artifact(
    artifact_id: UUID,
    body: ApprovalCreate,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    project = services.get_project(db, artifact.project_id, user.id)
    approval = services.approve_artifact(db, artifact, user.id, body.decision, body.reason)
    db.commit()

    # If approved, check if there's a paused run to resume
    if body.decision == "approved":
        paused_run = services.get_paused_run_for_project(db, project.id)
        if paused_run:
            background_tasks.add_task(_resume_pipeline_background, str(paused_run.id))

    return approval


@router.post("/artifacts/{artifact_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
def regenerate_artifact(
    artifact_id: UUID,
    background_tasks: BackgroundTasks,
    body: ArtifactRegenerateRequest | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    project = services.get_project(db, artifact.project_id, user.id)

    # Create a new run that re-executes from the producing stage
    run = services.create_run(db, project, user.id)
    db.commit()
    background_tasks.add_task(_run_pipeline_background, str(run.id))

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "Regeneration queued", "artifact_id": str(artifact_id), "run_id": str(run.id)},
    )


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactRead)
def edit_artifact(
    artifact_id: UUID,
    body: ArtifactPatch,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    services.get_project(db, artifact.project_id, user.id)
    services.update_artifact_payload(db, artifact, body.json_payload)
    db.commit()
    return artifact


@router.get("/artifacts/{artifact_id}/preview")
def preview_artifact(
    artifact_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    services.get_project(db, artifact.project_id, user.id)
    if not artifact.preview_file_id:
        raise NotFoundError("No preview available for this artifact")
    # TODO: return signed URL or redirect to PocketBase asset
    return {"preview_file_id": artifact.preview_file_id}


# ── Exports ─────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/exports", response_model=ExportJobRead, status_code=status.HTTP_202_ACCEPTED)
def create_export(
    project_id: UUID,
    body: ExportJobCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)
    job = services.create_export_job(db, project_id, body.export_type)
    db.commit()
    return job


@router.get("/projects/{project_id}/exports", response_model=list[ExportJobRead])
def list_exports(
    project_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.get_project(db, project_id, user.id)
    return services.list_export_jobs(db, project_id)
