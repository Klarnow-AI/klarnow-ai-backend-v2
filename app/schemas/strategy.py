"""Strategy artifact schema.

Produced by the StrategyAgent from the normalized business input.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KeyMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str
    supporting_point: str


class Strategy(BaseModel):
    """Structured brand strategy artifact."""

    model_config = ConfigDict(extra="ignore")

    positioning_statement: str
    audience_summary: str
    core_values: list[str] = Field(default_factory=list)
    brand_voice: str | None = None
    key_messages: list[KeyMessage] = Field(default_factory=list)
    competitive_differentiation: str | None = None
    primary_cta: str | None = None
    elevator_pitch: str | None = None
    mission: str | None = None
    vision: str | None = None
