"""Sprint day field suggestions: pre-fill and refine with AI using pack context."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.packs.models import Pack
from app.shared.services.openai_compatible import (
    create_sync_openai_client,
    get_fast_model,
    has_openai_compatible_provider,
)


def _sprint_ai_unavailable_reason() -> str | None:
    settings = get_settings()
    if not has_openai_compatible_provider():
        return "Sprint AI suggestions need OPENROUTER_API_KEY to be set."
    if not settings.ai_sprint_field_suggestions_enabled:
        return (
            "Sprint AI suggestions are disabled. Set "
            "AI_SPRINT_FIELD_SUGGESTIONS_ENABLED=true and restart the backend."
        )
    return None


def _pack_context_for_suggestions(pack: Pack) -> str:
    """Build a short context string for LLM prompts from pack data."""
    parts: list[str] = []
    oa = pack.onboarding_answers or {}
    if isinstance(oa, str):
        try:
            import json
            oa = json.loads(oa) if oa else {}
        except Exception:
            oa = {}
    if pack.brand_name:
        parts.append(f"Brand name: {pack.brand_name}")
    if pack.primary_cta:
        parts.append(f"Primary CTA: {pack.primary_cta}")
    if pack.usp_statement:
        parts.append(f"USP: {pack.usp_statement}")
    if pack.usp_proof:
        parts.append(f"Proof: {pack.usp_proof}")
    for key in ("brand_name", "primary_cta", "usp_statement", "usp_proof", "usp_category"):
        if key in oa and oa[key] and not any(f"{key}:" in p for p in parts):
            val = oa[key]
            if isinstance(val, str) and val.strip():
                parts.append(f"{key.replace('_', ' ').title()}: {val.strip()[:200]}")
    if pack.offer_one_liner:
        parts.append(f"Offer one-liner: {pack.offer_one_liner}")
    if pack.primary_pain:
        parts.append(f"Primary pain: {pack.primary_pain}")
    if pack.primary_outcome:
        parts.append(f"Primary outcome: {pack.primary_outcome}")
    return "\n".join(parts) if parts else "No pack context yet."


def suggest_day_fields(db: Session, pack_id: UUID, day_number: int) -> dict:
    """
    Return suggested values for a sprint day's fields (Day 1, 2, or 3).
    Uses pack context; one LLM call per field for simplicity.
    """
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return _empty_day_response(
            day_number,
            source="fallback",
            reason="Pack not found.",
        )

    context = _pack_context_for_suggestions(pack)
    unavailable_reason = _sprint_ai_unavailable_reason()
    if unavailable_reason:
        return _fallback_day_response(
            day_number,
            pack,
            source="fallback",
            reason=unavailable_reason,
        )

    client = create_sync_openai_client()
    if not client:
        return _fallback_day_response(
            day_number,
            pack,
            source="fallback",
            reason="Sprint AI suggestions need OPENROUTER_API_KEY to be set.",
        )

    if day_number == 1:
        suggestion = _call_llm_single(
            client,
            context=context,
            field_label="offer one-liner (one clear sentence: what you're selling)",
            current_value=(pack.offer_one_liner or "").strip(),
            instruction="Suggest a compelling one-sentence offer that someone can say yes or no to.",
        )
        return {
            "offer_one_liner": suggestion or (pack.offer_one_liner or ""),
            "source": "ai",
            "reason": None,
        }

    if day_number == 2:
        pain = _call_llm_single(
            client,
            context=context,
            field_label="primary pain point (main problem/frustration of target audience)",
            current_value=(pack.primary_pain or "").strip(),
            instruction="Suggest the main problem or frustration the target audience experiences.",
        )
        outcome = _call_llm_single(
            client,
            context=context,
            field_label="primary outcome (desired result/transformation)",
            current_value=(pack.primary_outcome or "").strip(),
            instruction="Suggest the desired result or transformation they want.",
        )
        return {
            "primary_pain": pain or (pack.primary_pain or ""),
            "primary_outcome": outcome or (pack.primary_outcome or ""),
            "source": "ai",
            "reason": None,
        }

    if day_number == 3:
        offer = (pack.offer_one_liner or "").strip()
        pain = (pack.primary_pain or "").strip()
        outcome = (pack.primary_outcome or "").strip()
        pitch = _call_llm_single(
            client,
            context=context,
            field_label="pitch script (under 60 seconds: Hi [Name], I help [who] with [problem]...)",
            current_value="",
            instruction="Write a short pitch script (under 60 seconds) using the pack's offer, pain, and outcome. Template: Hi [Name], I help [who] with [problem]. Most people struggle with [pain], but we [solution]. Interested in [CTA]?",
        )
        return {"pitch_script": pitch or "", "source": "ai", "reason": None}

    return _empty_day_response(
        day_number,
        source="fallback",
        reason="Unsupported sprint day.",
    )


def _call_llm_single(
    client,
    *,
    context: str,
    field_label: str,
    current_value: str,
    instruction: str,
    suppress_errors: bool = True,
) -> str:
    """One LLM call: suggest or refine a single text value."""
    current_phrase = (
        f"Current value (refine or replace): {current_value}"
        if current_value
        else "Field is empty; suggest an initial value."
    )
    prompt = f"""You are helping a business owner complete their 14-day sprint. Given this brand/pack context:

