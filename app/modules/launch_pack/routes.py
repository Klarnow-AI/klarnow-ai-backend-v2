"""Launch Pack export API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.subscription.services import check_credits, deduct_credit
from app.modules.launch_pack.schemas import BuildLaunchPackBody, BuildLaunchPackResponse
from app.modules.launch_pack.services import build_and_upload

router = APIRouter()


@router.post("/packs/{pack_id}/build-launch-pack", response_model=BuildLaunchPackResponse)
def build_launch_pack(
    pack_id: UUID,
    body: BuildLaunchPackBody | None = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Build Launch Pack ZIP (Brand OS, Marketing Plan, conversion page, proposals, invoices, assets manifest).
    Compliance: proof or waiver, CTA match, no revenue guarantees. Uses 1 credit. Returns presigned download URL.
    """
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    credits = check_credits(db, current_user.id)
    if credits < 1:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Upgrade your plan to export.",
        )
    waiver = (body and body.waiver_confirmed) or False
    try:
        url, expires = build_and_upload(db, pack_id, waiver_confirmed=waiver)
    except ValueError as e:
        raise NotFoundError(str(e))
    deduct_credit(db, current_user.id, 1)
    return BuildLaunchPackResponse(
        download_url=url,
        expires_in_seconds=expires,
        pack_id=str(pack_id),
    )
