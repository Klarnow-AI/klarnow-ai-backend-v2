"""Public site services: published conversion page + lead capture."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.modules.clients.services import create_lead
from app.modules.conversion_page.services import get_published
from app.modules.packs.models import Pack


def get_published_conversion_page_for_pack(db: Session, pack_id: UUID):
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise NotFoundError("Pack not found")
    page = get_published(db, pack_id)
    if not page:
        raise NotFoundError("No published conversion page found")
    return page


def create_public_lead_for_pack(
    db: Session,
    pack_id: UUID,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    summary: str | None = None,
    website: str | None = None,
):
    # Basic spam protection
    if website and str(website).strip():
        raise AppError("Invalid form submission", status_code=400)
    if not (email and str(email).strip()) and not (phone and str(phone).strip()):
        raise AppError("Please provide at least an email or phone number", status_code=400)

    # Only allow capture if the pack actually has a published page.
    _ = get_published_conversion_page_for_pack(db, pack_id)

    lead = create_lead(
        db,
        pack_id=pack_id,
        name=name,
        email=email,
        phone=phone,
        summary=summary,
        source="conversion_page",
    )
    return lead

