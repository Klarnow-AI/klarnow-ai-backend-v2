"""API routes for image context retrieval and indexing."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.db.session import get_db
from app.core.errors import AppError, NotFoundError
from app.core.storage import get_presigned_url, upload_file
from app.modules.image_context.jobs import start_image_context_worker
from app.modules.image_context.schemas import (
    GlobalImageContextItemRead,
    GlobalImageContextRetrieveResponse,
    ImageContextBackfillRequest,
    ImageContextBackfillResponse,
    ImageContextRetrieveRequest,
    ImageContextRetrieveResponse,
)
from app.modules.image_context.services import (
    enqueue_pack_backfill_jobs,
    retrieve_global_image_context,
    retrieve_pack_image_context,
    upsert_global_image_context_item,
)
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user

router = APIRouter()


@router.post(
    "/image-context/packs/{pack_id}/retrieve",
    response_model=ImageContextRetrieveResponse,
)
def retrieve_pack_images(
    pack_id: UUID,
    body: ImageContextRetrieveRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.image_context_enabled or not settings.image_context_poster_enabled:
        return ImageContextRetrieveResponse(
            query=body.query,
            items=[],
            references=[],
            context_text="",
        )

    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    payload = retrieve_pack_image_context(
        db,
        user_id=current_user.id,
        pack_id=pack_id,
        query=body.query,
        top_k=body.top_k,
        min_score=body.min_score,
    )
    return ImageContextRetrieveResponse(
        query=body.query,
        items=payload.get("items", []),
        references=payload.get("references", []),
        context_text=payload.get("context_text", ""),
    )


@router.post(
    "/image-context/packs/{pack_id}/backfill",
    response_model=ImageContextBackfillResponse,
)
def backfill_pack_images(
    pack_id: UUID,
    body: ImageContextBackfillRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.image_context_enabled:
        return ImageContextBackfillResponse(
            queued_jobs=0,
            queued_proof_jobs=0,
            queued_asset_jobs=0,
        )

    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    queued = enqueue_pack_backfill_jobs(
        db,
        user_id=current_user.id,
        pack_id=pack_id,
        include_proofs=body.include_proofs,
        include_assets=body.include_assets,
    )
    start_image_context_worker()
    return ImageContextBackfillResponse(**queued)


@router.post(
    "/image-context/global/upload",
    response_model=GlobalImageContextItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_global_image_context_image(
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    db=Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    if settings.app_env != "development":
        raise AppError(
            "Global image context uploads are only available in development.",
            status_code=403,
        )
    if not settings.image_context_enabled:
        raise AppError("Image context is disabled.", status_code=400)

    content = await file.read()
    if not content:
        raise AppError("File is empty", status_code=400)
    if not (file.content_type or "").lower().startswith("image/"):
        raise AppError("Only image files are supported.", status_code=400)

    safe_name = (file.filename or "image").replace(" ", "_")[:200]
    key = f"image-context/global/{uuid.uuid4().hex}_{safe_name}"
    uploaded_key = upload_file(key, content, content_type=file.content_type)
    if not uploaded_key:
        raise AppError("Storage not configured; cannot upload file.", status_code=503)

    parsed_tags = (
        [part.strip() for part in tags.split(",") if part.strip()]
        if isinstance(tags, str) and tags.strip()
        else None
    )
    item = upsert_global_image_context_item(
        db,
        source_storage_key=uploaded_key,
        source_name=safe_name,
        source_content_type=file.content_type,
        caption=caption,
        tags=parsed_tags,
    )
    preview_url = get_presigned_url(
        item.source_storage_key,
        expires_in=max(60, settings.image_context_preview_url_ttl_seconds),
    )
    return GlobalImageContextItemRead(
        id=item.id,
        source_name=item.source_name,
        caption=item.caption,
        metadata_json=item.metadata_json if isinstance(item.metadata_json, dict) else None,
        score=None,
        preview_url=preview_url,
    )


@router.post(
    "/image-context/global/retrieve",
    response_model=GlobalImageContextRetrieveResponse,
)
def retrieve_global_images(
    body: ImageContextRetrieveRequest,
    db=Depends(get_db),
):
    settings = get_settings()
    if not settings.image_context_enabled or not settings.image_context_poster_enabled:
        return GlobalImageContextRetrieveResponse(
            query=body.query,
            items=[],
            references=[],
            context_text="",
        )

    payload = retrieve_global_image_context(
        db,
        query=body.query,
        top_k=body.top_k,
        min_score=body.min_score,
    )
    return GlobalImageContextRetrieveResponse(
        query=body.query,
        items=payload.get("items", []),
        references=payload.get("references", []),
        context_text=payload.get("context_text", ""),
    )
