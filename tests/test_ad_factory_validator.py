from __future__ import annotations

import unittest

from app.modules.ad_factory.claim_guard import run_claim_guard
from app.modules.ad_factory.engines.engine0_pack_context import run as run_engine0
from app.modules.ad_factory.engines.engine1_context_builder import run as run_engine1
from app.modules.ad_factory.engines.engine2_variation_controller import run as run_engine2
from app.modules.ad_factory.engines.engine3_pattern_assembler import run as run_engine3
from app.modules.ad_factory.engines.engine4_script_converter import run as run_engine4
from app.modules.ad_factory.engines.engine5_visual_director import run as run_engine5
from app.modules.ad_factory.engines.engine6_kling_assembler import run as run_engine6
from app.modules.ad_factory.schemas import (
    BrandBrief,
    CTADestination,
    PackSnapshot,
    ProofAsset,
    VariantsBySlot,
)
from app.modules.ad_factory.validation import validate_variants


def _brand_brief() -> BrandBrief:
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


def _pack_snapshot() -> PackSnapshot:
    return PackSnapshot(
        pack_id="pack-123",
        pack_name="Glow Clinic",
        sprint_id="sprint-123",
        day=4,
        stage="setup",
        traffic_source="unknown",
    )


def _build_variants() -> VariantsBySlot:
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

    variants: dict[str, object] = {}
    for index, variant_plan in enumerate(engine2.variant_plans):
        scripts = engine4.scripts[index]
        shot_plan = engine5.shot_plans[index]
        render_intents = engine6.render_intents[index]
        variants[variant_plan.slot] = {
            "slot": variant_plan.slot,
            "intent": variant_plan.intent,
            "path": variant_plan.path,
            "treatment": variant_plan.treatment,
            "hook_type": variant_plan.hook_type,
            "core_concept": scripts.core_concept,
            "hook_line": scripts.hook_line,
            "hook_lineage": scripts.hook_lineage,
            "script_15s": scripts.script_15s,
            "script_30s": scripts.script_30s,
            "anchor_shot_plan": shot_plan.anchor_shot_plan,
            "on_screen_text": shot_plan.on_screen_text,
            "nanobanana_prompts": shot_plan.nanobanana_prompts,
            "render_intent_15s": render_intents.render_intent_15s,
            "render_intent_30s": render_intents.render_intent_30s,
            "cta": scripts.cta,
        }
    return VariantsBySlot.model_validate(
        {
            "A": variants["A"],
            "B": variants["B"],
            "C": variants["C"],
        }
    )


class AdFactoryValidatorTests(unittest.TestCase):
    def test_validator_passes_for_compiled_variants(self) -> None:
        brand_brief = _brand_brief()
        variants = _build_variants()
        claim_guard = run_claim_guard(variants)

        result = validate_variants(brand_brief, variants, claim_guard)

        self.assertEqual(result.status, "pass")
        self.assertFalse(result.blocking_errors)

    def test_claim_guard_blocks_guaranteed_claims(self) -> None:
        brand_brief = _brand_brief()
        variants = _build_variants()
        variants.A.hook_line = "Guaranteed results in one visit."
        claim_guard = run_claim_guard(variants)

        result = validate_variants(brand_brief, variants, claim_guard)

        self.assertEqual(claim_guard.status, "fail")
        self.assertEqual(result.status, "fail")
        self.assertTrue(any(check.check_id == "claim_guard_unsupported_guarantee" for check in result.blocking_errors))


if __name__ == "__main__":
    unittest.main()
