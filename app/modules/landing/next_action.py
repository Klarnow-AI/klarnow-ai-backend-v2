"""Next Action engine: one next action. Priority: blockers, revenue leaks, sprint day, optimisation, check-in."""

from datetime import timezone
from datetime import datetime as dt
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.gates import (
    can_pass_day7_gate,
    can_pass_day8_gate,
    can_pass_pack_gate,
)
from app.modules.clients.models import LEAD_STATUS_NEW
from app.modules.clients.services import list_leads_for_pack
from app.modules.builder.services import get_published_for_pack
from app.modules.landing.schemas import NextActionChip
from app.modules.packs.services import get_pack_for_user, list_packs_for_user
from app.modules.revenue.services import list_proposals_for_pack, list_invoices_for_pack
from app.modules.sprint.services import (
    get_active_sprint_for_pack,
    get_day_card,
)
from app.modules.tasks.services import get_overdue_tasks
from app.modules.packs.models import User


def _chip(label: str, href: str | None = None) -> NextActionChip:
    return NextActionChip(label=label, href=href)


def get_next_action(
    db: Session, user_id: UUID, pack_id: UUID | None = None
) -> dict:
    """
    Returns dict with: action_text, action_chips, stage, can_proceed, blocker_message,
    why_it_matters, time_estimate, progress_counters.
    Priority: 1 Hard blockers, 2 Revenue leaks, 3 Sprint day, 4 Optimisation, 5 Check-in.
    """
    packs = list_packs_for_user(db, user_id, include_archived=False)
    if not packs:
        return {
            "action_text": "Create Pack",
            "action_chips": [_chip("Create Campaign Pack", None)],
            "stage": "no_pack",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Get started by creating your first pack.",
            "time_estimate": "2 mins",
            "progress_counters": None,
        }

    pack = packs[0] if pack_id is None else get_pack_for_user(db, pack_id, user_id)
    if not pack:
        return {
            "action_text": "Create Pack",
            "action_chips": [_chip("Create Campaign Pack", None)],
            "stage": "no_pack",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": None,
            "time_estimate": None,
            "progress_counters": None,
        }

    pack_path = f"/packs/{pack.id}"
    overview_day = lambda n: f"{pack_path}?step={n}"

    # --- 0. Inactivity recovery (spec section 10) ---
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.last_activity_at:
        now = dt.now(timezone.utc)
        inactive_hours = (now - user.last_activity_at).total_seconds() / 3600
        if inactive_hours >= 72:
            return {
                "action_text": "Simplify your offer",
                "action_chips": [_chip("Step 1", overview_day(1)), _chip("Step 0", overview_day(0))],
                "stage": "inactivity",
                "can_proceed": True,
                "blocker_message": None,
                "why_it_matters": "You've been away. A simpler offer helps you get back on track.",
                "time_estimate": "5 mins",
                "progress_counters": None,
            }
        if inactive_hours >= 24:
            return {
                "action_text": "Restart in 5 minutes",
                "action_chips": [_chip("Overview", pack_path), _chip("Leads", f"{pack_path}/leads")],
                "stage": "inactivity",
                "can_proceed": True,
                "blocker_message": None,
                "why_it_matters": "Quick win to rebuild momentum.",
                "time_estimate": "5 mins",
                "progress_counters": None,
            }

    # --- 1. Hard blockers (pack gate, day 7, day 8) ---
    active_sprint = get_active_sprint_for_pack(db, pack.id)
    current_day = active_sprint.current_day if active_sprint else 0

    can_pack, pack_msg = can_pass_pack_gate(pack)
    if not can_pack:
        return {
            "action_text": "Complete pack basics",
            "action_chips": [_chip("Step 0 / Offer", overview_day(0)), _chip("Set CTA", overview_day(0))],
            "stage": "blocked",
            "can_proceed": False,
            "blocker_message": pack_msg,
            "why_it_matters": "Offer, audience and CTA are required before you can progress.",
            "time_estimate": "5 mins",
            "progress_counters": None,
        }

    if active_sprint and current_day == 7:
        can_d7, d7_msg = can_pass_day7_gate(db, pack)
        if not can_d7:
            return {
                "action_text": "Unlock Step 7",
                "action_chips": [_chip("Website", f"{pack_path}/website"), _chip("Add proof", f"{pack_path}")],
                "stage": "blocked",
                "can_proceed": False,
                "blocker_message": d7_msg,
                "why_it_matters": "You need a published website and at least one proof.",
                "time_estimate": None,
                "progress_counters": None,
            }

    if active_sprint and current_day == 8:
        can_d8, d8_msg = can_pass_day8_gate(db, pack)
        if not can_d8:
            return {
                "action_text": "Lock response rules",
                "action_chips": [_chip("Response rules", overview_day(8))],
                "stage": "blocked",
                "can_proceed": False,
                "blocker_message": d8_msg,
                "why_it_matters": "Locking rules keeps your responses consistent and saves time.",
            "time_estimate": "10 mins",
            "progress_counters": None,
        }

    # --- 2. Revenue leaks (overdue follow-ups) ---
    overdue = get_overdue_tasks(db, pack.id)
    if overdue:
        return {
            "action_text": f"Follow up with {len(overdue)} lead(s)",
            "action_chips": [_chip("Follow-up queue", overview_day(9)), _chip("Leads", f"{pack_path}/leads")],
            "stage": "revenue_leak",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Overdue follow-ups cost you deals. Clear the queue to keep pipeline moving.",
            "time_estimate": "15 mins",
            "progress_counters": {"overdue": str(len(overdue))},
        }

    # --- 3. Today's sprint requirements ---
    if active_sprint and active_sprint.current_day <= 14:
        sprint = active_sprint
        day_num = sprint.current_day
        card = get_day_card(db, sprint.id, day_num)
        sprint_path = pack_path
        day_path = overview_day(day_num)

        # Day 14: check-in state
        if day_num == 14 and card and not card.completed_at:
            return {
                "action_text": "Complete weekly check-in",
                "action_chips": [_chip("Step 14 check-in", day_path), _chip("Overview", sprint_path)],
                "stage": "checkin",
                "can_proceed": True,
                "blocker_message": None,
                "why_it_matters": "Wrap up this sprint and start Sprint 2.",
                "time_estimate": "5 mins",
                "progress_counters": None,
            }

        day_href = day_path
        chips = [_chip(f"Step {day_num}", day_href), _chip("Overview", sprint_path)]
        return {
            "action_text": f"Step {day_num}: work on today's tasks",
            "action_chips": chips,
            "stage": "sprint",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Staying on the current step keeps momentum.",
            "time_estimate": "15–30 mins",
            "progress_counters": None,
        }

    # --- 4. Lead/proposal/invoice (revenue actions) ---
    leads = list_leads_for_pack(db, pack.id)
    new_leads = [l for l in leads if l.status == LEAD_STATUS_NEW]
    proposals = list_proposals_for_pack(db, pack.id)
    invoices = list_invoices_for_pack(db, pack.id)
    has_proposal_pending = any(p.status in ("sent", "opened") for p in proposals)
    has_invoice_pending = any(i.status in ("sent", "overdue") for i in invoices)

    if new_leads:
        return {
            "action_text": "Contact new lead(s)",
            "action_chips": [_chip("Leads", f"{pack_path}/leads"), _chip("Follow-up", overview_day(9))],
            "stage": "leads",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "New leads go cold fast. Contact them first.",
            "time_estimate": "5 mins",
            "progress_counters": {"new_leads": str(len(new_leads))},
        }
    if has_proposal_pending:
        return {
            "action_text": "Proposal pending",
            "action_chips": [_chip("Proposals", f"{pack_path}/proposal"), _chip("Leads", f"{pack_path}/leads")],
            "stage": "leads",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Follow up on sent proposals to close deals.",
            "time_estimate": "5 mins",
            "progress_counters": None,
        }
    if has_invoice_pending:
        return {
            "action_text": "Invoice pending",
            "action_chips": [_chip("Invoices", f"{pack_path}/invoice"), _chip("Leads", f"{pack_path}/leads")],
            "stage": "leads",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Get paid by following up on outstanding invoices.",
            "time_estimate": "5 mins",
            "progress_counters": None,
        }

    # --- 5. No pack / no sprint: start ---
    published_site = get_published_for_pack(db, pack.id)
    day_0_done = pack.day_0_completed_at is not None
    has_basics = bool(pack.brand_name and pack.primary_cta and pack.usp_statement)

    if not day_0_done or not has_basics:
        return {
            "action_text": "Complete Step 0 setup",
            "action_chips": [_chip("Step 0", overview_day(0)), _chip("Set CTA & USP", overview_day(0))],
            "stage": "brand_os_done",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Lock brand name, USP and CTA to start your sprint.",
            "time_estimate": "10 mins",
            "progress_counters": None,
        }
    if not published_site:
        return {
            "action_text": "Publish website",
            "action_chips": [_chip("Website", f"{pack_path}/website")],
            "stage": "page_live",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "A live website is required before you can run the full sprint.",
            "time_estimate": "15 mins",
            "progress_counters": None,
        }
    if not active_sprint:
        return {
            "action_text": "Start 14-step sprint",
            "action_chips": [_chip("Start Sprint", pack_path)],
            "stage": "page_live",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Your sprint guides you step by step to offers, assets and revenue.",
            "time_estimate": "1 min",
            "progress_counters": None,
        }

    return {
        "action_text": "Check-in or start next sprint",
        "action_chips": [_chip("Overview", pack_path)],
        "stage": "leads",
        "can_proceed": True,
        "blocker_message": None,
        "why_it_matters": None,
        "time_estimate": None,
        "progress_counters": None,
    }
