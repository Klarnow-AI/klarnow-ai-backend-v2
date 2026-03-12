"""Deterministic claim guard checks for Ad Factory."""

from __future__ import annotations

from app.modules.ad_factory.schemas import ClaimGuardCheck, ClaimGuardResult, VariantsBySlot

_BLOCKED_PATTERNS: tuple[tuple[str, str], ...] = (
    ("unsupported_guarantee", "guaranteed"),
    ("medical_claim", "cure"),
    ("medical_claim", "heal"),
    ("legal_claim", "legal guarantee"),
    ("financial_claim", "double your money"),
    ("risky_before_after", "before and after"),
    ("prohibited_urgency", "act now or miss out forever"),
)


def run_claim_guard(variants: VariantsBySlot) -> ClaimGuardResult:
    checks: list[ClaimGuardCheck] = []
    for slot, variant in variants.as_dict().items():
        beat_paths = [
            (f"variants.{slot}.hook_line", variant.hook_line),
            *[
                (f"variants.{slot}.script_30s.beats[{index}].text", beat.text)
                for index, beat in enumerate(variant.script_30s.beats)
            ],
            (f"variants.{slot}.cta.mid_line", variant.cta.mid_line),
            (f"variants.{slot}.cta.end_line", variant.cta.end_line),
        ]
        for rule_id, pattern in _BLOCKED_PATTERNS:
            passed = True
            field_path = f"variants.{slot}"
            message = None
            for path, text in beat_paths:
                if pattern in text.lower():
                    passed = False
                    field_path = path
                    message = f"Blocked phrase '{pattern}' detected."
                    break
            checks.append(
                ClaimGuardCheck(
                    rule_id=rule_id,
                    passed=passed,
                    blocking=True,
                    slot=slot,
                    field_path=field_path,
                    message=message,
                )
            )

    blocking_errors = [check for check in checks if check.blocking and not check.passed]
    return ClaimGuardResult(
        status="fail" if blocking_errors else "pass",
        checks=checks,
        blocking_errors=blocking_errors,
    )
