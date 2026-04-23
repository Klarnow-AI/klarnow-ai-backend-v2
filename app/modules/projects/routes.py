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
    CreativeAssetSpecPatch,
    CreativeAssetSpecRead,
    ImagineAssetBody,
    ImagineAssetResponse,
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
    """Resume a run's orchestrator loop in a background thread.

    Used for two cases:
    - **Approval gate:** an artifact was just approved; any ``NEEDS_REVIEW``
      stages whose artifact is now ``approved`` get promoted to ``COMPLETED``
      before the loop picks up again.
    - **Pause → resume:** the run was paused by the user and has since been
      flipped back to ``RUNNING`` by ``resume_run``. The promotion step
      above is a no-op in this case (no approved artifacts waiting), and the
      loop simply picks up from the next pending stage.
    """
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


def _design_creative_asset_background(
    project_id: str,
    artifact_id: str,
    spec_id: str,
    prompt: str,
    asset_type: str,
    asset_format: str,
) -> None:
    """Run the imagine flow (copy + JSX) for a single pending spec.

    Mirrors the shape of ``_run_pipeline_background``: opens its own DB
    session because the request session is already closed by the time this
    lands on a background task worker.
    """
    db = SessionLocal()
    try:
        services.design_pending_creative_asset(
            db,
            UUID(project_id),
            UUID(artifact_id),
            spec_id,
            prompt=prompt,
            asset_type=asset_type,
            asset_format=asset_format,
        )
    except Exception:
        logger.exception(
            "Imagine asset: design failed for spec %s on artifact %s",
            spec_id,
            artifact_id,
        )
    finally:
        db.close()


def _redesign_creative_asset_background(
    project_id: str,
    artifact_id: str,
    spec_id: str,
) -> None:
    """Re-run the JSX designer for one spec after copy/token edits.

    Same pattern as ``_design_creative_asset_background`` — fresh DB
    session, swallow failures so the worker never crashes the task queue.
    """
    db = SessionLocal()
    try:
        services.redesign_creative_asset(
            db,
            UUID(project_id),
            UUID(artifact_id),
            spec_id,
        )
    except Exception:
        logger.exception(
            "Redesign asset: failed for spec %s on artifact %s",
            spec_id,
            artifact_id,
        )
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


@router.post("/runs/{run_id}/pause", response_model=RunRead)
def pause_run(
    run_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request the background pipeline to pause after the current stage.

    We only flip the status here — the orchestrator polls the run row
    between stages and exits cleanly on its own. Clients should keep
    polling; the status will flip to ``paused`` once the current stage
    finishes (usually within seconds).
    """
    run = services.get_run(db, run_id)
    services.get_project(db, run.project_id, user.id)
    services.pause_run(db, run)
    db.commit()
    return _run_with_stages(db, run)


@router.post("/runs/{run_id}/resume", response_model=RunRead)
def resume_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resume a paused run. Flips the status to ``running`` and schedules the
    orchestrator in a background task to pick up from the next pending
    stage."""
    run = services.get_run(db, run_id)
    services.get_project(db, run.project_id, user.id)
    services.resume_run(db, run)
    db.commit()
    background_tasks.add_task(_resume_pipeline_background, str(run.id))
    return _run_with_stages(db, run)


@router.post("/runs/{run_id}/retry", response_model=RunRead)
def retry_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed or cancelled run from the point it stopped.

    Only the stages that didn't finish successfully are reset — completed
    and needs_review stages stay put, so the user doesn't pay the cost
    of re-running everything that already passed.
    """
    run = services.get_run(db, run_id)
    services.get_project(db, run.project_id, user.id)
    services.retry_run(db, run)
    db.commit()
    background_tasks.add_task(_resume_pipeline_background, str(run.id))
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


@router.post(
    "/projects/{project_id}/creative-assets",
    response_model=ImagineAssetResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def imagine_creative_asset(
    project_id: UUID,
    body: ImagineAssetBody,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Append a pending creative asset and kick off copy + JSX generation.

    Returns immediately with the newly-appended spec id so the frontend can
    render an optimistic "imagining…" tile. The heavy lifting happens in
    :func:`_design_creative_asset_background`, and the UI picks up the
    finished spec via the existing artifact-poll loop.
    """
    services.get_project(db, project_id, user.id)
    artifact, spec_id = services.append_pending_creative_asset(
        db,
        project_id,
        prompt=body.prompt,
        asset_type=body.asset_type,
        asset_format=body.format,
    )
    db.commit()
    background_tasks.add_task(
        _design_creative_asset_background,
        str(project_id),
        str(artifact.id),
        spec_id,
        body.prompt,
        body.asset_type,
        body.format,
    )
    return ImagineAssetResponse(artifact_id=artifact.id, spec_id=spec_id)


@router.get(
    "/artifacts/{artifact_id}/creative-assets/{spec_id}",
    response_model=CreativeAssetSpecRead,
)
def get_creative_asset_spec_route(
    artifact_id: UUID,
    spec_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = services.get_artifact(db, artifact_id)
    services.get_project(db, artifact.project_id, user.id)
    return services.get_creative_asset_spec(db, artifact_id, spec_id)


@router.patch(
    "/artifacts/{artifact_id}/creative-assets/{spec_id}",
    response_model=CreativeAssetSpecRead,
)
def patch_creative_asset_spec_route(
    artifact_id: UUID,
    spec_id: str,
    body: CreativeAssetSpecPatch,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save edits from the canvas editor onto a single asset spec.

    The patch body is whichever tab the user is working in (copy, tokens,
    or raw JSX). We apply and commit synchronously so the response carries
    the final spec; callers that want a fresh designer pass on top of the
    edit call the sibling ``/render`` route right after.
    """
    artifact = services.get_artifact(db, artifact_id)
    services.get_project(db, artifact.project_id, user.id)
    updated = services.patch_creative_asset_spec(
        db, artifact_id, spec_id, body.model_dump(exclude_none=True)
    )
    db.commit()
    return updated


@router.post(
    "/artifacts/{artifact_id}/creative-assets/{spec_id}/render",
    status_code=status.HTTP_202_ACCEPTED,
)
def render_creative_asset_spec_route(
    artifact_id: UUID,
    spec_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kick off a fresh designer pass for this single spec.

    Flips the spec to ``"pending"`` inline and queues the LLM call in the
    background so the request returns fast. The client picks up the new
    JSX on its next artifact poll (or its own targeted spec fetch).
    """
    artifact = services.get_artifact(db, artifact_id)
    project = services.get_project(db, artifact.project_id, user.id)
    # Validate the spec exists before scheduling the worker — avoids a
    # background task that quietly does nothing because the client typo'd
    # the id.
    services.get_creative_asset_spec(db, artifact_id, spec_id)
    background_tasks.add_task(
        _redesign_creative_asset_background,
        str(project.id),
        str(artifact_id),
        spec_id,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "Redesign queued",
            "artifact_id": str(artifact_id),
            "spec_id": spec_id,
        },
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
