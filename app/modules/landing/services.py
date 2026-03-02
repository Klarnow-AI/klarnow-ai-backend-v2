"""Landing context service: derive stage from first pack; landing complete creates Pack + Sprint."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.clients.services import count_qualified_leads_for_pack
from app.modules.builder.services import get_published_for_pack
from app.modules.landing.schemas import LandingContext, LandingPack
from app.modules.packs.services import list_packs_for_user, create_pack
from app.modules.sprint.services import get_active_sprint_for_pack


@log_service_action()
def get_landing_context(db: Session, user_id: UUID) -> LandingContext:
    packs = list_packs_for_user(db, user_id, include_archived=False)
    if not packs:
        return LandingContext(pack=None, stage="no_pack")

    pack = packs[0]
    pack_id = pack.id

    # Leads: at least one qualified lead for this pack
    lead_count = count_qualified_leads_for_pack(db, pack_id)
    if lead_count > 0:
        return LandingContext(
            pack=LandingPack(id=str(pack_id), name=pack.name),
            stage="leads",
            lead_count=lead_count,
        )

    # Sprint: 14-day Sprint only
    active_sprint = get_active_sprint_for_pack(db, pack_id)
    if active_sprint is not None:
        return LandingContext(
            pack=LandingPack(id=str(pack_id), name=pack.name),
            stage="sprint",
            sprint_day=active_sprint.current_day,
        )

    # Page live: website published
    if get_published_for_pack(db, pack_id) is not None:
        return LandingContext(
            pack=LandingPack(id=str(pack_id), name=pack.name),
            stage="page_live",
        )

    # Brand OS done (onboarding completed) or default when pack exists
    return LandingContext(
        pack=LandingPack(id=str(pack_id), name=pack.name),
        stage="brand_os_done",
    )


@log_service_action()
def landing_complete(
    db: Session,
    user_id: UUID,
    pack_name: str,
    what_do_you_sell: str,
    who_is_it_for: str,
    where_are_you_based: str,
) -> tuple[UUID, str]:
    """
    Create Pack + Sprint from landing 3 questions + pack name. Returns (pack_id, redirect path).
    """
    pack = create_pack(db, user_id, name=pack_name.strip() or "My Pack")
    answers = {
        "pack_name": pack_name.strip(),
        "what_do_you_sell": what_do_you_sell.strip(),
        "who_is_it_for": who_is_it_for.strip(),
        "where_are_you_based": where_are_you_based.strip(),
    }
    pack.onboarding_answers = {**(pack.onboarding_answers or {}), **answers}
    pack.offer_one_liner = what_do_you_sell.strip() or None
    pack.target_audience = who_is_it_for.strip() or None
    pack.location_city = where_are_you_based.strip() or None
    pack.location_country = where_are_you_based.strip() or None
    db.commit()
    db.refresh(pack)
    # Sprint was already created in create_pack with started_at=pack.created_at
    return pack.id, f"/packs/{pack.id}"
