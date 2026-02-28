"""Engine 4 — Script Converter."""

from app.modules.ad_factory.registry.data import get_hook_template, LINE_TEMPLATES
from app.modules.ad_factory.schemas import (
    CTAResolved,
    Engine2VariationControllerOutput,
    Engine3PatternAssemblerOutput,
    Engine4ScriptConverterOutput,
    Script,
    ScriptBeat,
    VariantScripts,
)


def _fill_template(tpl: str, ctx: dict) -> str:
    for k, v in ctx.items():
        tpl = tpl.replace(f"[{k}]", str(v))
    return tpl


def run(
    brand_brief,
    engine2_output: Engine2VariationControllerOutput,
    engine3_output: Engine3PatternAssemblerOutput,
) -> Engine4ScriptConverterOutput:
    ctx = {
        "pain": brand_brief.primary_outcome or "results",
        "outcome": brand_brief.primary_outcome or "results",
        "mechanism": brand_brief.offer or "our process",
        "audience": brand_brief.audience,
    }

    scripts_list: list[VariantScripts] = []
    for vp in engine2_output.variant_plans:
        sel = next(s for s in engine3_output.selections if s.slot == vp.slot)
        hook_line = _fill_template(get_hook_template(vp.hook_type, vp.slot), ctx)[:60]
        core_concept = (brand_brief.core_concept or brand_brief.offer or "Get results")[:60]

        problem_tpl = LINE_TEMPLATES.get(sel.line_template_ids["problem"][0], "You're stuck.")
        mechanism_tpl = LINE_TEMPLATES.get("mechanism_1", "We do [mechanism] so you get [outcome].")
        offer_tpl = LINE_TEMPLATES.get("offer_1", "Get started today.")

        problem_text = _fill_template(problem_tpl, ctx)[:320]
        mechanism_text = _fill_template(mechanism_tpl, ctx)[:320]
        offer_text = _fill_template(offer_tpl, ctx)[:320]
        proof_text = f"See the results. {brand_brief.primary_outcome}."[:320]
        cta_mid = f"{brand_brief.cta_action.title()} now."[:140]
        cta_end = f"{brand_brief.cta_action.title()} in the link below."[:140]

        if vp.treatment == "offer_smash":
            beats_30s = [
                ScriptBeat(beat_name="hook", text=hook_line),
                ScriptBeat(beat_name="offer", text=offer_text),
                ScriptBeat(beat_name="problem", text=problem_text),
                ScriptBeat(beat_name="mechanism", text=mechanism_text),
                ScriptBeat(beat_name="proof", text=proof_text),
                ScriptBeat(beat_name="cta", text=cta_end),
            ]
        else:
            beats_30s = [
                ScriptBeat(beat_name="hook", text=hook_line),
                ScriptBeat(beat_name="problem", text=problem_text),
                ScriptBeat(beat_name="mechanism", text=mechanism_text),
                ScriptBeat(beat_name="proof", text=proof_text),
                ScriptBeat(beat_name="offer", text=offer_text),
                ScriptBeat(beat_name="cta", text=cta_mid),
            ]

        script_30s = Script(beats=beats_30s, timing_rules_satisfied=True)
        beats_15s = [
            beats_30s[0], beats_30s[1], beats_30s[2],
            beats_30s[3] if len(beats_30s) > 3 else ScriptBeat(beat_name="proof", text=proof_text),
            beats_30s[4] if len(beats_30s) > 4 else ScriptBeat(beat_name="offer", text=offer_text),
            ScriptBeat(beat_name="cta", text=cta_end),
        ]
        script_15s = Script(beats=beats_15s, timing_rules_satisfied=True)

        cta_resolved = CTAResolved(
            cta_action=brand_brief.cta_action,
            destination_type=brand_brief.cta_destination.destination_type,
            destination_value=brand_brief.cta_destination.value,
            mid_line=cta_mid,
            end_line=cta_end,
        )

        scripts_list.append(
            VariantScripts(
                slot=vp.slot,
                core_concept=core_concept,
                hook_line=hook_line,
                script_15s=script_15s,
                script_30s=script_30s,
                cta=cta_resolved,
            )
        )

    return Engine4ScriptConverterOutput(scripts=scripts_list)
