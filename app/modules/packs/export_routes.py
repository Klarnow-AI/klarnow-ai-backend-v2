"""Export and download routes (Phase 3).

Provides endpoints for:
- GET  /{pack_id}/download-all     - Download complete brand package as ZIP
- GET  /{pack_id}/brand-guide      - Download brand guide PDF
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.modules.packs.models import Pack, User
from app.modules.packs.services import get_pack_for_user

logger = get_logger("klarnow.routes.export")
router = APIRouter()


def _get_brand_os_data(db: Session, pack_id: UUID) -> dict | None:
    """Load raw Brand OS data for a pack."""
    from app.modules.brand_os.models import BrandOS as BrandOSModel

    brand_os = (
        db.query(BrandOSModel)
        .filter(BrandOSModel.pack_id == pack_id, BrandOSModel.is_active.is_(True))
        .first()
    )
    if not brand_os:
        return None
    result = {}
    if brand_os.foundation:
        result["foundation"] = brand_os.foundation
    if brand_os.brand_strategy:
        result["brand_strategy"] = brand_os.brand_strategy
    return result


@router.get("/{pack_id}/download-all")
def download_all_assets(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the complete brand package as a ZIP archive."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    brand_os_data = _get_brand_os_data(db, pack_id)

    # Brand guide PDF generation removed — was in deleted brand_guide module
    brand_guide_pdf = None

    from app.modules.packs.export import generate_export_zip
    buf = generate_export_zip(
        db=db,
        pack=pack,
        pack_id=pack_id,
        brand_os_data=brand_os_data,
        brand_guide_pdf=brand_guide_pdf,
    )

    brand_slug = (pack.brand_name or pack.name or "brand").replace(" ", "_").lower()

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{brand_slug}_brand_package.zip"'
        },
    )


@router.get("/{pack_id}/brand-guide")
def download_brand_guide(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the brand guide as a PDF."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    brand_os_data = _get_brand_os_data(db, pack_id)

    # Brand guide PDF generation removed — feature will be rebuilt in export jobs
    raise NotFoundError("Brand guide PDF export is temporarily unavailable")
