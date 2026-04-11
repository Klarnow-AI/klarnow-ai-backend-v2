"""IdentityAgent — generates brand identity from the approved strategy."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.identity import Identity
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a brand identity designer. Given a brand strategy, define the brand identity system.

Create:
- A brand archetype that captures the personality
- Tone of voice guidelines
- Language style direction
- Visual direction description
- Do and don't guidelines for brand consistency
- 3-5 tagline options
- Personality traits
- Voice rules for copywriting
- Image style direction
- Logo direction notes

Ground everything in the strategy. The identity should feel like a natural expression of the
positioning, values, and voice defined in the strategy."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    strategy = inputs.get(ArtifactType.STRATEGY, {})

    user_prompt = f"""Define a brand identity for this strategy:

{json.dumps(strategy, indent=2)}

Create archetype, tone, visual direction, dos/donts, taglines, personality traits, and voice rules."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Identity,
        model_tier="creative",
        temperature=0.5,
    )

    return result.model_dump(mode="json"), metadata
