"""Creative assets API: list, get, regenerate (Version B)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.modules.image_context.jobs import start_image_context_worker
from app.modules.image_context.services import (
    JOB_OPERATION_DELETE,
    JOB_OPERATION_UPSERT,
    SOURCE_TYPE_ASSET,
    enqueue_image_context_job,
)
from app.modules.creative.schemas import AssetCreate, AssetList, AssetRead
from app.modules.creative.services import (
    create_asset,
    delete_asset as delete_asset_service,
    get_asset_for_pack_user,
    list_assets_for_pack,
    regenerate_asset,
)
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user

router = APIRouter()
logger = get_logger("klarnow.image_context.hooks")
settings = get_settings()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


@router.post("/assets", response_model=AssetRead)
def create_asset_route(
    body: AssetCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a poster or flyer asset with source code. Pack must belong to current user."""
    _ensure_pack_access(db, body.pack_id, current_user.id)
    asset = create_asset(
        db,
        body.pack_id,
        body.type,
        body.name,
        body.source_code,
        current_user.id,
        template_id=body.template_id,
        chat_messages=body.chat_messages,
    )
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=asset.pack_id,
                source_type=SOURCE_TYPE_ASSET,
                source_id=asset.id,
                operation=JOB_OPERATION_UPSERT,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=asset_create | asset_id=%s | error=%s",
                asset.id,
                e,
            )
    return AssetRead.model_validate(asset)


@router.get("/assets", response_model=AssetList)
def list_assets(
    pack_id: UUID = Query(..., description="Pack id"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets for a pack. Pack must belong to current user."""
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_assets_for_pack(db, pack_id)
    return AssetList(items=[AssetRead.model_validate(a) for a in items], total=len(items))


@router.get("/assets/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single asset by id. Asset's pack must belong to current user."""
    asset = get_asset_for_pack_user(db, asset_id, current_user.id)
    if not asset:
        raise NotFoundError("Asset not found")
    return AssetRead.model_validate(asset)


@router.post("/assets/{asset_id}/regenerate", response_model=AssetRead)
def regenerate_asset_route(
    asset_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Version B of this asset (new asset). Never overwrites."""
    asset = get_asset_for_pack_user(db, asset_id, current_user.id)
    if not asset:
        raise NotFoundError("Asset not found")
    new_asset = regenerate_asset(db, asset, current_user.id)
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=new_asset.pack_id,
                source_type=SOURCE_TYPE_ASSET,
                source_id=new_asset.id,
                operation=JOB_OPERATION_UPSERT,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=asset_regenerate | asset_id=%s | error=%s",
                new_asset.id,
                e,
            )
    return AssetRead.model_validate(new_asset)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset_route(
    asset_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a poster/flyer asset. Pack must belong to current user."""
    asset = get_asset_for_pack_user(db, asset_id, current_user.id)
    if not asset:
        raise NotFoundError("Asset not found")
    pack_id = asset.pack_id
    delete_asset_service(db, asset_id, current_user.id)
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=pack_id,
                source_type=SOURCE_TYPE_ASSET,
                source_id=asset_id,
                operation=JOB_OPERATION_DELETE,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=asset_delete | asset_id=%s | error=%s",
                asset_id,
                e,
            )
