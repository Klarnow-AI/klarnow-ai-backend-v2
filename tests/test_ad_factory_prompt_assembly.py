from __future__ import annotations

import unittest

from app.modules.ad_factory.engines.engine0_pack_context import run as run_engine0
from app.modules.ad_factory.engines.engine1_context_builder import run as run_engine1
from app.modules.ad_factory.engines.engine2_variation_controller import run as run_engine2
from app.modules.ad_factory.engines.engine3_pattern_assembler import run as run_engine3
from app.modules.ad_factory.engines.engine4_script_converter import run as run_engine4
from app.modules.ad_factory.engines.engine5_visual_director import run as run_engine5
from app.modules.ad_factory.engines.engine6_kling_assembler import run as run_engine6
from app.modules.ad_factory.kling_adapter import build_kling_prompt, build_kling_request
from app.modules.ad_factory.schemas import (
    BrandBrief,
    BrandContextAudiencePersona,
    BrandContextColorPalette,
    BrandContextSnapshot,
    CTADestination,
    PackSnapshot,
    ProofAsset,
)


def _brand_brief() -> BrandBrief:
    return BrandBrief(
        business_name="Glow Clinic",
        offer="professional teeth whitening",
        audience="busy professionals",
        location="London",
        primary_pain="yellowing that shows up in every meeting",
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
        hero_angle="specialist_precision",
        brand_context=BrandContextSnapshot(
            mission="Help professionals feel camera-ready without overdone cosmetic work.",
            promise="Natural-looking whitening delivered with specialist care.",
            elevator_pitch="Glow Clinic gives busy professionals a fast, confidence-building smile reset.",
            proof_points=["1,200+ whitening treatments completed", "5-star local reviews"],
            audience_personas=[
                BrandContextAudiencePersona(
                    persona="Image-conscious professionals",
                    needs=["look polished for meetings and events"],
                    pain_points=["yellowing that shows up in every meeting"],
                )
            ],
            voice_archetype="calm authority",
            voice_traits=["warm", "expert", "reassuring"],
            design_cues=[
                "clean editorial lighting",
                "natural close-ups",
                "premium clinic realism",
            ],
            style_palette=["soft neutrals", "polished whites", "subtle navy"],
            typography_direction="Modern sans with elegant serif support",
            color_palette=BrandContextColorPalette(
                primary="#0B1020",
                secondary="#F6F1E8",
                accent="#C7A46A",
            ),
        ),
    )


def _pack_snapshot() -> PackSnapshot:
    return PackSnapshot(
        pack_id="pack-123",
        pack_name="Glow Clinic",
        sprint_id="sprint-123",
        day=4,
        stage="setup",
        traffic_source="unknown",
    )


class AdFactoryPromptAssemblyTests(unittest.TestCase):
    def test_visual_director_builds_eight_anchor_shots_with_lineage(self) -> None:
        brand_brief = _brand_brief()
        engine0 = run_engine0(_pack_snapshot(), brand_brief)
        engine1 = run_engine1(brand_brief, engine0, "seed-1234567890abcdef")
        engine2 = run_engine2(brand_brief, engine1, "seed-1234567890abcdef")
        engine3 = run_engine3(
            brand_brief,
            engine0,
            engine2,
            engine1.proof_strategy_candidate.strategy_id,
            "seed-1234567890abcdef",
        )
        engine4 = run_engine4(brand_brief, engine2, engine3)
        engine5 = run_engine5(brand_brief, engine3, engine4)

        first_variant_shots = engine5.shot_plans[0].anchor_shot_plan

        self.assertEqual(len(first_variant_shots), 8)
        self.assertIn("Glow Clinic", first_variant_shots[7].description)
        self.assertTrue(all(shot.caption_overlay["enabled"] for shot in first_variant_shots))
        self.assertTrue(all(shot.lineage.source_registry_item_id.startswith("pattern_") for shot in first_variant_shots))
        self.assertIn("Avoid factories", first_variant_shots[0].nanobanana_prompt)
        self.assertIn("clean editorial lighting", first_variant_shots[0].nanobanana_prompt)
        self.assertIn("#0B1020", first_variant_shots[0].nanobanana_prompt)

    def test_render_intent_stays_provider_neutral_until_adapter(self) -> None:
        brand_brief = _brand_brief()
        engine0 = run_engine0(_pack_snapshot(), brand_brief)
        engine1 = run_engine1(brand_brief, engine0, "seed-1234567890abcdef")
        engine2 = run_engine2(brand_brief, engine1, "seed-1234567890abcdef")
        engine3 = run_engine3(
            brand_brief,
            engine0,
            engine2,
            engine1.proof_strategy_candidate.strategy_id,
            "seed-1234567890abcdef",
        )
        engine4 = run_engine4(brand_brief, engine2, engine3)
        engine5 = run_engine5(brand_brief, engine3, engine4)
        engine6 = run_engine6(brand_brief, engine2, engine4, engine5)

        intent = engine6.render_intents[0].render_intent_15s
        prompt = build_kling_prompt(intent)
        request = build_kling_request(intent)

        self.assertEqual(intent.provider_target, "kling")
        self.assertEqual(intent.aspect_ratio, "9:16")
        self.assertEqual(len(intent.anchor_frames), 5)
        self.assertIn("Glow Clinic", prompt)
        self.assertIn("professional teeth whitening", prompt)
        self.assertIn("Brand context:", prompt)
        self.assertIn("clean editorial lighting", prompt)
        self.assertIn("yellowing that shows up in every meeting", prompt)
        self.assertIn("Narration should say exactly", prompt)
        self.assertEqual(request["aspect_ratio"], "9:16")
        self.assertEqual(request["duration"], 10)


if __name__ == "__main__":
    unittest.main()
