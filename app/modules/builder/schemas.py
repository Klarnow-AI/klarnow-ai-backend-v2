"""Builder project Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.generation_schemas import GenerationMessage


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
    published_files: dict | None = None
    live_url: str | None = None
    subdomain_slug: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuilderProjectList(BaseModel):
    items: list[BuilderProjectRead]
    total: int


class BuilderGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    messages: list[GenerationMessage]
    files: dict[str, str]
    selected_style: str | None = Field(default=None, alias="selectedStyle")
    assistant_mode: Literal["launch", "convert", "polish", "debug"] | None = Field(
        default=None,
        alias="assistantMode",
    )
