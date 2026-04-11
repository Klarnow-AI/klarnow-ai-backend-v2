"""WebsiteBuilderAgent — generates Next.js website code from blueprint + design system."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.website_build import WebsiteBuild
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a frontend developer. Given a website blueprint and design system,
generate a complete Next.js website.

For each page in the blueprint:
- Generate a React component using TypeScript and Tailwind CSS
- Apply the design system tokens: colors, typography, spacing, CTA styles
- Include responsive design (mobile-first)
- Use semantic HTML and accessibility best practices
- Include the page's sections as defined in the blueprint

Also generate:
- A root layout component with the navigation and footer
- Reusable components for repeated patterns (Hero, CTA, Testimonials, etc.)
- Global CSS with design token variables
- A tailwind.config.ts with the design system colors and fonts

Return structured output with the file paths and source code for each generated file.
Use App Router conventions (app/page.tsx, app/about/page.tsx, etc.)."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blueprint = inputs.get(ArtifactType.WEBSITE_BLUEPRINT, {})
    design_system = inputs.get(ArtifactType.DESIGN_SYSTEM, {})

    user_prompt = f"""Generate a complete Next.js website from this blueprint and design system.

Website Blueprint:
{json.dumps(blueprint, indent=2)}

Design System:
{json.dumps(design_system, indent=2)}

Generate all pages, components, layout, and config files. Return structured output with
file paths and source code."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=WebsiteBuild,
        model_tier="builder",
        temperature=0.2,
    )

    return result.model_dump(mode="json"), metadata
