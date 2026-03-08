"""Proposal and Invoice services."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.packs.models import Pack
from app.modules.revenue.models import Invoice, Proposal


@log_service_action()
def list_proposals_for_pack(db: Session, pack_id: UUID) -> list[Proposal]:
    return db.query(Proposal).filter(Proposal.pack_id == pack_id).order_by(Proposal.created_at.desc()).all()


@log_service_action()
def list_invoices_for_pack(db: Session, pack_id: UUID) -> list[Invoice]:
    return db.query(Invoice).filter(Invoice.pack_id == pack_id).order_by(Invoice.created_at.desc()).all()


@log_service_action()
def get_proposal(db: Session, proposal_id: UUID, user_id: UUID) -> Proposal | None:
    return (
        db.query(Proposal)
        .join(Pack, Pack.id == Proposal.pack_id)
        .filter(
            Proposal.id == proposal_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


@log_service_action()
def get_invoice(db: Session, invoice_id: UUID, user_id: UUID) -> Invoice | None:
    return (
        db.query(Invoice)
        .join(Pack, Pack.id == Invoice.pack_id)
        .filter(
            Invoice.id == invoice_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


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
    stripe_invoice_id: str | None = None,
    stripe_hosted_url: str | None = None,
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
    if stripe_invoice_id is not None:
        invoice.stripe_invoice_id = stripe_invoice_id
    if stripe_hosted_url is not None:
        invoice.stripe_hosted_url = stripe_hosted_url
    db.commit()
    return invoice
