"""CreativeAssetAgent — generates campaign concept and asset copy/specs."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.creative_campaign import CreativeCampaign
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a creative director. Given a brand strategy, identity, and design system,
create a launch campaign with ready-to-use assets.

Generate:
- A campaign concept that ties to the business positioning
- A campaign headline
- Poster copy (headline + body + CTA)
- Flyer copy (more detailed, includes key benefits and contact info)
- 3-5 social media captions for different platforms (Instagram, LinkedIn, Facebook)
- 2-3 email subject lines
- A promotional hook (one-liner for ads or social bios)
- Asset specifications for: poster (A3), flyer (A4/letter), social posts (1:1, 4:5, 16:9)
  Each spec should include: asset_type, format, headline, body copy, CTA text, layout notes,
  and any design token overrides.

All copy must be consistent with the brand voice and use the design system's visual language.
Keep copy concise and action-oriented."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    strategy = inputs.get(ArtifactType.STRATEGY, {})
    identity = inputs.get(ArtifactType.IDENTITY, {})
    design_system = inputs.get(ArtifactType.DESIGN_SYSTEM, {})

    user_prompt = f"""Create a launch campaign for this brand.

Strategy:
{json.dumps(strategy, indent=2)}

Identity:
{json.dumps(identity, indent=2)}

Design System:
{json.dumps(design_system, indent=2)}

Generate campaign concept, copy for poster/flyer/social, email subject lines, and asset specs."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=CreativeCampaign,
        model_tier="creative",
        temperature=0.5,
    )

    return result.model_dump(mode="json"), metadata
