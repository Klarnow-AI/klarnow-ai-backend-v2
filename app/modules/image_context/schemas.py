"""Schemas for image context retrieval and indexing operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import ReferenceSnippet


class ImageContextRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=10)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)


class ImageContextRetrieveItem(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    source_name: str | None = None
    caption: str | None = None
    metadata_json: dict | None = None
    score: float
    preview_url: str | None = None


class ImageContextRetrieveResponse(BaseModel):
    query: str
    items: list[ImageContextRetrieveItem]
    references: list[ReferenceSnippet]
    context_text: str


class GlobalImageContextItemRead(BaseModel):
    id: UUID
    source_name: str | None = None
    caption: str | None = None
    metadata_json: dict | None = None
    score: float | None = None
    preview_url: str | None = None


class GlobalImageContextRetrieveResponse(BaseModel):
    query: str
    items: list[GlobalImageContextItemRead]
    references: list[ReferenceSnippet]
    context_text: str


class ImageContextBackfillRequest(BaseModel):
    include_proofs: bool = True
    include_assets: bool = True


class ImageContextBackfillResponse(BaseModel):
    queued_jobs: int
    queued_proof_jobs: int
    queued_asset_jobs: int


class ImageContextJobRead(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    operation: str
    status: str
    attempt: int
    max_attempts: int
    last_error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
