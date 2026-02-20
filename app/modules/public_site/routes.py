"""Public site routes (no auth): published conversion page + lead capture."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.db.session import get_db
from app.modules.conversion_page.schemas import ConversionPagePreview
from app.modules.campaign.services import get_active_for_pack
from app.modules.public_site.schemas import PublicLeadCaptureBody, PublicLeadCaptureResponse
from app.modules.public_site.services import (
    create_public_lead_for_pack,
    get_published_conversion_page_for_pack,
)

router = APIRouter()


@router.get("/packs/{pack_id}/conversion-page", response_model=ConversionPagePreview)
def get_public_published_conversion_page(pack_id: UUID, db=Depends(get_db)):
    """Fetch published conversion page payload for public rendering."""
    page = get_published_conversion_page_for_pack(db, pack_id)
    campaign = get_active_for_pack(db, pack_id)
    return ConversionPagePreview(
        structure=page.structure,
        seo_metadata=page.seo_metadata,
        version=page.version,
        primary_cta=campaign.primary_cta if campaign else None,
    )


@router.post(
    "/packs/{pack_id}/leads",
    response_model=PublicLeadCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_public_lead(pack_id: UUID, body: PublicLeadCaptureBody, db=Depends(get_db)):
    """Capture a lead from a published conversion page (no auth)."""
    lead = create_public_lead_for_pack(
        db,
        pack_id=pack_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        summary=body.summary,
        website=body.website,
    )
    return PublicLeadCaptureResponse(lead_id=str(lead.id))

