"""Code-defined document template registry for Klarnow Docs v0.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.modules.docs.models import (
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


@dataclass(frozen=True)
class DocumentFieldDefinition:
    key: str
    label: str
    input_type: str
    required: bool = False
    description: str | None = None
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentSectionBlueprint:
    key: str
    label: str
    description: str | None = None


@dataclass(frozen=True)
class DocumentTemplateDefinition:
    type: str
    label: str
    category: str
    purpose: str
    use_cases: tuple[str, ...]
    required_fields: tuple[DocumentFieldDefinition, ...]
    optional_fields: tuple[DocumentFieldDefinition, ...]
    section_blueprint: tuple[DocumentSectionBlueprint, ...]
    tone_presets: tuple[str, ...]
    formatting_rules: tuple[str, ...]
    export_defaults: dict[str, str]
    validation_rules: tuple[str, ...]
    suggestion_rules: tuple[str, ...]


DEFAULT_TONES = (
    TONE_PRESET_FORMAL,
    TONE_PRESET_PROFESSIONAL,
    TONE_PRESET_PERSUASIVE,
    TONE_PRESET_CONCISE,
    TONE_PRESET_WARM,
)


def _template(
    *,
    type: str,
    label: str,
    category: str,
    purpose: str,
    use_cases: tuple[str, ...],
    required_fields: tuple[DocumentFieldDefinition, ...],
    optional_fields: tuple[DocumentFieldDefinition, ...],
    section_blueprint: tuple[DocumentSectionBlueprint, ...],
    suggestion_rules: tuple[str, ...],
) -> DocumentTemplateDefinition:
    return DocumentTemplateDefinition(
        type=type,
        label=label,
        category=category,
        purpose=purpose,
        use_cases=use_cases,
        required_fields=required_fields,
        optional_fields=optional_fields,
        section_blueprint=section_blueprint,
        tone_presets=DEFAULT_TONES,
        formatting_rules=(
            "Use clean heading hierarchy and readable spacing.",
            "Keep the layout print-friendly and professional.",
            "Do not invent critical factual details.",
        ),
        export_defaults={"format": "pdf", "paper_size": "A4"},
        validation_rules=(
            "Required fields should be present before final export.",
            "Keep pricing, dates, names, and terms stable unless explicitly edited.",
        ),
        suggestion_rules=suggestion_rules,
    )


TEMPLATE_REGISTRY: dict[str, DocumentTemplateDefinition] = {
    DOCUMENT_TYPE_PROPOSAL: _template(
        type=DOCUMENT_TYPE_PROPOSAL,
        label="Proposal",
        category="Pack-critical",
        purpose="Move a qualified lead to agreement with a structured proposal.",
        use_cases=("Qualified lead", "Warm deal stage", "Client-ready offer"),
        required_fields=(
            DocumentFieldDefinition("client_name", "Client Name", "short_text", True),
            DocumentFieldDefinition(
                "client_challenge", "Client Challenge", "long_text", True
            ),
            DocumentFieldDefinition(
                "scope_of_work", "Scope of Work", "long_text", True
            ),
            DocumentFieldDefinition("timeline", "Timeline", "long_text", True),
            DocumentFieldDefinition(
                "pricing_summary", "Pricing Summary", "currency", True
            ),
        ),
        optional_fields=(
            DocumentFieldDefinition("client_company", "Client Company", "short_text"),
            DocumentFieldDefinition("deliverables", "Deliverables", "checklist"),
            DocumentFieldDefinition("next_steps", "Next Steps", "long_text"),
            DocumentFieldDefinition("notes", "Notes", "notes"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("title", "Title"),
            DocumentSectionBlueprint("executive_summary", "Executive Summary"),
            DocumentSectionBlueprint("client_challenge", "Client Challenge"),
            DocumentSectionBlueprint("our_approach", "Our Approach"),
            DocumentSectionBlueprint("scope_of_work", "Scope of Work"),
            DocumentSectionBlueprint("deliverables", "Deliverables"),
            DocumentSectionBlueprint("timeline", "Timeline"),
            DocumentSectionBlueprint("pricing", "Pricing"),
            DocumentSectionBlueprint("next_steps", "Next Steps"),
        ),
        suggestion_rules=("qualified or warm lead -> proposal",),
    ),
    DOCUMENT_TYPE_INVOICE: _template(
        type=DOCUMENT_TYPE_INVOICE,
        label="Invoice",
        category="Pack-critical",
        purpose="Move an accepted proposal to payment.",
        use_cases=("Accepted proposal", "Payment request", "Client billing"),
        required_fields=(
            DocumentFieldDefinition("client_name", "Client Name", "short_text", True),
            DocumentFieldDefinition("bill_to", "Bill To", "long_text", True),
            DocumentFieldDefinition("line_items", "Line Items", "checklist", True),
            DocumentFieldDefinition(
                "payment_terms", "Payment Terms", "long_text", True
            ),
            DocumentFieldDefinition("due_date", "Due Date", "date", True),
        ),
        optional_fields=(
            DocumentFieldDefinition(
                "related_proposal_reference",
                "Related Proposal Reference",
                "short_text",
            ),
            DocumentFieldDefinition("client_email", "Client Email", "short_text"),
            DocumentFieldDefinition("amount", "Invoice Amount", "currency"),
            DocumentFieldDefinition(
                "currency",
                "Currency",
                "dropdown",
                options=("USD", "GBP", "EUR", "CAD"),
            ),
            DocumentFieldDefinition("notes", "Notes", "notes"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("header", "Header"),
            DocumentSectionBlueprint("bill_to", "Bill To"),
            DocumentSectionBlueprint(
                "related_proposal_reference", "Related Proposal Reference"
            ),
            DocumentSectionBlueprint("line_items", "Line Items"),
            DocumentSectionBlueprint(
                "payment_terms", "Deposit or Payment Terms"
            ),
            DocumentSectionBlueprint("due_date", "Due Date"),
            DocumentSectionBlueprint("notes", "Notes"),
        ),
        suggestion_rules=("accepted proposal -> invoice",),
    ),
    DOCUMENT_TYPE_COMPANY_PROFILE: _template(
        type=DOCUMENT_TYPE_COMPANY_PROFILE,
        label="Company Profile",
        category="Pack-critical",
        purpose="Create a reusable credibility document from company context.",
        use_cases=("Outreach support", "Trust-building", "Client introduction"),
        required_fields=(
            DocumentFieldDefinition(
                "about_company", "About the Company", "long_text", True
            ),
            DocumentFieldDefinition("services", "Services", "checklist", True),
            DocumentFieldDefinition(
                "why_choose_us", "Why Choose Us", "long_text", True
            ),
            DocumentFieldDefinition(
                "contact_details", "Contact Details", "long_text", True
            ),
        ),
        optional_fields=(
            DocumentFieldDefinition("cover_title", "Cover Title", "short_text"),
            DocumentFieldDefinition(
                "team_or_leadership", "Team or Leadership", "long_text"
            ),
            DocumentFieldDefinition(
                "past_work_or_proof", "Past Work or Proof", "long_text"
            ),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("cover", "Cover"),
            DocumentSectionBlueprint("about_the_company", "About the Company"),
            DocumentSectionBlueprint("what_we_do", "What We Do"),
            DocumentSectionBlueprint("services", "Services"),
            DocumentSectionBlueprint("why_choose_us", "Why Choose Us"),
            DocumentSectionBlueprint("team_or_leadership", "Team or Leadership"),
            DocumentSectionBlueprint("past_work_or_proof", "Past Work or Proof"),
            DocumentSectionBlueprint("contact_details", "Contact Details"),
        ),
        suggestion_rules=(
            "missing company profile + active outreach or leads -> company profile",
        ),
    ),
    DOCUMENT_TYPE_MEETING_SUMMARY: _template(
        type=DOCUMENT_TYPE_MEETING_SUMMARY,
        label="Meeting Summary",
        category="Pack-critical",
        purpose="Turn notes into a clean post-meeting document.",
        use_cases=("Post-call summary", "Review notes", "Action-item capture"),
        required_fields=(
            DocumentFieldDefinition("meeting_title", "Meeting Title", "short_text", True),
            DocumentFieldDefinition(
                "date_and_attendees", "Date and Attendees", "long_text", True
            ),
            DocumentFieldDefinition("objective", "Objective", "long_text", True),
            DocumentFieldDefinition(
                "key_discussion_points", "Key Discussion Points", "notes", True
            ),
            DocumentFieldDefinition("decisions_made", "Decisions Made", "notes", True),
            DocumentFieldDefinition("action_items", "Action Items", "notes", True),
            DocumentFieldDefinition("next_step", "Next Step", "long_text", True),
        ),
        optional_fields=(
            DocumentFieldDefinition("raw_notes", "Raw Notes", "notes"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("meeting_title", "Meeting Title"),
            DocumentSectionBlueprint("date_and_attendees", "Date and Attendees"),
            DocumentSectionBlueprint("objective", "Objective"),
            DocumentSectionBlueprint("key_discussion_points", "Key Discussion Points"),
            DocumentSectionBlueprint("decisions_made", "Decisions Made"),
            DocumentSectionBlueprint("action_items", "Action Items"),
            DocumentSectionBlueprint("next_step", "Next Step"),
        ),
        suggestion_rules=("notes paste flow -> meeting summary",),
    ),
    DOCUMENT_TYPE_FOLLOW_UP_SUMMARY: _template(
        type=DOCUMENT_TYPE_FOLLOW_UP_SUMMARY,
        label="Follow-up Summary",
        category="Pack-critical",
        purpose="Capture progression and generate the next follow-up move.",
        use_cases=("Lead progression", "Follow-up queue", "Client handoff"),
        required_fields=(
            DocumentFieldDefinition(
                "lead_or_client_name", "Lead or Client Name", "short_text", True
            ),
            DocumentFieldDefinition("current_context", "Current Context", "long_text", True),
            DocumentFieldDefinition(
                "what_was_discussed", "What Was Discussed", "notes", True
            ),
            DocumentFieldDefinition(
                "recommended_next_action",
                "Recommended Next Action",
                "long_text",
                True,
            ),
            DocumentFieldDefinition(
                "follow_up_message_draft",
                "Follow-up Message Draft",
                "long_text",
                True,
            ),
            DocumentFieldDefinition("owner", "Owner", "short_text", True),
            DocumentFieldDefinition("due_date", "Due Date", "date", True),
        ),
        optional_fields=(
            DocumentFieldDefinition("raw_notes", "Raw Notes", "notes"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("lead_or_client_name", "Lead or Client Name"),
            DocumentSectionBlueprint("current_context", "Current Context"),
            DocumentSectionBlueprint("what_was_discussed", "What Was Discussed"),
            DocumentSectionBlueprint(
                "recommended_next_action", "Recommended Next Action"
            ),
            DocumentSectionBlueprint(
                "follow_up_message_draft", "Follow-up Message Draft"
            ),
            DocumentSectionBlueprint("owner", "Owner"),
            DocumentSectionBlueprint("due_date", "Due Date"),
        ),
        suggestion_rules=("follow-up task or lead progression -> follow-up summary",),
    ),
    DOCUMENT_TYPE_EMPLOYMENT_LETTER: _template(
        type=DOCUMENT_TYPE_EMPLOYMENT_LETTER,
        label="Employment Letter",
        category="Utility",
        purpose="Create a formal employment letter from guided fields.",
        use_cases=("Employment confirmation", "Offer confirmation"),
        required_fields=(
            DocumentFieldDefinition("recipient_name", "Recipient Name", "short_text", True),
            DocumentFieldDefinition("role_title", "Role Title", "short_text", True),
            DocumentFieldDefinition(
                "employment_dates", "Role and Dates", "long_text", True
            ),
            DocumentFieldDefinition("compensation", "Compensation", "currency", True),
            DocumentFieldDefinition("terms", "Terms", "long_text", True),
        ),
        optional_fields=(
            DocumentFieldDefinition("letterhead", "Letterhead", "short_text"),
            DocumentFieldDefinition("sign_off", "Sign-off", "long_text"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("letterhead", "Letterhead"),
            DocumentSectionBlueprint("employee_details", "Employee Details"),
            DocumentSectionBlueprint("role_and_dates", "Role and Dates"),
            DocumentSectionBlueprint("compensation", "Compensation"),
            DocumentSectionBlueprint("terms", "Terms"),
            DocumentSectionBlueprint("sign_off", "Sign-off"),
        ),
        suggestion_rules=("manual template selection",),
    ),
    DOCUMENT_TYPE_SPONSORSHIP_LETTER: _template(
        type=DOCUMENT_TYPE_SPONSORSHIP_LETTER,
        label="Sponsorship Letter",
        category="Utility",
        purpose="Create a formal sponsorship request letter.",
        use_cases=("Sponsorship outreach", "Partnership request"),
        required_fields=(
            DocumentFieldDefinition("recipient_name", "Recipient", "short_text", True),
            DocumentFieldDefinition(
                "request_summary", "Request Summary", "long_text", True
            ),
            DocumentFieldDefinition(
                "business_overview", "Business Overview", "long_text", True
            ),
            DocumentFieldDefinition(
                "sponsorship_offer", "Sponsorship Offer", "long_text", True
            ),
            DocumentFieldDefinition("next_steps", "Next Steps", "long_text", True),
        ),
        optional_fields=(
            DocumentFieldDefinition("letterhead", "Letterhead", "short_text"),
            DocumentFieldDefinition("sign_off", "Sign-off", "long_text"),
        ),
        section_blueprint=(
            DocumentSectionBlueprint("letterhead", "Letterhead"),
            DocumentSectionBlueprint("recipient", "Recipient"),
            DocumentSectionBlueprint("request_summary", "Request Summary"),
            DocumentSectionBlueprint("business_overview", "Business Overview"),
            DocumentSectionBlueprint("sponsorship_offer", "Sponsorship Offer"),
            DocumentSectionBlueprint("next_steps", "Next Steps"),
            DocumentSectionBlueprint("sign_off", "Sign-off"),
        ),
        suggestion_rules=("manual template selection",),
    ),
}


def list_template_definitions() -> list[DocumentTemplateDefinition]:
    return list(TEMPLATE_REGISTRY.values())


def get_template_definition(document_type: str) -> DocumentTemplateDefinition:
    return TEMPLATE_REGISTRY[document_type]


def serialize_template_definition(
    definition: DocumentTemplateDefinition,
) -> dict[str, object]:
    return asdict(definition)
