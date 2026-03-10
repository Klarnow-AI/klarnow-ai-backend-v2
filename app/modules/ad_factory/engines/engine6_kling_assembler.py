"""Engine 6 — Kling Assembler."""

from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine2VariationControllerOutput,
    Engine4ScriptConverterOutput,
    Engine5VisualDirectorOutput,
    Engine6KlingAssemblerOutput,
    KlingPrompt,
    VariantKlingPrompts,
)


INTENT_DIRECTIONS = {
    "emotion_led": "emotion-led, human, relatable, high-empathy",
    "logic_led": "logic-led, clear, credible, proof-forward",
    "offer_led": "offer-led, urgent, conversion-focused, direct-response",
}

TREATMENT_DIRECTIONS = {
    "talking_head_authority": "founder-to-camera delivery with authority and trust",
    "cinematic_process": "show the process in polished but believable real-world scenes",
    "ugc_customer_story": "UGC-style customer story with authentic handheld energy",
    "offer_smash": "direct-response ad pacing with bold offer framing",
}


def _clip(text: str | None, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


def _build_spoken_narration(script, max_chars: int = 420) -> str:
    beats = getattr(script, "beats", []) or []
    spoken_lines = [
        _clip(getattr(beat, "text", None), 140)
        for beat in beats
        if _clip(getattr(beat, "text", None), 140)
    ]
    return _clip(" ".join(spoken_lines), max_chars)


def _build_kling_prompt(
    brand_brief: BrandBrief,
    variant_plan,
    scripts,
    shot_plan,
    shot_count: int,
    duration_hint: str,
    spoken_narration: str,
) -> str:
    selected_shots = shot_plan.shots[:shot_count]
    visual_sequence = "; ".join(_clip(shot.description, 180) for shot in selected_shots if shot.description)
    caption_lines = " | ".join(_clip(shot.on_screen_text, 60) for shot in selected_shots if shot.on_screen_text)
    proof_label = (
        brand_brief.proof_assets[0].label
        if brand_brief.proof_assets
        else "real customer proof"
    )

    parts = [
        f"Create a vertical 9:16 short-form video ad for {brand_brief.business_name}.",
        f"Promote {brand_brief.offer} to {brand_brief.audience}.",
        f"Variant {variant_plan.slot}: {INTENT_DIRECTIONS.get(variant_plan.intent, variant_plan.intent)}.",
        f"Treatment: {TREATMENT_DIRECTIONS.get(variant_plan.treatment, variant_plan.treatment)}.",
        f"Open with the spoken hook: '{scripts.hook_line}'.",
        f"Keep the concept centered on {scripts.core_concept}.",
        f"Visual sequence: {visual_sequence}.",
        "Enable native audio with clear English narration that stays tightly synced to the edit.",
        f"Narration should say exactly: {spoken_narration}.",
        f"On-screen text should use lines like: {caption_lines}.",
        f"Land proof around {proof_label} and the outcome {brand_brief.primary_outcome}.",
        f"End with CTA text: '{scripts.cta.end_line}'.",
        duration_hint,
        (
            "Use real people, believable environments, natural motion, social-ad pacing, and conversion-focused framing. "
            "Avoid factories, industrial machines, engineering diagrams, gears, robotics, or abstract mechanical visuals "
            "unless the offer genuinely requires them."
        ),
    ]
    return _clip(" ".join(part for part in parts if part), 4000)


def run(
    brand_brief: BrandBrief,
    engine2_output: Engine2VariationControllerOutput,
    engine4_output: Engine4ScriptConverterOutput,
    engine5_output: Engine5VisualDirectorOutput,
) -> Engine6KlingAssemblerOutput:
    kling_prompts_list: list[VariantKlingPrompts] = []

    for index, sp in enumerate(engine5_output.shot_plans):
        scripts = engine4_output.scripts[index]
        variant_plan = engine2_output.variant_plans[index]
        narration_30s = _build_spoken_narration(scripts.script_30s)
        narration_15s = _build_spoken_narration(scripts.script_15s)
        full_prompt_30s = _build_kling_prompt(
            brand_brief,
            variant_plan,
            scripts,
            sp,
            shot_count=len(sp.shots),
            duration_hint="Build enough visual coverage for a full 30-second social ad with distinct beats.",
            spoken_narration=narration_30s,
        )
        full_prompt_15s = _build_kling_prompt(
            brand_brief,
            variant_plan,
            scripts,
            sp,
            shot_count=5,
            duration_hint="Keep the pacing punchy so it can compress into a high-conviction 10 to 15 second cut.",
            spoken_narration=narration_15s,
        )

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
