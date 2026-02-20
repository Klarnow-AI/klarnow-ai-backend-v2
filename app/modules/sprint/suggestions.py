"""Sprint day field suggestions: pre-fill and refine with AI using pack context."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.packs.models import Pack


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
        return _empty_day_response(day_number)

    context = _pack_context_for_suggestions(pack)
    settings = get_settings()
    if not settings.openai_api_key:
        return _fallback_day_response(day_number, pack)

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)

    if day_number == 1:
        suggestion = _call_llm_single(
            client,
            context=context,
            field_label="offer one-liner (one clear sentence: what you're selling)",
            current_value=(pack.offer_one_liner or "").strip(),
            instruction="Suggest a compelling one-sentence offer that someone can say yes or no to.",
        )
        return {"offer_one_liner": suggestion or (pack.offer_one_liner or "")}

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
        return {"pitch_script": pitch or ""}

    return _empty_day_response(day_number)


def _call_llm_single(
    client,
    *,
    context: str,
    field_label: str,
    current_value: str,
    instruction: str,
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
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=500,
        )
        return (r.choices[0].message.content or "").strip() or current_value
    except Exception:
        return current_value


def _empty_day_response(day_number: int) -> dict:
    if day_number == 1:
        return {"offer_one_liner": ""}
    if day_number == 2:
        return {"primary_pain": "", "primary_outcome": ""}
    if day_number == 3:
        return {"pitch_script": ""}
    return {}


def _fallback_day_response(day_number: int, pack: Pack) -> dict:
    """When API key is missing, return current pack values where applicable."""
    if day_number == 1:
        return {"offer_one_liner": (pack.offer_one_liner or "").strip()}
    if day_number == 2:
        return {
            "primary_pain": (pack.primary_pain or "").strip(),
            "primary_outcome": (pack.primary_outcome or "").strip(),
        }
    if day_number == 3:
        return {"pitch_script": ""}
    return _empty_day_response(day_number)


SPRINT_DAY_FIELDS = {"offer_one_liner", "primary_pain", "primary_outcome", "pitch_script"}


def suggest_sprint_field(
    db: Session,
    pack_id: UUID,
    day: int,
    field: str,
    current_value: str | None = None,
) -> str:
    """
    Suggest or refine a single sprint day field. Uses pack context.
    field must be one of: offer_one_liner, primary_pain, primary_outcome, pitch_script.
    """
    if field not in SPRINT_DAY_FIELDS:
        return (current_value or "").strip()

    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return (current_value or "").strip()

    context = _pack_context_for_suggestions(pack)
    settings = get_settings()
    if not settings.openai_api_key:
        return (current_value or "").strip()

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)

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

    return _call_llm_single(
        client,
        context=context,
        field_label=labels.get(field, field.replace("_", " ")),
        current_value=(current_value or "").strip(),
        instruction=instructions.get(field, "Suggest a value for this field."),
    )
