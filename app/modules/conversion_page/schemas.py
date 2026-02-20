"""Conversion page Pydantic schemas. Structure is React-driven (sections with type + props)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversionPageRead(BaseModel):
    id: UUID
    pack_id: UUID
    version: str
    structure: dict | None
    lead_filter_type: str | None
    lead_filter_value: str | None
    published_at: datetime | None
    live_url: str | None
    seo_metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversionPageList(BaseModel):
    items: list[ConversionPageRead]
    total: int


class ConversionPageUpdate(BaseModel):
    structure: dict | None = None
    lead_filter_type: str | None = None
    lead_filter_value: str | None = None
    seo_metadata: dict | None = None

    model_config = {"extra": "forbid"}


class ConversionPagePublish(BaseModel):
    # If omitted, backend will publish to {frontend_url}/p/{pack_id}
    live_url: str | None = None
    waiver_confirmed: bool = False  # If True, allow publish without proof in Proof Vault


class ConversionPagePreview(BaseModel):
    """Payload for live preview: structure + metadata so React can render."""
    structure: dict | None
    seo_metadata: dict | None
    version: str
    primary_cta: str | None
