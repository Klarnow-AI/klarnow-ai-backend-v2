"""Proposal and Invoice services."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.packs.models import Pack
from app.modules.revenue.models import Invoice, Proposal


def _get_pack_for_user(db: Session, pack_id: UUID, user_id: UUID) -> Pack | None:
    from app.modules.packs.services import get_pack_for_user
    return get_pack_for_user(db, pack_id, user_id)


@log_service_action()
def list_proposals_for_pack(db: Session, pack_id: UUID) -> list[Proposal]:
    return db.query(Proposal).filter(Proposal.pack_id == pack_id).order_by(Proposal.created_at.desc()).all()


@log_service_action()
def list_invoices_for_pack(db: Session, pack_id: UUID) -> list[Invoice]:
    return db.query(Invoice).filter(Invoice.pack_id == pack_id).order_by(Invoice.created_at.desc()).all()


@log_service_action()
def get_proposal(db: Session, proposal_id: UUID, user_id: UUID) -> Proposal | None:
    p = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not p:
        return None
    pack = _get_pack_for_user(db, p.pack_id, user_id)
    return p if pack else None


@log_service_action()
def get_invoice(db: Session, invoice_id: UUID, user_id: UUID) -> Invoice | None:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        return None
    pack = _get_pack_for_user(db, inv.pack_id, user_id)
    return inv if pack else None


@log_service_action()
def create_proposal(
    db: Session,
    pack_id: UUID,
    amount: str,
    currency: str = "USD",
    due_date: date | None = None,
    content: dict | None = None,
    client_id: UUID | None = None,
) -> Proposal:
    proposal = Proposal(
        pack_id=pack_id,
        client_id=client_id,
        status="draft",
        amount=amount,
        currency=currency,
        due_date=due_date,
        content=content,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@log_service_action()
def create_invoice(
    db: Session,
    pack_id: UUID,
    amount: str,
    currency: str = "USD",
    due_date: date | None = None,
    content: dict | None = None,
    client_id: UUID | None = None,
) -> Invoice:
    invoice = Invoice(
        pack_id=pack_id,
        client_id=client_id,
        status="draft",
        amount=amount,
        currency=currency,
        due_date=due_date,
        content=content,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@log_service_action()
def update_proposal(
    db: Session,
    proposal: Proposal,
    status: str | None = None,
    amount: str | None = None,
    currency: str | None = None,
    due_date: date | None = None,
    content: dict | None = None,
) -> Proposal:
    if status is not None:
        proposal.status = status
    if amount is not None:
        proposal.amount = amount
    if currency is not None:
        proposal.currency = currency
    if due_date is not None:
        proposal.due_date = due_date
    if content is not None:
        proposal.content = content
    db.commit()
    db.refresh(proposal)
    return proposal


@log_service_action()
def update_invoice(
    db: Session,
    invoice: Invoice,
    status: str | None = None,
    amount: str | None = None,
    currency: str | None = None,
    due_date: date | None = None,
    content: dict | None = None,
) -> Invoice:
    if status is not None:
        invoice.status = status
    if amount is not None:
        invoice.amount = amount
    if currency is not None:
        invoice.currency = currency
    if due_date is not None:
        invoice.due_date = due_date
    if content is not None:
        invoice.content = content
    db.commit()
    db.refresh(invoice)
    return invoice
