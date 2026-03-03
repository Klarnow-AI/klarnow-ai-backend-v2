"""Stage gates: enforce MVP flow. Raise GateBlockedError when prerequisite not met."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import GateBlockedError
from app.modules.packs.models import Pack


def can_generate_website(db: Session, pack: Pack) -> None:
    """Gate: Brand OS and Campaign (with CTA) must exist before building website."""
    if not pack.active_brand_os_id:
        raise GateBlockedError(
            "You need a Brand OS before building your website. Complete Core (generate Brand OS) first."
        )
    if not pack.active_campaign_id:
        raise GateBlockedError(
            "You need a Campaign with a primary CTA before building your website. Set up your offer and CTA first."
        )
    from app.modules.campaign.services import get_active_for_pack
    campaign = get_active_for_pack(db, pack.id)
    if not campaign or not campaign.primary_cta:
        raise GateBlockedError(
            "Your campaign must have a primary CTA before building the website."
        )


def can_generate_sprint(db: Session, pack: Pack) -> None:
    """Gate: Website must be published before starting the 7-day sprint."""
    from app.modules.builder.services import get_published_for_pack
    if get_published_for_pack(db, pack.id) is None:
        raise GateBlockedError(
            "Publish your website before starting the 7-Day Sprint. The site must be live and CTA working."
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
    """Day 7 gate: Require published website and proof. Auto-generate proof if none."""
    from app.modules.builder.services import get_published_for_pack
    from app.modules.proof_vault.models import Proof
    from app.modules.proof_vault.services import ensure_proof_exists
    
    site = get_published_for_pack(db, pack.id)
    
    if not site:
        return False, "Publish your website first"
    
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
    Daily completion gate (Days 4-13) currently has no extra requirements.
    Day unlock logic and Day 7/8 specific gates remain enforced elsewhere.
    """
    return True, ""
