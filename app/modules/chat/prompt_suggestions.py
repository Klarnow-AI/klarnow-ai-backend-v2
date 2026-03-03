"""LLM-generated starter prompts for pack chat empty state."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.agents.orchestrator import assemble_context
from app.modules.landing.next_action import get_next_action
from app.modules.packs.services import get_pack_for_user

logger = get_logger("klarnow.chat.prompt_suggestions")

PROMPT_COUNT = 3
MAX_PROMPT_LEN = 120


def _clean_prompt(text: Any) -> str | None:
    """Normalize one suggested prompt string."""
    if not isinstance(text, str):
        return None
    compact = " ".join(text.strip().split())
    if not compact:
        return None
    if len(compact) > MAX_PROMPT_LEN:
        compact = compact[:MAX_PROMPT_LEN].rstrip()
    return compact


def _dedupe_prompts(prompts: list[str]) -> list[str]:
    """Deduplicate prompts while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for p in prompts:
        key = p.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _extract_next_action_chip_labels(next_action: dict[str, Any]) -> list[str]:
    """Extract user-facing chip labels from next-action payload."""
    labels: list[str] = []
    raw_chips = next_action.get("action_chips")
    if not isinstance(raw_chips, list):
        return labels
    for chip in raw_chips:
        label = None
        if isinstance(chip, dict):
            label = chip.get("label")
        else:
            label = getattr(chip, "label", None)
        if isinstance(label, str) and label.strip():
            labels.append(" ".join(label.strip().split()))
    return labels


def _fallback_prompts(
    pack_context: dict[str, Any],
    next_action: dict[str, Any],
) -> list[str]:
    """Context-aware fallback prompts when LLM generation is unavailable."""
    prompts: list[str] = []

    action_text = next_action.get("action_text")
    if isinstance(action_text, str) and action_text.strip():
        prompts.append(f"Help me execute this next action: {action_text.strip()}.")

    cta = pack_context.get("campaign_primary_cta")
    if isinstance(cta, str) and cta.strip():
        prompts.append(f"Improve this CTA so it converts better: {cta.strip()}")

    goal = pack_context.get("campaign_goal")
    goal_line = None
    if isinstance(goal, dict):
        candidate = goal.get("description") or goal.get("title")
        if isinstance(candidate, str) and candidate.strip():
            goal_line = candidate.strip()
    elif isinstance(goal, str) and goal.strip():
        goal_line = goal.strip()
    if goal_line:
        prompts.append(f"Give me a 7-day execution plan to hit this goal: {goal_line}")

    website_status = pack_context.get("website_status")
    if isinstance(website_status, str):
        if website_status == "none":
            prompts.append("What website page should I launch first to support my current offer?")
        elif website_status == "draft":
            prompts.append("Review my draft website strategy and tell me the highest-impact fix to ship today.")
        elif website_status == "published":
            prompts.append("How do I optimize my live page to increase conversions this week?")

    for label in _extract_next_action_chip_labels(next_action):
        prompts.append(f"Turn '{label}' into a concrete action plan I can complete today.")

    why_it_matters = next_action.get("why_it_matters")
    if isinstance(why_it_matters, str) and why_it_matters.strip():
        prompts.append(f"Break this into today's checklist: {why_it_matters.strip()}")

    stage = next_action.get("stage")
    if isinstance(stage, str) and stage.strip():
        prompts.append(
            f"I'm in stage '{stage.strip()}'. What should I prioritize in the next 30 minutes?"
        )

    cleaned = [_clean_prompt(p) for p in prompts]
    deduped = _dedupe_prompts([p for p in cleaned if p])
    if len(deduped) < PROMPT_COUNT:
        action_seed = action_text.strip() if isinstance(action_text, str) and action_text.strip() else "my current priority"
        stage_seed = stage.strip() if isinstance(stage, str) and stage.strip() else "my current stage"
        deduped.extend(
            _dedupe_prompts(
                [
                    f"Create a step-by-step plan to execute '{action_seed}' in one focused session.",
                    f"After '{action_seed}', what should my immediate next move be?",
                    f"Given '{stage_seed}', what should I avoid so I don't slow down progress?",
                ]
            )
        )
    return _dedupe_prompts(deduped)[:PROMPT_COUNT]


def _strip_markdown_fences(raw: str) -> str:
    """Remove optional markdown code fences around JSON."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.startswith("json"):
        text = text[4:].lstrip()
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0].strip()
    return text


def suggest_pack_chat_prompts(
    db: Session,
    user_id: UUID,
    pack_id: UUID,
) -> list[str]:
    """
    Return up to 3 starter prompts tailored to pack/campaign state and next action.

    Uses OpenAI when available and falls back to deterministic context-aware prompts.
    """
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise ValueError("Pack not found")

    pack_context = assemble_context(pack_id, db)
    next_action = get_next_action(db, user_id, pack_id)
    fallback = _fallback_prompts(pack_context, next_action)

    settings = get_settings()
    if not settings.openai_api_key:
        return fallback

    prompt_context = {
        "pack_name": pack.name,
        "brand_name": pack.brand_name,
        "offer_one_liner": pack.offer_one_liner,
        "target_audience": pack.target_audience,
        "primary_pain": pack.primary_pain,
        "primary_outcome": pack.primary_outcome,
        "campaign_primary_cta": pack_context.get("campaign_primary_cta"),
        "campaign_goal": pack_context.get("campaign_goal"),
        "campaign_angles_count": (
            len(pack_context["campaign_angles"])
            if isinstance(pack_context.get("campaign_angles"), list)
            else 0
        ),
        "website_status": pack_context.get("website_status"),
        "plan_horizon": pack_context.get("plan_horizon"),
        "next_action": {
            "action_text": next_action.get("action_text"),
            "stage": next_action.get("stage"),
            "can_proceed": next_action.get("can_proceed"),
            "blocker_message": next_action.get("blocker_message"),
            "why_it_matters": next_action.get("why_it_matters"),
            "time_estimate": next_action.get("time_estimate"),
            "progress_counters": next_action.get("progress_counters"),
            "action_chips": _extract_next_action_chip_labels(next_action),
        },
    }

    user_prompt = (
        "Generate exactly 3 short chat starter prompts for the user to click in a marketing assistant UI.\n"
        "The prompts must be grounded in this pack/campaign context and next action.\n"
        "Each prompt should be specific, actionable, and phrased as something the user asks Klaro.\n"
        "Keep each prompt under 120 characters.\n"
        "Avoid generic prompts and avoid repeating the same idea.\n"
        "Return ONLY valid JSON in this format: {\"prompts\":[\"...\",\"...\",\"...\"]}\n\n"
        f"CONTEXT:\n{json.dumps(prompt_context, ensure_ascii=True)}"
    )

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise, high-signal chat starter prompts for marketing execution workflows. "
                        "Output strict JSON only."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=220,
        )
        raw = response.choices[0].message.content if response.choices else ""
        if not raw:
            return fallback
        parsed = json.loads(_strip_markdown_fences(raw))
        raw_prompts = parsed.get("prompts") if isinstance(parsed, dict) else None
        if not isinstance(raw_prompts, list):
            return fallback
        cleaned = [_clean_prompt(p) for p in raw_prompts]
        deduped = _dedupe_prompts([p for p in cleaned if p])
        final_prompts = deduped[:PROMPT_COUNT]
        return final_prompts if final_prompts else fallback
    except Exception as e:
        logger.warning("chat_prompt_suggestions_failed | error=%s", e)
        return fallback
