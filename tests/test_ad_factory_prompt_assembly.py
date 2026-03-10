from __future__ import annotations

import unittest

from app.modules.ad_factory.engines.engine5_visual_director import run as run_engine5
from app.modules.ad_factory.engines.engine6_kling_assembler import run as run_engine6
from app.modules.ad_factory.schemas import (
    BrandBrief,
    CTADestination,
    Engine2VariationControllerOutput,
    Engine4ScriptConverterOutput,
    ProofAsset,
    Script,
    ScriptBeat,
    VariantPlan,
    VariantScripts,
)


def _build_brand_brief() -> BrandBrief:
    return BrandBrief(
        business_name="Glow Clinic",
        offer="professional teeth whitening",
        audience="busy professionals",
        location="London",
        primary_outcome="a brighter smile",
        proof_assets=[ProofAsset(asset_type="testimonial", label="5-star reviews")],
        tone="direct",
        face_on_camera=True,
        price_position="mid",
        cta_action="book",
        cta_destination=CTADestination(
            destination_type="landing_page",
            value="https://example.com/book",
        ),
        usp="Dentist-led whitening with natural-looking results",
        core_concept="Smile reset",
    )


def _build_engine2_output() -> Engine2VariationControllerOutput:
    return Engine2VariationControllerOutput(
        variant_plans=[
            VariantPlan(
                slot="A",
                intent="emotion_led",
                path="transformation",
                treatment="talking_head_authority",
                hook_type="question",
            ),
            VariantPlan(
                slot="B",
                intent="logic_led",
                path="trust_safety",
                treatment="cinematic_process",
                hook_type="contrarian_truth",
            ),
            VariantPlan(
                slot="C",
                intent="offer_led",
                path="convenience",
                treatment="offer_smash",
                hook_type="stop_doing_this",
            ),
        ]
    )


def _build_script(slot: str, hook_line: str, concept: str, cta_line: str) -> VariantScripts:
    beats = [
        ScriptBeat(beat_name="hook", text=hook_line),
        ScriptBeat(
            beat_name="problem",
            text="Coffee, wine, and camera flash make your smile look dull.",
        ),
        ScriptBeat(
            beat_name="mechanism",
            text="A dentist-led whitening session lifts stains safely in one visit.",
        ),
        ScriptBeat(
            beat_name="proof",
            text="Backed by 5-star reviews and visible before-and-after results.",
        ),
        ScriptBeat(
            beat_name="offer",
            text="Book a whitening appointment this week and leave with a brighter smile.",
        ),
        ScriptBeat(beat_name="cta", text=cta_line),
    ]
    script = Script(beats=beats, timing_rules_satisfied=True)
    return VariantScripts(
        slot=slot,
        core_concept=concept,
        hook_line=hook_line,
        script_15s=script,
        script_30s=script,
        cta={
            "cta_action": "book",
            "destination_type": "landing_page",
            "destination_value": "https://example.com/book",
            "mid_line": "Book now.",
            "end_line": cta_line,
        },
    )


def _build_engine4_output() -> Engine4ScriptConverterOutput:
    return Engine4ScriptConverterOutput(
        scripts=[
            _build_script(
                "A",
                "Still hiding your smile in photos?",
                "Smile reset",
                "Book your whitening session below.",
            ),
            _build_script(
                "B",
                "Most whitening ads skip the dentist part.",
                "Dentist-led precision",
                "Tap below to book your appointment.",
            ),
            _build_script(
                "C",
                "Stop paying for whitening that barely shows.",
                "Visible result in one visit",
                "Claim your slot from the link below.",
            ),
        ]
    )


class AdFactoryPromptAssemblyTests(unittest.TestCase):
    def test_engine5_builds_variant_specific_visual_descriptions(self) -> None:
        brand_brief = _build_brand_brief()
        engine5 = run_engine5(brand_brief, _build_engine2_output(), _build_engine4_output())

        first_variant_shots = engine5.shot_plans[0].shots

        self.assertIn("Still hiding your smile in photos?", first_variant_shots[0].description)
        self.assertIn("professional teeth whitening", first_variant_shots[2].description)
        self.assertIn("Glow Clinic", first_variant_shots[7].description)
        self.assertIn("Avoid factories", first_variant_shots[0].nanobanana_prompt)
        self.assertNotIn("Pattern Interrupt", first_variant_shots[0].description)

    def test_engine6_kling_prompt_uses_brand_and_variant_content(self) -> None:
        brand_brief = _build_brand_brief()
        engine2 = _build_engine2_output()
        engine4 = _build_engine4_output()
        engine5 = run_engine5(brand_brief, engine2, engine4)

        engine6 = run_engine6(brand_brief, engine2, engine4, engine5)
        prompt = engine6.kling_prompts[0].kling_15s.prompt

        self.assertIn("Glow Clinic", prompt)
        self.assertIn("professional teeth whitening", prompt)
        self.assertIn("Still hiding your smile in photos?", prompt)
        self.assertIn("emotion-led", prompt)
        self.assertIn("Enable native audio", prompt)
        self.assertIn("Narration should say exactly", prompt)
        self.assertIn("Avoid factories", prompt)
        self.assertNotIn("Pattern Interrupt", prompt)
        self.assertNotIn("Mechanism 1", prompt)


if __name__ == "__main__":
    unittest.main()
