"""Business-rule validator for Ad Factory compile results."""

from __future__ import annotations

from app.modules.ad_factory.schemas import (
    BrandBrief,
    ClaimGuardResult,
    ValidationCheck,
    ValidatorResult,
    VariantsBySlot,
)


def _check(
    *,
    check_id: str,
    passed: bool,
    field_path: str,
    slot: str | None = None,
    message: str | None = None,
    blocking: bool = True,
) -> ValidationCheck:
    return ValidationCheck(
        check_id=check_id,
        passed=passed,
        blocking=blocking,
        slot=slot,  # type: ignore[arg-type]
        field_path=field_path,
        message=None if passed else message,
    )


def validate_variants(
    brand_brief: BrandBrief,
    variants: VariantsBySlot,
    claim_guard_result: ClaimGuardResult,
) -> ValidatorResult:
    variants_by_slot = variants.as_dict()
    checks: list[ValidationCheck] = []
    slot_keys = list(variants_by_slot.keys())

    checks.append(
        _check(
            check_id="slots_exactly_A_B_C",
            passed=slot_keys == ["A", "B", "C"],
            field_path="compile_result.variants",
            message="Variants must be keyed exactly as A, B, and C.",
        )
    )

    expected_intents = {"A": "emotion_led", "B": "logic_led", "C": "offer_led"}
    checks.extend(
        _check(
            check_id="variant_intents_locked_to_slots",
            passed=variant.intent == expected_intents[slot],
            field_path=f"variants.{slot}.intent",
            slot=slot,
            message=f"Variant {slot} intent must be {expected_intents[slot]}.",
        )
        for slot, variant in variants_by_slot.items()
    )

    paths = [variant.path for variant in variants_by_slot.values()]
    checks.append(
        _check(
            check_id="paths_unique_across_variants",
            passed=len(paths) == len(set(paths)),
            field_path="compile_result.variants",
            message="Paths must differ across A, B, and C.",
        )
    )

    hooks = [variant.hook_type for variant in variants_by_slot.values()]
    checks.append(
        _check(
            check_id="hook_types_unique_across_variants",
            passed=len(hooks) == len(set(hooks)),
            field_path="compile_result.variants",
            message="Hook types must differ across A, B, and C.",
        )
    )

    checks.append(
        _check(
            check_id="variant_c_offer_smash",
            passed=(
                variants.C.treatment == "offer_smash"
                and variants.C.intent == "offer_led"
            ),
            field_path="variants.C.treatment",
            slot="C",
            message="Variant C must use offer_smash treatment.",
        )
    )

    talking_head_ok = True
    if not brand_brief.face_on_camera:
        talking_head_ok = all(
            variant.treatment != "talking_head_authority"
            for variant in variants_by_slot.values()
        )
    checks.append(
        _check(
            check_id="talking_head_disallowed_when_face_off",
            passed=talking_head_ok,
            field_path="compile_result.variants",
            message="Talking-head treatment is not allowed when face_on_camera is false.",
        )
    )

    for slot, variant in variants_by_slot.items():
        checks.append(
            _check(
                check_id="cta_matches_brandbrief_action",
                passed=variant.cta.cta_action == brand_brief.cta_action,
                field_path=f"variants.{slot}.cta.cta_action",
                slot=slot,
                message="CTA action must match the BrandBrief CTA action.",
            )
        )
        proof_beat = next(
            (beat for beat in variant.script_30s.beats if beat.beat_name == "proof"),
            None,
        )
        checks.append(
            _check(
                check_id="proof_by_second_10_in_30s",
                passed=proof_beat is not None and proof_beat.start_second <= 10,
                field_path=f"variants.{slot}.script_30s.beats",
                slot=slot,
                message="Proof beat must start by second 10 or earlier.",
            )
        )
        cta_beats = [beat for beat in variant.script_30s.beats if beat.beat_name == "cta"]
        checks.append(
            _check(
                check_id="one_cta_only",
                passed=len(cta_beats) == 1,
                field_path=f"variants.{slot}.script_30s.beats",
                slot=slot,
                message="Each 30s script must have exactly one CTA beat.",
            )
        )
        checks.append(
            _check(
                check_id="cta_repeated_mid_and_end",
                passed=bool(variant.cta.mid_line and variant.cta.end_line),
                field_path=f"variants.{slot}.cta",
                slot=slot,
                message="CTA copy must be present at both the mid and end positions.",
            )
        )
        mechanism_beat = next(
            (beat for beat in variant.script_30s.beats if beat.beat_name == "mechanism"),
            None,
        )
        mechanism_ok = bool(
            mechanism_beat
            and mechanism_beat.text.startswith("We do ")
            and " so you get " in mechanism_beat.text
        )
        checks.append(
            _check(
                check_id="mechanism_line_format_valid",
                passed=mechanism_ok,
                field_path=f"variants.{slot}.script_30s.beats",
                slot=slot,
                message="Mechanism beat must use the 'We do X so you get Y' format.",
            )
        )
        captions_ok = all(
            bool(shot.caption_overlay.get("enabled"))
            for shot in variant.anchor_shot_plan
        )
        checks.append(
            _check(
                check_id="captions_enabled_all_shots",
                passed=captions_ok,
                field_path=f"variants.{slot}.anchor_shot_plan",
                slot=slot,
                message="Captions must be enabled for all anchor shots.",
            )
        )

    for issue in claim_guard_result.blocking_errors:
        checks.append(
            _check(
                check_id=f"claim_guard_{issue.rule_id}",
                passed=False,
                field_path=issue.field_path,
                slot=issue.slot,
                message=issue.message or "Claim guard blocked the compile result.",
            )
        )

    blocking_errors = [check for check in checks if check.blocking and not check.passed]
    return ValidatorResult(
        status="fail" if blocking_errors else "pass",
        checks=checks,
        blocking_errors=blocking_errors,
    )
