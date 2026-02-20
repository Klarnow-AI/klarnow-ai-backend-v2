"""Shared Pydantic schemas (e.g. Goal object per A-PRD)."""

from pydantic import BaseModel, Field


class GoalSchema(BaseModel):
    """Machine-readable goal object for a campaign (A-PRD)."""

    metric_type: str = Field(..., description="e.g. enquiries, signups")
    target_value: int = Field(..., ge=0)
    time_horizon_days: int = Field(..., ge=1)
    primary_channel: str = Field(..., description="e.g. Meta Ads")
    conversion_action: str = Field(..., description="e.g. Book Call")
