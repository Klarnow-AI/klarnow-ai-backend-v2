"""Engine 5 — Visual Director."""

from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine2VariationControllerOutput,
    Engine4ScriptConverterOutput,
    Engine5VisualDirectorOutput,
    Shot,
    VariantShotPlan,
)

SHOT_TYPES = [
    "pattern_interrupt", "establishing", "mechanism_1", "mechanism_2",
    "proof_overlay", "human_moment", "result_reveal", "cta_frame",
]


def _clip(text: str | None, limit: int, fallback: str) -> str:
    normalized = " ".join((text or "").split())
    return (normalized or fallback)[:limit]


def run(
    brand_brief: BrandBrief,
    engine2_output: Engine2VariationControllerOutput,
    engine4_output: Engine4ScriptConverterOutput,
) -> Engine5VisualDirectorOutput:
    shot_plans: list[VariantShotPlan] = []
    proof_label = (
        brand_brief.proof_assets[0].label
        if brand_brief.proof_assets
        else "real customer proof"
    )

    for i, variant_plan in enumerate(engine2_output.variant_plans):
        scripts = engine4_output.scripts[i]
        beat_lookup = {beat.beat_name: beat.text for beat in scripts.script_30s.beats}
        shot_descriptions = {
            "pattern_interrupt": (
                f"Open on a real person delivering the hook '{scripts.hook_line}' directly to camera "
                f"for {brand_brief.audience}."
            ),
            "establishing": (
                f"Show {brand_brief.audience} dealing with {beat_lookup.get('problem', brand_brief.offer)} "
                f"before discovering {brand_brief.business_name}."
            ),
            "mechanism_1": (
                f"Demonstrate {brand_brief.offer} in action so the viewer instantly understands "
                f"the core idea '{scripts.core_concept}'."
            ),
            "mechanism_2": (
                f"Show the key transformation step that moves someone from "
                f"{beat_lookup.get('problem', 'the old way')} toward {brand_brief.primary_outcome}."
            ),
            "proof_overlay": (
                f"Layer in believable proof like {proof_label} while reinforcing "
                f"'{beat_lookup.get('proof', brand_brief.primary_outcome)}'."
            ),
            "human_moment": (
                f"Capture a genuine human reaction of confidence, relief, or delight after using "
                f"{brand_brief.offer}."
            ),
            "result_reveal": (
                f"Reveal the outcome clearly: {brand_brief.primary_outcome} for {brand_brief.audience}."
            ),
            "cta_frame": (
                f"Close with a direct CTA from {brand_brief.business_name}: '{scripts.cta.end_line}'."
            ),
        }
        shots: list[Shot] = []
        on_screen_texts = [
            _clip(scripts.hook_line, 60, "Watch this"),
            _clip(beat_lookup.get("problem"), 60, "The problem"),
            _clip(beat_lookup.get("mechanism"), 60, "How we help"),
            _clip(scripts.core_concept, 60, "Our process"),
            _clip(beat_lookup.get("proof"), 60, "Proof"),
            _clip(brand_brief.business_name, 60, "Human moment"),
            _clip(brand_brief.primary_outcome, 60, "Results"),
            _clip(scripts.cta.end_line or scripts.cta.mid_line, 60, "Act now"),
        ]
        for j, st in enumerate(SHOT_TYPES):
            ost = on_screen_texts[j] if j < len(on_screen_texts) else "Next"
            description = _clip(shot_descriptions.get(st), 200, f"Show {brand_brief.offer} in a real-world scene.")
            nano = _clip(
                (
                    f"Vertical 9:16 short-form ad for {brand_brief.business_name}. {description} "
                    f"Real people relevant to {brand_brief.audience}, natural light, authentic expression, "
                    "mobile-first framing, premium commercial quality. Avoid factories, industrial machinery, "
                    "engineering diagrams, and abstract mechanical visuals unless the offer requires them."
                ),
                800,
                "Vertical 9:16 short-form ad with real people and natural light.",
            )
            shots.append(
                Shot(
                    index=j + 1,
                    shot_type=st,
                    description=description,
                    on_screen_text=ost,
                    nanobanana_prompt=nano,
                    caption_overlay={"enabled": True},
                )
            )
        shot_plans.append(
            VariantShotPlan(
                slot=variant_plan.slot,
                shots=shots,
                pacing={"avg_shot_seconds_min": 1.2, "avg_shot_seconds_max": 1.6},
            )
        )

    return Engine5VisualDirectorOutput(shot_plans=shot_plans)
