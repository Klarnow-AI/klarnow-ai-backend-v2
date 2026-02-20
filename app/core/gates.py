"""Stage gates: enforce MVP flow. Raise GateBlockedError when prerequisite not met."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import GateBlockedError
from app.modules.packs.models import Pack


def can_generate_conversion_page(db: Session, pack: Pack) -> None:
    """Gate: Brand OS and Campaign (with CTA) must exist before generating conversion page."""
    if not pack.active_brand_os_id:
        raise GateBlockedError(
            "You need a Brand OS before building your conversion page. Complete Core (generate Brand OS) first."
        )
    if not pack.active_campaign_id:
        raise GateBlockedError(
            "You need a Campaign with a primary CTA before building your conversion page. Set up your offer and CTA first."
        )
    from app.modules.campaign.services import get_active_for_pack
    campaign = get_active_for_pack(db, pack.id)
    if not campaign or not campaign.primary_cta:
        raise GateBlockedError(
            "Your campaign must have a primary CTA before generating the conversion page."
        )


def can_generate_sprint(db: Session, pack: Pack) -> None:
    """Gate: Conversion page must be published before starting the 7-day sprint."""
    from app.modules.conversion_page.services import get_published
    if get_published(db, pack.id) is None:
        raise GateBlockedError(
            "Publish your conversion page before starting the 7-Day Sprint. The page must be live and CTA working."
        )


def can_generate_assets(db: Session, pack: Pack) -> None:
    """Gate: An active 14-day sprint must exist before generating ads/posters."""
    from app.modules.sprint.services import get_active_sprint_for_pack
    if get_active_sprint_for_pack(db, pack.id) is None:
        raise GateBlockedError(
            "Start your 14-day sprint before generating ads or posters. Create the sprint first."
        )


def can_create_proposal(db: Session, pack: Pack) -> None:
    """Gate: At least one qualified lead is required before creating a proposal."""
    from app.modules.clients.services import count_qualified_leads_for_pack
    if count_qualified_leads_for_pack(db, pack.id) < 1:
        raise GateBlockedError(
            "You need at least one qualified lead before creating a proposal. Add and qualify a lead first."
        )


def can_create_invoice(db: Session, pack: Pack) -> None:
    """Gate: Invoice only created from an accepted proposal (MVP rule)."""
    from app.modules.revenue.services import list_proposals_for_pack
    proposals = list_proposals_for_pack(db, pack.id)
    has_accepted = any(p.status == "accepted" for p in proposals)
    if not has_accepted:
        raise GateBlockedError(
            "Create an invoice only after a proposal has been accepted. Get a proposal accepted first."
        )


def can_pass_paywall_gate(db: Session, user_id: UUID, current_day: int) -> tuple[bool, str]:
    """Paywall gate: Free users blocked after Day 4."""
    from app.modules.subscription.services import get_user_subscription
    from app.modules.subscription.models import PLAN_FREE
    
    subscription = get_user_subscription(db, user_id)
    if subscription.plan == PLAN_FREE and current_day > 4:
        return False, "Upgrade to Standard to continue past Day 4"
    return True, ""


def can_pass_pack_gate(pack: Pack) -> tuple[bool, str]:
    """Pack prerequisites gate: Require offer, audience, CTA."""
    if not pack.offer_one_liner:
        return False, "Complete your offer first"
    if not pack.target_audience:
        return False, "Define your target audience"
    if not pack.primary_cta:
        return False, "Set your primary call-to-action"
    return True, ""


def can_pass_day7_gate(db: Session, pack: Pack) -> tuple[bool, str]:
    """Day 7 gate: Require lead filter, proof, destination confirmed. Auto-generate proof if none."""
    from app.modules.conversion_page.services import get_published
    from app.modules.proof_vault.models import Proof
    from app.modules.proof_vault.services import ensure_proof_exists
    
    conversion_page = get_published(db, pack.id)
    
    if not conversion_page:
        return False, "Publish your conversion destination first"
    
    if not conversion_page.lead_filter_type:
        return False, "Add a lead filter to your conversion page"
    
    proof_count = db.query(Proof).filter(Proof.pack_id == pack.id).count()
    if proof_count == 0:
        ensure_proof_exists(db, pack.id, "process")
        proof_count = db.query(Proof).filter(Proof.pack_id == pack.id).count()
    if proof_count == 0:
        return False, "Add at least one proof asset"
    
    return True, ""


def can_pass_day8_gate(db: Session, pack: Pack) -> tuple[bool, str]:
    """Day 8 gate: Require response rules locked."""
    from app.modules.response_rules.services import are_rules_locked
    
    if not are_rules_locked(db, pack.id):
        return False, "Lock your response rules before proceeding"
    
    return True, ""


def can_complete_day(db: Session, day_card, day_number: int, pack: Pack) -> tuple[bool, str]:
    """
    Daily completion gate (requires all):
    - Output shipped
    - Outreach target met
    - Follow-up target met
    - Proof logged
    
    (Only applies to Days 4-13)
    
    IMPORTANT: These are requirements PER SPRINT DAY, not per calendar day.
    Each DayCard tracks its own completion requirements. Users can complete
    multiple sprint days in one calendar sitting if they meet each day's requirements.
    """
    from app.modules.sprint.outreach_targets import get_daily_outreach_target, get_daily_followup_target
    
    if day_number < 4 or day_number > 13:
        return True, ""  # No daily gate for Days 0-3, 14
    
    if not day_card.output_shipped:
        return False, "Ship today's output first"
    
    outreach_target = get_daily_outreach_target(pack.business_type or "product")
    if day_card.outreach_count < outreach_target:
        return False, f"Complete {outreach_target} outreach activities ({day_card.outreach_count}/{outreach_target})"
    
    followup_target = get_daily_followup_target(pack.business_type or "product")
    if day_card.followup_count < followup_target:
        return False, f"Complete {followup_target} follow-ups ({day_card.followup_count}/{followup_target})"
    
    if not day_card.proof_logged:
        return False, "Log proof for today"
    
    return True, ""

