"""StrategyAgent — generates brand strategy from normalized business input."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.strategy import Strategy
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a brand strategist. Given a structured business profile, create a comprehensive
brand strategy. Focus on:
- A clear positioning statement that differentiates the business
- An audience summary that captures who the business serves and why
- Core values that feel authentic to the founder's story
- A brand voice description that matches the tone preferences
- Key messages: each item MUST be a JSON object with exactly two string fields:
  "headline" (short hook) and "supporting_point" (one concrete proof, stat, or detail — never empty)
- Competitive differentiation rooted in the business's actual advantages
- A primary CTA that aligns with the business goals
- 3-5 `tagline_options`: short (≤8 word) brand taglines. Distinct in angle,
  not rewordings of each other. These feed the website and creative agents.
- 2-6 `voice_rules`: one-line constraints on ALL downstream copy (e.g.
  "never use emojis", "default to active voice", "no exclamation points",
  "use plain English — avoid SaaS jargon"). Rules, not descriptions.

Be specific and actionable. Avoid generic platitudes. Ground everything in the actual business details provided."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
    on_progress: Any = None,  # noqa: ARG001 — single-LLM stage, no partial output
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = inputs.get(ArtifactType.NORMALIZED_INPUT, {})

    user_prompt = f"""Create a brand strategy for this business:

{json.dumps(normalized, indent=2)}

Generate a positioning statement, audience summary, core values, brand voice,
3–5 key_messages (each with both headline and supporting_point), competitive differentiation,
primary CTA, 3–5 tagline_options, 2–6 voice_rules, and optional elevator_pitch, mission, vision
if they fit the profile."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Strategy,
        model_tier="reasoning",
        temperature=0.3,
    )

    return result.model_dump(mode="json"), metadata
