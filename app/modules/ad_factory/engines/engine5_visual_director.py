"""Engine 5 — Visual Director."""

from __future__ import annotations

from app.modules.ad_factory.registry.data import ENGINE_LOGIC_VERSION, REGISTRY_VERSION
from app.modules.ad_factory.schemas import (
    AnchorShot,
    BrandBrief,
    Engine3PatternAssemblerOutput,
    Engine4ScriptConverterOutput,
    Engine5VisualDirectorOutput,
    Lineage,
    LineageTextItem,
    VariantShotPlan,
)

SHOT_TYPES = [
    "pattern_interrupt",
    "establishing",
    "mechanism_1",
    "mechanism_2",
    "proof_overlay",
    "human_moment",
    "result_reveal",
    "cta_frame",
]


def _clip(text: str | None, limit: int, fallback: str) -> str:
    normalized = " ".join((text or "").split())
    return (normalized or fallback)[:limit]


def _lineage(source_registry_item_id: str, fill_variables: dict[str, str]) -> Lineage:
    return Lineage(
        source_registry_item_id=source_registry_item_id,
        source_registry_item_type="pattern",
        template_id=source_registry_item_id,
        fill_variables=fill_variables,
        registry_version=REGISTRY_VERSION,
        engine_logic_version=ENGINE_LOGIC_VERSION,
        generator_stage="engine5_visual_director",
    )


def _on_screen_copy(*parts: str) -> str:
    words = " ".join(" ".join(part.split()) for part in parts if part).split()
    return " ".join(words[:7])[:60] or "Watch this now"


def run(
    brand_brief: BrandBrief,
    engine3_output: Engine3PatternAssemblerOutput,
    engine4_output: Engine4ScriptConverterOutput,
) -> Engine5VisualDirectorOutput:
    shot_plans: list[VariantShotPlan] = []
    proof_label = (
        brand_brief.proof_assets[0].label
        if brand_brief.proof_assets
        else "specific customer proof"
    )

    for index, scripts in enumerate(engine4_output.scripts):
        selection = engine3_output.selections[index]
        beat_lookup = {beat.beat_name: beat.text for beat in scripts.script_30s.beats}
        fill_variables = {
            "business_name": brand_brief.business_name,
            "offer": brand_brief.offer,
            "audience": brand_brief.audience,
            "primary_outcome": brand_brief.primary_outcome,
            "proof_label": proof_label,
        }
        shot_descriptions = {
            "pattern_interrupt": (
                (
                    f"Open on a believable human moment delivering '{scripts.hook_line}' directly to camera "
                    f"for {brand_brief.audience}."
                    if brand_brief.face_on_camera
                    else f"Open on a believable environment cue that sets up '{scripts.hook_line}' for {brand_brief.audience}."
                )
            ),
            "establishing": (
                f"Show {brand_brief.audience} dealing with {beat_lookup.get('problem', brand_brief.offer)} "
                f"in a real environment."
            ),
            "mechanism_1": (
                f"Show how {brand_brief.offer} begins so the system feels concrete and premium."
            ),
            "mechanism_2": (
                f"Continue the transformation step that turns {brand_brief.offer} into "
                f"{brand_brief.primary_outcome}."
            ),
            "proof_overlay": (
                f"Layer in proof using {proof_label} while reinforcing {beat_lookup.get('proof', brand_brief.primary_outcome)}."
            ),
            "human_moment": (
                "Capture relief, confidence, and visible momentum in a grounded human reaction."
            ),
            "result_reveal": (
                f"Reveal the outcome clearly for {brand_brief.audience}: {brand_brief.primary_outcome}."
            ),
            "cta_frame": (
                f"Close with {brand_brief.business_name} delivering the end CTA '{scripts.cta.end_line}'."
            ),
        }
        anchor_shots: list[AnchorShot] = []
        on_screen_text_items: list[LineageTextItem] = []
        nanobanana_items: list[LineageTextItem] = []

        for shot_index, shot_type in enumerate(SHOT_TYPES, start=1):
            lineage = _lineage(selection.pattern_id, fill_variables)
            on_screen_text = _on_screen_copy(
                scripts.hook_line if shot_type == "pattern_interrupt" else "",
                brand_brief.primary_outcome if shot_type == "result_reveal" else "",
                scripts.cta.end_line if shot_type == "cta_frame" else "",
                proof_label if shot_type == "proof_overlay" else "",
                scripts.core_concept if shot_type in {"mechanism_1", "mechanism_2"} else "",
            )
            description = _clip(
                shot_descriptions[shot_type],
                200,
                f"Show {brand_brief.offer} in a believable scene.",
            )
            nanobanana_prompt = _clip(
                (
                    f"Vertical 9:16 social ad for {brand_brief.business_name}. {description} "
                    f"Use real people relevant to {brand_brief.audience}, natural light, premium ad direction, "
                    "captions enabled, continuity between anchor shots, and mobile-first framing. "
                    "Avoid factories, industrial machinery, engineering diagrams, and abstract mechanical visuals."
                ),
                800,
                "Vertical 9:16 social ad with real people and captions.",
            )
            anchor_shots.append(
                AnchorShot(
                    index=shot_index,
                    shot_type=shot_type,  # type: ignore[arg-type]
                    description=description,
                    on_screen_text=on_screen_text,
                    nanobanana_prompt=nanobanana_prompt,
                    lineage=lineage,
                    caption_overlay={"enabled": True},
                )
            )
            on_screen_text_items.append(LineageTextItem(text=on_screen_text, lineage=lineage))
            nanobanana_items.append(LineageTextItem(text=nanobanana_prompt, lineage=lineage))

        shot_plans.append(
            VariantShotPlan(
                slot=scripts.slot,
                anchor_shot_plan=anchor_shots,
                pacing={
                    "mode": "stretch_compress_anchors",
                    "anchor_count": 8,
                    "duration_profiles": {
                        "15": {"avg_shot_seconds_min": 1.2, "avg_shot_seconds_max": 2.0},
                        "30": {"avg_shot_seconds_min": 2.6, "avg_shot_seconds_max": 4.2},
                    },
                },
                on_screen_text=on_screen_text_items,
                nanobanana_prompts=nanobanana_items,
            )
        )

    return Engine5VisualDirectorOutput(shot_plans=shot_plans)
