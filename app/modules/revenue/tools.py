"""Revenue tools: create_proposal, create_invoice (draft only)."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack
from app.modules.revenue.services import create_proposal as svc_create_proposal
from app.modules.revenue.services import create_invoice as svc_create_invoice


CREATE_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "client_id": {"type": "string", "format": "uuid", "description": "Optional client id"},
        "amount": {"type": "string", "description": "Amount e.g. 1500.00"},
        "currency": {"type": "string", "description": "Currency code", "default": "USD"},
        "due_date": {"type": "string", "format": "date", "description": "Optional due date YYYY-MM-DD"},
        "content": {"type": "object", "description": "Optional summary/line items"},
    },
    "required": ["pack_id", "amount"],
}


CREATE_INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "client_id": {"type": "string", "format": "uuid", "description": "Optional client id"},
        "amount": {"type": "string", "description": "Amount e.g. 1500.00"},
        "currency": {"type": "string", "description": "Currency code", "default": "USD"},
        "due_date": {"type": "string", "format": "date", "description": "Optional due date YYYY-MM-DD"},
        "content": {"type": "object", "description": "Optional line items"},
    },
    "required": ["pack_id", "amount"],
}


def create_proposal(
    db: Session,
    pack_id: UUID | str,
    amount: str,
    client_id: UUID | str | None = None,
    currency: str = "USD",
    due_date: str | date | None = None,
    content: dict | None = None,
) -> dict:
    """Create a draft proposal for a pack. Pack must exist."""
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    client_id = UUID(str(client_id)) if isinstance(client_id, str) else client_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {"ok": False, "error": "Pack not found", "proposal_id": None}
    d = date.fromisoformat(due_date) if isinstance(due_date, str) else due_date
    proposal = svc_create_proposal(
        db, pack_id=pack_id, amount=amount, currency=currency, due_date=d, content=content, client_id=client_id
    )
    return {"ok": True, "proposal_id": str(proposal.id), "status": "draft"}


def create_invoice(
    db: Session,
    pack_id: UUID | str,
    amount: str,
    client_id: UUID | str | None = None,
    currency: str = "USD",
    due_date: str | date | None = None,
    content: dict | None = None,
) -> dict:
    """Create a draft invoice for a pack. Pack must exist. Gate: at least one proposal must be accepted."""
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    client_id = UUID(str(client_id)) if isinstance(client_id, str) else client_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return {"ok": False, "error": "Pack not found", "invoice_id": None}
    from app.core.gates import can_create_invoice
    try:
        can_create_invoice(db, pack)
    except Exception as e:
        return {"ok": False, "error": str(e), "invoice_id": None}
    d = date.fromisoformat(due_date) if isinstance(due_date, str) else due_date
    invoice = svc_create_invoice(
        db, pack_id=pack_id, amount=amount, currency=currency, due_date=d, content=content, client_id=client_id
    )
    return {"ok": True, "invoice_id": str(invoice.id), "status": "draft"}
