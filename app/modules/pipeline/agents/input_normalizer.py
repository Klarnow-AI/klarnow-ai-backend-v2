"""InputNormalizerAgent — normalizes 6 onboarding answers into a structured business profile.

This is the first stage of the pipeline. Its job is to take the raw answers
submitted through the onboarding form and turn them into a canonical
``NormalizedInput`` artifact that every downstream agent can rely on.

The prompt is intentionally strict about *preserving* information rather than
inventing anything — the LLM here is a structured extractor, not a
storyteller.
"""

from __future__ import annotations

from typing import Any

from app.modules.projects.models import Project
from app.modules.pipeline.model_gateway import generate_structured
from app.schemas.normalized_input import NormalizedInput


REQUIRED_ANSWER_KEYS: tuple[str, ...] = (
    "question_1_identity_and_location",
    "question_2_offer",
    "question_3_customer_and_problem",
    "question_4_differentiation",
    "question_5_goals",
    "question_6_founder_story_and_brand_feeling",
)


SYSTEM_PROMPT = """You are a business analyst. Given raw onboarding answers from a small business owner,
extract a structured business profile.

Rules you must follow:
- Preserve exact names, locations, numbers, currencies, and product/service terms from the answers.
- Do not invent facts that are not in the answers. If a field cannot be inferred, leave it null or empty.
- Keep list items short, specific, and deduplicated.
- Write every field in the same language as the original answers.
- Tone preferences should be adjectives (e.g. "warm", "credible", "playful"), not full sentences.
- Brand feelings should describe how the customer should feel (e.g. "reassured", "energised").
- Differentiators should be concrete reasons to choose this business, not generic claims.

Return a JSON object matching the NormalizedInput schema exactly. Do not add extra fields."""


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

Extract a structured business profile grounded strictly in these answers."""


def _collect_answers(project: Project) -> dict[str, str]:
    """Pull the 6 onboarding answers off the project and validate them.

    Raises ``ValueError`` with a friendly message listing every missing or
    empty question, so the orchestrator surfaces a single actionable error
    instead of a stack trace.
    """
    raw = project.onboarding_answers or {}
    answers: dict[str, str] = {}
    missing: list[str] = []
    for key in REQUIRED_ANSWER_KEYS:
        value = raw.get(key)
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            missing.append(key)
        answers[key] = text
    if missing:
        raise ValueError(
            "Cannot normalize input — the following onboarding answers are missing or empty: "
            + ", ".join(missing)
        )
    return answers


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],  # noqa: ARG001 — first stage has no upstream artifacts
    on_progress: Any = None,  # noqa: ARG001 — no partial output to stream
) -> tuple[dict[str, Any], dict[str, Any]]:
    answers = _collect_answers(project)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        q1=answers["question_1_identity_and_location"],
        q2=answers["question_2_offer"],
        q3=answers["question_3_customer_and_problem"],
        q4=answers["question_4_differentiation"],
        q5=answers["question_5_goals"],
        q6=answers["question_6_founder_story_and_brand_feeling"],
    )

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=NormalizedInput,
        model_tier="fast",
        temperature=0.1,
    )

    if not result.business_name or not result.business_name.strip():
        raise ValueError(
            "Input normalizer returned a profile without a business name — "
            "check that answer 1 contains the business name."
        )

    return result.model_dump(mode="json"), metadata
