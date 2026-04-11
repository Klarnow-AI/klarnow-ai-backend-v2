"""Brand identity artifact schema.

Produced by the IdentityAgent from the approved strategy.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Identity(BaseModel):
    """Structured brand identity artifact."""

    model_config = ConfigDict(extra="ignore")

    brand_archetype: str | None = None
    tone_of_voice: str | None = None
    language_style: str | None = None
    visual_direction: str | None = None
    do_guidelines: list[str] = Field(default_factory=list)
    dont_guidelines: list[str] = Field(default_factory=list)
    tagline_options: list[str] = Field(default_factory=list)
    personality_traits: list[str] = Field(default_factory=list)
    voice_rules: list[str] = Field(default_factory=list)
    image_style: str | None = None
    logo_direction: str | None = None
