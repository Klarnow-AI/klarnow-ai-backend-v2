"""Shared schemas for generation flows."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class GenerationColorPalette(BaseModel):
    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None


class GenerationAudiencePersona(BaseModel):
    persona: str
    needs: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)


class GenerationBrandContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    brand_name: str | None = None
    industry: str | None = None
    target_audience: str | None = None
    main_audience: list[str] | None = None
    core_offer: str | None = None
    primary_cta: str | None = None
    primary_pain: str | None = None
    primary_outcome: str | None = None
    hero_angle: str | None = None
    usp_statement: str | None = None
    usp_proof: str | None = None
    logo_url: str | None = None
    logo_markup: str | None = None
    color_palette: GenerationColorPalette | None = None
    fonts: list[str] | None = None
    brand_purpose: list[str] | None = None
    mission: str | None = None
    vision: str | None = None
    promise: str | None = None
    elevator_pitch: str | None = None
    proof_points: list[str] | None = None
    audience_personas: list[GenerationAudiencePersona] | None = None
    voice_archetype: str | None = None
    voice_traits: list[str] | None = None
    design_cues: list[str] | None = None
    style_palette: list[str] | None = None
    typography_direction: str | None = None
