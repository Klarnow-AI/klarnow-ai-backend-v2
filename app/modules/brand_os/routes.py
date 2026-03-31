"""Brand OS API routes (read-only + regenerate)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError, map_value_error_to_app_error
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.brand_os.schemas import (
    BrandOSList,
    BrandOSRead,
    BrandOSSuggestRequest,
    BrandOSSuggestResponse,
    BrandOSUpdate,
    brand_os_read_from_orm,
)
from app.modules.brand_os.services import (
    get_active_for_pack,
    get_by_version_and_pack,
    list_versions_for_pack,
    update_active_brand_os,
)
from app.modules.brand_os.tools import regenerate_brand_os, suggest_field_value

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")


@router.get("/projects/{pack_id}/brand-os/active", response_model=BrandOSRead | None)
def get_active_brand_os(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the active Brand OS for a pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    brand_os = get_active_for_pack(db, pack_id)
    return brand_os_read_from_orm(brand_os) if brand_os else None


@router.get("/projects/{pack_id}/brand-os", response_model=BrandOSList)
def list_brand_os_versions(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Brand OS versions for a pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_versions_for_pack(db, pack_id)
    return BrandOSList(
        items=[brand_os_read_from_orm(x) for x in items],
        total=len(items),
    )


@router.get("/projects/{pack_id}/brand-os/version/{version}", response_model=BrandOSRead)
def get_brand_os_by_version(
    pack_id: UUID,
    version: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific Brand OS version by version label (e.g. A, B)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    brand_os = get_by_version_and_pack(db, pack_id, version)
    if not brand_os:
        raise NotFoundError("Brand OS version not found")
    return brand_os_read_from_orm(brand_os)


@router.post(
    "/projects/{pack_id}/brand-os/suggest",
    response_model=BrandOSSuggestResponse,
)
def suggest_brand_os_field(
    pack_id: UUID,
    body: BrandOSSuggestRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest a value for a Brand OS strategy field using AI and the active Brand OS as context."""
    _ensure_pack_access(db, pack_id, current_user.id)
    suggestion = suggest_field_value(
        db,
        pack_id,
        field=body.field,
        current_value=body.current_value,
    )
    return BrandOSSuggestResponse(suggestion=suggestion)


@router.patch("/projects/{pack_id}/brand-os/active", response_model=BrandOSRead)
def update_active_brand_os_route(
    pack_id: UUID,
    body: BrandOSUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the active Brand OS for the pack (merge foundation and/or brand_strategy)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    updated = update_active_brand_os(
        db,
        pack_id,
        foundation=body.foundation,
        brand_strategy=body.brand_strategy,
    )
    if not updated:
        raise NotFoundError("No active Brand OS found for this pack")
    return brand_os_read_from_orm(updated)


@router.post(
    "/projects/{pack_id}/brand-os/{brand_os_id}/regenerate",
    response_model=BrandOSRead,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_brand_os_route(
    pack_id: UUID,
    brand_os_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Version B from the given Brand OS (never overwrite)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        new_brand_os = regenerate_brand_os(db, pack_id, brand_os_id)
        return brand_os_read_from_orm(new_brand_os)
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
