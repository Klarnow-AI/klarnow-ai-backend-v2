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


def _join(values: list[str] | None, *, limit: int = 3) -> str:
    items = [" ".join(str(value).split()) for value in values or [] if str(value).strip()]
    return ", ".join(items[:limit])


def _spoken_narration(script, max_chars: int) -> str:
    lines = [_clip(beat.text, 140) for beat in script.beats if _clip(beat.text, 140)]
    return _clip(" ".join(lines), max_chars)


def _proof_line(brand_brief: BrandBrief) -> str:
    if brand_brief.brand_context and brand_brief.brand_context.usp_proof:
        return _clip(brand_brief.brand_context.usp_proof, 180)
    if brand_brief.brand_context and brand_brief.brand_context.proof_points:
        return _clip(brand_brief.brand_context.proof_points[0], 180)
    if brand_brief.proof_assets:
        return _clip(brand_brief.proof_assets[0].label, 180)
    return "specific customer proof"


def _brand_context_summary(brand_brief: BrandBrief) -> str | None:
    context = brand_brief.brand_context
    if context is None:
        return None

    parts: list[str] = []
    if context.mission:
        parts.append(f"Mission: {context.mission}")
    if context.promise:
        parts.append(f"Promise: {context.promise}")
    if context.elevator_pitch:
        parts.append(f"Elevator pitch: {context.elevator_pitch}")
    if context.voice_archetype or context.voice_traits:
        voice_bits = [
            value
            for value in [context.voice_archetype, _join(context.voice_traits, limit=4)]
            if value
        ]
        if voice_bits:
            parts.append(f"Voice: {'; '.join(voice_bits)}")
    if context.audience_personas:
        persona = context.audience_personas[0]
        persona_bits = [persona.persona]
        if persona.needs:
            persona_bits.append(f"needs {persona.needs[0]}")
        if persona.pain_points:
            persona_bits.append(f"pain {persona.pain_points[0]}")
        parts.append(f"Audience persona: {'; '.join(persona_bits)}")
    if context.proof_points:
        parts.append(f"Proof cues: {_join(context.proof_points, limit=2)}")

    summary = " ".join(parts)
    return _clip(summary, 600) or None


def _visual_direction(brand_brief: BrandBrief) -> str | None:
    context = brand_brief.brand_context
    if context is None:
        return None

    parts: list[str] = []
    if context.design_cues:
        parts.append(f"Design cues: {_join(context.design_cues)}")
    if context.style_palette:
        parts.append(f"Style palette: {_join(context.style_palette)}")
    if context.color_palette:
        colors = [
            f"{label} {value}"
            for label, value in (
                ("primary", context.color_palette.primary),
                ("secondary", context.color_palette.secondary),
                ("accent", context.color_palette.accent),
            )
            if value
        ]
        if colors:
            parts.append(f"Brand colors: {', '.join(colors)}")
    if context.typography_direction:
        parts.append(f"Typography: {context.typography_direction}")
    if brand_brief.hero_angle:
        parts.append(f"Hero angle: {brand_brief.hero_angle.replace('_', ' ')}")

    direction = ". ".join(parts)
    return _clip(direction, 600) or None


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
        primary_pain=brand_brief.primary_pain,
        primary_outcome=brand_brief.primary_outcome,
        proof_line=_proof_line(brand_brief),
        brand_context_summary=_brand_context_summary(brand_brief),
        visual_direction=_visual_direction(brand_brief),
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
