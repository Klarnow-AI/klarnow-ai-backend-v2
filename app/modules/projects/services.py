"""Business logic for the projects v2 API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.schemas.enums import ArtifactStatus, ArtifactType, ProjectStatus
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


def pause_run(db: Session, run: GenerationRun) -> GenerationRun:
    """Request a pause. The orchestrator sees this on its next stage boundary
    and halts; the current stage (if any) is allowed to finish so we never
    leave a half-executed stage behind."""
    if run.status not in ("queued", "running"):
        raise BadRequestError(f"Cannot pause a run with status '{run.status}'")
    run.status = "paused"
    db.flush()
    return run


def resume_run(db: Session, run: GenerationRun) -> GenerationRun:
    """Flip a paused run back to running. The caller is expected to re-kick
    the background pipeline task; this only updates the status so polling
    clients see the transition right away."""
    if run.status != "paused":
        raise BadRequestError(f"Cannot resume a run with status '{run.status}'")
    run.status = "running"
    db.flush()
    return run


def retry_run(db: Session, run: GenerationRun) -> GenerationRun:
    """Pick the run up from where it stopped.

    Handles two cases:
    - **failed**: the run tripped on a stage error. We reset every failed
      stage back to ``PENDING`` (clearing ``error_message`` / timestamps /
      ``output_artifact_id``) so the orchestrator re-runs only the broken
      step. Completed and needs_review stages upstream are left untouched.
    - **cancelled**: the user hit Stop, which marked any in-flight or
      future stages as ``SKIPPED``. We flip those skipped stages back to
      ``PENDING`` so they get another chance. Anything genuinely finished
      (completed / needs_review) stays put.

    The caller schedules ``_resume_pipeline_background`` after committing
    so the orchestrator picks up the restored run.
    """
    if run.status not in ("failed", "cancelled"):
        raise BadRequestError(
            f"Cannot retry a run with status '{run.status}' — "
            "retry is only valid for failed or cancelled runs."
        )

    now = datetime.now(timezone.utc)
    reset_statuses = ("failed", "skipped")
    touched = 0
    for stage in run.stage_runs:
        if stage.status in reset_statuses:
            stage.status = "pending"
            stage.error_message = None
            stage.started_at = None
            stage.completed_at = None
            stage.output_artifact_id = None
            stage.latency_ms = None
            touched += 1

    if touched == 0:
        # Nothing to retry — all stages are already terminal in a success
        # state. Surface a clear error instead of silently starting a no-op.
        raise BadRequestError(
            "Nothing to retry — no failed or skipped stages on this run."
        )

    run.status = "running"
    run.completed_at = None
    if run.started_at is None:
        run.started_at = now
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
    artifacts = list(db.scalars(stmt).all())
    for artifact in artifacts:
        _ensure_creative_campaign_spec_ids(db, artifact)
    return artifacts


def get_artifact(db: Session, artifact_id: UUID) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise NotFoundError("Artifact not found")
    _ensure_creative_campaign_spec_ids(db, artifact)
    return artifact


def _ensure_creative_campaign_spec_ids(db: Session, artifact: Artifact) -> None:
    """Lazy-backfill ``AssetSpec.id`` on legacy creative campaign artifacts.

    The ``id`` field was added to ``AssetSpec`` after some campaigns had
    already been persisted, so their stored ``asset_specs`` entries have
    no id. The frontend canvas editor keys edits on that id, so we assign
    one per spec on first read and commit the migration back to the row.
    Safe to call on any artifact — it no-ops for non-campaign types and
    for campaigns whose specs are already fully id'd.
    """
    if artifact.artifact_type != ArtifactType.CREATIVE_CAMPAIGN:
        return
    payload = artifact.json_payload or {}
    specs = payload.get("asset_specs")
    if not isinstance(specs, list) or not specs:
        return
    changed = False
    new_specs: list[Any] = []
    for spec in specs:
        if isinstance(spec, dict) and not spec.get("id"):
            new_specs.append({**spec, "id": uuid4().hex})
            changed = True
        else:
            new_specs.append(spec)
    if not changed:
        return
    # Reassign the full payload so SQLAlchemy notices the JSON column
    # mutation (matching the pattern used by ``append_pending_creative_asset``
    # and the update helper below).
    artifact.json_payload = {**payload, "asset_specs": new_specs}
    db.commit()


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


# ---------------------------------------------------------------------------
# On-demand creative asset (imagine flow)
# ---------------------------------------------------------------------------

def _latest_artifact_payload(
    db: Session,
    project_id: UUID,
    artifact_type: str,
) -> dict[str, Any] | None:
    """Return the most recent payload for ``artifact_type`` or ``None``.

    Prefers approved versions, falling back to the highest-version draft.
    Mirrors the precedence the stage runner uses when gathering inputs so
    the imagine flow sees the same context as the pipeline agents do.
    """
    artifact = db.scalars(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .where(Artifact.artifact_type == artifact_type)
        .order_by(
            (Artifact.status == "approved").desc(),
            Artifact.version_number.desc(),
        )
        .limit(1)
    ).first()
    return dict(artifact.json_payload) if artifact else None


def append_pending_creative_asset(
    db: Session,
    project_id: UUID,
    *,
    prompt: str,
    asset_type: str,
    asset_format: str,
) -> tuple[Artifact, str]:
    """Append a ``status="pending"`` ``AssetSpec`` to the latest campaign.

    Returns ``(artifact, spec_id)`` so the route can immediately respond with
    the id the frontend needs to show its optimistic tile. The background
    worker then fills copy + JSX in place.

    Raises ``BadRequestError`` when there's no creative campaign artifact to
    append to — we want the user to have to finish the pipeline at least once
    before they can imagine more assets.
    """
    from uuid import uuid4

    # Import here to avoid circular import through agents at module load.
    from app.modules.pipeline.agents.creative_asset import _dimensions_for
    from app.schemas.creative_campaign import AssetSpec

    artifact = db.scalars(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .where(Artifact.artifact_type == ArtifactType.CREATIVE_CAMPAIGN)
        .order_by(
            (Artifact.status == "approved").desc(),
            Artifact.version_number.desc(),
        )
        .limit(1)
    ).first()
    if artifact is None:
        raise BadRequestError(
            "No creative campaign to append to yet. "
            "Run the generation pipeline at least once before requesting new assets."
        )

    spec_id = uuid4().hex
    # Seed the pending spec with the user's prompt as the headline so the
    # optimistic tile has something meaningful to render while the LLMs
    # rewrite it. The background worker replaces this with proper copy.
    placeholder = AssetSpec(
        id=spec_id,
        asset_type=asset_type,
        format=asset_format,
        headline=prompt.strip()[:80] or "Imagining…",
        status="pending",
    )
    width_px, height_px = _dimensions_for(placeholder)
    placeholder.width_px = width_px
    placeholder.height_px = height_px

    payload = dict(artifact.json_payload or {})
    specs = list(payload.get("asset_specs") or [])
    specs.append(placeholder.model_dump(mode="json"))
    payload["asset_specs"] = specs
    # Reassigning the whole dict is how the rest of the module flags JSON
    # column mutations for SQLAlchemy (``update_artifact_payload`` does the
    # same). ``flag_modified`` would also work but isn't used anywhere else
    # in this codebase.
    artifact.json_payload = payload
    db.flush()
    return artifact, spec_id


def get_creative_asset_spec(
    db: Session,
    artifact_id: UUID,
    spec_id: str,
) -> dict[str, Any]:
    """Return the single ``AssetSpec`` dict for ``spec_id``.

    Raises ``NotFoundError`` when either the artifact or the spec inside it
    is missing. Callers use this to pre-flight edits so they can 404 cleanly.
    """
    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.artifact_type != ArtifactType.CREATIVE_CAMPAIGN:
        raise NotFoundError("Creative campaign artifact not found")
    for spec in artifact.json_payload.get("asset_specs") or []:
        if isinstance(spec, dict) and spec.get("id") == spec_id:
            return dict(spec)
    raise NotFoundError("Asset spec not found on this campaign")


def patch_creative_asset_spec(
    db: Session,
    artifact_id: UUID,
    spec_id: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Apply a partial update to a single ``AssetSpec`` inside a campaign.

    Accepts the handful of fields the canvas editor exposes (copy, design
    token overrides, raw ``jsx_code``). Null values are skipped so the
    client can send only the changed keys. When ``jsx_code`` lands with
    non-empty content we also bump the spec's ``status`` to ``"ok"`` —
    saving JSX directly is a valid alternative to re-running the designer.
    """
    _ALLOWED = {
        "headline",
        "body_copy",
        "cta_text",
        "layout_notes",
        "design_token_overrides",
        "jsx_code",
    }

    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.artifact_type != ArtifactType.CREATIVE_CAMPAIGN:
        raise NotFoundError("Creative campaign artifact not found")

    cleaned = {k: v for k, v in patch.items() if k in _ALLOWED and v is not None}
    if not cleaned:
        raise BadRequestError("Nothing to update — patch was empty.")

    updated: dict[str, Any] | None = None

    def _apply(spec: dict[str, Any]) -> dict[str, Any]:
        nonlocal updated
        merged = {**spec, **cleaned}
        # If the client saved raw JSX, treat that as a successful render so
        # the tile flips out of any "pending" / "error" state. Empty strings
        # don't count — we only promote on real content landing.
        if isinstance(cleaned.get("jsx_code"), str) and cleaned["jsx_code"].strip():
            merged["status"] = "ok"
        updated = merged
        return merged

    _update_spec_in_artifact(db, artifact_id, spec_id, updater=_apply)
    if updated is None:
        raise NotFoundError("Asset spec not found on this campaign")
    return updated


