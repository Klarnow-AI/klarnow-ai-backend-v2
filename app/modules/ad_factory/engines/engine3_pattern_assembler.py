"""Engine 3 — Pattern Assembler."""

from app.modules.ad_factory.registry.data import get_pattern_for_path
from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine2VariationControllerOutput,
    Engine3PatternAssemblerOutput,
    PatternSelection,
)


def run(
    brand_brief: BrandBrief,
    engine2_output: Engine2VariationControllerOutput,
    engine1_proof_strategy_id: str,
    selection_seed: str,
) -> Engine3PatternAssemblerOutput:
    cta_action = brand_brief.cta_action
    cta_id = f"cta_{cta_action}"

    selections: list[PatternSelection] = []
    for vp in engine2_output.variant_plans:
        selections.append(
            PatternSelection(
                slot=vp.slot,
                pattern_id=get_pattern_for_path(vp.path),
                hook_id=f"hook_{vp.hook_type}",
                proof_strategy_id=engine1_proof_strategy_id,
                cta_id=cta_id,
                line_template_ids={"problem": ["problem_1", "problem_2"], "mechanism": ["mechanism_1"], "offer": ["offer_1"]},
            )
        )
    return Engine3PatternAssemblerOutput(selections=selections)
