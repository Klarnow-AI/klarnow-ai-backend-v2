"""Proof Vault API: upload, list, tag, delete."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.core.storage import upload_file
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.proof_vault.schemas import ProofList, ProofRead, ProofTagUpdate
from app.modules.proof_vault.services import (
    list_for_pack,
    get_for_user,
    create_proof,
    update_tags,
    delete_proof,
)

router = APIRouter()


def _ensure_pack(db, pack_id: UUID, user_id: UUID):
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")
    return pack


@router.get("/packs/{pack_id}/proofs", response_model=ProofList)
def list_proofs(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack(db, pack_id, current_user.id)
    items = list_for_pack(db, pack_id)
    return ProofList(items=[ProofRead.model_validate(p) for p in items], total=len(items))


@router.post("/packs/{pack_id}/proofs", response_model=ProofRead, status_code=status.HTTP_201_CREATED)
async def upload_proof(
    pack_id: UUID,
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file to Proof Vault (S3)."""
    _ensure_pack(db, pack_id, current_user.id)
    content = await file.read()
    if not content:
        from app.core.errors import AppError
        raise AppError("File is empty", status_code=400)
    # Key: proofs/{pack_id}/{uuid}_{filename}
    import uuid as u
    safe_name = (file.filename or "file").replace(" ", "_")[:200]
    key = f"proofs/{pack_id}/{u.uuid4().hex}_{safe_name}"
    uploaded_key = upload_file(key, content, content_type=file.content_type)
    if not uploaded_key:
        from app.core.errors import AppError
        raise AppError("Storage not configured; cannot upload proof", status_code=503)
    proof = create_proof(db, pack_id=pack_id, file_key=uploaded_key, tags=None)
    return ProofRead.model_validate(proof)


@router.get("/proofs/{proof_id}", response_model=ProofRead)
def get_proof(
    proof_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proof = get_for_user(db, proof_id, current_user.id)
    if not proof:
        raise NotFoundError("Proof not found")
    return ProofRead.model_validate(proof)


@router.patch("/proofs/{proof_id}", response_model=ProofRead)
def update_proof_tags(
    proof_id: UUID,
    body: ProofTagUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proof = get_for_user(db, proof_id, current_user.id)
    if not proof:
        raise NotFoundError("Proof not found")
    proof = update_tags(db, proof, body.tags)
    return ProofRead.model_validate(proof)


@router.delete("/proofs/{proof_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proof_route(
    proof_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proof = get_for_user(db, proof_id, current_user.id)
    if not proof:
        raise NotFoundError("Proof not found")
    delete_proof(db, proof)
