"""Website build artifact schema.

Produced by the WebsiteBuilderAgent from the approved blueprint + design system.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GeneratedPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    file_path: str  # e.g. "app/page.tsx", "app/about/page.tsx"
    source_code: str
    sections_used: list[str] = Field(default_factory=list)


class GeneratedComponent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    file_path: str  # e.g. "components/Hero.tsx"
    source_code: str


class WebsiteBuild(BaseModel):
    """Generated Next.js website artifact."""

    model_config = ConfigDict(extra="ignore")

    pages: list[GeneratedPage] = Field(default_factory=list)
    components: list[GeneratedComponent] = Field(default_factory=list)
    layout_source: str | None = None  # root layout.tsx
    global_css: str | None = None  # globals.css / tailwind config
    design_tokens_applied: dict[str, str] = Field(default_factory=dict)
    config_files: dict[str, str] = Field(default_factory=dict)  # e.g. next.config.js, tailwind.config.ts
    bundle_file_id: str | None = None  # PocketBase file reference for downloadable zip
