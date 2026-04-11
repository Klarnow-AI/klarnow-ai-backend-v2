"""Website blueprint artifact schema.

Produced by the WebsitePlannerAgent. Varies by website type.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PageSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section_type: str  # e.g. "hero", "features", "testimonials", "cta", "faq"
    purpose: str | None = None
    content_notes: str | None = None
    cta: str | None = None


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str  # e.g. "home", "about", "services", "contact"
    title: str
    goal: str | None = None
    sections: list[PageSection] = Field(default_factory=list)
    seo_title: str | None = None
    seo_description: str | None = None


class NavigationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    href: str
    children: list[NavigationItem] = Field(default_factory=list)


class FormDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    purpose: str
    fields: list[str] = Field(default_factory=list)
    submit_action: str | None = None


class WebsiteBlueprint(BaseModel):
    """Structured website blueprint artifact."""

    model_config = ConfigDict(extra="ignore")

    website_type: str  # landing_page, brochure_static, service_lead_gen
    primary_goal: str
    secondary_goals: list[str] = Field(default_factory=list)
    navigation: list[NavigationItem] = Field(default_factory=list)
    site_map: list[str] = Field(default_factory=list)
    pages: list[PageDefinition] = Field(default_factory=list)
    global_components: list[str] = Field(default_factory=list)
    forms: list[FormDefinition] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    seo_strategy: str | None = None
    design_application_notes: str | None = None
    cta_strategy: str | None = None
