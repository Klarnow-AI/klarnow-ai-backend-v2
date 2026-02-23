"""Builder project Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BuilderProjectCreate(BaseModel):
    pack_id: UUID
    name: str = "Untitled Project"


class BuilderProjectUpdate(BaseModel):
    name: str | None = None
    files: dict | None = None
    messages: list | None = None

    model_config = {"extra": "forbid"}


class BuilderProjectRead(BaseModel):
    id: UUID
    pack_id: UUID
    user_id: UUID
    name: str
    files: dict
    messages: list
    live_url: str | None = None
    subdomain_slug: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuilderProjectList(BaseModel):
    items: list[BuilderProjectRead]
    total: int
