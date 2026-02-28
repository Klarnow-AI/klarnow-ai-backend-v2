"""Engine 6 — Kling Assembler."""

from app.modules.ad_factory.schemas import (
    Engine5VisualDirectorOutput,
    Engine6KlingAssemblerOutput,
    KlingPrompt,
    VariantKlingPrompts,
)


def run(engine4_scripts: list, engine5_output: Engine5VisualDirectorOutput) -> Engine6KlingAssemblerOutput:
    kling_prompts_list: list[VariantKlingPrompts] = []

    for sp in engine5_output.shot_plans:
        shot_descs = [s.description for s in sp.shots]
        full_prompt_30s = " | ".join(shot_descs) + ". Vertical 9:16. Fast cuts. Captions on. CTA mid and end."
        full_prompt_15s = " | ".join(shot_descs[:5]) + ". Vertical 9:16. Fast cuts. Captions on."

        kling_prompts_list.append(
            VariantKlingPrompts(
                slot=sp.slot,
                kling_15s=KlingPrompt(prompt=full_prompt_15s[:4000], duration_seconds=15),
                kling_30s=KlingPrompt(prompt=full_prompt_30s[:4000], duration_seconds=30),
                render_requirements={
                    "aspect_ratio": "9:16",
                    "captions_on": True,
                    "fast_cuts": True,
                    "cta_mid_and_end": True,
                    "nanobanana_anchors": True,
                },
            )
        )

    return Engine6KlingAssemblerOutput(kling_prompts=kling_prompts_list)