def redesign_creative_asset(
    db: Session,
    project_id: UUID,
    artifact_id: UUID,
    spec_id: str,
) -> None:
    """Re-run the designer phase for a single spec using its current copy.

    Intended for the "Update design" button on the canvas editor: the user
    tweaks headline/body/cta/tokens via ``patch_creative_asset_spec``, then
    fires this to turn the updated copy into fresh JSX. We flip the spec to
    ``"pending"`` up front so the UI can show a shimmer, then either land
    real JSX or mark ``"error"``.
    """
    import asyncio as _asyncio

    from app.modules.pipeline.agents.creative_asset import design_one_asset
    from app.schemas.creative_campaign import AssetSpec

    spec_dict = get_creative_asset_spec(db, artifact_id, spec_id)
    brand_identity = (
        _latest_artifact_payload(db, project_id, ArtifactType.BRAND_IDENTITY) or {}
    )
    campaign = (
        _latest_artifact_payload(db, project_id, ArtifactType.CREATIVE_CAMPAIGN) or {}
    )
    campaign_concept = str(campaign.get("campaign_concept") or "")

    # Mark pending so the canvas shows a loading state immediately.
    _update_spec_in_artifact(
        db,
        artifact_id,
        spec_id,
        updater=lambda s: {**s, "status": "pending"},
    )
    db.commit()

    # Hydrate into the Pydantic model so ``design_one_asset`` sees the
    # expected shape (it reads from attributes, not dict keys).
    spec_model = AssetSpec.model_validate(spec_dict)

    jsx_code, outcome = _asyncio.run(
        design_one_asset(
            spec=spec_model,
            brand_identity=brand_identity,
            campaign_concept=campaign_concept,
        )
    )

    def _finalize(s: dict[str, Any]) -> dict[str, Any]:
        merged = dict(s)
        if jsx_code:
            merged["jsx_code"] = jsx_code
            merged["status"] = "ok"
        else:
            merged["status"] = "error"
        if outcome.get("width_px"):
            merged["width_px"] = outcome["width_px"]
        if outcome.get("height_px"):
            merged["height_px"] = outcome["height_px"]
        return merged

    _update_spec_in_artifact(db, artifact_id, spec_id, updater=_finalize)
    db.commit()


