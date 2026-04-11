"""Brand OS tools: generate_brand_os (Strategy Agent), suggest_field_value. Writes only via this layer."""

import json
from time import monotonic
from typing import Any, Callable
from uuid import UUID

from openai import APITimeoutError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainGateBlockedError, DomainNotFoundError
from app.core.logging import get_logger
from app.modules.brand_os.domain_schema import BrandOS as BrandOSDomain
from app.modules.brand_os.models import BrandOS
from app.modules.brand_os.services import get_active_for_pack, get_by_source_job_id, list_versions_for_pack
from app.modules.packs.models import Pack
from app.modules.packs.services import build_step_2_finalization_payload
from app.shared.services.openai_compatible import (
    create_sync_openai_client,
    get_default_model,
    get_fast_model,
    has_openai_compatible_provider,
)

logger = get_logger("klarnow.brand_os")


GENERATE_BRAND_OS_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Project id"},
        "onboarding_answers": {
            "type": "object",
            "description": "Optional override; otherwise uses pack.onboarding_answers",
        },
        "source_job_id": {
            "type": "string",
            "description": "Optional idempotency key for background onboarding jobs.",
        },
    },
    "required": ["pack_id"],
}


def _next_version(existing_versions: list[str]) -> str:
    """Next version label: A if none, else B, C, ..."""
    if not existing_versions:
        return "A"
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used = {v for v in existing_versions if len(v) == 1 and v in letters}
    for c in letters:
        if c not in used:
            return c
    return "Z1"


def _stub_brand_os_domain() -> BrandOSDomain:
    """Fallback when OpenAI unavailable."""
    from app.modules.brand_os.domain_schema import (
        BrandFoundation,
        BrandStrategyProfile,
        MissionVision,
        AudiencePersona,
        PositioningDifferentiation,
        VoicePersonality,
        CoreMessagingHierarchy,
        StyleDirectionSeeds,
    )
    return BrandOSDomain(
        foundation=BrandFoundation(
            brand_name="",
            main_audience=[],
            one_line_offer="To be defined with your input.",
            brand_purpose=["Quality", "Customer first", "Integrity"],
            vision_12_month=[],
            brand_industry="",
        ),
        brand_strategy=BrandStrategyProfile(
            mission_vision=MissionVision(
                mission="To be defined with your input.",
                vision="To be defined with your input.",
                promise="To be defined with your input.",
            ),
            audience_personas=[
                AudiencePersona(
                    persona="Owner",
                    needs=["Clarity", "Results"],
                    pain_points=["Time", "Budget"],
                ),
            ],
            positioning_differentiation=PositioningDifferentiation(
                statement="SMB",
                unique_advantage="TBD",
            ),
            voice_personality=VoicePersonality(
                profile=["Professional", "friendly"],
                archetype="Caregiver",
                we_are=[],
                we_are_not=[],
            ),
            core_messaging_hierarchy=CoreMessagingHierarchy(
                elevator_pitch="TBD",
                proof_points=[],
            ),
            style_direction_seeds=StyleDirectionSeeds(
                typography="",
                design_cues=[],
                palette=[],
            ),
        ),
    )


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.startswith("json"):
        text = text[4:].lstrip()
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0].strip()
    return text


def _build_brand_os_context_payload(
    pack: Pack,
    onboarding_answers_override: dict | None = None,
) -> dict[str, Any]:
    payload = build_step_2_finalization_payload(pack)
    if not onboarding_answers_override:
        return payload

    override = dict(onboarding_answers_override)
    answers = dict(payload.get("answers") or {})
    answers.update({key: value for key, value in override.items() if value is not None})
    payload["answers"] = answers

    override_field_map = {
        "pack_name": "pack_name",
        "pack_type": "pack_type",
        "brand_name": "brand_name",
        "primary_cta": "primary_cta",
        "usp_category": "usp_category",
        "usp_statement": "usp_statement",
        "usp_proof": "usp_proof",
        "proof_text": "proof_text",
        "offer_one_liner": "offer_one_liner",
        "primary_pain": "primary_pain",
        "primary_outcome": "primary_outcome",
        "target_audience": "target_audience",
    }
    for payload_key, override_key in override_field_map.items():
        raw_value = override.get(override_key)
        if isinstance(raw_value, str) and raw_value.strip():
            payload[payload_key] = raw_value.strip()

    if override.get("has_existing_brand") is not None:
        payload["has_existing_brand"] = override.get("has_existing_brand")
    if override.get("brand_url") is not None:
        payload["brand_url"] = override.get("brand_url")
    if override.get("extracted_brand") is not None:
        payload["extracted_brand"] = override.get("extracted_brand")
    if override.get("vibe_chips") is not None:
        payload["vibe_chips"] = override.get("vibe_chips")

    if not payload.get("target_audience"):
        for fallback_key in ("who_is_it_for", "q1"):
            raw_value = override.get(fallback_key)
            if isinstance(raw_value, str) and raw_value.strip():
                payload["target_audience"] = raw_value.strip()
                break

    return payload


