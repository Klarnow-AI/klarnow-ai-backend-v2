"""Engine 5 — Visual Director."""

from app.modules.ad_factory.schemas import (
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


def run(engine2_output: Engine2VariationControllerOutput, engine4_output: Engine4ScriptConverterOutput) -> Engine5VisualDirectorOutput:
    shot_plans: list[VariantShotPlan] = []

    for i, vp in enumerate(engine2_output.variant_plans):
        scripts = engine4_output.scripts[i]
        shots: list[Shot] = []
        on_screen_texts = [
            scripts.hook_line[:7].strip() or "Watch",
            "The problem", "How we help", "Our process",
            "Proof", "Human moment", "Results",
            scripts.cta.mid_line[:7].strip() or "Act now",
        ]
        for j, st in enumerate(SHOT_TYPES):
            ost = (on_screen_texts[j] if j < len(on_screen_texts) else "Next")[:60]
            nano = f"Professional ad shot, {st}, clear lighting, vertical 9:16, high quality"[:800]
            shots.append(
                Shot(
                    index=j + 1,
                    shot_type=st,
                    description=f"Shot {j+1}: {st.replace('_', ' ').title()}",
                    on_screen_text=ost,
                    nanobanana_prompt=nano,
                    caption_overlay={"enabled": True},
                )
            )
        shot_plans.append(
            VariantShotPlan(
                slot=vp.slot,
                shots=shots,
                pacing={"avg_shot_seconds_min": 1.2, "avg_shot_seconds_max": 1.6},
            )
        )

    return Engine5VisualDirectorOutput(shot_plans=shot_plans)
