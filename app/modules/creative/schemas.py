"""Creative asset Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.generation_schemas import GenerationMessage


class AssetRead(BaseModel):
    id: UUID
    pack_id: UUID
    type: str
    version: str | None
    name: str | None
    template_id: str | None
    source_code: str | None
    output_key: str | None
    script: str | None
    srt_key: str | None
    sprint_day: int | None
    chat_messages: list[dict] | None = None  # [{role, content}] for poster/flyer
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    pack_id: UUID
    type: str  # poster | flyer
    name: str
    source_code: str
    template_id: str | None = None  # e.g. a4_portrait, instagram_square
    chat_messages: list[dict] | None = None  # [{role, content}]


class AssetList(BaseModel):
    items: list[AssetRead]
    total: int


class PosterReferenceImageInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str
    mime_type: str = Field(alias="mimeType")
    data_url: str = Field(alias="dataUrl")


class PosterGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    pack_id: UUID = Field(alias="packId")
    messages: list[GenerationMessage]
    generation_mode: Literal["auto", "manual"] = Field(
        default="manual",
        alias="generationMode",
    )
    reference_images: list[PosterReferenceImageInput] = Field(
        default_factory=list,
        alias="referenceImages",
    )
