"""Orchestrator (Klaro Control Plane): intent classification, context assembly, tool chain execution."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.agents.registry import REGISTRY, execute
from app.modules.brand_os.services import get_active_for_pack
from app.modules.builder.services import get_for_pack_any, get_published_for_pack
from app.modules.packs.models import Pack

CHAT_CONTEXT_LAST_N_MESSAGES = 20

ONBOARDING_DAY_CONTEXT: dict[int, dict[str, object]] = {
    0: {
        "title": "Business foundations",
        "playbook": "Capture what the business does, why it exists, and the action you want customers to take.",
        "tasks": [
            "Describe the business clearly",
            "Explain why it started",
            "Define the main call-to-action",
        ],
        "win_condition": "Business foundations captured",
        "steps": ["what_do_you_do", "why_started", "primary_cta"],
    },
    1: {
        "title": "Audience clarity",
        "playbook": "Clarify who the business serves and what matters most to them.",
        "tasks": [
            "Describe the target customer",
            "Capture the main pain or desired outcome",
        ],
        "win_condition": "Audience captured",
        "steps": ["who_are_your_customers"],
    },
    2: {
        "title": "Brand assets",
        "playbook": "Collect existing brand assets or define a new brand direction.",
        "tasks": [
            "Share a website or logo if one exists",
            "Otherwise choose a brand name and vibe",
        ],
        "win_condition": "Brand input captured",
        "steps": ["has_existing_brand", "brand_url", "brand_name", "vibe_chips"],
    },
    3: {
        "title": "Proof and trust",
        "playbook": "Capture wins, testimonials, and credibility signals that strengthen copy.",
        "tasks": [
            "Share testimonials, outcomes, or milestones",
        ],
        "win_condition": "Proof captured",
        "steps": ["proof_text"],
    },
}


def assemble_context(
    pack_id: UUID, db: Session, day_context: int | None = None
) -> dict:
    """Load project, onboarding, active Brand OS, CTA context, and website status."""
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {}
    brand_os = get_active_for_pack(db, pack_id)

    draft_site = get_for_pack_any(db, pack_id)
    published_site = get_published_for_pack(db, pack_id)
    if published_site:
        website_status = "published"
    elif draft_site:
        website_status = "draft"
    else:
        website_status = "none"

    ctx: dict = {
        "pack_id": str(pack_id),
        "pack_name": pack.name,
        "onboarding_answers": pack.onboarding_answers,
        "onboarding_completed": pack.onboarding_completed_at is not None,
        "onboarding_background_completed": pack.onboarding_background_completed_at is not None,
        "active_brand_os_version": brand_os.version if brand_os else None,
        "campaign_goal": pack.core_concept,
        "campaign_primary_cta": pack.primary_cta,
        "campaign_angles": None,
        "website_status": website_status,
        "plan_horizon": "growth" if pack.onboarding_completed_at else "onboarding",
    }

    context = ONBOARDING_DAY_CONTEXT.get(day_context or -1)
    if context:
        ctx["day_context"] = day_context
        ctx["day_title"] = context["title"]
        ctx["day_playbook"] = context["playbook"]
        ctx["day_tasks"] = context["tasks"]
        ctx["day_win_condition"] = context["win_condition"]
        ctx["day_conversation_steps"] = context["steps"]

    return ctx


def run_tool_chain(
    pack_id: UUID,
    tool_names: list[str],
    db: Session,
    agent: str = "orchestrator",
    tool_inputs_override: dict[str, dict] | None = None,
) -> list[dict]:
    """Run a sequence of tools; log each; stop on error after retries. Returns list of results."""
    settings = get_settings()
    max_len = settings.max_tool_chain_length
    retry_cap = settings.retry_cap_per_tool
    if len(tool_names) > max_len:
        tool_names = tool_names[:max_len]
    results = []
    override = tool_inputs_override or {}
    for tool_name in tool_names:
        if tool_name not in REGISTRY:
            continue
        inputs = override.get(tool_name, {"pack_id": str(pack_id)})
        if "pack_id" not in inputs:
            inputs["pack_id"] = str(pack_id)
        retries = 0
        while retries <= retry_cap:
            try:
                out = execute(tool_name, agent, pack_id, inputs, db)
                results.append({"tool": tool_name, "success": True, "result": out})
                break
            except Exception as e:
                retries += 1
                try:
                    db.rollback()
                except Exception:
                    pass
                if retries > retry_cap:
                    results.append({"tool": tool_name, "success": False, "error": str(e)})
                    raise
    return results


def handle_onboarding_complete(
    pack_id: UUID,
    db: Session,
    *,
    source_job_id: str | None = None,
) -> list[dict]:
    """After onboarding complete: generate Brand OS."""
    tool_inputs_override = None
    if source_job_id:
        tool_inputs_override = {
            "generate_brand_os": {
                "pack_id": str(pack_id),
                "source_job_id": source_job_id,
            }
        }
    return run_tool_chain(
        pack_id,
        ["generate_brand_os"],
        db,
        agent="orchestrator",
        tool_inputs_override=tool_inputs_override,
    )
