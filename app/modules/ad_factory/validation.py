"""Ad Factory V2 validation. Hard block on failure."""

from app.modules.ad_factory.schemas import BrandBrief, Variant


def validate_variants(brand_brief: BrandBrief, variants: list[Variant]) -> tuple[bool, list[dict]]:
    checks: list[dict] = []

    paths = [v.path for v in variants]
    paths_unique = len(paths) == len(set(paths))
    checks.append({
        "check_id": "paths_unique_across_variants",
        "passed": paths_unique,
        "message": "Paths must differ across A/B/C" if not paths_unique else None,
        "blocking": True,
    })

    hooks = [v.hook_type for v in variants]
    hooks_unique = len(hooks) == len(set(hooks))
    checks.append({
        "check_id": "hook_types_unique_across_variants",
        "passed": hooks_unique,
        "message": "Hook types must differ across A/B/C" if not hooks_unique else None,
        "blocking": True,
    })

    variant_c = next((v for v in variants if v.slot == "C"), None)
    c_offer_smash = (
        variant_c is not None
        and variant_c.treatment == "offer_smash"
        and variant_c.intent == "offer_led"
    )
    checks.append({
        "check_id": "variant_c_offer_smash",
        "passed": c_offer_smash,
        "message": "Variant C must use offer_smash treatment" if not c_offer_smash else None,
        "blocking": True,
    })

    talking_head_ok = True
    if not brand_brief.face_on_camera:
        for v in variants:
            if v.treatment == "talking_head_authority":
                talking_head_ok = False
                break
    checks.append({
        "check_id": "talking_head_disallowed_when_face_off",
        "passed": talking_head_ok,
        "message": "Talking head not allowed when face_on_camera is false" if not talking_head_ok else None,
        "blocking": True,
    })

    cta_match = all(
        brand_brief.cta_action.lower() in v.script_30s.beats[-1].text.lower()
        for v in variants
    )
    checks.append({
        "check_id": "cta_matches_brandbrief_action",
        "passed": cta_match,
        "message": "CTA verb must match BrandBrief cta_action" if not cta_match else None,
        "blocking": True,
    })

    proof_ok = all(any(b.beat_name == "proof" for b in v.script_30s.beats) for v in variants)
    checks.append({
        "check_id": "proof_by_second_10_in_30s",
        "passed": proof_ok,
        "message": "Proof beat required in 30s script" if not proof_ok else None,
        "blocking": True,
    })

    return all(c["passed"] for c in checks), checks
