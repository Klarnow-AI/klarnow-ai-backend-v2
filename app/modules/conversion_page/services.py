"""Conversion page service: get draft/published, list versions, update, publish with governance."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.governance import (
    validate_conversion_page_copy,
    validate_conversion_page_cta,
)
from app.core.logging import log_service_action
from app.modules.campaign.services import get_active_for_pack
from app.modules.conversion_page.models import ConversionPage


@log_service_action()
def get_draft(db: Session, pack_id: UUID) -> ConversionPage | None:
    """Latest conversion page with published_at NULL."""
    return (
        db.query(ConversionPage)
        .filter(ConversionPage.pack_id == pack_id, ConversionPage.published_at.is_(None))
        .order_by(ConversionPage.created_at.desc())
        .first()
    )


@log_service_action()
def get_published(db: Session, pack_id: UUID) -> ConversionPage | None:
    return (
        db.query(ConversionPage)
        .filter(ConversionPage.pack_id == pack_id, ConversionPage.published_at.isnot(None))
        .order_by(ConversionPage.published_at.desc())
        .first()
    )


@log_service_action()
def list_versions(db: Session, pack_id: UUID) -> list[ConversionPage]:
    return (
        db.query(ConversionPage)
        .filter(ConversionPage.pack_id == pack_id)
        .order_by(ConversionPage.created_at.desc())
        .all()
    )


@log_service_action()
def get_by_version(db: Session, pack_id: UUID, version: str) -> ConversionPage | None:
    return (
        db.query(ConversionPage)
        .filter(ConversionPage.pack_id == pack_id, ConversionPage.version == version)
        .first()
    )


@log_service_action()
def update_draft(
    db: Session,
    page: ConversionPage,
    structure: dict | None = None,
    seo_metadata: dict | None = None,
    lead_filter_type: str | None = None,
    lead_filter_value: str | None = None,
) -> ConversionPage:
    if structure is not None:
        page.structure = structure
    if seo_metadata is not None:
        page.seo_metadata = seo_metadata
    if lead_filter_type is not None:
        page.lead_filter_type = lead_filter_type
    if lead_filter_value is not None:
        page.lead_filter_value = lead_filter_value
    db.commit()
    db.refresh(page)
    return page


@log_service_action()
def publish(
    db: Session,
    page: ConversionPage,
    live_url: str,
    pack_id: UUID,
) -> ConversionPage:
    campaign = get_active_for_pack(db, pack_id)
    if not campaign or not campaign.primary_cta:
        raise ValueError("Campaign must have a primary CTA before publishing")
    validate_conversion_page_cta(page.structure, campaign.primary_cta)
    validate_conversion_page_copy(page.structure)
    from datetime import datetime, timezone
    page.published_at = datetime.now(timezone.utc)
    page.live_url = live_url
    db.query(ConversionPage).filter(
        ConversionPage.pack_id == pack_id,
        ConversionPage.id != page.id,
        ConversionPage.published_at.isnot(None),
    ).update({"published_at": None})
    db.commit()
    db.refresh(page)
    return page
