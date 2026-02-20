"""Client Pydantic schemas."""

from datetime import datetime
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

    model_config = {"extra": "forbid"}


class LeadRead(LeadBase):
    id: UUID
    pack_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadList(BaseModel):
    items: list[LeadRead]
    total: int
