"""Engine 6 — Render Assembler producing provider-neutral intents."""

from app.modules.ad_factory.schemas import (
    BrandBrief,
    Engine2VariationControllerOutput,
    Engine4ScriptConverterOutput,
    Engine5VisualDirectorOutput,
    Engine6RenderAssemblerOutput,
    ProviderNeutralRenderIntent,
    RenderAnchorFrame,
    VariantRenderIntents,
)


def _clip(text: str | None, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


def _spoken_narration(script, max_chars: int) -> str:
    lines = [_clip(beat.text, 140) for beat in script.beats if _clip(beat.text, 140)]
    return _clip(" ".join(lines), max_chars)


def _render_intent(
    *,
    brand_brief: BrandBrief,
    treatment: str,
    scripts,
    shot_plan,
    duration_seconds: int,
    shot_count: int,
) -> ProviderNeutralRenderIntent:
    selected_shots = shot_plan.anchor_shot_plan[:shot_count]
    proof_line = (
        brand_brief.proof_assets[0].label
        if brand_brief.proof_assets
        else "specific customer proof"
    )
    return ProviderNeutralRenderIntent(
        duration_seconds=duration_seconds,  # type: ignore[arg-type]
        aspect_ratio="9:16",
        treatment=treatment,
        pacing_mode="stretch_compress_anchors",
        captions_on=True,
        fast_cuts=True,
        cta_mid_and_end=True,
        anchor_frames=[
            RenderAnchorFrame(
                index=shot.index,
                shot_type=shot.shot_type,
                description=shot.description,
                on_screen_text=shot.on_screen_text,
            )
            for shot in selected_shots
        ],
        continuity_requirements={
            "anchor_frames_present": True,
            "continuity_required": True,
        },
        voiceover_mode="native_audio",
        provider_target="kling",
        spoken_narration=_spoken_narration(
            scripts.script_15s if duration_seconds == 15 else scripts.script_30s,
            420 if duration_seconds == 15 else 900,
        ),
        caption_lines=[shot.on_screen_text for shot in selected_shots],
        hook_line=scripts.hook_line,
        core_concept=scripts.core_concept,
        cta_line=scripts.cta.end_line,
        business_name=brand_brief.business_name,
        offer=brand_brief.offer,
        audience=brand_brief.audience,
        primary_outcome=brand_brief.primary_outcome,
        proof_line=proof_line,
    )


def run(
    brand_brief: BrandBrief,
    engine2_output: Engine2VariationControllerOutput,
    engine4_output: Engine4ScriptConverterOutput,
    engine5_output: Engine5VisualDirectorOutput,
) -> Engine6RenderAssemblerOutput:
    render_intents: list[VariantRenderIntents] = []

    for index, shot_plan in enumerate(engine5_output.shot_plans):
        scripts = engine4_output.scripts[index]
        variant_plan = engine2_output.variant_plans[index]
        render_intents.append(
            VariantRenderIntents(
                slot=shot_plan.slot,
                render_intent_15s=_render_intent(
                    brand_brief=brand_brief,
                    treatment=variant_plan.treatment,
                    scripts=scripts,
                    shot_plan=shot_plan,
                    duration_seconds=15,
                    shot_count=5,
                ),
                render_intent_30s=_render_intent(
                    brand_brief=brand_brief,
                    treatment=variant_plan.treatment,
                    scripts=scripts,
                    shot_plan=shot_plan,
                    duration_seconds=30,
                    shot_count=len(shot_plan.anchor_shot_plan),
                ),
                render_requirements={
                    "aspect_ratio": "9:16",
                    "captions_on": True,
                    "fast_cuts": True,
                    "cta_mid_and_end": True,
                    "anchor_frames_present": True,
                    "continuity_required": True,
                },
            )
        )

    return Engine6RenderAssemblerOutput(render_intents=render_intents)
