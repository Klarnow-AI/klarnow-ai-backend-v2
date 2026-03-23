"""Engine 4 — Script Converter."""

from __future__ import annotations

from app.modules.ad_factory.registry.data import (
    CTA_TEMPLATES,
    ENGINE_LOGIC_VERSION,
    HOOKS,
    LINE_TEMPLATES,
    REGISTRY_VERSION,
    get_beat_blueprint,
)
from app.modules.ad_factory.schemas import (
    BrandBrief,
    CTAResolved,
    Engine2VariationControllerOutput,
    Engine3PatternAssemblerOutput,
    Engine4ScriptConverterOutput,
    Lineage,
    Script,
    TimedScriptBeat,
    VariantScripts,
)


_TIMINGS_30_STANDARD = {
    "hook": (0.0, 2.5),
    "problem": (2.5, 6.5),
    "mechanism": (6.5, 9.5),
    "proof": (9.5, 14.0),
    "offer": (14.0, 22.0),
    "cta": (22.0, 30.0),
}
_TIMINGS_30_OFFER = {
    "hook": (0.0, 2.5),
    "offer": (2.5, 5.5),
    "problem": (5.5, 8.0),
    "mechanism": (8.0, 10.0),
    "proof": (10.0, 16.0),
    "cta": (16.0, 30.0),
}
_TIMINGS_15_STANDARD = {
    "hook": (0.0, 2.0),
    "problem": (2.0, 4.5),
    "mechanism": (4.5, 7.0),
    "proof": (7.0, 9.5),
    "offer": (9.5, 12.0),
    "cta": (12.0, 15.0),
}


def _title(value: str) -> str:
    if not value:
        return ""
    return value[0].upper() + value[1:]


