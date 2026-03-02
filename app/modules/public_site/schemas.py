"""Public site schemas: lead capture."""

from pydantic import BaseModel


class PublicLeadCaptureBody(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    # Honeypot: bots often fill every field.
    website: str | None = None


class PublicLeadCaptureResponse(BaseModel):
    lead_id: str
