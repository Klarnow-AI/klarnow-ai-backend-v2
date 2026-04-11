"""Creative campaign artifact schema.

Produced by the CreativeAssetAgent from the approved strategy + identity + design system.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AssetSpec(BaseModel):
    """Specification for a single creative asset (poster, flyer, social post)."""

    model_config = ConfigDict(extra="ignore")

    asset_type: str  # poster, flyer, social_instagram, social_linkedin, social_facebook
    format: str  # e.g. "4x5", "1x1", "16x9", "A4"
    headline: str
    body_copy: str | None = None
    cta_text: str | None = None
    layout_notes: str | None = None
    design_token_overrides: dict[str, str] = Field(default_factory=dict)


class CreativeCampaign(BaseModel):
    """Structured creative campaign artifact."""

    model_config = ConfigDict(extra="ignore")

    campaign_concept: str
    campaign_headline: str
    poster_copy: str | None = None
    flyer_copy: str | None = None
    social_captions: list[str] = Field(default_factory=list)
    email_subject_lines: list[str] = Field(default_factory=list)
    promotional_hook: str | None = None
    asset_specs: list[AssetSpec] = Field(default_factory=list)
