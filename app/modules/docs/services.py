"""Services for the Docs module."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import log_service_action
from app.modules.brand_os.services import get_active_for_pack
from app.modules.docs.composer import (
    apply_section_action,
    compose_document,
)
from app.modules.docs.models import (
    CompanyData,
    Document,
    DocumentSection,
    DOCUMENT_STATUS_ACCEPTED,
    DOCUMENT_STATUS_ARCHIVED,
    DOCUMENT_STATUS_DRAFT,
    DOCUMENT_STATUS_GENERATED,
    DOCUMENT_STATUS_SENT,
    DOCUMENT_TYPE_COMPANY_PROFILE,
    DOCUMENT_TYPE_FOLLOW_UP_SUMMARY,
    DOCUMENT_TYPE_INVOICE,
    DOCUMENT_TYPE_MEETING_SUMMARY,
    DOCUMENT_TYPE_PROPOSAL,
)
from app.modules.docs.pdf import build_document_pdf
from app.modules.docs.registry import get_template_definition, list_template_definitions
from app.modules.packs.models import Pack, User
from app.modules.docs.stripe_invoice import create_invoice_on_connected_account
from app.shared.services.generation_context import build_generation_brand_context


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _coalesce(*values: object | None, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _listify(value: object | None) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    parts = [part.strip("- ").strip() for part in text.replace(";", "\n").replace(",", "\n").splitlines()]
    return [part for part in parts if part]


def _company_data_payload(company_data: CompanyData | None) -> dict[str, object]:
    if not company_data:
        return {}
    return {
        "business_name": company_data.business_name,
        "tagline": company_data.tagline,
        "description": company_data.description,
        "address": company_data.address,
        "phone": company_data.phone,
        "email": company_data.email,
        "website": company_data.website,
        "services": company_data.services or [],
        "team_members": company_data.team_members or [],
        "packages": company_data.packages or [],
        "standard_signatory": company_data.standard_signatory or {},
        "standard_footer": company_data.standard_footer,
        "logo_url": company_data.logo_url,
        "logo_markup": company_data.logo_markup,
        "brand_voice": company_data.brand_voice,
    }


def _default_document_title(document_type: str, inputs_json: dict[str, object]) -> str:
    label = get_template_definition(document_type).label
    client_name = _coalesce(inputs_json.get("client_name"), inputs_json.get("lead_or_client_name"))
    if client_name:
        return f"{label}: {client_name}"
    return label


def seed_company_data_from_pack(pack: Pack) -> dict[str, object]:
    onboarding = _as_dict(getattr(pack, "onboarding_answers", None))
    brand_os = get_active_for_pack(Session.object_session(pack), pack.id) if Session.object_session(pack) else None
    brand_context = build_generation_brand_context(pack, brand_os=brand_os)
    city = _coalesce(getattr(pack, "location_city", None))
    country = _coalesce(getattr(pack, "location_country", None))
    address = ", ".join(part for part in (city, country) if part)
    team_members = []
    if onboarding.get("team_members"):
        team_members = _listify(onboarding.get("team_members"))
    packages = []
    if onboarding.get("packages"):
        packages = _listify(onboarding.get("packages"))

    return {
        "business_name": _coalesce(pack.brand_name, pack.name),
        "tagline": _coalesce(pack.offer_one_liner),
        "description": _coalesce(brand_context.elevator_pitch, pack.offer_one_liner),
        "address": address,
        "phone": _coalesce(onboarding.get("phone"), onboarding.get("contact_phone")),
        "email": _coalesce(onboarding.get("email"), onboarding.get("contact_email")),
        "website": _coalesce(getattr(pack, "website_url", None), onboarding.get("website")),
        "services": _listify(onboarding.get("services")) or _listify(pack.offer_one_liner),
        "team_members": team_members,
        "packages": packages,
        "standard_signatory": {
            "name": _coalesce(pack.brand_name, pack.name),
            "title": "Founder",
        },
        "standard_footer": _coalesce(onboarding.get("footer")),
        "logo_url": brand_context.logo_url,
        "logo_markup": brand_context.logo_markup,
        "brand_voice": brand_context.voice_archetype,
    }


@log_service_action()
def get_or_create_company_data(db: Session, pack: Pack) -> CompanyData:
    row = db.query(CompanyData).filter(CompanyData.pack_id == pack.id).first()
    if row:
        return row
    seeded = seed_company_data_from_pack(pack)
    row = CompanyData(pack_id=pack.id, **seeded)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@log_service_action()
def update_company_data(db: Session, company_data: CompanyData, body: dict[str, object]) -> CompanyData:
    for key, value in body.items():
        if hasattr(company_data, key):
            setattr(company_data, key, value)
    db.commit()
    db.refresh(company_data)
    return company_data


def _document_query_for_pack_user(db: Session, document_id: UUID, user_id: UUID):
    return (
        db.query(Document)
        .join(Pack, Pack.id == Document.pack_id)
        .options(joinedload(Document.sections))
        .filter(Document.id == document_id, Pack.created_by_user_id == user_id)
    )


@log_service_action()
def get_document_for_pack_user(db: Session, document_id: UUID, user_id: UUID) -> Document | None:
    return _document_query_for_pack_user(db, document_id, user_id).first()


@log_service_action()
def list_documents_for_pack(
    db: Session,
    pack_id: UUID,
    *,
    document_type: str | None = None,
) -> list[Document]:
    query = (
        db.query(Document)
        .options(joinedload(Document.sections))
        .filter(Document.pack_id == pack_id, Document.status != DOCUMENT_STATUS_ARCHIVED)
        .order_by(Document.updated_at.desc())
    )
    if document_type:
        query = query.filter(Document.type == document_type)
    return query.all()


def _document_source_context(db: Session, pack: Pack, document: Document | None = None) -> dict[str, object]:
    linked = document.linked_document if document else None
    brand_os = get_active_for_pack(db, pack.id)
    brand_context = build_generation_brand_context(pack, brand_os=brand_os)
    context = {
        "pack_name": pack.name,
        "brand_name": brand_context.brand_name or pack.brand_name or pack.name,
        "lead_name": None,
        "lead_summary": None,
        "client_name": document.inputs_json.get("client_name") if document and isinstance(document.inputs_json, dict) else None,
        "client_company": document.inputs_json.get("client_company") if document and isinstance(document.inputs_json, dict) else None,
        "owner_name": pack.name,
        "onboarding_completed": pack.onboarding_completed_at is not None,
        "automation_ready": pack.onboarding_background_completed_at is not None,
        "pending_followup_task": None,
        "linked_document_title": linked.title if linked else None,
        "linked_document_status": linked.status if linked else None,
        "brand_voice": brand_context.voice_archetype,
    }
    return context


def _replace_sections(db: Session, document: Document, sections) -> None:
    document.sections.clear()
    for index, section in enumerate(sections):
        document.sections.append(
            DocumentSection(
                section_key=section.section_key,
                section_label=section.section_label,
                content=section.content,
                order_index=index,
                metadata_json=section.metadata,
            )
        )
    db.flush()


@log_service_action()
def create_document(
    db: Session,
    *,
    pack: Pack,
    current_user: User,
    document_type: str,
    title: str | None,
    tone_preset: str,
    start_mode: str,
    inputs_json: dict[str, object] | None,
    linked_document_id: UUID | None = None,
) -> Document:
    payload = dict(inputs_json or {})
    doc = Document(
        pack_id=pack.id,
        created_by_user_id=current_user.id,
        linked_document_id=linked_document_id,
        type=document_type,
        status=DOCUMENT_STATUS_DRAFT,
        title=title or _default_document_title(document_type, payload),
        tone_preset=tone_preset,
        start_mode=start_mode,
        inputs_json=payload,
        source_context_json={},
        export_meta_json={},
    )
    db.add(doc)
    definition = get_template_definition(document_type)
    for index, section in enumerate(definition.section_blueprint):
        doc.sections.append(
            DocumentSection(
                section_key=section.key,
                section_label=section.label,
                content="",
                order_index=index,
                metadata_json=None,
            )
        )
    db.commit()
    db.refresh(doc)
    return get_document_for_pack_user(db, doc.id, current_user.id) or doc


@log_service_action()
def update_document(
    db: Session,
    *,
    document: Document,
    body: dict[str, object],
) -> Document:
    if "title" in body and body["title"] is not None:
        document.title = str(body["title"]).strip() or document.title
    if "status" in body and body["status"] is not None:
        document.status = str(body["status"])
    if "tone_preset" in body and body["tone_preset"] is not None:
        document.tone_preset = str(body["tone_preset"])
    if "start_mode" in body and body["start_mode"] is not None:
        document.start_mode = str(body["start_mode"])
    if "inputs_json" in body and isinstance(body["inputs_json"], dict):
        document.inputs_json = dict(body["inputs_json"])
    if "sections" in body and isinstance(body["sections"], list):
        patch_by_id = {str(item["id"]): item["content"] for item in body["sections"] if "id" in item and "content" in item}
        for section in document.sections:
            if str(section.id) in patch_by_id:
                section.content = str(patch_by_id[str(section.id)])
    db.commit()
    db.refresh(document)
    return document


@log_service_action()
def delete_document(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()


@log_service_action()
def generate_document_draft(db: Session, *, document: Document, pack: Pack) -> Document:
    company_data = get_or_create_company_data(db, pack)
    definition = get_template_definition(document.type)
    context = _document_source_context(db, pack, document=document)
    result = compose_document(
        definition,
        inputs=document.inputs_json or {},
        company_data=_company_data_payload(company_data),
        source_context=context,
    )
    document.title = result.title or document.title
    document.inputs_json = result.inputs
    document.status = DOCUMENT_STATUS_GENERATED
    document.source_context_json = {
        **context,
        "missing_fields": result.missing_fields,
        "warnings": result.warnings,
    }
    _replace_sections(db, document, result.sections)
    db.commit()
    db.refresh(document)
    return document


def _regenerated_section_content(
    db: Session,
    *,
    document: Document,
    section: DocumentSection,
) -> str:
    pack = db.query(Pack).filter(Pack.id == document.pack_id).first()
    if not pack:
        raise NotFoundError("Pack not found")
    company_data = get_or_create_company_data(db, pack)
    definition = get_template_definition(document.type)
    result = compose_document(
        definition,
        inputs=document.inputs_json or {},
        company_data=_company_data_payload(company_data),
        source_context=_document_source_context(db, pack, document=document),
    )
    for draft in result.sections:
        if draft.section_key == section.section_key:
            return draft.content
    return section.content


@log_service_action()
def apply_document_section_action(
    db: Session,
    *,
    document: Document,
    section_id: UUID,
    action: str,
) -> Document:
    section = next((item for item in document.sections if item.id == section_id), None)
    if not section:
        raise NotFoundError("Section not found")
    regenerated = _regenerated_section_content(db, document=document, section=section)
    section.content = apply_section_action(
        action=action,
        content=section.content,
        regenerated_content=regenerated,
    )
    if document.status == DOCUMENT_STATUS_DRAFT:
        document.status = DOCUMENT_STATUS_GENERATED
    db.commit()
    db.refresh(document)
    return document


def _invoice_amount_and_currency(document: Document) -> tuple[str, str]:
    inputs = document.inputs_json or {}
    amount = _coalesce(inputs.get("amount"), inputs.get("pricing_summary"))
    currency = _coalesce(inputs.get("currency"), default="USD").upper()
    if not amount:
        raise BadRequestError("Add an invoice amount before creating a payment link.")
    return amount, currency


@log_service_action()
def publish_invoice_document(
    db: Session,
    *,
    document: Document,
    current_user: User,
) -> tuple[str, str]:
    if document.type != DOCUMENT_TYPE_INVOICE:
        raise BadRequestError("Only invoice documents can create payment links.")
    pack = db.query(Pack).filter(Pack.id == document.pack_id).first()
    if not pack:
        raise NotFoundError("Pack not found")

    owner = db.query(User).filter(User.id == pack.created_by_user_id).first()
    if not owner or not owner.stripe_connect_account_id:
        raise BadRequestError("Connect your Stripe account to create payment links.")
    if not owner.stripe_connect_onboarding_complete:
        raise BadRequestError("Complete Stripe onboarding before creating payment links.")

    export_meta = document.export_meta_json or {}
    if export_meta.get("payment_link"):
        return str(export_meta["payment_link"]), str(export_meta.get("stripe_invoice_id") or "")

    amount, currency = _invoice_amount_and_currency(document)
    due_date_raw = _coalesce((document.inputs_json or {}).get("due_date"))
    due_date = None
    if due_date_raw:
        try:
            due_date = datetime.fromisoformat(due_date_raw).date()
        except ValueError:
            due_date = None

    invoice_adapter = SimpleNamespace(
        amount=amount,
        currency=currency,
        due_date=due_date,
        content={
            "description": next(
                (section.content for section in document.sections if section.section_key == "notes"),
                document.title,
            ),
            "notes": next(
                (section.content for section in document.sections if section.section_key == "notes"),
                "",
            ),
        },
    )
    customer_email = _coalesce((document.inputs_json or {}).get("client_email"))
    customer_name = _coalesce((document.inputs_json or {}).get("client_name"))
    stripe_invoice_id, hosted_url, err = create_invoice_on_connected_account(
        owner.stripe_connect_account_id,
        invoice_adapter,
        customer_email or None,
        customer_name or None,
    )
    if err or not hosted_url:
        raise BadRequestError(err or "Failed to create payment link")

    document.export_meta_json = {
        **export_meta,
        "payment_link": hosted_url,
        "stripe_invoice_id": stripe_invoice_id,
        "published_at": datetime.utcnow().isoformat(),
    }
    document.status = DOCUMENT_STATUS_SENT
    db.commit()
    db.refresh(document)
    return hosted_url, stripe_invoice_id or ""


@log_service_action()
def build_docs_home(db: Session, *, pack: Pack) -> dict[str, object]:
    company_data = get_or_create_company_data(db, pack)
    recent_documents = list_documents_for_pack(db, pack.id)[:8]
    counts = Counter(item.type for item in recent_documents)
    suggestions: list[dict[str, object]] = []
    accepted_proposal = (
        db.query(Document)
        .filter(
            Document.pack_id == pack.id,
            Document.type == DOCUMENT_TYPE_PROPOSAL,
            Document.status == DOCUMENT_STATUS_ACCEPTED,
        )
        .order_by(Document.updated_at.desc())
        .first()
    )
    has_company_profile = (
        db.query(Document)
        .filter(
            Document.pack_id == pack.id,
            Document.type == DOCUMENT_TYPE_COMPANY_PROFILE,
            Document.status != DOCUMENT_STATUS_ARCHIVED,
        )
        .first()
        is not None
    )
    if pack.onboarding_completed_at is not None:
        suggestions.append(
            {
                "type": DOCUMENT_TYPE_PROPOSAL,
                "label": "Create proposal",
                "reason": "Your strategy context is ready to turn into a structured proposal.",
                "href": f"/projects/{pack.id}/docs/new?{urlencode({'type': DOCUMENT_TYPE_PROPOSAL, 'startMode': 'suggested'})}",
                "priority": 10,
            }
        )
    if accepted_proposal:
        suggestions.append(
            {
                "type": DOCUMENT_TYPE_INVOICE,
                "label": "Generate invoice",
                "reason": "An accepted proposal is ready to move to payment.",
                "href": f"/projects/{pack.id}/docs/new?{urlencode({'type': DOCUMENT_TYPE_INVOICE, 'startMode': 'suggested', 'linkedDocumentId': str(accepted_proposal.id)})}",
                "priority": 20,
            }
        )
    if not has_company_profile:
        suggestions.append(
            {
                "type": DOCUMENT_TYPE_COMPANY_PROFILE,
                "label": "Build company profile",
                "reason": "A reusable company profile strengthens downstream brand and sales assets.",
                "href": f"/projects/{pack.id}/docs/new?{urlencode({'type': DOCUMENT_TYPE_COMPANY_PROFILE, 'startMode': 'suggested'})}",
                "priority": 30,
            }
        )
    suggestions.append(
        {
            "type": DOCUMENT_TYPE_MEETING_SUMMARY,
            "label": "Turn notes into summary",
            "reason": "Use the notes-to-structure flow for meetings or review notes.",
            "href": f"/projects/{pack.id}/docs/new?{urlencode({'type': DOCUMENT_TYPE_MEETING_SUMMARY, 'startMode': 'notes'})}",
            "priority": 40,
        }
    )
    return {
        "suggestions": sorted(suggestions, key=lambda item: int(item["priority"])),
        "recent_documents": recent_documents,
        "templates": list_template_definitions(),
        "company_data": company_data,
        "document_counts": dict(counts),
    }


@log_service_action()
def export_document_pdf(db: Session, *, document: Document) -> bytes:
    pack = db.query(Pack).filter(Pack.id == document.pack_id).first()
    if not pack:
        raise NotFoundError("Pack not found")
    company_data = get_or_create_company_data(db, pack)
    return build_document_pdf(document, company_data)