def _format_timeout_seconds(timeout_seconds: float) -> str:
    if float(timeout_seconds).is_integer():
        return str(int(timeout_seconds))
    return f"{timeout_seconds:.1f}".rstrip("0").rstrip(".")


def _brand_os_timeout_message(timeout_seconds: float) -> str:
    return (
        "Brand OS generation timed out after "
        f"{_format_timeout_seconds(timeout_seconds)} seconds while waiting for the AI provider."
    )


def _remaining_brand_os_timeout(deadline: float, total_timeout_seconds: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise RuntimeError(_brand_os_timeout_message(total_timeout_seconds))
    return max(1.0, remaining)


def _is_brand_os_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return True
    return "timed out" in str(exc).lower()


def _brand_os_failure_message(exc: Exception) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return f"Brand OS generation failed: {detail}"


def _report_brand_os_progress(
    progress_callback: Callable[[str], None] | None,
    message: str,
) -> None:
    if not progress_callback:
        return
    try:
        progress_callback(message)
    except Exception:
        logger.warning("brand_os_progress_callback_failed | message=%s", message)


def _call_openai_for_brand_os(
    context: str,
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> BrandOSDomain:
    """
    Generate Brand OS content from context using a two-step chain-of-thought approach:
    1. Brief reasoning pass to identify core brand signals
    2. Structured generation using that reasoning as additional context
    """
    settings = get_settings()
    if not has_openai_compatible_provider():
        return _stub_brand_os_domain()
    client = create_sync_openai_client(max_retries=0)
    if not client:
        return _stub_brand_os_domain()
    context_trimmed = context[:6000]
    timeout_seconds = max(float(settings.brand_os_request_timeout_seconds), 1.0)
    deadline = monotonic() + timeout_seconds

    # Step 1: Brief reasoning pass — identify key brand signals before generating
    reasoning = ""
    if settings.ai_brand_os_reasoning_enabled:
        reasoning_started = monotonic()
        _report_brand_os_progress(progress_callback, "Brand OS reasoning started.")
        try:
            reasoning_response = client.chat.completions.create(
                model=get_default_model(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a brand strategist. Identify the most important signals "
                            "from the provided business context. Be specific and concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analyze this brand context and identify in 4-5 sentences:\n"
                            f"1. The single most important problem this brand solves\n"
                            f"2. The primary buyer persona (who exactly needs this)\n"
                            f"3. The brand's key differentiator (what sets it apart)\n"
                            f"4. The appropriate brand tone and archetype\n\n"
                            f"Context:\n{context_trimmed}"
                        ),
                    },
                ],
                temperature=0.4,
                max_tokens=300,
                timeout=_remaining_brand_os_timeout(deadline, timeout_seconds),
            )
            reasoning = reasoning_response.choices[0].message.content or ""
            logger.info(
                "brand_os_reasoning_step_completed | duration_ms=%.2f",
                (monotonic() - reasoning_started) * 1000,
            )
            _report_brand_os_progress(
                progress_callback,
                f"Brand OS reasoning completed in {monotonic() - reasoning_started:.2f}s.",
            )
        except Exception as exc:
            reasoning_duration_seconds = monotonic() - reasoning_started
            logger.warning(
                "brand_os_reasoning_step_failed | duration_ms=%.2f | error=%s",
                reasoning_duration_seconds * 1000,
                exc,
            )
            _report_brand_os_progress(
                progress_callback,
                f"Brand OS reasoning failed after {reasoning_duration_seconds:.2f}s; continuing without it.",
            )
            pass  # Reasoning step failed — proceed with direct generation

    # Step 2: Structured generation using reasoning as additional context
    generation_prompt = (
        f"Generate a complete Brand OS (brand strategy) for this business.\n\n"
        + (f"Strategic analysis:\n{reasoning}\n\n" if reasoning else "")
        + f"Original context:\n{context_trimmed}\n\n"
        + "Fill in all fields:\n"
        + "- foundation: brand_name, main_audience, one_line_offer, brand_purpose, vision_12_month, brand_industry\n"
        + "- brand_strategy:\n"
        + "  - mission_vision: mission, vision, promise\n"
        + "  - audience_personas: list with persona, needs, pain_points\n"
        + "  - positioning_differentiation: statement, unique_advantage\n"
        + "  - voice_personality: profile tags, archetype, we_are, we_are_not\n"
        + "  - core_messaging_hierarchy: elevator_pitch, proof_points\n"
        + "  - style_direction_seeds: typography, design_cues, palette\n\n"
        + "Be specific to this brand — no generic templates. Return only valid JSON matching the schema."
    )

    generation_started = monotonic()
    _report_brand_os_progress(progress_callback, "Brand OS final generation started.")
    try:
        completion = client.chat.completions.create(
            model=get_default_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strategic brand consultant. Generate focused, specific brand "
                        "strategies tailored to the business — not generic filler."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{generation_prompt}\n\n"
                        "JSON schema:\n"
                        f"{json.dumps(BrandOSDomain.model_json_schema(), ensure_ascii=True)}"
                    ),
                },
            ],
            temperature=0.6,
            timeout=_remaining_brand_os_timeout(deadline, timeout_seconds),
        )
        content = completion.choices[0].message.content or "{}"
        logger.info(
            "brand_os_generation_step_completed | duration_ms=%.2f | content_chars=%s",
            (monotonic() - generation_started) * 1000,
            len(content),
        )
        _report_brand_os_progress(
            progress_callback,
            f"Brand OS final generation completed in {monotonic() - generation_started:.2f}s.",
        )
        return BrandOSDomain.model_validate(json.loads(_strip_markdown_fences(content)))
    except Exception as exc:
        generation_duration_seconds = monotonic() - generation_started
        if _is_brand_os_timeout_error(exc):
            message = _brand_os_timeout_message(timeout_seconds)
            _report_brand_os_progress(
                progress_callback,
                f"Brand OS final generation timed out after {generation_duration_seconds:.2f}s.",
            )
            if str(exc).strip() == message:
                raise
            raise RuntimeError(message) from exc
        logger.warning(
            "brand_os_generation_step_failed | duration_ms=%.2f | error_type=%s | error=%s",
            generation_duration_seconds * 1000,
            exc.__class__.__name__,
            exc,
        )
        _report_brand_os_progress(
            progress_callback,
            f"Brand OS final generation failed after {generation_duration_seconds:.2f}s: {exc}",
        )
        raise RuntimeError(_brand_os_failure_message(exc)) from exc


