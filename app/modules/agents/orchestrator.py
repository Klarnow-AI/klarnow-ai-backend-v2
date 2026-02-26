"""Orchestrator (Klaro Control Plane): intent classification, context assembly, tool chain execution."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.agents.registry import REGISTRY, execute
from app.modules.brand_os.services import get_active_for_pack
from app.modules.campaign.services import get_active_for_pack as get_campaign_for_pack
from app.modules.packs.models import Pack

CHAT_CONTEXT_LAST_N_MESSAGES = 20


def assemble_context(
    pack_id: UUID, db: Session, day_context: int | None = None
) -> dict:
    """Load pack, onboarding, active Brand OS, Campaign, conversion page status, plan horizon.
    When day_context is 0-3, include day playbook, tasks, win_condition for the Day 0-3 flow."""
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {}
    brand_os = get_active_for_pack(db, pack_id)
    campaign = get_campaign_for_pack(db, pack_id)

    conversion_page_status = None
    from app.modules.conversion_page.services import get_draft, get_published
    draft = get_draft(db, pack_id)
    published = get_published(db, pack_id)
    if published:
        conversion_page_status = "published"
    elif draft:
        conversion_page_status = "draft"
    else:
        conversion_page_status = "none"

    plan_horizon = None
    mode = "build"
    from app.modules.sprint.services import get_active_sprint_for_pack
    from app.modules.sprint.day_definitions import get_day_definition, get_day_content, get_day_conversation_steps

    active_sprint = get_active_sprint_for_pack(db, pack_id)
    if active_sprint:
        plan_horizon = "14"
        mode = active_sprint.mode or "build"

    ctx: dict = {
        "pack_id": str(pack_id),
        "pack_name": pack.name,
        "onboarding_answers": pack.onboarding_answers,
        "onboarding_completed": pack.onboarding_completed_at is not None,
        "active_brand_os_version": brand_os.version if brand_os else None,
        "campaign_goal": campaign.goal if campaign else None,
        "campaign_primary_cta": campaign.primary_cta if campaign else None,
        "campaign_angles": campaign.angles if campaign else None,
        "conversion_page_status": conversion_page_status,
        "plan_horizon": plan_horizon,
    }

    if day_context is not None and 0 <= day_context <= 3:
        try:
            day_def = get_day_definition(day_context)
            day_content = get_day_content(day_context, mode)
            ctx["day_context"] = day_context
            ctx["day_title"] = day_def["title"]
            ctx["day_playbook"] = day_content["playbook"]
            ctx["day_tasks"] = day_content["tasks"]
            ctx["day_win_condition"] = day_def["win_condition"]
            ctx["day_conversation_steps"] = get_day_conversation_steps(day_context)
        except ValueError:
            pass

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
                if retries > retry_cap:
                    results.append({"tool": tool_name, "success": False, "error": str(e)})
                    raise
    return results


def handle_onboarding_complete(pack_id: UUID, db: Session) -> list[dict]:
    """After onboarding complete: generate Brand OS."""
    return run_tool_chain(
        pack_id,
        ["generate_brand_os"],
        db,
        agent="orchestrator",
    )