def _update_spec_in_artifact(
    db: Session,
    artifact_id: UUID,
    spec_id: str,
    *,
    updater: Any,
) -> None:
    """Apply ``updater(spec_dict) -> spec_dict`` to the matching spec.

    Kept internal because the calling shape is narrow — the imagine worker
    is the only consumer.
    """
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        return
    payload = dict(artifact.json_payload or {})
    specs = list(payload.get("asset_specs") or [])
    for i, spec in enumerate(specs):
        if isinstance(spec, dict) and spec.get("id") == spec_id:
            specs[i] = updater(dict(spec))
            break
    else:
        # Spec disappeared — the artifact was regenerated while we were
        # working. Drop the result on the floor rather than creating a
        # zombie entry.
        return
    payload["asset_specs"] = specs
    artifact.json_payload = payload
    db.flush()


def design_pending_creative_asset(
    db: Session,
    project_id: UUID,
    artifact_id: UUID,
    spec_id: str,
    *,
    prompt: str,
    asset_type: str,
    asset_format: str,
) -> None:
    """Turn a pending ``AssetSpec`` into a fully-designed one.

    This is the background worker: it runs the copywriter for this single
    prompt, then the designer, then writes the populated spec back to the
    artifact. If either phase fails we mark the spec as ``"error"`` so the
    UI can surface a retry affordance — we never remove the spec, because
    the optimistic tile on the client is keyed off its id.
    """
    import asyncio as _asyncio

    from app.modules.pipeline.agents.creative_asset import (
        design_one_asset,
        write_copy_for_prompt,
    )

    strategy = _latest_artifact_payload(db, project_id, ArtifactType.STRATEGY) or {}
    brand_identity = (
        _latest_artifact_payload(db, project_id, ArtifactType.BRAND_IDENTITY) or {}
    )
    campaign = (
        _latest_artifact_payload(db, project_id, ArtifactType.CREATIVE_CAMPAIGN) or {}
    )
    campaign_concept = str(campaign.get("campaign_concept") or "")

    try:
        spec = _asyncio.run(
            write_copy_for_prompt(
                user_prompt=prompt,
                asset_type=asset_type,
                asset_format=asset_format,
                strategy=strategy,
                brand_identity=brand_identity,
            )
        )
    except Exception as exc:  # noqa: BLE001 — report back to the UI
        _update_spec_in_artifact(
            db,
            artifact_id,
            spec_id,
            updater=lambda s: {**s, "status": "error", "layout_notes": f"copy failed: {exc}"},
        )
        db.commit()
        return

    # Preserve the id the client is already polling for.
    spec.id = spec_id

    # Persist the copy-populated spec right away so the tile can show real
    # headline / body / CTA while the designer is still writing JSX.
    _update_spec_in_artifact(
        db,
        artifact_id,
        spec_id,
        updater=lambda s: {**spec.model_dump(mode="json"), "status": "pending"},
    )
    db.commit()

    jsx_code, outcome = _asyncio.run(
        design_one_asset(
            spec=spec,
            brand_identity=brand_identity,
            campaign_concept=campaign_concept,
        )
    )

    if jsx_code:
        spec.jsx_code = jsx_code
        spec.status = "ok"
    else:
        spec.status = "error"

    # ``outcome`` has width/height overrides when the designer actually ran.
    if outcome.get("width_px"):
        spec.width_px = outcome["width_px"]
    if outcome.get("height_px"):
        spec.height_px = outcome["height_px"]

    _update_spec_in_artifact(
        db,
        artifact_id,
        spec_id,
        updater=lambda _s: spec.model_dump(mode="json"),
    )
    db.commit()
