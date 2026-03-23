"""Proof Vault schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProofRead(BaseModel):
    id: UUID
    pack_id: UUID
    file_key: str
    tags: list[str] | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ProofList(BaseModel):
    items: list[ProofRead]
    total: int


class ProofTagUpdate(BaseModel):
    tags: list[str] | None = None

    model_config = {"extra": "forbid"}
