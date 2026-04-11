"""DesignSystemAgent — generates structured design tokens from the approved identity."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.design_system import DesignSystem
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a design systems engineer. Given a brand identity, create a concrete design system
with renderable tokens. This system bridges brand identity and actual UI implementation.

Create:
- Color palette: 5-7 named colors with hex values and usage notes (primary, secondary, accent, background, surface, text, muted)
- Typography: heading and body font families with weights and size classes
- Spacing style: airy, compact, or balanced
- Corner radius: rounded-lg, sharp, pill, etc.
- CTA button styles: primary and secondary variants with colors and border radius
- Surface styles: card, hero, and section backgrounds
- Icon style: outlined, filled, or duotone
- Imagery style: photography, illustration, or abstract
- Component treatments: specific notes for nav, footer, testimonial cards, etc.

Use real hex values, real font names (Google Fonts preferred), and concrete CSS-ready values.
The design system must be directly implementable."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = inputs.get(ArtifactType.IDENTITY, {})

    user_prompt = f"""Create a design system from this brand identity:

{json.dumps(identity, indent=2)}

Generate color palette (with hex values), typography tokens, spacing, CTA styles,
surface styles, and component treatments. Use concrete, implementable values."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=DesignSystem,
        model_tier="creative",
        temperature=0.3,
    )

    return result.model_dump(mode="json"), metadata
