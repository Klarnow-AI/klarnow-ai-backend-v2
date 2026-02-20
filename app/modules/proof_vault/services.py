"""Proof Vault: upload to S3, CRUD Proof."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.core.storage import upload_file, delete_file
from app.modules.packs.services import get_pack_for_user
from app.modules.proof_vault.models import Proof


@log_service_action()
def list_for_pack(db: Session, pack_id: UUID) -> list[Proof]:
    return db.query(Proof).filter(Proof.pack_id == pack_id).order_by(Proof.uploaded_at.desc()).all()


@log_service_action()
def get_for_user(db: Session, proof_id: UUID, user_id: UUID) -> Proof | None:
    p = db.query(Proof).filter(Proof.id == proof_id).first()
    if not p:
        return None
    pack = get_pack_for_user(db, p.pack_id, user_id)
    return p if pack else None


@log_service_action()
def count_for_pack(db: Session, pack_id: UUID) -> int:
    return db.query(Proof).filter(Proof.pack_id == pack_id).count()


@log_service_action()
def create_proof(
    db: Session,
    pack_id: UUID,
    file_key: str,
    tags: list[str] | None = None,
    proof_text: str | None = None,
) -> Proof:
    proof = Proof(pack_id=pack_id, file_key=file_key, tags=tags, proof_text=proof_text)
    db.add(proof)
    db.commit()
    db.refresh(proof)
    return proof


@log_service_action()
def ensure_proof_exists(db: Session, pack_id: UUID, proof_type: str = "process") -> Proof | None:
    """If pack has no proof, generate one (process, policy, or founder). Returns new proof or None."""
    if count_for_pack(db, pack_id) > 0:
        return None
    from app.modules.packs.models import Pack
    from app.modules.proof_vault.generators import generate_one_proof

    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return None
    text = generate_one_proof(pack, proof_type)
    return create_proof(
        db,
        pack_id=pack_id,
        file_key="generated",
        tags=[proof_type],
        proof_text=text,
    )


@log_service_action()
def update_tags(db: Session, proof: Proof, tags: list[str] | None) -> Proof:
    proof.tags = tags
    db.commit()
    db.refresh(proof)
    return proof


@log_service_action()
def delete_proof(db: Session, proof: Proof, remove_from_storage: bool = True) -> None:
    if remove_from_storage:
        delete_file(proof.file_key)
    db.delete(proof)
    db.commit()
