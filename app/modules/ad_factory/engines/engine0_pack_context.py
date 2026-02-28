"""Engine 0 — Pack Context Resolver."""

from app.modules.ad_factory.schemas import Engine0PackContextOutput, PackSnapshot


def run(pack_snapshot: PackSnapshot) -> Engine0PackContextOutput:
    stage = pack_snapshot.stage
    day = pack_snapshot.day

    if day <= 3:
        funnel_stage = "cold"
        awareness_level = "unaware"
    elif day <= 7:
        funnel_stage = "warm"
        awareness_level = "problem_aware"
    else:
        funnel_stage = "hot"
        awareness_level = "solution_aware"

    objective_type = "lead_gen" if "traffic" in stage or "publish" in stage else "lead_gen"

    return Engine0PackContextOutput(
        objective_type=objective_type,
        funnel_stage=funnel_stage,
        awareness_level=awareness_level,
        traffic_source=pack_snapshot.traffic_source or "unknown",
    )
