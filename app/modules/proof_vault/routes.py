"""Proof Vault API: upload, list, tag, delete."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.storage import upload_file
from app.modules.image_context.jobs import start_image_context_worker
from app.modules.image_context.services import (
    JOB_OPERATION_DELETE,
    JOB_OPERATION_UPSERT,
    SOURCE_TYPE_PROOF,
    enqueue_image_context_job,
)
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
logger = get_logger("klarnow.image_context.hooks")
settings = get_settings()


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
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=pack_id,
                source_type=SOURCE_TYPE_PROOF,
                source_id=proof.id,
                operation=JOB_OPERATION_UPSERT,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=proof_upload | proof_id=%s | error=%s",
                proof.id,
                e,
            )
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
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=proof.pack_id,
                source_type=SOURCE_TYPE_PROOF,
                source_id=proof.id,
                operation=JOB_OPERATION_UPSERT,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=proof_tag_update | proof_id=%s | error=%s",
                proof.id,
                e,
            )
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
    pack_id = proof.pack_id
    delete_proof(db, proof)
    if settings.image_context_enabled:
        try:
            enqueue_image_context_job(
                db,
                user_id=current_user.id,
                pack_id=pack_id,
                source_type=SOURCE_TYPE_PROOF,
                source_id=proof_id,
                operation=JOB_OPERATION_DELETE,
            )
            start_image_context_worker()
        except Exception as e:
            logger.warning(
                "image_context_enqueue_failed | source=proof_delete | proof_id=%s | error=%s",
                proof_id,
                e,
            )
