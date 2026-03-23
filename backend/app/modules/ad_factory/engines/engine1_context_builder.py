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


def _sentence_fragment(text: str | None, fallback: str) -> str:
    normalized = " ".join((text or "").split()).strip()
    return (normalized or fallback).rstrip(".")


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
        brand_brief.brand_context.elevator_pitch
        if brand_brief.brand_context and brand_brief.brand_context.elevator_pitch
        else (
            f"{brand_brief.business_name} helps {brand_brief.audience} achieve "
            f"{brand_brief.primary_outcome} with {brand_brief.offer}."
        )
    )
    primary_pain = _sentence_fragment(
        brand_brief.primary_pain,
        f"{brand_brief.primary_outcome.lower()} feeling far away",
    )
    proof_point = (
        brand_brief.brand_context.proof_points[0]
        if brand_brief.brand_context and brand_brief.brand_context.proof_points
        else ""
    )

    pains = [
        f"{brand_brief.audience} are tired of {primary_pain.lower()}.",
        f"{brand_brief.offer} feels harder to trust when {engine0_output.awareness_level.replace('_', ' ')}.",
        f"Without a clear system, {brand_brief.primary_outcome.lower()} keeps taking too much time and energy.",
    ]
    outcomes = [
        brand_brief.primary_outcome,
        f"A clearer path to {brand_brief.primary_outcome.lower()}",
        "Faster momentum with less friction",
    ]
    differentiators = [
        brand_brief.usp or brand_brief.offer,
        proof_point or f"{brand_brief.tone} delivery for {brand_brief.audience}",
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
