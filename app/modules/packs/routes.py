"""Legacy packs API routes — retained for backward compatibility during migration."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import Pack, User
from app.modules.packs.schemas import (
    PackCreate,
    PackList,
    PackListItem,
    PackPatch,
    PackRead,
)
from app.modules.packs.services import (
    create_pack,
    delete_pack,
    get_pack_for_user,
    list_packs_for_user,
)

router = APIRouter()


@router.get("/", response_model=PackList)
def list_packs(
    include_archived: bool = Query(False),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = list_packs_for_user(db, user.id, include_archived=include_archived)
    return PackList(items=[PackListItem.model_validate(p) for p in items])


@router.post("/", response_model=PackRead, status_code=status.HTTP_201_CREATED)
def create(
    body: PackCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pack = create_pack(db, user.id, body)
    db.commit()
    return pack


@router.get("/{pack_id}", response_model=PackRead)
def get_pack(
    pack_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_pack_for_user(db, pack_id, user.id)


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pack(
    pack_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_pack(db, pack_id, user.id)
    db.commit()
