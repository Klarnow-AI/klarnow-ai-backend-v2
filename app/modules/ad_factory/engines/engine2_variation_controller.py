"""Engine 2 — Variation Controller."""

import hashlib

from app.modules.ad_factory.registry.data import (
    HOOK_TYPES,
    INTENT_MAP,
    PATHS,
    TREATMENTS,
    VARIANT_C_TREATMENT,
)
from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine1ContextBuilderOutput,
    Engine2VariationControllerOutput,
    VariantPlan,
)


def _select_from_seed(
    choices: list[str],
    seed: str,
    slot: str,
    exclude: set[str] | None = None,
) -> str:
    exclude = exclude or set()
    available = [choice for choice in choices if choice not in exclude]
    if not available:
        return choices[0]
    digest = hashlib.sha256(f"{seed}::{slot}".encode("utf-8")).hexdigest()
    return available[int(digest[:8], 16) % len(available)]


def run(
    brand_brief: BrandBrief,
    engine1_output: Engine1ContextBuilderOutput,
    selection_seed: str,
) -> Engine2VariationControllerOutput:
    _ = engine1_output
    variant_plans: list[VariantPlan] = []
    used_paths: set[str] = set()
    used_hooks: set[str] = set()

    for slot in ["A", "B", "C"]:
        intent = INTENT_MAP[slot]
        path = _select_from_seed(PATHS, selection_seed, f"{slot}:path", used_paths)
        used_paths.add(path)

        if slot == "C":
            treatment = VARIANT_C_TREATMENT
        else:
            treatment_choices = [
                treatment
                for treatment in TREATMENTS
                if treatment != "offer_smash"
                and (brand_brief.face_on_camera or treatment != "talking_head_authority")
            ]
            treatment = _select_from_seed(
                treatment_choices or ["cinematic_process"],
                selection_seed,
                f"{slot}:treatment",
            )

        hook_type = _select_from_seed(HOOK_TYPES, selection_seed, f"{slot}:hook", used_hooks)
        used_hooks.add(hook_type)

        variant_plans.append(
            VariantPlan(
                slot=slot,
                intent=intent,
                path=path,
                treatment=treatment,
                hook_type=hook_type,
            )
        )

    return Engine2VariationControllerOutput(variant_plans=variant_plans)
