"""Pack tools for Day 0-3 conversational flow."""

import asyncio
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack
from app.modules.packs.services import merge_onboarding_answers


UPDATE_PACK_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "has_existing_brand": {"type": "string", "description": "Day 0: 'yes' or 'no'"},
        "brand_url": {"type": "string", "description": "Day 0: website URL (triggers extraction when has_existing_brand=yes)"},
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

EXTRACT_BRAND_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "url": {"type": "string", "description": "Website URL to extract brand from"},
    },
    "required": ["pack_id", "url"],
}


def extract_brand_from_url(db: Session, pack_id: UUID | str, *, url: str, **kwargs: object) -> dict:
    """
    Extract brand profile from website URL for existing brand (Day 0).
    Merges extracted data into onboarding_answers and pack fields.
    Call this when user provides a website URL and has_existing_brand is yes.
    """
    import json
    from app.modules.packs.onboarding_services import extract_brand as extract_brand_async

    if isinstance(pack_id, str):
        pack_id = UUID(pack_id)
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError("Pack not found")
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is required")
    result = asyncio.run(extract_brand_async(input_type="url", url=url))
    extracted = {
        "brand_name": result.get("brand_name") or "My Brand",
        "offer_cues": result.get("offer_cues", []),
        "tagline": result.get("tagline"),
        "description": result.get("description"),
        "industry": result.get("industry"),
        "contact_info": result.get("contact_info", {}),
        "social_links": result.get("social_links", []),
        "logo_url": result.get("logo_url"),
        "color_candidates": result.get("color_candidates", []),
        "raw_extract": result.get("raw_extract", {}),
    }
    merge_onboarding_answers(
        db,
        pack,
        {
            "has_existing_brand": "yes",
            "brand_url": url,
            "brand_input_type": "url",
            "extracted_brand": json.dumps(extracted),
        },
    )
    if extracted.get("brand_name"):
        pack.brand_name = extracted["brand_name"].strip()
        db.commit()
        db.refresh(pack)
    return {
        "extracted": True,
        "brand_name": extracted.get("brand_name"),
        "tagline": extracted.get("tagline"),
        "industry": extracted.get("industry"),
        "description": (extracted.get("description") or "")[:500],
    }


def update_pack(
    db: Session,
    pack_id: UUID,
    *,
    has_existing_brand: str | None = None,
    brand_url: str | None = None,
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

    if has_existing_brand is not None:
        merge_onboarding_answers(db, pack, {"has_existing_brand": has_existing_brand})
        updates["has_existing_brand"] = has_existing_brand
    if brand_url is not None:
        url = (brand_url or "").strip()
        oa = pack.onboarding_answers or {}
        is_existing = has_existing_brand == "yes" or oa.get("has_existing_brand") == "yes"
        if url and is_existing:
            extract_result = extract_brand_from_url(db, pack_id, url=url)
            if extract_result.get("brand_name"):
                pack.brand_name = extract_result["brand_name"]
                updates["brand_name"] = pack.brand_name
        else:
            merge_onboarding_answers(db, pack, {"brand_url": url})
        updates["brand_url"] = brand_url

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
