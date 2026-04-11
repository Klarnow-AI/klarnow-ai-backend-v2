"""Design system artifact schema.

Produced by the DesignSystemAgent from the approved identity.
This is the bridge between brand identity and rendered outputs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ColorToken(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    hex: str
    usage: str | None = None


class TypographyToken(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str  # e.g. "heading", "body", "caption"
    font_family: str
    weight: str | None = None
    size_class: str | None = None  # e.g. "lg", "base", "sm"


class CTAStyle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    variant: str  # e.g. "primary", "secondary", "ghost"
    background_color: str | None = None
    text_color: str | None = None
    border_radius: str | None = None
    label_style: str | None = None


class SurfaceStyle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str  # e.g. "card", "hero", "section"
    background: str | None = None
    border: str | None = None
    shadow: str | None = None
    corner_radius: str | None = None


class DesignSystem(BaseModel):
    """Structured design system artifact with renderable tokens."""

    model_config = ConfigDict(extra="ignore")

    color_palette: list[ColorToken] = Field(default_factory=list)
    typography: list[TypographyToken] = Field(default_factory=list)
    spacing_style: str | None = None  # e.g. "airy", "compact", "balanced"
    corner_radius: str | None = None  # e.g. "rounded-lg", "sharp", "pill"
    cta_styles: list[CTAStyle] = Field(default_factory=list)
    surface_styles: list[SurfaceStyle] = Field(default_factory=list)
    icon_style: str | None = None  # e.g. "outlined", "filled", "duotone"
    imagery_style: str | None = None  # e.g. "photography", "illustration", "abstract"
    component_treatments: dict[str, str] = Field(default_factory=dict)
