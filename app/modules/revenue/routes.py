"""Proposals and Invoices API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import Response

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError, BadRequestError
from app.modules.packs.models import User
from app.modules.revenue.schemas import (
    ConnectOnboardingLinkResponse,
    ConnectStatusResponse,
    InvoiceCreate,
    InvoiceList,
    InvoiceListEntry,
    InvoicePublishResponse,
    InvoiceRead,
    InvoiceUpdate,
    ProposalCreate,
    ProposalGenerateBody,
    ProposalGenerateResponse,
    ProposalList,
    ProposalListEntry,
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


# ---- Stripe Connect ----

@router.post("/connect/onboarding-link", response_model=ConnectOnboardingLinkResponse)
def connect_onboarding_link(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a URL to redirect the user to Stripe Connect onboarding."""
    from app.modules.revenue.stripe_connect import create_connect_account_and_onboarding_link

    url, err = create_connect_account_and_onboarding_link(
        db, current_user,
        return_path="/invoices",
        refresh_path="/invoices",
    )
    if err or not url:
        raise BadRequestError(err or "Failed to create onboarding link")
    return ConnectOnboardingLinkResponse(url=url)


@router.get("/connect/status", response_model=ConnectStatusResponse)
def connect_status(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether the user has connected Stripe and completed onboarding. Refreshes from Stripe if connected."""
    from app.modules.revenue.stripe_connect import retrieve_account_details

    connected = bool(current_user.stripe_connect_account_id)
    onboarding_complete = bool(current_user.stripe_connect_onboarding_complete)

    if connected and current_user.stripe_connect_account_id:
        details = retrieve_account_details(current_user.stripe_connect_account_id)
        if details:
            submitted = details.get("details_submitted", False)
            if submitted and not onboarding_complete:
                current_user.stripe_connect_onboarding_complete = True
                db.commit()
            onboarding_complete = submitted

    return ConnectStatusResponse(connected=connected, onboarding_complete=onboarding_complete)


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
    from app.modules.clients.models import Client

    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_proposals_for_pack(db, pack_id)
    client_ids = [p.client_id for p in items if p.client_id is not None]
    clients_map = {}
    if client_ids:
        clients = db.query(Client).filter(
            Client.id.in_(client_ids),
            Client.user_id == current_user.id,
        ).all()
        clients_map = {c.id: c.name for c in clients}
    entries = [
        ProposalListEntry(
            **ProposalRead.model_validate(p).model_dump(),
            client_name=clients_map.get(p.client_id) if p.client_id else None,
        )
        for p in items
    ]
    return ProposalList(items=entries, total=len(entries))


@router.post("/packs/{pack_id}/proposals/generate", response_model=ProposalGenerateResponse)
def generate_proposal_route(
    pack_id: UUID,
    body: ProposalGenerateBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate proposal draft content and suggested amount/due date from pack and optional lead."""
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    from app.core.gates import can_create_proposal
    can_create_proposal(db, pack)
    if body.client_id:
        from app.modules.clients.services import get_for_user as get_client_for_user
        if not get_client_for_user(db, body.client_id, current_user.id):
            raise NotFoundError("Client not found")
    from app.modules.revenue.proposal_generation import generate_proposal_draft
    result = generate_proposal_draft(db, pack, current_user.id, body.client_id)
    return ProposalGenerateResponse(
        content=result["content"],
        suggested_amount=result.get("suggested_amount"),
        suggested_due_date=result.get("suggested_due_date"),
        references=result.get("references"),
    )


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


@router.get("/proposals/{proposal_id}/pdf")
def get_proposal_pdf_route(
    proposal_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download proposal as PDF."""
    proposal = get_proposal(db, proposal_id, current_user.id)
    if not proposal:
        raise NotFoundError("Proposal not found")
    from app.modules.packs.models import Pack
    from app.modules.clients.models import Client
    from app.modules.revenue.pdf import build_proposal_pdf

    pack = db.query(Pack).filter(Pack.id == proposal.pack_id).first()
    pack_name = pack.name if pack else str(proposal.pack_id)
    client_name = None
    if proposal.client_id:
        client = db.query(Client).filter(
            Client.id == proposal.client_id,
            Client.user_id == current_user.id,
        ).first()
        if client:
            client_name = client.name

    pdf_bytes = build_proposal_pdf(proposal, pack_name, client_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="proposal-{proposal_id}.pdf"',
        },
    )


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
    from app.modules.clients.models import Client

    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_invoices_for_pack(db, pack_id)
    client_ids = [i.client_id for i in items if i.client_id is not None]
    clients_map = {}
    if client_ids:
        clients = db.query(Client).filter(
            Client.id.in_(client_ids),
            Client.user_id == current_user.id,
        ).all()
        clients_map = {c.id: (c.name, c.email) for c in clients}
    entries = [
        InvoiceListEntry(
            **InvoiceRead.model_validate(i).model_dump(),
            client_name=(clients_map.get(i.client_id) or (None, None))[0] if i.client_id else None,
            client_email=(clients_map.get(i.client_id) or (None, None))[1] if i.client_id else None,
        )
        for i in items
    ]
    return InvoiceList(items=entries, total=len(entries))


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


@router.post("/invoices/{invoice_id}/publish", response_model=InvoicePublishResponse)
def publish_invoice_route(
    invoice_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Stripe invoice on the invoice owner's connected account and return the payment link."""
    from app.modules.packs.models import Pack
    from app.modules.clients.models import Client
    from app.modules.revenue.stripe_invoice import create_invoice_on_connected_account

    invoice = get_invoice(db, invoice_id, current_user.id)
    if not invoice:
        raise NotFoundError("Invoice not found")

    pack = db.query(Pack).filter(Pack.id == invoice.pack_id).first()
    if not pack:
        raise NotFoundError("Pack not found")

    owner_id = pack.created_by_user_id
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner or not owner.stripe_connect_account_id:
        raise BadRequestError("Connect your Stripe account in Settings to create payment links.")
    if not owner.stripe_connect_onboarding_complete:
        raise BadRequestError("Complete Stripe onboarding in Settings before creating payment links.")

    if invoice.stripe_hosted_url:
        return InvoicePublishResponse(
            payment_link=invoice.stripe_hosted_url,
            stripe_invoice_id=invoice.stripe_invoice_id or "",
        )

    customer_email = None
    customer_name = None
    if invoice.client_id:
        client = db.query(Client).filter(
            Client.id == invoice.client_id,
            Client.user_id == owner_id,
        ).first()
        if client:
            customer_email = client.email
            customer_name = client.name

    stripe_invoice_id, hosted_url, err = create_invoice_on_connected_account(
        owner.stripe_connect_account_id,
        invoice,
        customer_email,
        customer_name,
    )
    if err or not hosted_url:
        raise BadRequestError(err or "Failed to create payment link")

    update_invoice(
        db,
        invoice,
        status="sent",
        stripe_invoice_id=stripe_invoice_id,
        stripe_hosted_url=hosted_url,
    )
    return InvoicePublishResponse(payment_link=hosted_url, stripe_invoice_id=stripe_invoice_id or "")


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
                invoice_due_date=invoice.due_date,
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


# ---- Stripe webhook (no auth; verified by signature) ----

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db=Depends(get_db),
):
    """Handle Stripe webhook events (e.g. invoice.paid). Verifies signature with STRIPE_WEBHOOK_SECRET."""
    from app.core.config import get_settings
    from app.modules.revenue.models import Invoice

    body = await request.body()
    secret = get_settings().stripe_webhook_secret
    if not secret or not stripe_signature:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Webhook secret or signature missing")

    import stripe

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, secret)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Invalid signature")

    if event.type == "invoice.paid":
        stripe_invoice_id = event.data.object.id if hasattr(event.data.object, "id") else None
        if stripe_invoice_id:
            inv = db.query(Invoice).filter(Invoice.stripe_invoice_id == stripe_invoice_id).first()
            if inv:
                update_invoice(db, inv, status="paid")

    return {"received": True}
