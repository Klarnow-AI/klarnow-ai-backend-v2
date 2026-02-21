"""Proposals and Invoices API."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.revenue.schemas import (
    InvoiceCreate,
    InvoiceList,
    InvoiceRead,
    InvoiceUpdate,
    ProposalCreate,
    ProposalList,
    ProposalRead,
    ProposalUpdate,
)
from app.modules.revenue.services import (
    create_proposal,
    create_invoice,
    get_proposal,
    get_invoice,
    list_proposals_for_pack,
    list_invoices_for_pack,
    update_proposal,
    update_invoice,
)
from app.modules.packs.services import get_pack_for_user

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID):
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")
    return pack


# ---- Proposals ----

@router.get("/packs/{pack_id}/proposals", response_model=ProposalList)
def list_proposals(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_proposals_for_pack(db, pack_id)
    return ProposalList(items=[ProposalRead.model_validate(p) for p in items], total=len(items))


@router.post("/packs/{pack_id}/proposals", response_model=ProposalRead, status_code=status.HTTP_201_CREATED)
def create_proposal_route(
    pack_id: UUID,
    body: ProposalCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    from app.core.gates import can_create_proposal
    can_create_proposal(db, pack)
    # Allow client_id only if user owns that client
    if body.client_id:
        from app.modules.clients.services import get_for_user as get_client_for_user
        if not get_client_for_user(db, body.client_id, current_user.id):
            raise NotFoundError("Client not found")
    proposal = create_proposal(
        db,
        pack_id=pack_id,
        amount=body.amount,
        currency=body.currency,
        due_date=body.due_date,
        content=body.content,
        client_id=body.client_id,
    )
    return ProposalRead.model_validate(proposal)


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
def get_proposal_route(
    proposal_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = get_proposal(db, proposal_id, current_user.id)
    if not proposal:
        raise NotFoundError("Proposal not found")
    return ProposalRead.model_validate(proposal)


@router.patch("/proposals/{proposal_id}", response_model=ProposalRead)
def update_proposal_route(
    proposal_id: UUID,
    body: ProposalUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = get_proposal(db, proposal_id, current_user.id)
    if not proposal:
        raise NotFoundError("Proposal not found")
    data = body.model_dump(exclude_unset=True)
    old_status = proposal.status
    proposal = update_proposal(db, proposal, **data)
    if data.get("status") == "sent" and old_status != "sent":
        try:
            from app.modules.clients.services import get_lead_by_pack_and_client, get_for_user as get_client_for_user
            from app.modules.tasks.services import create_proposal_followup_task
            lead = get_lead_by_pack_and_client(db, proposal.pack_id, proposal.client_id) if proposal.client_id else None
            client = get_client_for_user(db, proposal.client_id, current_user.id) if proposal.client_id else None
            name = (lead.name if lead else (client.name if client else "Prospect"))
            create_proposal_followup_task(
                db, pack_id=proposal.pack_id,
                lead_id=lead.id if lead else None,
                lead_name=name,
            )
        except Exception:
            pass
    return ProposalRead.model_validate(proposal)


# ---- Invoices ----

@router.get("/packs/{pack_id}/invoices", response_model=InvoiceList)
def list_invoices(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_invoices_for_pack(db, pack_id)
    return InvoiceList(items=[InvoiceRead.model_validate(i) for i in items], total=len(items))


@router.post("/packs/{pack_id}/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice_route(
    pack_id: UUID,
    body: InvoiceCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    from app.core.gates import can_create_invoice
    can_create_invoice(db, pack)
    if body.client_id:
        from app.modules.clients.services import get_for_user as get_client_for_user
        if not get_client_for_user(db, body.client_id, current_user.id):
            raise NotFoundError("Client not found")
    invoice = create_invoice(
        db,
        pack_id=pack_id,
        amount=body.amount,
        currency=body.currency,
        due_date=body.due_date,
        content=body.content,
        client_id=body.client_id,
    )
    return InvoiceRead.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def get_invoice_route(
    invoice_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_invoice(db, invoice_id, current_user.id)
    if not invoice:
        raise NotFoundError("Invoice not found")
    return InvoiceRead.model_validate(invoice)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceRead)
def update_invoice_route(
    invoice_id: UUID,
    body: InvoiceUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_invoice(db, invoice_id, current_user.id)
    if not invoice:
        raise NotFoundError("Invoice not found")
    data = body.model_dump(exclude_unset=True)
    old_status = invoice.status
    invoice = update_invoice(db, invoice, **data)
    if data.get("status") == "sent" and old_status != "sent":
        try:
            from app.modules.clients.services import get_lead_by_pack_and_client, get_for_user as get_client_for_user
            from app.modules.tasks.services import create_invoice_followup_task
            lead = get_lead_by_pack_and_client(db, invoice.pack_id, invoice.client_id) if invoice.client_id else None
            client = get_client_for_user(db, invoice.client_id, current_user.id) if invoice.client_id else None
            name = (lead.name if lead else (client.name if client else "Prospect"))
            create_invoice_followup_task(
                db, pack_id=invoice.pack_id,
                lead_id=lead.id if lead else None,
                lead_name=name,
            )
        except Exception:
            pass
    return InvoiceRead.model_validate(invoice)


# ---- Invoice reminder ----

@router.post("/invoices/remind-overdue")
def remind_overdue_invoices(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find overdue invoices for current user's packs and send reminder emails via Resend."""
    from datetime import date

    from app.core.config import get_settings
    from app.modules.clients.models import Client
    from app.modules.packs.models import Pack
    from app.modules.revenue.models import Invoice

    overdue = (
        db.query(Invoice)
        .join(Pack, Invoice.pack_id == Pack.id)
        .filter(Pack.created_by_user_id == current_user.id)
        .filter(Invoice.status == "sent", Invoice.due_date < date.today())
        .all()
    )
    settings = get_settings()
    sent = 0
    if overdue and settings.resend_api_key:
        import resend

        resend.api_key = settings.resend_api_key
        for inv in overdue:
            to_email = None
            if inv.client_id:
                c = db.query(Client).filter(Client.id == inv.client_id).first()
                if c and c.email:
                    to_email = c.email
            if to_email:
                try:
                    resend.Emails.send({
                        "from": settings.resend_from_email or "onboarding@resend.dev",
                        "to": to_email,
                        "subject": f"Invoice overdue – {inv.amount} {inv.currency}",
                        "html": f"<p>This is a reminder that invoice {inv.id} for {inv.amount} {inv.currency} is overdue (due {inv.due_date}).</p>",
                    })
                    sent += 1
                except Exception:
                    pass
    return {"overdue_count": len(overdue), "reminders_sent": sent}
