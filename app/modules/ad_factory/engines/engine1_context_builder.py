"""Engine 1 — Context Builder."""

from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine0PackContextOutput,
    Engine1ContextBuilderOutput,
    MessagingConstraints,
    ProofStrategyOutput,
)


def run(brand_brief: BrandBrief, engine0_output: Engine0PackContextOutput) -> Engine1ContextBuilderOutput:
    fallback_used = len(brand_brief.proof_assets) == 0
    strategy_id = "testimonial_lead" if brand_brief.proof_assets else "fallback_generic"

    summary = f"{brand_brief.business_name} helps {brand_brief.audience} achieve {brand_brief.primary_outcome} through {brand_brief.offer}."

    pains = [
        brand_brief.primary_outcome.replace(" ", " lack of ").capitalize(),
        f"Struggling to get results with {brand_brief.offer}",
        "Time and effort going to waste",
    ][:3]

    outcomes = [
        brand_brief.primary_outcome,
        f"Better results with {brand_brief.offer}",
        "Faster progress",
    ][:3]

    differentiators = [
        brand_brief.usp or brand_brief.offer,
        f"{brand_brief.tone} approach",
        f"{brand_brief.price_position} positioning",
    ][:3]

    return Engine1ContextBuilderOutput(
        summary=summary[:280],
        pains=[p[:140] for p in pains],
        outcomes=[o[:140] for o in outcomes],
        differentiators=[d[:140] for d in differentiators],
        proof_strategy=ProofStrategyOutput(strategy_id=strategy_id, fallback_used=fallback_used),
        messaging_constraints=MessagingConstraints(no_assumptions=True, no_freeform=True, disallowed_claims=[]),
    )