def generate_brand_os(
    db: Session,
    pack_id: UUID | str,
    onboarding_answers: dict | None = None,
    source_job_id: str | None = None,
    allow_without_onboarding_complete: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """Create a new Brand OS version (A or B) for the pack. Strategy Agent only."""
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")

    if source_job_id:
        existing_for_job = get_by_source_job_id(db, pack_id, source_job_id)
        if existing_for_job:
            return {
                "version": existing_for_job.version,
                "brand_os_id": str(existing_for_job.id),
            }

    # Do not generate Brand OS for new brands until Day 0 (onboarding) is complete.
    answers = onboarding_answers if onboarding_answers is not None else (pack.onboarding_answers or {})
    is_new_brand = answers.get("has_existing_brand") == "no"
    if is_new_brand and pack.onboarding_completed_at is None and not allow_without_onboarding_complete:
        raise DomainGateBlockedError(
            "Complete Day 0 onboarding before generating Brand OS for new brands."
        )

    context = ""
    if onboarding_answers is not None:
        context = json.dumps(
            _build_brand_os_context_payload(pack, onboarding_answers),
            ensure_ascii=True,
        )
    elif pack.onboarding_answers:
        context = json.dumps(
            _build_brand_os_context_payload(pack),
            ensure_ascii=True,
        )
    else:
        existing = list_versions_for_pack(db, pack_id)
        if existing:
            last = existing[0]
            if last.foundation and last.brand_strategy:
                context = (
                    f"Existing Brand OS (JSON): foundation={last.foundation}, "
                    f"brand_strategy={last.brand_strategy}"
                )
            else:
                context = (
                    f"Existing: mission={last.mission}, vision={last.vision}, "
                    f"values={last.values}, positioning={last.positioning}"
                )
        else:
            context = f"New pack: {pack.name}"

    content = _call_openai_for_brand_os(context, progress_callback=progress_callback)
    existing_versions = [b.version for b in list_versions_for_pack(db, pack_id)]
    version = _next_version(existing_versions)

    db.query(BrandOS).filter(
        BrandOS.pack_id == pack_id,
        BrandOS.is_active.is_(True),
    ).update({"is_active": False})

    brand_os = BrandOS(
        pack_id=pack_id,
        version=version,
        source_job_id=source_job_id,
        foundation=content.foundation.model_dump(),
        brand_strategy=content.brand_strategy.model_dump(),
        is_active=True,
    )
    db.add(brand_os)
    db.flush()
    pack.active_brand_os_id = brand_os.id
    db.commit()
    db.refresh(brand_os)
    return {"version": version, "brand_os_id": str(brand_os.id)}


def regenerate_brand_os(db: Session, pack_id: UUID, brand_os_id: UUID) -> BrandOS:
    """Create Version B from an existing Brand OS (same logic as generate_brand_os, context = existing)."""
    from app.modules.brand_os.services import get_by_id_and_pack

    existing = get_by_id_and_pack(db, brand_os_id, pack_id)
    if not existing:
        raise DomainNotFoundError("Brand OS not found")
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")
    if existing.foundation and existing.brand_strategy:
        context = (
            f"Existing Brand OS (JSON): foundation={existing.foundation}, "
            f"brand_strategy={existing.brand_strategy}"
        )
    else:
        context = (
            f"Existing: mission={existing.mission}, vision={existing.vision}, "
            f"values={existing.values}, positioning={existing.positioning}"
        )
    content = _call_openai_for_brand_os(context)
    existing_versions = [b.version for b in list_versions_for_pack(db, pack_id)]
    version = _next_version(existing_versions)
    db.query(BrandOS).filter(
        BrandOS.pack_id == pack_id,
        BrandOS.is_active.is_(True),
    ).update({"is_active": False})
    brand_os = BrandOS(
        pack_id=pack_id,
        version=version,
        foundation=content.foundation.model_dump(),
        brand_strategy=content.brand_strategy.model_dump(),
        is_active=True,
    )
    db.add(brand_os)
    db.flush()
    pack.active_brand_os_id = brand_os.id
    db.commit()
    db.refresh(brand_os)
    return brand_os


# Human-readable field names for the suggest prompt
SUGGEST_FIELD_LABELS: dict[str, str] = {
    "mission_vision.mission": "mission statement",
    "mission_vision.vision": "vision statement",
    "mission_vision.promise": "brand promise",
    "positioning_differentiation.statement": "positioning statement",
    "positioning_differentiation.unique_advantage": "unique advantage / differentiation",
    "voice_personality.archetype": "brand archetype",
    "voice_personality.profile": "voice profile tags (one per line)",
    "voice_personality.we_are": "we are traits (one per line)",
    "voice_personality.we_are_not": "we are not traits (one per line)",
    "core_messaging_hierarchy.elevator_pitch": "elevator pitch",
    "core_messaging_hierarchy.proof_points": "proof points (one per line)",
    "style_direction_seeds.typography": "typography",
    "style_direction_seeds.design_cues": "design cues (one per line)",
    "style_direction_seeds.palette": "palette / colours (one per line)",
}
# Audience persona fields: audience_personas.0.persona, audience_personas.0.needs, etc.
for i in range(5):
    SUGGEST_FIELD_LABELS[f"audience_personas.{i}.persona"] = f"persona {i + 1} name"
    SUGGEST_FIELD_LABELS[f"audience_personas.{i}.needs"] = f"persona {i + 1} needs (one per line)"
    SUGGEST_FIELD_LABELS[f"audience_personas.{i}.pain_points"] = f"persona {i + 1} pain points (one per line)"


def suggest_field_value(
    db: Session,
    pack_id: UUID,
    field: str,
    current_value: str | None = None,
) -> str:
    """Suggest a value for a Brand OS strategy field using the active Brand OS as context."""
    active = get_active_for_pack(db, pack_id)
    context_parts: list[str] = []
    if active:
        if active.foundation and isinstance(active.foundation, dict):
            context_parts.append(f"Foundation: {json.dumps(active.foundation)[:1500]}")
        if active.brand_strategy and isinstance(active.brand_strategy, dict):
            context_parts.append(f"Brand strategy: {json.dumps(active.brand_strategy)[:2500]}")
    context_str = "\n".join(context_parts) if context_parts else "No existing brand context."
    field_label = SUGGEST_FIELD_LABELS.get(field, field.replace("_", " "))
    current = (current_value or "").strip()
    prompt = f"""You are helping edit a brand strategy. Given the following brand context, suggest a value for the field described below.

Brand context:
{context_str}

Field to suggest: {field_label}.
{"Current value (can refine or replace): " + current if current else "Field is empty; suggest an initial value."}

Respond with only the suggested value. For list fields (e.g. one per line), output each item on its own line. No explanation, no markdown, no quotes around the whole thing."""

    if not has_openai_compatible_provider():
        return current or f"(Suggestions require OPENROUTER_API_KEY; field: {field_label})"
    client = create_sync_openai_client()
    if not client:
        return current or f"(Suggestions require OPENROUTER_API_KEY; field: {field_label})"
    try:
        r = client.chat.completions.create(
            model=get_fast_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=500,
        )
        text = (r.choices[0].message.content or "").strip()
        return text if text else current
    except Exception:
        return current
