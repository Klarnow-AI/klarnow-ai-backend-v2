"""QAAgent — validates consistency across all generated artifacts."""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.qa_report import QAReport
from app.modules.pipeline.model_gateway import generate_structured

SYSTEM_PROMPT = """You are a brand quality assurance reviewer. Given all generated artifacts for a business,
evaluate consistency and quality across the entire output.

Check for:
1. Tone consistency — does the website copy, campaign copy, and identity all sound like the same brand?
2. Message consistency — are the key messages, positioning, and CTA consistent across all outputs?
3. Target audience consistency — do all outputs speak to the same audience?
4. Factual grounding — are claims grounded in the business profile? No invented features or benefits.
5. Completeness — are all expected outputs present and substantive?
6. CTA clarity — is the primary CTA clear and consistent across all touchpoints?

For each check, report:
- check_name: short identifier
- category: one of (tone_consistency, message_consistency, audience_consistency, factual_grounding, completeness, cta_clarity)
- status: passed, warning, or failed
- detail: explanation
- affected_artifact: which artifact type has the issue (if any)

Also report:
- overall_status: passed if all checks pass, warning if any warnings, failed if any failures
- consistency_score: 0-100 (deduct 20 per failure, 5 per warning)
- issues: list of specific problems found with severity and suggested fixes
- recommendations: actionable improvement suggestions"""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    # QA receives all prior artifacts
    artifacts_summary = {k: v for k, v in inputs.items()}

    user_prompt = f"""Review these generated artifacts for consistency and quality:

{json.dumps(artifacts_summary, indent=2)}

Evaluate tone consistency, message consistency, audience consistency, factual grounding,
completeness, and CTA clarity. Report your findings as a structured QA report."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=QAReport,
        model_tier="fast",
        temperature=0.1,
    )

    return result.model_dump(mode="json"), metadata
