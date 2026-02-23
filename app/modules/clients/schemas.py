"""Client Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ClientBase(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None

    model_config = {"extra": "forbid"}


class ClientRead(ClientBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientList(BaseModel):
    items: list[ClientRead]
    total: int


# --- Lead schemas ---

class LeadBase(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    summary: str | None = None
    budget_range: str | None = None
    urgency: str | None = None
    client_id: UUID | None = None
    pipeline_stage: str | None = None
    due_date: date | None = None
    deal_value: Decimal | None = None
    assigned_user_id: UUID | None = None


class LeadCreate(LeadBase):
    pack_id: UUID


class LeadUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: str | None = None
    summary: str | None = None
    budget_range: str | None = None
    urgency: str | None = None
    client_id: UUID | None = None
    pipeline_stage: str | None = None
    due_date: date | None = None
    deal_value: Decimal | None = None
    assigned_user_id: UUID | None = None

    model_config = {"extra": "forbid"}


class LeadRead(LeadBase):
    id: UUID
    pack_id: UUID
    status: str
    pipeline_stage: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadList(BaseModel):
    items: list[LeadRead]
    total: int
