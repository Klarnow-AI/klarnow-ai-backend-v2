"""API routes for pack image context retrieval and backfill."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.image_context.jobs import start_image_context_worker
from app.modules.image_context.schemas import (
    ImageContextBackfillRequest,
    ImageContextBackfillResponse,
    ImageContextRetrieveRequest,
    ImageContextRetrieveResponse,
)
from app.modules.image_context.services import (
    enqueue_pack_backfill_jobs,
    retrieve_pack_image_context,
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
