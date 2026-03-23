"""Engine 3 — Pattern Assembler."""

from app.modules.ad_factory.registry.data import (
    PATTERN_PACK_VERSION,
    REGISTRY_VERSION,
    get_cta_template,
    get_hook_template,
    get_line_templates,
    get_pattern_for_path,
)
from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine0PackContextOutput,
    Engine2VariationControllerOutput,
    Engine3PatternAssemblerOutput,
    PatternSelection,
)


def run(
    brand_brief: BrandBrief,
    engine0_output: Engine0PackContextOutput,
    engine2_output: Engine2VariationControllerOutput,
    engine1_proof_strategy_id: str,
    selection_seed: str,
) -> Engine3PatternAssemblerOutput:
    selections: list[PatternSelection] = []
    for variant_plan in engine2_output.variant_plans:
        pattern = get_pattern_for_path(
            variant_plan.path,
            objective_type=engine0_output.objective_type,
            treatment=variant_plan.treatment,
            traffic_source=engine0_output.traffic_source,
            selection_seed=selection_seed,
            slot=variant_plan.slot,
        )
        hook = get_hook_template(
            variant_plan.hook_type,
            objective_type=engine0_output.objective_type,
            treatment=variant_plan.treatment,
            traffic_source=engine0_output.traffic_source,
            selection_seed=selection_seed,
            slot=variant_plan.slot,
        )
        cta = get_cta_template(
            brand_brief.cta_action,
            selection_seed=selection_seed,
            slot=variant_plan.slot,
        )
        # Engine 4 resolves the final CTA copy from BrandBrief, but the registry choice
        # stays explicit here for lineage and replay.
        selections.append(
            PatternSelection(
                slot=variant_plan.slot,
                pattern_id=str(pattern["id"]),
                hook_id=str(hook["id"]),
                proof_strategy_id=engine1_proof_strategy_id,
                cta_id=str(cta["id"]),
                line_template_ids={
                    "problem": [
                        item["id"]
                        for item in get_line_templates(
                            "problem",
                            objective_type=engine0_output.objective_type,
                            treatment=variant_plan.treatment,
                            traffic_source=engine0_output.traffic_source,
                            selection_seed=selection_seed,
                            slot=variant_plan.slot,
                            count=2,
                        )
                    ],
                    "mechanism": [
                        item["id"]
                        for item in get_line_templates(
                            "mechanism",
                            objective_type=engine0_output.objective_type,
                            treatment=variant_plan.treatment,
                            traffic_source=engine0_output.traffic_source,
                            selection_seed=selection_seed,
                            slot=variant_plan.slot,
                            count=1,
                        )
                    ],
                    "offer": [
                        item["id"]
                        for item in get_line_templates(
                            "offer",
                            objective_type=engine0_output.objective_type,
                            treatment=variant_plan.treatment,
                            traffic_source=engine0_output.traffic_source,
                            selection_seed=selection_seed,
                            slot=variant_plan.slot,
                            count=1,
                        )
                    ],
                },
                registry_version=REGISTRY_VERSION,
                pattern_pack_version=PATTERN_PACK_VERSION,
            )
        )
    return Engine3PatternAssemblerOutput(selections=selections)
