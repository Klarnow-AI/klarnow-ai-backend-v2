"""Conversion page API: draft, published, versions, update, publish, live preview (React), regenerate."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import AppError, NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.campaign.services import get_active_for_pack
from app.modules.conversion_page.models import ConversionPage
from app.modules.conversion_page.schemas import (
    ConversionPageList,
    ConversionPagePreview,
    ConversionPageRead,
    ConversionPageUpdate,
    ConversionPagePublish,
)
from app.modules.conversion_page.services import (
    get_draft,
    get_published,
    get_by_version,
    list_versions,
    update_draft,
    publish,
)
from app.modules.conversion_page.tools import generate_conversion_page

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")


@router.get("/packs/{pack_id}/conversion-page/draft", response_model=ConversionPageRead | None)
def get_conversion_page_draft(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current draft conversion page (unpublished)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    page = get_draft(db, pack_id)
    return ConversionPageRead.model_validate(page) if page else None


@router.get("/packs/{pack_id}/conversion-page/published", response_model=ConversionPageRead | None)
def get_conversion_page_published(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the published conversion page."""
    _ensure_pack_access(db, pack_id, current_user.id)
    page = get_published(db, pack_id)
    return ConversionPageRead.model_validate(page) if page else None


@router.get("/packs/{pack_id}/conversion-page/preview", response_model=ConversionPagePreview)
def get_conversion_page_preview(
    pack_id: UUID,
    version: str | None = Query(None, description="Version (A, B) or omit for draft"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Live preview payload: structure + metadata for React to render. Omit version for draft."""
    _ensure_pack_access(db, pack_id, current_user.id)
    if version:
        page = get_by_version(db, pack_id, version)
    else:
        page = get_draft(db, pack_id) or get_published(db, pack_id)
    if not page:
        raise NotFoundError("No conversion page found")
    campaign = get_active_for_pack(db, pack_id)
    return ConversionPagePreview(
        structure=page.structure,
        seo_metadata=page.seo_metadata,
        version=page.version,
        primary_cta=campaign.primary_cta if campaign else None,
    )


@router.get("/packs/{pack_id}/conversion-page", response_model=ConversionPageList)
def list_conversion_page_versions(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all conversion page versions for the pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_versions(db, pack_id)
    return ConversionPageList(
        items=[ConversionPageRead.model_validate(x) for x in items],
        total=len(items),
    )


@router.get("/packs/{pack_id}/conversion-page/version/{version}", response_model=ConversionPageRead)
def get_conversion_page_by_version(
    pack_id: UUID,
    version: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversion page version."""
    _ensure_pack_access(db, pack_id, current_user.id)
    page = get_by_version(db, pack_id, version)
    if not page:
        raise NotFoundError("Conversion page version not found")
    return ConversionPageRead.model_validate(page)


@router.patch("/packs/{pack_id}/conversion-page/draft", response_model=ConversionPageRead)
def update_conversion_page_draft(
    pack_id: UUID,
    body: ConversionPageUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update draft structure and/or seo_metadata. Governance: no revenue guarantees on copy."""
    _ensure_pack_access(db, pack_id, current_user.id)
    page = get_draft(db, pack_id)
    if not page:
        raise NotFoundError("No draft conversion page; generate one first")
    if body.structure is not None:
        from app.core.governance import validate_conversion_page_copy
        validate_conversion_page_copy(body.structure)
    data = body.model_dump(exclude_unset=True)
    page = update_draft(
        db,
        page,
        structure=data.get("structure"),
        seo_metadata=data.get("seo_metadata"),
        lead_filter_type=data.get("lead_filter_type"),
        lead_filter_value=data.get("lead_filter_value"),
    )
    return ConversionPageRead.model_validate(page)


@router.get("/packs/{pack_id}/conversion-page/version/{version}/export", response_model=ConversionPagePreview)
def export_conversion_page_for_react(
    pack_id: UUID,
    version: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export conversion page as React payload (structure + metadata) for Launch Pack or static build."""
    _ensure_pack_access(db, pack_id, current_user.id)
    page = get_by_version(db, pack_id, version)
    if not page:
        raise NotFoundError("Conversion page version not found")
    campaign = get_active_for_pack(db, pack_id)
    return ConversionPagePreview(
        structure=page.structure,
        seo_metadata=page.seo_metadata,
        version=page.version,
        primary_cta=campaign.primary_cta if campaign else None,
    )


@router.post(
    "/packs/{pack_id}/conversion-page/regenerate",
    response_model=ConversionPageRead,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_conversion_page_route(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Version B conversion page (never overwrite). Requires Brand OS + Campaign with CTA."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        result = generate_conversion_page(db, pack_id)
        page_id = UUID(result["conversion_page_id"])
        page = db.query(ConversionPage).filter(ConversionPage.id == page_id).first()
        if not page:
            raise NotFoundError("Conversion page not found after generate")
        return ConversionPageRead.model_validate(page)
    except ValueError as e:
        raise AppError(str(e), status_code=400)


@router.post("/packs/{pack_id}/conversion-page/publish", response_model=ConversionPageRead)
def publish_conversion_page(
    pack_id: UUID,
    body: ConversionPagePublish,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish draft. Governance: CTA match; no revenue guarantees; proof or waiver required."""
    _ensure_pack_access(db, pack_id, current_user.id)
    from app.core.governance import check_proof_before_launch
    from app.modules.proof_vault.services import count_for_pack
    has_proof = count_for_pack(db, pack_id) > 0
    check_proof_before_launch(str(pack_id), has_proof=has_proof, waiver_confirmed=body.waiver_confirmed)
    page = get_draft(db, pack_id)
    if not page:
        raise NotFoundError("No draft conversion page to publish")
    live_url = body.live_url
    if not live_url:
        from app.core.config import get_settings
        settings = get_settings()
        live_url = f"{settings.frontend_url.rstrip('/')}/p/{pack_id}"
    try:
        page = publish(db, page, live_url, pack_id)
    except ValueError as e:
        raise AppError(str(e), status_code=400)
    return ConversionPageRead.model_validate(page)
