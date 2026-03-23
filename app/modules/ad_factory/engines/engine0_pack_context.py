"""Engine 0 — Pack Context Resolver."""

from app.modules.ad_factory.schemas import BrandBrief, Engine0PackContextOutput, PackSnapshot


def run(pack_snapshot: PackSnapshot, brand_brief: BrandBrief) -> Engine0PackContextOutput:
    day = pack_snapshot.day

    if day <= 3:
        funnel_stage = "cold"
        awareness_level = "unaware"
    elif day <= 7:
        funnel_stage = "warm"
        awareness_level = "problem_aware"
    elif day <= 11:
        funnel_stage = "hot"
        awareness_level = "solution_aware"
    else:
        funnel_stage = "retargeting"
        awareness_level = "offer_aware"

    if brand_brief.cta_action in {"book", "call", "apply"}:
        objective_type = "booking"
    elif brand_brief.cta_action == "buy":
        objective_type = "purchase"
    else:
        objective_type = "lead_gen"

    return Engine0PackContextOutput(
        objective_type=objective_type,
        funnel_stage=funnel_stage,
        awareness_level=awareness_level,
        traffic_source=pack_snapshot.traffic_source or "unknown",
    )
