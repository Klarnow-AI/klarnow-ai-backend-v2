"""Agents API schemas: decision log (read-only for debugging/audits)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DecisionLogEntryRead(BaseModel):
    id: UUID
    tool_name: str
    agent: str
    pack_id: UUID | None
    inputs_sanitized: dict | None
    success: bool
    result_summary: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionLogList(BaseModel):
    items: list[DecisionLogEntryRead]
    total: int
