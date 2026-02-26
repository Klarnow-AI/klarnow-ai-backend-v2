"""Pack tools for Day 0-3 conversational flow."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack


UPDATE_PACK_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "brand_name": {"type": "string", "description": "Brand name (Day 0)"},
        "primary_cta": {"type": "string", "description": "Primary call-to-action (Day 0)"},
        "usp_statement": {"type": "string", "description": "USP statement (Day 0)"},
        "usp_category": {"type": "string", "description": "USP category (Day 0)"},
        "usp_proof": {"type": "string", "description": "USP proof (Day 0)"},
        "proof_text": {"type": "string", "description": "Proof text (Day 0)"},
        "offer_one_liner": {"type": "string", "description": "One-line offer (Day 1)"},
        "target_audience": {"type": "string", "description": "Target audience (Day 2)"},
        "primary_pain": {"type": "string", "description": "Primary pain point (Day 2)"},
        "primary_outcome": {"type": "string", "description": "Primary outcome (Day 2)"},
        "hero_angle": {"type": "string", "description": "Hero angle (Day 3)"},
    },
    "required": ["pack_id"],
}


def update_pack(
    db: Session,
    pack_id: UUID,
    *,
    brand_name: str | None = None,
    primary_cta: str | None = None,
    usp_statement: str | None = None,
    usp_category: str | None = None,
    usp_proof: str | None = None,
    proof_text: str | None = None,
    offer_one_liner: str | None = None,
    target_audience: str | None = None,
    primary_pain: str | None = None,
    primary_outcome: str | None = None,
    hero_angle: str | None = None,
    **kwargs: object,
) -> dict:
    """
    Update pack fields (Day 0-3 conversational flow).
    Extracts from conversation and saves. Sets day_0_completed_at when brand_name + primary_cta + usp_statement are set.
    """
    from datetime import datetime, timezone

    if isinstance(pack_id, str):
        pack_id = UUID(pack_id)
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError("Pack not found")

    updates: dict = {}
    if brand_name is not None:
        pack.brand_name = (brand_name or "").strip() or None
        updates["brand_name"] = pack.brand_name
    if primary_cta is not None:
        pack.primary_cta = (primary_cta or "").strip() or None
        updates["primary_cta"] = pack.primary_cta
    if usp_statement is not None:
        pack.usp_statement = (usp_statement or "").strip() or None
        updates["usp_statement"] = pack.usp_statement
    if usp_category is not None:
        pack.usp_category = (usp_category or "").strip() or None
    if usp_proof is not None:
        pack.usp_proof = (usp_proof or "").strip() or None
    if proof_text is not None:
        pack.proof_text = (proof_text or "").strip() or None
    if offer_one_liner is not None:
        pack.offer_one_liner = (offer_one_liner or "").strip() or None
        updates["offer_one_liner"] = pack.offer_one_liner
    if target_audience is not None:
        pack.target_audience = (target_audience or "").strip() or None
        updates["target_audience"] = pack.target_audience
    if primary_pain is not None:
        pack.primary_pain = (primary_pain or "").strip() or None
        updates["primary_pain"] = pack.primary_pain
    if primary_outcome is not None:
        pack.primary_outcome = (primary_outcome or "").strip() or None
        updates["primary_outcome"] = pack.primary_outcome
    if hero_angle is not None:
        pack.hero_angle = (hero_angle or "").strip() or None
        updates["hero_angle"] = pack.hero_angle

    if pack.primary_cta and not pack.active_campaign_id:
        from app.modules.campaign.services import get_active_for_pack as get_active_campaign
        from app.core.governance import validate_one_cta
        from app.modules.campaign.models import Campaign

        cta = (pack.primary_cta or "").strip()
        if cta:
            validate_one_cta(cta)
            active_campaign = get_active_campaign(db, pack_id)
            if active_campaign:
                pack.active_campaign_id = active_campaign.id
            else:
                campaign = Campaign(
                    pack_id=pack_id,
                    version="A",
                    primary_cta=cta,
                    goal=None,
                    angles=[],
                    is_active=True,
                )
                db.add(campaign)
                db.flush()
                pack.active_campaign_id = campaign.id

    if pack.day_0_completed_at is None:
        bn = (pack.brand_name or "").strip()
        cta = (pack.primary_cta or "").strip()
        usp = (pack.usp_statement or "").strip()
        if bn and cta and usp:
            pack.day_0_completed_at = datetime.now(timezone.utc)
            updates["day_0_completed"] = True

    db.commit()
    db.refresh(pack)
    return {"updated": True, "fields": list(updates.keys())}
