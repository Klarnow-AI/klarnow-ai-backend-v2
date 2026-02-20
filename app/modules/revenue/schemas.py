"""Proposal and Invoice schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ProposalBase(BaseModel):
    amount: str
    currency: str = "USD"
    due_date: date | None = None
    content: dict | None = None


class ProposalCreate(ProposalBase):
    """For API: pack_id comes from path."""
    client_id: UUID | None = None


class ProposalUpdate(BaseModel):
    status: str | None = None  # sent | accepted | declined
    amount: str | None = None
    currency: str | None = None
    due_date: date | None = None
    content: dict | None = None

    model_config = {"extra": "forbid"}


class ProposalRead(ProposalBase):
    id: UUID
    pack_id: UUID
    client_id: UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    amount: str
    currency: str = "USD"
    due_date: date | None = None
    content: dict | None = None


class InvoiceCreate(InvoiceBase):
    """For API: pack_id comes from path."""
    client_id: UUID | None = None


class InvoiceUpdate(BaseModel):
    status: str | None = None  # sent | paid | overdue
    amount: str | None = None
    currency: str | None = None
    due_date: date | None = None
    content: dict | None = None

    model_config = {"extra": "forbid"}


class InvoiceRead(InvoiceBase):
    id: UUID
    pack_id: UUID
    client_id: UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProposalList(BaseModel):
    items: list[ProposalRead]
    total: int


class InvoiceList(BaseModel):
    items: list[InvoiceRead]
    total: int
