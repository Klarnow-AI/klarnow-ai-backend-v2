"""Exercise the InputNormalizer agent (pipeline stage #1) end-to-end without HTTP.

The script calls the agent directly — it does NOT touch the database or the
orchestrator. That keeps it fast and lets us iterate on the prompt without
spinning up the full pipeline.

Usage:
    python scripts/run_input_normalizer_local.py
    python scripts/run_input_normalizer_local.py --raw  # dump full JSON

Requires ``OPENROUTER_API_KEY`` in the environment (same as production runs).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace


_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# Match the FastAPI app: load klargro-server/.env so OPENROUTER_API_KEY etc. are
# available without the caller having to `export` or `source` anything. Real env
# vars still win because ``override=False``.
try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=False)
except ImportError:  # python-dotenv is in requirements.txt, but degrade gracefully
    pass


# Sample onboarding answers that roughly match the OnboardingFormSubmission
# schema (see app/schemas/onboarding_form.py). All strings satisfy the
# min/max length constraints.
SAMPLE_ANSWERS: dict[str, str] = {
    "question_1_identity_and_location": (
        "We're Northstar Launch Studio, a brand and web studio in Lagos, Nigeria, "
        "serving founders across West Africa and remotely worldwide."
    ),
    "question_2_offer": (
        "We design brand identities and ship launch-ready websites for new startups. "
        "Most clients buy a single $4,500 package that delivers a brand, a one-page "
        "site, and a week-one campaign kit in 14 days."
    ),
    "question_3_customer_and_problem": (
        "Our ideal customer is a solo founder or 2-person team preparing to launch "
        "or pivot in the next 60 days. They need to look credible, tell their story "
        "clearly, and start getting leads without hiring a whole team."
    ),
    "question_4_differentiation": (
        "Unlike agencies that take 2-3 months and designers that only ship a logo, "
        "we deliver a whole launch system in 14 days, with positioning, copy, visuals, "
        "website, and ad creatives all working together."
    ),
    "question_5_goals": (
        "Over the next 3-6 months we want to sign 6-8 new launch packages and build "
        "a stronger founder-focused audience on LinkedIn."
    ),
    "question_6_founder_story_and_brand_feeling": (
        "I started Northstar after watching too many good founders stall on launch "
        "because their branding and website weren't ready. I want people to feel "
        "calm, capable, and excited when they work with us — like they finally have "
        "a co-pilot for the scary part."
    ),
}


def _make_fake_project(answers: dict[str, str]) -> SimpleNamespace:
    """Build a minimal duck-typed ``Project`` for the agent.

    The agent only reads ``project.onboarding_answers``; no other fields are
    needed, so we can side-step SQLAlchemy entirely.
    """
    return SimpleNamespace(onboarding_answers=dict(answers))


async def _run(raw: bool) -> int:
    from app.modules.pipeline.agents.input_normalizer import run as run_agent

    if not os.environ.get("OPENROUTER_API_KEY"):
        print(
            "error: OPENROUTER_API_KEY is not set — the agent cannot reach the model.",
            file=sys.stderr,
        )
        return 2

    project = _make_fake_project(SAMPLE_ANSWERS)

    print("→ Running input_normalizer agent with sample onboarding answers…")
    try:
        payload, metadata = await run_agent(project=project, inputs={})  # pyright: ignore[reportArgumentType]
    except Exception as exc:
        print(f"✗ Agent failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1

    print("✓ Agent succeeded")
    print(
        f"  model: {metadata.get('model_id')}  "
        f"latency: {metadata.get('latency_ms')}ms  "
        f"tokens: {metadata.get('token_usage', {}).get('total_tokens', 0)}"
    )

    if raw:
        print("\n--- NormalizedInput (raw JSON) ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    # Pretty, human-readable summary of the typed artifact.
    print("\n--- Normalized business profile ---")
    print(f"  business_name:      {payload.get('business_name')}")
    print(f"  industry:           {payload.get('industry')}")
    print(f"  geographic_focus:   {payload.get('geographic_focus')}")
    print(f"  delivery_model:     {payload.get('delivery_model')}")
    print(f"  core_offer:         {payload.get('core_offer')}")
    print(f"  target_audience:    {payload.get('target_audience')}")
    print(f"  problem_solved:     {payload.get('problem_solved')}")
    print(f"  price_signals:      {payload.get('price_signals')}")
    print(f"  founder_story:      {payload.get('founder_story')}")
    for label in ("differentiators", "goals", "tone_preferences", "brand_feelings",
                  "constraints", "trust_signals"):
        values = payload.get(label) or []
        joined = "\n    - " + "\n    - ".join(values) if values else " (none)"
        print(f"  {label}:{joined}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the full NormalizedInput JSON payload.",
    )
    args = parser.parse_args()
    return asyncio.run(_run(raw=args.raw))


if __name__ == "__main__":
    sys.exit(main())
