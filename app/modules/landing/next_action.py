"""Next Action engine: one next action. Priority: blockers, revenue leaks, sprint day, optimisation, check-in."""

from datetime import timedelta, timezone
from datetime import datetime as dt
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.gates import (
    can_pass_day7_gate,
    can_pass_day8_gate,
    can_pass_pack_gate,
    can_pass_paywall_gate,
    can_complete_day,
)
from app.modules.clients.models import LEAD_STATUS_NEW
from app.modules.clients.services import list_leads_for_pack
from app.modules.conversion_page.services import get_published
from app.modules.landing.schemas import NextActionChip
from app.modules.packs.models import Pack
from app.modules.packs.services import get_pack_for_user, list_packs_for_user
from app.modules.revenue.services import list_proposals_for_pack, list_invoices_for_pack
from app.modules.sprint.services import (
    get_active_sprint_for_pack,
    get_day_card,
    get_sprint_day_detail,
)
from app.modules.sprint.outreach_targets import get_daily_outreach_target, get_daily_followup_target
from app.modules.tasks.services import get_overdue_tasks
from app.modules.subscription.services import check_credits
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
    chat_day = lambda n: f"/chat?pack={pack.id}&day={n}"

    # --- 0. Inactivity recovery (spec section 10) ---
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.last_activity_at:
        now = dt.now(timezone.utc)
        inactive_hours = (now - user.last_activity_at).total_seconds() / 3600
        if inactive_hours >= 72:
            return {
                "action_text": "Simplify your offer",
                "action_chips": [_chip("Day 1", chat_day(1)), _chip("Day 0", chat_day(0))],
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
                "action_chips": [_chip("Plan tracker", f"{pack_path}/plan-tracker"), _chip("Leads", f"{pack_path}/leads")],
                "stage": "inactivity",
                "can_proceed": True,
                "blocker_message": None,
                "why_it_matters": "Quick win to rebuild momentum.",
                "time_estimate": "5 mins",
                "progress_counters": None,
            }

    # --- 1. Hard blockers (paywall, pack gate, day 7, day 8) ---
    active_sprint = get_active_sprint_for_pack(db, pack.id)
    current_day = active_sprint.current_day if active_sprint else 0

    can_paywall, paywall_msg = can_pass_paywall_gate(db, user_id, current_day)
    if not can_paywall:
        return {
            "action_text": "Upgrade to continue",
            "action_chips": [_chip("Upgrade", f"{pack_path}")],
            "stage": "blocked",
            "can_proceed": False,
            "blocker_message": paywall_msg,
            "why_it_matters": "Free plan includes Days 0–4. Unlock the full sprint with Standard or Premium.",
            "time_estimate": None,
            "progress_counters": None,
        }

    can_pack, pack_msg = can_pass_pack_gate(pack)
    if not can_pack:
        return {
            "action_text": "Complete pack basics",
            "action_chips": [_chip("Day 0 / Offer", chat_day(0)), _chip("Set CTA", chat_day(0))],
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
                "action_text": "Unlock Day 7",
                "action_chips": [_chip("Conversion page", f"{pack_path}/conversion-page"), _chip("Add proof", f"{pack_path}")],
                "stage": "blocked",
                "can_proceed": False,
                "blocker_message": d7_msg,
                "why_it_matters": "You need a lead filter, at least one proof, and a published destination.",
                "time_estimate": None,
                "progress_counters": None,
            }

    if active_sprint and current_day == 8:
        can_d8, d8_msg = can_pass_day8_gate(db, pack)
        if not can_d8:
            return {
                "action_text": "Lock response rules",
                "action_chips": [_chip("Response rules", f"{pack_path}/plan-tracker/day/8")],
                "stage": "blocked",
                "can_proceed": False,
                "blocker_message": d8_msg,
                "why_it_matters": "Locking rules keeps your responses consistent and saves time.",
                "time_estimate": "10 mins",
                "progress_counters": None,
            }

    # --- 2. Revenue leaks (overdue follow-ups) ---
    credits = check_credits(db, user_id)
    overdue = get_overdue_tasks(db, pack.id)
    if overdue:
        return {
            "action_text": f"Follow up with {len(overdue)} lead(s)",
            "action_chips": [_chip("Follow-up queue", f"{pack_path}/plan-tracker/day/9"), _chip("Leads", f"{pack_path}/leads")],
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
        sprint_path = f"{pack_path}/plan-tracker"
        day_path = f"{sprint_path}/day/{day_num}"

        if card and day_num >= 4 and day_num <= 13:
            can_daily, daily_msg = can_complete_day(db, card, day_num, pack)
            outreach_target = get_daily_outreach_target(pack.business_type or "product")
            followup_target = get_daily_followup_target(pack.business_type or "product")
            progress_counters = {
                "outreach": f"{card.outreach_count}/{outreach_target}",
                "followups": f"{card.followup_count}/{followup_target}",
                "output": "done" if card.output_shipped else "pending",
                "proof": "done" if card.proof_logged else "pending",
            }
            if not card.output_shipped:
                return {
                    "action_text": "Ship today's output",
                    "action_chips": [_chip(f"Day {day_num}", day_path), _chip("Sprint", sprint_path)],
                    "stage": "sprint_day",
                    "can_proceed": True,
                    "blocker_message": None,
                    "why_it_matters": "Completing the day's deliverable is the first step to finishing the day.",
                    "time_estimate": "20 mins",
                    "progress_counters": progress_counters,
                }
            if card.outreach_count < outreach_target:
                return {
                    "action_text": f"Complete outreach ({card.outreach_count}/{outreach_target})",
                    "action_chips": [_chip("Log outreach", day_path), _chip("Sprint", sprint_path)],
                    "stage": "sprint_day",
                    "can_proceed": True,
                    "blocker_message": None,
                    "why_it_matters": "Daily outreach keeps your pipeline full and enables day completion.",
                    "time_estimate": "20 mins",
                    "progress_counters": progress_counters,
                }
            if card.followup_count < followup_target:
                return {
                    "action_text": f"Complete follow-ups ({card.followup_count}/{followup_target})",
                    "action_chips": [_chip("Follow-up queue", f"{pack_path}/plan-tracker/day/9"), _chip("Day", day_path)],
                    "stage": "sprint_day",
                    "can_proceed": True,
                    "blocker_message": None,
                    "why_it_matters": "Follow-ups move leads forward and are required to complete the day.",
                    "time_estimate": "15 mins",
                    "progress_counters": progress_counters,
                }
            if not card.proof_logged:
                return {
                    "action_text": "Log proof for today",
                    "action_chips": [_chip("Log proof", day_path), _chip("Sprint", sprint_path)],
                    "stage": "sprint_day",
                    "can_proceed": True,
                    "blocker_message": None,
                    "why_it_matters": "Logging proof completes the daily gate so you can finish the day.",
                    "time_estimate": "2 mins",
                    "progress_counters": progress_counters,
                }
            if not can_daily and daily_msg:
                return {
                    "action_text": "Complete Day " + str(day_num),
                    "action_chips": [_chip("Day " + str(day_num), day_path)],
                    "stage": "sprint_day",
                    "can_proceed": False,
                    "blocker_message": daily_msg,
                    "why_it_matters": None,
                    "time_estimate": None,
                    "progress_counters": progress_counters,
                }

            # Day complete: optimisation actions (never replace revenue)
            if can_daily:
                chips = [_chip("Mark day complete", day_path), _chip("Improve hook", chat_day(1)), _chip("Add proof", f"{pack_path}")]
                if credits == 0:
                    chips.append(_chip("Buy credits", "/settings"))
                return {
                    "action_text": "Day complete — improve your offer",
                    "action_chips": chips,
                    "stage": "sprint_day",
                    "can_proceed": True,
                    "blocker_message": None,
                    "why_it_matters": "Polish your hook or add proof before the next day.",
                    "time_estimate": "5 mins",
                    "progress_counters": progress_counters,
                }

        # Day 14: check-in state
        if day_num == 14 and card and not card.completed_at:
            return {
                "action_text": "Complete weekly check-in",
                "action_chips": [_chip("Day 14 check-in", day_path), _chip("Plan tracker", sprint_path)],
                "stage": "checkin",
                "can_proceed": True,
                "blocker_message": None,
                "why_it_matters": "Wrap up this sprint and start Sprint 2.",
                "time_estimate": "5 mins",
                "progress_counters": None,
            }

        # Default: work on current day (Days 0-3 go to chat; 4+ to plan-tracker)
        day_href = chat_day(day_num) if 0 <= day_num <= 3 else day_path
        chips = [_chip(f"Day {day_num}", day_href), _chip("Sprint", sprint_path)]
        if credits == 0 and day_num >= 4:
            chips.append(_chip("Buy credits", "/settings"))
        return {
            "action_text": f"Day {day_num}: work on today's tasks",
            "action_chips": chips,
            "stage": "sprint",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Staying on the sprint day keeps momentum.",
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
            "action_chips": [_chip("Leads", f"{pack_path}/leads"), _chip("Follow-up", f"{pack_path}/plan-tracker/day/9")],
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
    published_page = get_published(db, pack.id)
    day_0_done = pack.day_0_completed_at is not None
    has_basics = bool(pack.brand_name and pack.primary_cta and pack.usp_statement)

    if not day_0_done or not has_basics:
        return {
            "action_text": "Complete Day 0 setup",
            "action_chips": [_chip("Day 0", chat_day(0)), _chip("Set CTA & USP", chat_day(0))],
            "stage": "brand_os_done",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Lock brand name, USP and CTA to start your sprint.",
            "time_estimate": "10 mins",
            "progress_counters": None,
        }
    if not published_page:
        return {
            "action_text": "Publish conversion page",
            "action_chips": [_chip("Conversion page", f"{pack_path}/conversion-page")],
            "stage": "page_live",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "A live page is required before you can run the full sprint.",
            "time_estimate": "15 mins",
            "progress_counters": None,
        }
    if not active_sprint:
        return {
            "action_text": "Start 14-day sprint",
            "action_chips": [_chip("Start Sprint", f"{pack_path}/plan-tracker")],
            "stage": "page_live",
            "can_proceed": True,
            "blocker_message": None,
            "why_it_matters": "Your sprint guides you day by day to offers, assets and revenue.",
            "time_estimate": "1 min",
            "progress_counters": None,
        }

    return {
        "action_text": "Check-in or start next sprint",
        "action_chips": [_chip("Plan tracker", f"{pack_path}/plan-tracker")],
        "stage": "leads",
        "can_proceed": True,
        "blocker_message": None,
        "why_it_matters": None,
        "time_estimate": None,
        "progress_counters": None,
    }
