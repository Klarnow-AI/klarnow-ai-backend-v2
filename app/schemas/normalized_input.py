"""Normalized business input artifact schema.

Produced by the InputNormalizerAgent from the 6 onboarding answers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NormalizedInput(BaseModel):
    """Structured business profile derived from the 6 onboarding questions."""

    model_config = ConfigDict(extra="ignore")

    business_name: str
    industry: str | None = None
    target_audience: str | None = None
    core_offer: str | None = None
    differentiators: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    tone_preferences: list[str] = Field(default_factory=list)
    geographic_focus: str | None = None
    constraints: list[str] = Field(default_factory=list)
    founder_story: str | None = None
    brand_feelings: list[str] = Field(default_factory=list)
    problem_solved: str | None = None
    price_signals: str | None = None
    trust_signals: list[str] = Field(default_factory=list)
    delivery_model: str | None = None
