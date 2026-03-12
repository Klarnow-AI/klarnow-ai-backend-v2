"""Pack-scoped API routes for Klarnow Docs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.docs.registry import serialize_template_definition
from app.modules.docs.schemas import (
    CompanyDataRead,
    CompanyDataUpdate,
    DocsHomeRead,
    DocumentCreate,
    DocumentGenerateBody,
    DocumentList,
    DocumentListItem,
    DocumentRead,
    DocumentUpdate,
    InvoicePublishResponse,
    SectionActionBody,
    TemplateDefinitionRead,
)
from app.modules.docs.services import (
    apply_document_section_action,
    build_docs_home,
    create_document,
    delete_document,
    export_document_pdf,
    generate_document_draft,
    get_document_for_pack_user,
    get_or_create_company_data,
    list_documents_for_pack,
    publish_invoice_document,
    update_company_data,
    update_document,
)
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID):
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")
    return pack


@router.get("/home", response_model=DocsHomeRead)
def docs_home(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    payload = build_docs_home(db, pack=pack)
    return DocsHomeRead(
        suggestions=payload["suggestions"],
        recent_documents=[DocumentListItem.model_validate(item) for item in payload["recent_documents"]],
        templates=[
            TemplateDefinitionRead.model_validate(serialize_template_definition(item))
            for item in payload["templates"]
        ],
        company_data=CompanyDataRead.model_validate(payload["company_data"]),
        document_counts=payload["document_counts"],
    )


@router.get("/templates", response_model=list[TemplateDefinitionRead])
def list_templates(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    home = build_docs_home(db, pack=get_pack_for_user(db, pack_id, current_user.id))
    return [
        TemplateDefinitionRead.model_validate(serialize_template_definition(item))
        for item in home["templates"]
    ]


@router.get("/company-data", response_model=CompanyDataRead)
def get_company_data_route(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    row = get_or_create_company_data(db, pack)
    return CompanyDataRead.model_validate(row)


@router.patch("/company-data", response_model=CompanyDataRead)
def update_company_data_route(
    pack_id: UUID,
    body: CompanyDataUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    row = get_or_create_company_data(db, pack)
    updated = update_company_data(db, row, body.model_dump(exclude_unset=True))
    return CompanyDataRead.model_validate(updated)


@router.get("/documents", response_model=DocumentList)
def list_documents_route(
    pack_id: UUID,
    type: str | None = Query(default=None),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = list_documents_for_pack(db, pack_id, document_type=type)
    return DocumentList(
        items=[DocumentListItem.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document_route(
    pack_id: UUID,
    body: DocumentCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    document = create_document(
        db,
        pack=pack,
        current_user=current_user,
        document_type=body.type,
        title=body.title,
        tone_preset=body.tone_preset,
        start_mode=body.start_mode,
        inputs_json=body.inputs_json,
        linked_document_id=body.linked_document_id,
    )
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document_route(
    pack_id: UUID,
    document_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    return DocumentRead.model_validate(document)


@router.patch("/documents/{document_id}", response_model=DocumentRead)
def update_document_route(
    pack_id: UUID,
    document_id: UUID,
    body: DocumentUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    updated = update_document(db, document=document, body=body.model_dump(exclude_unset=True))
    return DocumentRead.model_validate(updated)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_route(
    pack_id: UUID,
    document_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    delete_document(db, document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/documents/{document_id}/generate", response_model=DocumentRead)
def generate_document_route(
    pack_id: UUID,
    document_id: UUID,
    body: DocumentGenerateBody | None = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    if body and body.notes_text:
        payload = dict(document.inputs_json or {})
        payload["notes_text"] = body.notes_text
        document = update_document(db, document=document, body={"inputs_json": payload})
    generated = generate_document_draft(db, document=document, pack=pack)
    return DocumentRead.model_validate(generated)


@router.post("/documents/{document_id}/sections/{section_id}/actions", response_model=DocumentRead)
def section_action_route(
    pack_id: UUID,
    document_id: UUID,
    section_id: UUID,
    body: SectionActionBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    updated = apply_document_section_action(
        db,
        document=document,
        section_id=section_id,
        action=body.action,
    )
    return DocumentRead.model_validate(updated)


@router.get("/documents/{document_id}/pdf")
def export_document_pdf_route(
    pack_id: UUID,
    document_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    pdf_bytes = export_document_pdf(db, document=document)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document.type}-{document.id}.pdf"',
        },
    )


@router.post("/documents/{document_id}/publish", response_model=InvoicePublishResponse)
def publish_invoice_document_route(
    pack_id: UUID,
    document_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    document = get_document_for_pack_user(db, document_id, current_user.id)
    if not document or document.pack_id != pack_id:
        raise NotFoundError("Document not found")
    payment_link, stripe_invoice_id = publish_invoice_document(
        db,
        document=document,
        current_user=current_user,
    )
    return InvoicePublishResponse(
        payment_link=payment_link,
        stripe_invoice_id=stripe_invoice_id,
    )
