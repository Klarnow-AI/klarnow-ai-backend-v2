"""Engine 1 — Context Builder."""

from app.modules.ad_factory.registry.data import get_proof_strategy
from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine0PackContextOutput,
    Engine1ContextBuilderOutput,
    MessagingConstraints,
    ProofStrategyCandidate,
)


def _clip(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


def run(
    brand_brief: BrandBrief,
    engine0_output: Engine0PackContextOutput,
    selection_seed: str,
) -> Engine1ContextBuilderOutput:
    proof_strategy = get_proof_strategy(
        len(brand_brief.proof_assets) > 0,
        selection_seed=selection_seed,
    )
    summary = (
        f"{brand_brief.business_name} helps {brand_brief.audience} achieve "
        f"{brand_brief.primary_outcome} with {brand_brief.offer}."
    )

    pains = [
        f"{brand_brief.audience} are tired of {brand_brief.primary_outcome.lower()} feeling far away.",
        f"{brand_brief.offer} feels harder to trust when {engine0_output.awareness_level.replace('_', ' ')}.",
        "Slow progress keeps draining time, energy, and confidence.",
    ]
    outcomes = [
        brand_brief.primary_outcome,
        f"A clearer path to {brand_brief.primary_outcome.lower()}",
        "Faster momentum with less friction",
    ]
    differentiators = [
        brand_brief.usp or brand_brief.offer,
        f"{brand_brief.tone} delivery for {brand_brief.audience}",
        f"{engine0_output.objective_type.replace('_', ' ')} focused structure",
    ]

    return Engine1ContextBuilderOutput(
        summary=_clip(summary, 280),
        pains=[_clip(item, 140) for item in pains[:3]],
        outcomes=[_clip(item, 140) for item in outcomes[:3]],
        differentiators=[_clip(item, 140) for item in differentiators[:3]],
        proof_strategy_candidate=ProofStrategyCandidate(
            strategy_id=str(proof_strategy["id"]),
            fallback_used=bool(proof_strategy["fallback_used"]),
        ),
        messaging_constraints=MessagingConstraints(
            no_assumptions=True,
            no_freeform=True,
            disallowed_claims=[
                "guaranteed results",
                "medical cures",
                "legal certainty",
                "risk-free financial returns",
            ],
        ),
    )