{context}

{instruction}

Field: {field_label}.
{current_phrase}

Respond with ONLY the suggested value. No explanation, no markdown, no quotes around the whole thing. One paragraph or a few short lines max."""

    try:
        r = client.chat.completions.create(
            model=get_fast_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=500,
        )
        return (r.choices[0].message.content or "").strip() or current_value
    except Exception:
        if not suppress_errors:
            raise
        return current_value


def _empty_day_response(
    day_number: int,
    *,
    source: str = "fallback",
    reason: str | None = None,
) -> dict:
    if day_number == 1:
        return {"offer_one_liner": "", "source": source, "reason": reason}
    if day_number == 2:
        return {
            "primary_pain": "",
            "primary_outcome": "",
            "source": source,
            "reason": reason,
        }
    if day_number == 3:
        return {"pitch_script": "", "source": source, "reason": reason}
    return {}


def _fallback_day_response(
    day_number: int,
    pack: Pack,
    *,
    source: str = "fallback",
    reason: str | None = None,
) -> dict:
    """When API key is missing, return current pack values where applicable."""
    if day_number == 1:
        return {
            "offer_one_liner": (pack.offer_one_liner or "").strip(),
            "source": source,
            "reason": reason,
        }
    if day_number == 2:
        return {
            "primary_pain": (pack.primary_pain or "").strip(),
            "primary_outcome": (pack.primary_outcome or "").strip(),
            "source": source,
            "reason": reason,
        }
    if day_number == 3:
        return {"pitch_script": "", "source": source, "reason": reason}
    return _empty_day_response(day_number, source=source, reason=reason)


SPRINT_DAY_FIELDS = {"offer_one_liner", "primary_pain", "primary_outcome", "pitch_script"}

DAY_0_LLM_FIELDS = {"brand_name", "primary_cta", "usp_statement", "usp_proof", "proof_text", "brand_url"}


def suggest_day_field_chips(
    db: Session,
    pack_id: UUID,
    day_number: int,
    field_key: str,
    count: int = 3,
    exclude: list[str] | None = None,
) -> list[dict]:
    """
    Return 2-4 suggestion chips for a day field. For static-option fields (usp_category,
    voice_notes_sent) returns those options. For LLM fields, generates alternatives.
    exclude: list of labels to avoid when re-suggesting.
    """
    exclude_set = set((exclude or []))
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return []

    from app.modules.sprint.day_definitions import get_step_by_field_key

    step = get_step_by_field_key(day_number, field_key)
    if not step:
        return []

    options = step.get("options")
    if options:
        chips = [
            {"label": o, "value": o}
            for o in options
            if isinstance(o, str) and o not in exclude_set
        ]
        return chips[:count] if count else chips

    context = _pack_context_for_suggestions(pack)
    settings = get_settings()
    if not has_openai_compatible_provider() or not settings.ai_sprint_field_suggestions_enabled:
        return []
    client = create_sync_openai_client()
    if not client:
        return []

    field_labels = {
        "brand_name": "brand name",
        "brand_url": "website URL",
        "primary_cta": "primary call-to-action",
        "usp_statement": "USP statement (why choose you)",
        "usp_proof": "proof point",
        "proof_text": "additional proof or testimonial",
        "offer_one_liner": "offer in one sentence",
        "primary_pain": "primary pain point",
        "primary_outcome": "primary outcome",
        "pitch_script": "pitch script (under 60 seconds)",
    }
    label = field_labels.get(field_key, field_key.replace("_", " "))
    exclude_phrase = (
        f" Exclude these (user already saw them): {', '.join(exclude_set)}."
        if exclude_set
        else ""
    )

    prompt = f"""You are helping a business owner complete their 14-day sprint. Given this brand context:

