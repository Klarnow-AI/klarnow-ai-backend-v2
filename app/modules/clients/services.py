"""Client and Lead services. Client by user; Lead by pack (pack ownership checked in routes)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.packs.models import Pack
from app.modules.clients.models import (
    Client,
    Lead,
    LEAD_STATUS_QUALIFIED,
    PIPELINE_STAGE_CONTACTED,
)


@log_service_action()
def list_for_user(db: Session, user_id: UUID) -> list[Client]:
    return db.query(Client).filter(Client.user_id == user_id).order_by(Client.name).all()


@log_service_action()
def get_for_user(db: Session, client_id: UUID, user_id: UUID) -> Client | None:
    return (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == user_id)
        .first()
    )


@log_service_action()
def create(db: Session, user_id: UUID, name: str, email: str | None = None, company: str | None = None) -> Client:
    client = Client(user_id=user_id, name=name, email=email, company=company)
    db.add(client)
    db.commit()
    return client


@log_service_action()
def update(
    db: Session,
    client: Client,
    name: str | None = None,
    email: str | None = None,
    company: str | None = None,
) -> Client:
    if name is not None:
        client.name = name
    if email is not None:
        client.email = email
    if company is not None:
        client.company = company
    db.commit()
    return client


@log_service_action()
def delete(db: Session, client: Client) -> None:
    db.delete(client)
    db.commit()


# --- Lead services ---

@log_service_action()
def list_leads_for_pack(db: Session, pack_id: UUID) -> list[Lead]:
    return (
        db.query(Lead)
        .filter(Lead.pack_id == pack_id)
        .order_by(Lead.created_at.desc())
        .all()
    )


@log_service_action()
def list_qualified_leads_for_pack(db: Session, pack_id: UUID) -> list[Lead]:
    return (
        db.query(Lead)
        .filter(Lead.pack_id == pack_id, Lead.status == LEAD_STATUS_QUALIFIED)
        .order_by(Lead.created_at.desc())
        .all()
    )


@log_service_action()
def count_qualified_leads_for_pack(db: Session, pack_id: UUID) -> int:
    return (
        db.query(Lead)
        .filter(Lead.pack_id == pack_id, Lead.status == LEAD_STATUS_QUALIFIED)
        .count()
    )


@log_service_action()
def get_lead_by_id(db: Session, lead_id: UUID) -> Lead | None:
    return db.query(Lead).filter(Lead.id == lead_id).first()


@log_service_action()
def get_lead_by_pack_and_client(db: Session, pack_id: UUID, client_id: UUID | None) -> Lead | None:
    """Find a lead for this pack linked to the given client (if any)."""
    if not client_id:
        return None
    return (
        db.query(Lead)
        .filter(Lead.pack_id == pack_id, Lead.client_id == client_id)
        .order_by(Lead.created_at.desc())
        .first()
    )


@log_service_action()
def get_lead_for_pack_user(db: Session, lead_id: UUID, user_id: UUID) -> Lead | None:
    return (
        db.query(Lead)
        .join(Pack, Pack.id == Lead.pack_id)
        .filter(
            Lead.id == lead_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


@log_service_action()
def create_lead(
    db: Session,
    pack_id: UUID,
    name: str,
    phone: str | None = None,
    email: str | None = None,
    source: str | None = None,
    summary: str | None = None,
    budget_range: str | None = None,
    urgency: str | None = None,
    client_id: UUID | None = None,
    pipeline_stage: str | None = None,
    due_date: date | None = None,
    deal_value: Decimal | None = None,
    assigned_user_id: UUID | None = None,
) -> Lead:
    lead = Lead(
        pack_id=pack_id,
        name=name,
        phone=phone,
        email=email,
        source=source,
        summary=summary,
        budget_range=budget_range,
        urgency=urgency,
        client_id=client_id,
        pipeline_stage=pipeline_stage or PIPELINE_STAGE_CONTACTED,
        due_date=due_date,
        deal_value=deal_value,
        assigned_user_id=assigned_user_id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    try:
        from app.modules.operations.services import publish_new_lead_activity

        publish_new_lead_activity(db, lead)
    except Exception:
        db.rollback()
    return lead


@log_service_action()
def update_lead(
    db: Session,
    lead: Lead,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    source: str | None = None,
    status: str | None = None,
    summary: str | None = None,
    budget_range: str | None = None,
    urgency: str | None = None,
    client_id: UUID | None = None,
    pipeline_stage: str | None = None,
    due_date: date | None = None,
    deal_value: Decimal | None = None,
    assigned_user_id: UUID | None = None,
) -> Lead:
    if name is not None:
        lead.name = name
    if phone is not None:
        lead.phone = phone
    if email is not None:
        lead.email = email
    if source is not None:
        lead.source = source
    if status is not None:
        lead.status = status
    if summary is not None:
        lead.summary = summary
    if budget_range is not None:
        lead.budget_range = budget_range
    if urgency is not None:
        lead.urgency = urgency
    if client_id is not None:
        lead.client_id = client_id
    if pipeline_stage is not None:
        lead.pipeline_stage = pipeline_stage
    if due_date is not None:
        lead.due_date = due_date
    if deal_value is not None:
        lead.deal_value = deal_value
    if assigned_user_id is not None:
        lead.assigned_user_id = assigned_user_id
    db.commit()
    return lead


@log_service_action()
def qualify_lead(db: Session, lead: Lead) -> Lead:
    lead.status = LEAD_STATUS_QUALIFIED
    db.commit()
    return lead
