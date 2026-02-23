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


class ProposalListEntry(ProposalRead):
    """Proposal with optional resolved client name for list views."""

    client_name: str | None = None


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
    stripe_invoice_id: str | None = None
    stripe_hosted_url: str | None = None

    model_config = {"from_attributes": True}


class InvoiceListEntry(InvoiceRead):
    """Invoice with optional resolved client name and email for list views."""

    client_name: str | None = None
    client_email: str | None = None


class ProposalList(BaseModel):
    items: list[ProposalListEntry]
    total: int


class ProposalGenerateBody(BaseModel):
    """Optional client_id for lead context when generating draft."""
    client_id: UUID | None = None


class ProposalGenerateResponse(BaseModel):
    content: dict  # description, line_items, terms, notes
    suggested_amount: str | None = None
    suggested_due_date: str | None = None


class InvoiceList(BaseModel):
    items: list[InvoiceListEntry]
    total: int


class ConnectOnboardingLinkResponse(BaseModel):
    url: str


class ConnectStatusResponse(BaseModel):
    connected: bool
    onboarding_complete: bool


class InvoicePublishResponse(BaseModel):
    payment_link: str
    stripe_invoice_id: str
