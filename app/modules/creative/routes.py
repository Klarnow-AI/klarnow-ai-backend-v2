"""Creative assets API: list, get, regenerate (Version B)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from app.modules.creative.generation import (
    create_poster_generation_stream,
    normalize_reference_images,
)
from app.modules.creative.serializers import serialize_asset
from app.modules.creative.schemas import (
    AssetCreate,
    AssetList,
    AssetRead,
    PosterGenerateRequest,
)
from app.modules.creative.services import (
    create_asset,
    delete_asset as delete_asset_service,
    get_asset_for_pack_user,
    list_assets_for_pack,
    regenerate_asset,
)
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.shared.services.generation_context import load_generation_brand_context

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


def _serialize_asset(asset) -> AssetRead:
    return serialize_asset(asset)


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
        template_id=body.template_id,
        chat_messages=body.chat_messages,
    )
    return _serialize_asset(asset)


@router.get("/assets", response_model=AssetList)
def list_assets(
    pack_id: UUID = Query(..., description="Pack id"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets for a pack. Pack must belong to current user."""
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_assets_for_pack(db, pack_id)
    return AssetList(items=[_serialize_asset(a) for a in items], total=len(items))


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
    return _serialize_asset(asset)


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
    new_asset = regenerate_asset(db, asset)
    return _serialize_asset(new_asset)


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
    delete_asset_service(db, asset)


@router.post("/generate")
async def generate_posters(
    body: PosterGenerateRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate poster TSX output for the authenticated user's pack."""
    if not body.messages:
        raise BadRequestError("Missing messages")

    pack = get_pack_for_user(db, body.pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    brand_context = load_generation_brand_context(db, body.pack_id, pack=pack)

    try:
        reference_images = normalize_reference_images(
            [image.model_dump() for image in body.reference_images]
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    existing_files = [file.model_dump() for file in body.existing_files]

    try:
        stream = await create_poster_generation_stream(
            messages=body.messages,
            pack=pack,
            brand_context=brand_context,
            reference_images=reference_images,
            generation_mode=body.generation_mode,
            edit_variant=body.edit_variant,
            slot_id=body.slot_id,
            existing_files=existing_files,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        message = str(exc)
        if "not configured" in message.lower():
            raise ServiceUnavailableError(message) from exc
        raise ServiceUnavailableError(
            "We're having trouble generating right now. Please try again in a few moments."
        ) from exc

    return StreamingResponse(
        stream,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
