"""Campaign Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import GoalSchema


class CampaignRead(BaseModel):
    id: UUID
    pack_id: UUID
    version: str
    primary_cta: str | None
    goal: dict | None
    angles: list | None
    active_angle_id: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignUpdate(BaseModel):
    primary_cta: str | None = None
    goal: GoalSchema | None = None
    angles: list | None = None
    active_angle_id: str | None = None

    model_config = {"extra": "forbid"}


class CampaignCreate(BaseModel):
    """Used by tools in Phase 2; API may create draft campaign with CTA/goal."""

    primary_cta: str = Field(..., min_length=1)
    goal: GoalSchema | None = None
    angles: list | None = None