def _clip(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


def _fill_template(template: str, context: dict[str, str]) -> str:
    text = template
    for key, value in context.items():
        text = text.replace(f"[{key}]", str(value))
        text = text.replace(f"[{_title(key)}]", _title(str(value)))
    return text


def _lineage(
    *,
    source_registry_item_id: str,
    source_registry_item_type: str,
    template_id: str,
    fill_variables: dict[str, str],
    generator_stage: str,
) -> Lineage:
    return Lineage(
        source_registry_item_id=source_registry_item_id,
        source_registry_item_type=source_registry_item_type,
        template_id=template_id,
        fill_variables=fill_variables,
        registry_version=REGISTRY_VERSION,
        engine_logic_version=ENGINE_LOGIC_VERSION,
        generator_stage=generator_stage,
    )


def _make_beat(
    beat_name: str,
    text: str,
    timing_map: dict[str, tuple[float, float]],
    template_id: str,
    fill_variables: dict[str, str],
    source_registry_item_type: str = "line_template",
) -> TimedScriptBeat:
    start_second, end_second = timing_map[beat_name]
    return TimedScriptBeat(
        beat_name=beat_name,  # type: ignore[arg-type]
        text=_clip(text, 320),
        start_second=start_second,
        end_second=end_second,
        lineage=_lineage(
            source_registry_item_id=template_id,
            source_registry_item_type=source_registry_item_type,
            template_id=template_id,
            fill_variables=fill_variables,
            generator_stage="engine4_script_converter",
        ),
    )


def run(
    brand_brief: BrandBrief,
    engine2_output: Engine2VariationControllerOutput,
    engine3_output: Engine3PatternAssemblerOutput,
) -> Engine4ScriptConverterOutput:
    fill_variables = {
        "pain": brand_brief.primary_outcome.lower(),
        "outcome": brand_brief.primary_outcome,
        "mechanism": brand_brief.offer,
        "audience": brand_brief.audience,
        "offer": brand_brief.offer,
    }

    scripts_list: list[VariantScripts] = []
    for variant_plan in engine2_output.variant_plans:
        selection = next(
            selection
            for selection in engine3_output.selections
            if selection.slot == variant_plan.slot
        )
        hook_item = HOOKS[selection.hook_id]
        problem_item = LINE_TEMPLATES[selection.line_template_ids["problem"][0]]
        mechanism_item = LINE_TEMPLATES[selection.line_template_ids["mechanism"][0]]
        offer_item = LINE_TEMPLATES[selection.line_template_ids["offer"][0]]
        cta_item = CTA_TEMPLATES[selection.cta_id]
        blueprint = get_beat_blueprint(variant_plan.treatment)

        hook_line = _clip(_fill_template(str(hook_item["template"]), fill_variables), 60)
        core_concept = _clip(brand_brief.core_concept or brand_brief.offer or "Get results", 60)
        problem_text = _clip(_fill_template(str(problem_item["template"]), fill_variables), 320)
        mechanism_text = _clip(
            f"We do {brand_brief.offer} so you get {brand_brief.primary_outcome}.",
            320,
        )
        proof_reference = (
            brand_brief.proof_assets[0].label
            if brand_brief.proof_assets
            else "specific customer proof"
        )
        proof_text = _clip(
            f"Proof comes through {proof_reference}, making {brand_brief.primary_outcome.lower()} feel believable.",
            320,
        )
        offer_text = _clip(_fill_template(str(offer_item["template"]), fill_variables), 320)
        cta_mid = _clip(str(cta_item["mid"]), 140)
        cta_end = _clip(str(cta_item["end"]), 140)

        timing_30 = (
            _TIMINGS_30_OFFER
            if variant_plan.treatment == "offer_smash"
            else _TIMINGS_30_STANDARD
        )
        beats_by_name = {
            "hook": _make_beat("hook", hook_line, timing_30, str(hook_item["id"]), fill_variables),
            "problem": _make_beat(
                "problem",
                problem_text,
                timing_30,
                str(problem_item["id"]),
                fill_variables,
            ),
            "mechanism": _make_beat(
                "mechanism",
                mechanism_text,
                timing_30,
                str(mechanism_item["id"]),
                fill_variables,
            ),
            "proof": _make_beat(
                "proof",
                proof_text,
                timing_30,
                selection.proof_strategy_id,
                {
                    **fill_variables,
                    "proof_reference": proof_reference,
                },
                source_registry_item_type="proof_strategy",
            ),
            "offer": _make_beat("offer", offer_text, timing_30, str(offer_item["id"]), fill_variables),
            "cta": _make_beat(
                "cta",
                cta_end,
                timing_30,
                str(cta_item["id"]),
                {
                    **fill_variables,
                    "cta_mid": cta_mid,
                    "cta_end": cta_end,
                },
            ),
        }
        script_30s = Script(
            beats=[beats_by_name[name] for name in blueprint["beats"]],
            timing_rules_satisfied=True,
        )
        script_15s = Script(
            beats=[
                TimedScriptBeat(
                    beat_name=beat.beat_name,
                    text=beat.text,
                    start_second=_TIMINGS_15_STANDARD[beat.beat_name][0],
                    end_second=_TIMINGS_15_STANDARD[beat.beat_name][1],
                    lineage=beat.lineage,
                )
                for beat in [
                    beats_by_name["hook"],
                    beats_by_name["problem"],
                    beats_by_name["mechanism"],
                    beats_by_name["proof"],
                    beats_by_name["offer"],
                    beats_by_name["cta"],
                ]
            ],
            timing_rules_satisfied=True,
        )

        scripts_list.append(
            VariantScripts(
                slot=variant_plan.slot,
                core_concept=core_concept,
                hook_line=hook_line,
                hook_lineage=_lineage(
                    source_registry_item_id=str(hook_item["id"]),
                    source_registry_item_type="hook",
                    template_id=str(hook_item["id"]),
                    fill_variables=fill_variables,
                    generator_stage="engine4_script_converter",
                ),
                script_15s=script_15s,
                script_30s=script_30s,
                cta=CTAResolved(
                    cta_action=brand_brief.cta_action,
                    destination_type=brand_brief.cta_destination.destination_type,
                    destination_value=brand_brief.cta_destination.value,
                    mid_line=cta_mid,
                    end_line=cta_end,
                    mid_lineage=_lineage(
                        source_registry_item_id=str(cta_item["id"]),
                        source_registry_item_type="cta",
                        template_id=str(cta_item["id"]),
                        fill_variables=fill_variables,
                        generator_stage="engine4_script_converter",
                    ),
                    end_lineage=_lineage(
                        source_registry_item_id=str(cta_item["id"]),
                        source_registry_item_type="cta",
                        template_id=str(cta_item["id"]),
                        fill_variables=fill_variables,
                        generator_stage="engine4_script_converter",
                    ),
                ),
            )
        )

    return Engine4ScriptConverterOutput(scripts=scripts_list)
