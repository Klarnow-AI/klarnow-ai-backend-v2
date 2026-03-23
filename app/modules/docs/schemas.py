"""Pydantic schemas for the Docs module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.docs.models import (
    DOCUMENT_START_MODE_NOTES,
    DOCUMENT_START_MODE_SUGGESTED,
    DOCUMENT_START_MODE_TEMPLATE,
    DOCUMENT_STATUS_ACCEPTED,
    DOCUMENT_STATUS_ARCHIVED,
    DOCUMENT_STATUS_DRAFT,
    DOCUMENT_STATUS_GENERATED,
    DOCUMENT_STATUS_IN_REVIEW,
    DOCUMENT_STATUS_PAID,
    DOCUMENT_STATUS_READY_TO_SEND,
    DOCUMENT_STATUS_SENT,
    DOCUMENT_TYPE_COMPANY_PROFILE,
    DOCUMENT_TYPE_EMPLOYMENT_LETTER,
    DOCUMENT_TYPE_FOLLOW_UP_SUMMARY,
    DOCUMENT_TYPE_INVOICE,
    DOCUMENT_TYPE_MEETING_SUMMARY,
    DOCUMENT_TYPE_PROPOSAL,
    DOCUMENT_TYPE_SPONSORSHIP_LETTER,
    TONE_PRESET_CONCISE,
    TONE_PRESET_FORMAL,
    TONE_PRESET_PERSUASIVE,
    TONE_PRESET_PROFESSIONAL,
    TONE_PRESET_WARM,
)

DocumentType = Literal[
    DOCUMENT_TYPE_PROPOSAL,
    DOCUMENT_TYPE_INVOICE,
    DOCUMENT_TYPE_COMPANY_PROFILE,
    DOCUMENT_TYPE_MEETING_SUMMARY,
    DOCUMENT_TYPE_FOLLOW_UP_SUMMARY,
    DOCUMENT_TYPE_EMPLOYMENT_LETTER,
    DOCUMENT_TYPE_SPONSORSHIP_LETTER,
]
DocumentStatus = Literal[
    DOCUMENT_STATUS_DRAFT,
    DOCUMENT_STATUS_GENERATED,
    DOCUMENT_STATUS_IN_REVIEW,
    DOCUMENT_STATUS_READY_TO_SEND,
    DOCUMENT_STATUS_SENT,
    DOCUMENT_STATUS_ACCEPTED,
    DOCUMENT_STATUS_PAID,
    DOCUMENT_STATUS_ARCHIVED,
]
DocumentStartMode = Literal[
    DOCUMENT_START_MODE_SUGGESTED,
    DOCUMENT_START_MODE_TEMPLATE,
    DOCUMENT_START_MODE_NOTES,
]
TonePreset = Literal[
    TONE_PRESET_FORMAL,
    TONE_PRESET_PROFESSIONAL,
    TONE_PRESET_PERSUASIVE,
    TONE_PRESET_CONCISE,
    TONE_PRESET_WARM,
]


class TemplateFieldRead(BaseModel):
    key: str
    label: str
    input_type: str
    required: bool
    description: str | None = None
    options: list[str] = Field(default_factory=list)


class TemplateSectionRead(BaseModel):
    key: str
    label: str
    description: str | None = None


class TemplateDefinitionRead(BaseModel):
    type: DocumentType
    label: str
    category: str
    purpose: str
    use_cases: list[str]
    required_fields: list[TemplateFieldRead]
    optional_fields: list[TemplateFieldRead]
    section_blueprint: list[TemplateSectionRead]
    tone_presets: list[TonePreset]
    formatting_rules: list[str]
    export_defaults: dict[str, str]
    validation_rules: list[str]
    suggestion_rules: list[str]


class CompanyDataRead(BaseModel):
    id: UUID
    pack_id: UUID
    business_name: str | None = None
    tagline: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    services: list[object] | None = None
    team_members: list[object] | None = None
    packages: list[object] | None = None
    standard_signatory: dict | None = None
    standard_footer: str | None = None
    logo_url: str | None = None
    logo_markup: str | None = None
    brand_voice: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyDataUpdate(BaseModel):
    business_name: str | None = None
    tagline: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    services: list[object] | None = None
    team_members: list[object] | None = None
    packages: list[object] | None = None
    standard_signatory: dict | None = None
    standard_footer: str | None = None
    logo_url: str | None = None
    logo_markup: str | None = None
    brand_voice: str | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentSectionRead(BaseModel):
    id: UUID
    document_id: UUID
    section_key: str
    section_label: str
    content: str
    order_index: int
    metadata_json: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentSectionPatch(BaseModel):
    id: UUID
    content: str


class DocumentListItem(BaseModel):
    id: UUID
    pack_id: UUID
    created_by_user_id: UUID
    linked_document_id: UUID | None = None
    type: DocumentType
    status: DocumentStatus
    title: str
    tone_preset: TonePreset
    start_mode: DocumentStartMode
    inputs_json: dict | None = None
    source_context_json: dict | None = None
    export_meta_json: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(DocumentListItem):
    sections: list[DocumentSectionRead] = Field(default_factory=list)


class DocumentList(BaseModel):
    items: list[DocumentListItem]
    total: int


class DocumentCreate(BaseModel):
    type: DocumentType
    title: str | None = None
    tone_preset: TonePreset = TONE_PRESET_PROFESSIONAL
    start_mode: DocumentStartMode = DOCUMENT_START_MODE_TEMPLATE
    inputs_json: dict = Field(default_factory=dict)
    linked_document_id: UUID | None = None

    model_config = ConfigDict(extra="ignore")


class DocumentUpdate(BaseModel):
    title: str | None = None
    status: DocumentStatus | None = None
    tone_preset: TonePreset | None = None
    start_mode: DocumentStartMode | None = None
    inputs_json: dict | None = None
    sections: list[DocumentSectionPatch] | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentSuggestionRead(BaseModel):
    type: DocumentType
    label: str
    reason: str
    href: str
    priority: int


class DocsHomeRead(BaseModel):
    suggestions: list[DocumentSuggestionRead]
    recent_documents: list[DocumentListItem]
    templates: list[TemplateDefinitionRead]
    company_data: CompanyDataRead
    document_counts: dict[str, int]


class DocumentGenerateBody(BaseModel):
    notes_text: str | None = None

    model_config = ConfigDict(extra="ignore")


class SectionActionBody(BaseModel):
    action: Literal[
        "rewrite",
        "shorten",
        "expand",
        "more_formal",
        "more_persuasive",
        "bullets",
        "add_next_steps",
        "regenerate",
    ]

    model_config = ConfigDict(extra="forbid")


class InvoicePublishResponse(BaseModel):
    payment_link: str
    stripe_invoice_id: str
