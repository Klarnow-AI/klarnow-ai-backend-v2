"""
Dissertation multi-agent pipeline.

Standalone pipeline that runs six sequential agents against a business
scenario JSON. Supports a `use_retrieval` flag to switch between the
baseline variant (no RAG) and the grounded variant (with FAISS + sentence-BERT).

Agent sequence
--------------
1. InputNormalisationAgent  — clean and structure raw business input
2. StrategyAgent            — generate Brand OS (positioning, messaging, values)
3. IdentityAgent            — derive brand personality and tone of voice
4. WebsiteAgent             — produce website content blueprint
5. CreativeAgent            — create campaign copy and poster/flyer briefs
6. QAAgent                  — consistency check across all outputs

Each agent:
  - Receives the previous agents' outputs as context
  - Optionally receives retrieved source-document chunks (RAG)
  - Returns a structured JSON output via the LLM service

Outputs are saved to app/data/outputs/{baseline|grounded}/{scenario_id}.json
so the evaluation pipeline can load and compare them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# -----------------------------------------------------------------------
# Pydantic output schemas for each agent
# -----------------------------------------------------------------------

class NormalisedInput(BaseModel):
    business_name: str
    industry: str
    target_audience: str
    core_offer: str
    differentiators: list[str]
    goals: list[str]
    tone_preferences: list[str]
    geographic_focus: str
    constraints: list[str]


class BrandOS(BaseModel):
    brand_name: str
    positioning_statement: str
    target_audience_summary: str
    core_values: list[str]
    brand_voice: str
    key_messages: list[str]
    competitive_differentiation: str
    primary_cta: str


class BrandIdentity(BaseModel):
    brand_personality_archetype: str
    tone_of_voice: str
    visual_style_direction: str
    language_style: str
    dos: list[str]
    donts: list[str]
    tagline_options: list[str]


class WebsiteBlueprint(BaseModel):
    hero_headline: str
    hero_subheading: str
    hero_cta: str
    about_section: str
    services_section: list[str]
    social_proof_section: str
    faq_items: list[str]
    footer_cta: str


class CreativeOutput(BaseModel):
    campaign_concept: str
    campaign_headline: str
    poster_copy: str
    flyer_copy: str
    social_caption_options: list[str]
    email_subject_lines: list[str]
    promotional_hook: str


class QAReport(BaseModel):
    overall_consistency_rating: str
    brand_os_alignment: str
    tone_consistency: str
    issues_found: list[str]
    recommendations: list[str]
    passed: bool


class PipelineOutput(BaseModel):
    scenario_id: str
    variant: str  # 'baseline' or 'grounded'
    normalised_input: dict
    brand_os: dict
    identity: dict
    website: dict
    creative: dict
    qa: dict
    retrieval_stats: Optional[dict] = None


# -----------------------------------------------------------------------
# Core runner
# -----------------------------------------------------------------------

async def run_dissertation_pipeline(
    scenario: dict,
    use_retrieval: bool = False,
    output_dir: str = "app/data/outputs",
) -> PipelineOutput:
    """
    Run the full 6-agent dissertation pipeline on a scenario.

    Args:
        scenario: Parsed scenario JSON dict (from app/data/scenarios/).
        use_retrieval: If True, inject retrieved source-document context
                       into each agent's prompt (grounded variant).
                       If False, run without retrieval (baseline variant).
        output_dir: Directory to save outputs for evaluation.

    Returns:
        PipelineOutput with all agent outputs and metadata.
    """
    from app.shared.services.llm import get_llm

    llm = get_llm()
    variant = "grounded" if use_retrieval else "baseline"
    scenario_id = scenario["scenario_id"]
    business_input = scenario["business_input"]

    # ------------------------------------------------------------------
    # Build retrieval store (grounded variant only)
    # ------------------------------------------------------------------
    store = None
    retrieval_stats: Optional[dict] = None

    if use_retrieval and scenario.get("source_documents"):
        from app.retrieval.retriever import build_store_from_scenario
        store = build_store_from_scenario(scenario)
        retrieval_stats = {
            "total_chunks": len(store.chunks),
            "embedding_model": "all-MiniLM-L6-v2",
            "index_type": "faiss.IndexFlatIP",
        }

    def _retrieval_context(agent_type: str) -> str:
        if store is None:
            return ""
        from app.retrieval.retriever import get_retrieval_context
        return get_retrieval_context(
            store, agent_type, business_input.get("business_name", "")
        )

    # ------------------------------------------------------------------
    # Agent 1: Input Normalisation
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("strategy")
    normalised_input: NormalisedInput = await llm.parse(
        system=(
            "You are an expert business analyst. Your task is to normalise and "
            "structure raw business onboarding information into a clean, concise "
            "profile ready for brand strategy generation. Be specific — extract "
            "concrete facts, not generalities."
        ),
        user=(
            f"Business information:\n{json.dumps(business_input, indent=2)}"
            f"{extra_ctx}"
        ),
        schema=NormalisedInput,
        temperature=0.1,
    )

    # ------------------------------------------------------------------
    # Agent 2: Strategy — Brand OS
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("strategy")
    brand_os: BrandOS = await llm.parse(
        system=(
            "You are a senior brand strategist. Generate a complete Brand OS — "
            "the strategic foundation of the brand. Every element must be specific "
            "to this business, not generic. Avoid clichés like 'quality service' "
            "or 'customer-first'. Ground everything in the business's real "
            "differentiators and audience."
        ),
        user=(
            f"Normalised business profile:\n"
            f"{json.dumps(normalised_input.model_dump(), indent=2)}"
            f"{extra_ctx}"
        ),
        schema=BrandOS,
        temperature=0.3,
    )

    # ------------------------------------------------------------------
    # Agent 3: Identity
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("identity")
    identity: BrandIdentity = await llm.parse(
        system=(
            "You are a brand identity specialist. Based on the Brand OS provided, "
            "define the brand's personality, tone of voice, and visual/language "
            "style. Ensure every direction is actionable and clearly differentiated "
            "from generic competitors in this sector."
        ),
        user=(
            f"Brand OS:\n{json.dumps(brand_os.model_dump(), indent=2)}"
            f"{extra_ctx}"
        ),
        schema=BrandIdentity,
        temperature=0.4,
    )

    # ------------------------------------------------------------------
    # Agent 4: Website
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("website")
    website: WebsiteBlueprint = await llm.parse(
        system=(
            "You are a conversion copywriter and UX strategist. Write a complete "
            "website content blueprint for the homepage. Every section must use "
            "the exact brand voice and tone defined in the identity, and must "
            "directly address the target audience's pain points. Include real "
            "specifics: prices, services, outcomes — not placeholders."
        ),
        user=(
            f"Brand OS:\n{json.dumps(brand_os.model_dump(), indent=2)}\n\n"
            f"Brand Identity:\n{json.dumps(identity.model_dump(), indent=2)}"
            f"{extra_ctx}"
        ),
        schema=WebsiteBlueprint,
        temperature=0.4,
    )

    # ------------------------------------------------------------------
    # Agent 5: Creative
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("creative")
    creative: CreativeOutput = await llm.parse(
        system=(
            "You are a creative director and campaign copywriter. Generate a "
            "complete set of creative assets: campaign concept, poster copy, "
            "flyer copy, social captions, and email subject lines. All copy must "
            "reflect the brand voice, speak directly to the target audience's "
            "desires and pain points, and drive the primary CTA."
        ),
        user=(
            f"Brand OS:\n{json.dumps(brand_os.model_dump(), indent=2)}\n\n"
            f"Brand Identity:\n{json.dumps(identity.model_dump(), indent=2)}\n\n"
            f"Website Blueprint:\n{json.dumps(website.model_dump(), indent=2)}"
            f"{extra_ctx}"
        ),
        schema=CreativeOutput,
        temperature=0.6,
    )

    # ------------------------------------------------------------------
    # Agent 6: QA / Consistency Check
    # ------------------------------------------------------------------
    extra_ctx = _retrieval_context("qa")
    qa: QAReport = await llm.parse(
        system=(
            "You are a brand quality assurance reviewer. Evaluate whether the "
            "identity, website content, and creative assets are consistent with "
            "the Brand OS. Check: (1) tone and voice alignment, (2) message "
            "consistency, (3) target audience clarity, (4) specificity vs "
            "genericness. Identify any drift or contradictions."
        ),
        user=(
            f"Brand OS:\n{json.dumps(brand_os.model_dump(), indent=2)}\n\n"
            f"Identity:\n{json.dumps(identity.model_dump(), indent=2)}\n\n"
            f"Website:\n{json.dumps(website.model_dump(), indent=2)}\n\n"
            f"Creative:\n{json.dumps(creative.model_dump(), indent=2)}"
            f"{extra_ctx}"
        ),
        schema=QAReport,
        temperature=0.2,
    )

    # ------------------------------------------------------------------
    # Assemble and persist output
    # ------------------------------------------------------------------
    output = PipelineOutput(
        scenario_id=scenario_id,
        variant=variant,
        normalised_input=normalised_input.model_dump(),
        brand_os=brand_os.model_dump(),
        identity=identity.model_dump(),
        website=website.model_dump(),
        creative=creative.model_dump(),
        qa=qa.model_dump(),
        retrieval_stats=retrieval_stats,
    )

    _save_output(output, output_dir)
    return output


def _save_output(output: PipelineOutput, output_dir: str) -> None:
    """Persist pipeline output to disk for the evaluation pipeline."""
    dir_path = Path(output_dir) / output.variant
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{output.scenario_id}.json"
    with open(file_path, "w") as f:
        json.dump(output.model_dump(), f, indent=2)
