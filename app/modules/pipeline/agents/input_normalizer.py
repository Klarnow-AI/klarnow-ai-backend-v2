"""InputNormalizerAgent — normalizes 6 onboarding answers into structured business profile.

This stage is primarily deterministic (rule-based extraction) with an optional
LLM pass for ambiguous fields.
"""

from __future__ import annotations

from typing import Any

from app.modules.projects.models import Project
from app.schemas.normalized_input import NormalizedInput
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a business analyst. Given raw onboarding answers from a small business owner,
extract a structured business profile. Be precise — preserve exact names, locations, numbers, and
differentiators from the original answers. Do not invent information not present in the answers.

Return a JSON object matching the NormalizedInput schema."""

USER_PROMPT_TEMPLATE = """Here are the 6 onboarding answers from the business owner:

1. Business identity and location:
{q1}

2. Offer and typical purchase:
{q2}

3. Ideal customer and their problem:
{q3}

4. Why choose them over alternatives:
{q4}

5. Top goals for the next 3-6 months:
{q5}

6. Founder story and desired brand feeling:
{q6}

Extract a structured business profile from these answers."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    answers = project.onboarding_answers or {}

    user_prompt = USER_PROMPT_TEMPLATE.format(
        q1=answers.get("question_1_identity_and_location", ""),
        q2=answers.get("question_2_offer", ""),
        q3=answers.get("question_3_customer_and_problem", ""),
        q4=answers.get("question_4_differentiation", ""),
        q5=answers.get("question_5_goals", ""),
        q6=answers.get("question_6_founder_story_and_brand_feeling", ""),
    )

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=NormalizedInput,
        model_tier="fast",
        temperature=0.1,
    )

    return result.model_dump(mode="json"), metadata