{context}

Suggest exactly {min(count, 4)} distinct, short options for the field: {label}.
Output one option per line. Each line = one suggestion. No numbering, no explanation, no markdown.{exclude_phrase}
Make each suggestion concrete and specific to their brand."""

    try:
        r = client.chat.completions.create(
            model=get_fast_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=400,
        )
        text = (r.choices[0].message.content or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        chips = [{"label": ln, "value": ln} for ln in lines[:count] if ln not in exclude_set]
        return chips
    except Exception:
        return []


def suggest_sprint_field(
    db: Session,
    pack_id: UUID,
    day: int,
    field: str,
    current_value: str | None = None,
) -> dict:
    """
    Suggest or refine a single sprint day field. Uses pack context.
    field must be one of: offer_one_liner, primary_pain, primary_outcome, pitch_script.
    """
    current = (current_value or "").strip()
    if field not in SPRINT_DAY_FIELDS:
        return {
            "suggestion": current,
            "source": "fallback",
            "reason": f"Unsupported sprint field: {field}.",
        }

    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {
            "suggestion": current,
            "source": "fallback",
            "reason": "Pack not found.",
        }

    context = _pack_context_for_suggestions(pack)
    unavailable_reason = _sprint_ai_unavailable_reason()
    if unavailable_reason:
        return {
            "suggestion": current,
            "source": "fallback",
            "reason": unavailable_reason,
        }

    client = create_sync_openai_client()
    if not client:
        return {
            "suggestion": current,
            "source": "fallback",
            "reason": "Sprint AI suggestions need OPENROUTER_API_KEY to be set.",
        }

    labels = {
        "offer_one_liner": "offer one-liner (one clear sentence: what you're selling)",
        "primary_pain": "primary pain point (main problem/frustration of target audience)",
        "primary_outcome": "primary outcome (desired result/transformation)",
        "pitch_script": "pitch script (under 60 seconds)",
    }
    instructions = {
        "offer_one_liner": "Suggest a compelling one-sentence offer.",
        "primary_pain": "Suggest the main problem or frustration the target audience experiences.",
        "primary_outcome": "Suggest the desired result or transformation they want.",
        "pitch_script": "Write a short pitch script (under 60 seconds) using offer, pain, and outcome.",
    }

    try:
        suggestion = _call_llm_single(
            client,
            context=context,
            field_label=labels.get(field, field.replace("_", " ")),
            current_value=current,
            instruction=instructions.get(field, "Suggest a value for this field."),
            suppress_errors=False,
        )
    except Exception:
        return {
            "suggestion": current,
            "source": "fallback",
            "reason": "Sprint AI suggestions are temporarily unavailable. Please try again.",
        }

    return {
        "suggestion": suggestion,
        "source": "ai",
        "reason": None,
    }
