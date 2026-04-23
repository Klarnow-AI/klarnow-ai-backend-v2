"""Request/response schemas for the projects v2 API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.onboarding_form import OnboardingFormSubmission  # noqa: F401 — re-export


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_user_id: UUID
    settings: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    website_goal: str | None = None


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    website_goal: str | None = None
    selected_website_type: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    website_goal: str | None = None
    recommended_website_type: str | None = None
    selected_website_type: str | None = None
    status: str
    onboarding_answers: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# GenerationRun
# ---------------------------------------------------------------------------

class RunCreate(BaseModel):
    """Trigger a new generation run. Optionally specify stages to re-run."""
    from_stage: str | None = None  # if set, re-run from this stage


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    triggered_by_user_id: UUID | None = None
    status: str
    pipeline_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    stages: list[StageRunRead] = Field(default_factory=list)


class StageRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage_name: str
    status: str
    model_id: str | None = None
    prompt_version: str | None = None
    output_artifact_id: UUID | None = None
    token_usage: dict[str, Any] | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# Resolve forward reference
RunRead.model_rebuild()


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------

class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    artifact_type: str
    version_number: int
    status: str
    schema_version: int
    json_payload: dict[str, Any]
    preview_file_id: str | None = None
    created_by_stage: str | None = None
    created_at: datetime


class ApprovalCreate(BaseModel):
    decision: str  # approved / rejected
    reason: str | None = None


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_id: UUID
    user_id: UUID
    decision: str
    reason: str | None = None
    created_at: datetime


class ArtifactPatch(BaseModel):
    """Allow inline editing of an artifact's JSON payload."""
    model_config = ConfigDict(extra="forbid")

    json_payload: dict[str, Any]


class ArtifactRegenerateRequest(BaseModel):
    """Request regeneration of an artifact (re-run its producing stage)."""
    instructions: str | None = None  # optional user guidance for the rerun


class ImagineAssetBody(BaseModel):
    """Create one new creative asset on-demand from a user prompt."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1, max_length=500)
    # ``asset_type`` and ``format`` mirror the values the copywriter emits
    # on its own specs so rendering stays uniform across pipeline and
    # on-demand tiles.
    asset_type: str = Field(..., min_length=1, max_length=64)
    format: str = Field(..., min_length=1, max_length=32)


class ImagineAssetResponse(BaseModel):
    """Returned immediately after a spec is queued — carries the id the
    client needs to track its optimistic tile against the polled artifact.
    """

    artifact_id: UUID
    spec_id: str


class CreativeAssetSpecPatch(BaseModel):
    """Partial update to a single ``AssetSpec`` inside a campaign.

    Every field is optional — the canvas editor patches just the tab the
    user is working in (copy, tokens, or raw JSX). ``None`` means "leave
    as-is"; the service layer drops null keys before merging.
    """

    model_config = ConfigDict(extra="forbid")

    headline: str | None = Field(default=None, max_length=500)
    body_copy: str | None = Field(default=None, max_length=2000)
    cta_text: str | None = Field(default=None, max_length=120)
    layout_notes: str | None = Field(default=None, max_length=1000)
    design_token_overrides: dict[str, str] | None = None
    # Raw JSX source from the power-user tab. Capped to keep abusive pastes
    # from ballooning the artifact row — the real designer pass stays well
    # under this.
    jsx_code: str | None = Field(default=None, max_length=50_000)


class CreativeAssetSpecRead(BaseModel):
    """Single asset spec, as returned by the canvas editor endpoints."""

    model_config = ConfigDict(extra="allow")

    id: str
    asset_type: str
    format: str
    headline: str
    body_copy: str | None = None
    cta_text: str | None = None
    layout_notes: str | None = None
    design_token_overrides: dict[str, str] = Field(default_factory=dict)
    jsx_code: str = ""
    width_px: int = 1080
    height_px: int = 1080
    status: str = "ok"


# ---------------------------------------------------------------------------
# SourceDocument
# ---------------------------------------------------------------------------

class SourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    source_type: str | None = None
    storage_path: str
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# ExportJob
# ---------------------------------------------------------------------------

class ExportJobCreate(BaseModel):
    export_type: str  # brand_package, website_bundle, asset_package, full_project


class ExportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    export_type: str
    status: str
    file_id: str | None = None
    created_at: datetime
