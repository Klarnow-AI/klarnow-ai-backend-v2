"""WebsitePlannerAgent — generates a website blueprint based on business type."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.website_blueprint import WebsiteBlueprint
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a website strategist. Given a business profile, strategy, and design system,
create a detailed website blueprint.

The blueprint must be type-aware based on the website_type:

- landing_page: One offer, one conversion goal, single-page flow.
  Typical sections: hero, problem, solution, trust proof, CTA block, FAQ.

- brochure_static: Informational small-business website for credibility.
  Typical pages: Home, About, Services, Contact.

- service_lead_gen: Lead capture focus with service explanation and trust-building.
  Typical pages: Home, Services, About, FAQ, Contact.

For each page, define:
- Slug, title, and goal
- Sections with section_type, purpose, content notes, and CTA
- SEO title and description

Also define:
- Navigation structure
- Site map
- Global components (header, footer, etc.)
- Forms with fields and submit actions
- CTA strategy
- SEO strategy
- Design application notes

Be specific and structured. Every page and section should have a clear purpose aligned to the business goals."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = inputs.get(ArtifactType.NORMALIZED_INPUT, {})
    design_system = inputs.get(ArtifactType.DESIGN_SYSTEM, {})

    # Determine website type
    website_type = project.selected_website_type or project.recommended_website_type or "brochure_static"

    user_prompt = f"""Create a website blueprint for this business.

Website type: {website_type}

Business profile:
{json.dumps(normalized, indent=2)}

Design system:
{json.dumps(design_system, indent=2)}

Generate the complete blueprint with pages, sections, navigation, forms, and SEO strategy.
Set website_type to "{website_type}" in the output."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=WebsiteBlueprint,
        model_tier="reasoning",
        temperature=0.3,
    )

    # Store the recommended type back on the project if not set
    if not project.recommended_website_type:
        project.recommended_website_type = result.website_type

    return result.model_dump(mode="json"), metadata
