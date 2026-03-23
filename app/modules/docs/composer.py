"""Deterministic section composer for Klarnow Docs v0.1."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.docs.models import TONE_PRESET_FORMAL, TONE_PRESET_PERSUASIVE
from app.modules.docs.registry import DocumentTemplateDefinition


@dataclass(frozen=True)
class SectionDraft:
    section_key: str
    section_label: str
    content: str
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class CompositionResult:
    title: str
    inputs: dict[str, object]
    sections: list[SectionDraft]
    missing_fields: list[str]
    warnings: list[str]


def _clean_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _placeholder(label: str) -> str:
    return f"[Add {label.lower()}]"


def _split_items(value: object | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r"[\n,;]+", text)
    return [part.strip("- ").strip() for part in parts if part.strip("- ").strip()]


def _sentence_list(items: list[str]) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item}" for item in items)


def _source_value(
    key: str,
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> str:
    if key in inputs and _clean_text(inputs.get(key)):
        return _clean_text(inputs.get(key))
    if key in company_data and _clean_text(company_data.get(key)):
        return _clean_text(company_data.get(key))

    context_map = {
        "client_name": source_context.get("lead_name") or source_context.get("client_name"),
        "client_company": source_context.get("client_company"),
        "lead_or_client_name": source_context.get("lead_name") or source_context.get("client_name"),
        "owner": source_context.get("owner_name"),
        "cover_title": company_data.get("business_name"),
    }
    return _clean_text(context_map.get(key))


def extract_inputs_from_notes(
    document_type: str,
    inputs: dict[str, object],
) -> dict[str, object]:
    raw_notes = _clean_text(inputs.get("raw_notes") or inputs.get("notes_text"))
    if not raw_notes:
        return dict(inputs)

    note_lines = [line.strip("- ").strip() for line in raw_notes.splitlines() if line.strip()]
    note_blob = " ".join(note_lines)
    merged = dict(inputs)
    if document_type == "meeting_summary":
        merged.setdefault("meeting_title", note_lines[0] if note_lines else "Meeting Summary")
        merged.setdefault("date_and_attendees", note_lines[1] if len(note_lines) > 1 else "")
        merged.setdefault("objective", note_lines[2] if len(note_lines) > 2 else note_blob[:160])
        merged.setdefault("key_discussion_points", raw_notes)
        merged.setdefault("decisions_made", note_lines[3] if len(note_lines) > 3 else "")
        merged.setdefault("action_items", "\n".join(note_lines[4:7]) if len(note_lines) > 4 else "")
        merged.setdefault("next_step", note_lines[-1] if note_lines else "")
        return merged

    if document_type == "follow_up_summary":
        merged.setdefault("what_was_discussed", raw_notes)
        merged.setdefault("current_context", note_lines[0] if note_lines else note_blob[:160])
        merged.setdefault("recommended_next_action", note_lines[-1] if note_lines else "")
        merged.setdefault(
            "follow_up_message_draft",
            "Thanks for the update. Sharing the next recommended step based on our conversation.",
        )
        return merged

    return merged


def _proposal_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    client_name = _source_value("client_name", inputs, company_data, source_context) or "the client"
    business_name = _source_value("business_name", inputs, company_data, source_context) or "our team"
    challenge = _source_value("client_challenge", inputs, company_data, source_context) or _placeholder("client challenge")
    scope = _source_value("scope_of_work", inputs, company_data, source_context) or _placeholder("scope of work")
    timeline = _source_value("timeline", inputs, company_data, source_context) or _placeholder("timeline")
    pricing = _source_value("pricing_summary", inputs, company_data, source_context) or _placeholder("pricing summary")
    deliverables = _split_items(inputs.get("deliverables")) or _split_items(scope)
    next_steps = _source_value("next_steps", inputs, company_data, source_context) or "Confirm the scope, approve the proposal, and schedule the kickoff."

    return {
        "title": f"Proposal for {client_name}",
        "executive_summary": (
            f"{business_name} is proposing a focused engagement for {client_name}. "
            f"This draft addresses the current challenge, outlines the delivery approach, "
            f"and gives a clear path from approval to execution."
        ),
        "client_challenge": challenge,
        "our_approach": (
            f"We will address the challenge by aligning the scope to the agreed outcome, "
            f"keeping delivery practical, and communicating progress clearly."
        ),
        "scope_of_work": scope,
        "deliverables": _sentence_list(deliverables) or "- Confirm scope\n- Deliver agreed work\n- Review outcomes",
        "timeline": timeline,
        "pricing": pricing,
        "next_steps": next_steps,
    }


def _invoice_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    client_name = _source_value("client_name", inputs, company_data, source_context) or "Client"
    bill_to = _source_value("bill_to", inputs, company_data, source_context) or _placeholder("billing details")
    proposal_ref = _source_value("related_proposal_reference", inputs, company_data, source_context)
    line_items = _split_items(inputs.get("line_items"))
    payment_terms = _source_value("payment_terms", inputs, company_data, source_context) or _placeholder("payment terms")
    due_date = _source_value("due_date", inputs, company_data, source_context) or _placeholder("due date")
    notes = _clean_text(inputs.get("notes")) or "Please reference the invoice ID in any payment confirmation."
    amount = _source_value("amount", inputs, company_data, source_context) or _source_value("pricing_summary", inputs, company_data, source_context)

    return {
        "header": (
            f"Invoice from {_source_value('business_name', inputs, company_data, source_context) or 'Klarnow Business'}"
            + (f"\nAmount due: {amount}" if amount else "")
        ),
        "bill_to": f"{client_name}\n{bill_to}",
        "related_proposal_reference": proposal_ref or "Generated without a linked proposal reference.",
        "line_items": _sentence_list(line_items) or "- Service delivery\n- Agreed project work",
        "payment_terms": payment_terms,
        "due_date": due_date,
        "notes": notes,
    }


def _company_profile_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    business_name = _source_value("business_name", inputs, company_data, source_context) or "Business"
    about_company = _source_value("about_company", inputs, company_data, source_context) or _clean_text(company_data.get("description")) or _placeholder("company overview")
    services = _split_items(inputs.get("services")) or _split_items(company_data.get("services"))
    why_choose_us = _source_value("why_choose_us", inputs, company_data, source_context) or _placeholder("reasons to choose this business")
    team = _clean_text(inputs.get("team_or_leadership")) or _sentence_list(_split_items(company_data.get("team_members")))
    proof = _clean_text(inputs.get("past_work_or_proof")) or "Add relevant case studies, outcomes, or trust indicators."
    contact = _source_value("contact_details", inputs, company_data, source_context) or "\n".join(
        part
        for part in (
            _clean_text(company_data.get("website")),
            _clean_text(company_data.get("email")),
            _clean_text(company_data.get("phone")),
        )
        if part
    ) or _placeholder("contact details")

    return {
        "cover": _clean_text(inputs.get("cover_title")) or business_name,
        "about_the_company": about_company,
        "what_we_do": f"{business_name} delivers focused services aligned to client outcomes and operational clarity.",
        "services": _sentence_list(services) or "- Core service offering\n- Supporting delivery scope",
        "why_choose_us": why_choose_us,
        "team_or_leadership": team or "Add leadership or delivery-team detail here.",
        "past_work_or_proof": proof,
        "contact_details": contact,
    }


def _meeting_summary_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    return {
        "meeting_title": _source_value("meeting_title", inputs, company_data, source_context) or "Meeting Summary",
        "date_and_attendees": _source_value("date_and_attendees", inputs, company_data, source_context) or _placeholder("date and attendees"),
        "objective": _source_value("objective", inputs, company_data, source_context) or _placeholder("meeting objective"),
        "key_discussion_points": _source_value("key_discussion_points", inputs, company_data, source_context) or _placeholder("discussion points"),
        "decisions_made": _source_value("decisions_made", inputs, company_data, source_context) or "No final decisions were recorded yet.",
        "action_items": _source_value("action_items", inputs, company_data, source_context) or "Add action items and owners.",
        "next_step": _source_value("next_step", inputs, company_data, source_context) or "Confirm ownership and the next follow-up date.",
    }


def _follow_up_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    lead_name = _source_value("lead_or_client_name", inputs, company_data, source_context) or "Lead"
    owner = _source_value("owner", inputs, company_data, source_context) or "Owner to assign"
    due_date = _source_value("due_date", inputs, company_data, source_context) or _placeholder("due date")

    return {
        "lead_or_client_name": lead_name,
        "current_context": _source_value("current_context", inputs, company_data, source_context) or _placeholder("current context"),
        "what_was_discussed": _source_value("what_was_discussed", inputs, company_data, source_context) or _placeholder("discussion summary"),
        "recommended_next_action": _source_value("recommended_next_action", inputs, company_data, source_context) or "Follow up with a concrete next step and deadline.",
        "follow_up_message_draft": _source_value("follow_up_message_draft", inputs, company_data, source_context) or f"Hi {lead_name}, following up with the next recommended step from our last conversation.",
        "owner": owner,
        "due_date": due_date,
    }


def _employment_letter_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    recipient = _source_value("recipient_name", inputs, company_data, source_context) or "Recipient"
    role = _source_value("role_title", inputs, company_data, source_context) or _placeholder("role title")
    dates = _source_value("employment_dates", inputs, company_data, source_context) or _placeholder("employment dates")
    compensation = _source_value("compensation", inputs, company_data, source_context) or _placeholder("compensation")
    signatory = _clean_text(inputs.get("sign_off")) or _clean_text(company_data.get("business_name")) or "Authorized Signatory"
    return {
        "letterhead": _source_value("letterhead", inputs, company_data, source_context) or _clean_text(company_data.get("business_name")) or "Employment Letter",
        "employee_details": f"This letter confirms employment details for {recipient}.",
        "role_and_dates": f"Role: {role}\nDates: {dates}",
        "compensation": compensation,
        "terms": _source_value("terms", inputs, company_data, source_context) or _placeholder("terms"),
        "sign_off": signatory,
    }


def _sponsorship_letter_sections(
    inputs: dict[str, object],
    company_data: dict[str, object],
    source_context: dict[str, object],
) -> dict[str, str]:
    recipient = _source_value("recipient_name", inputs, company_data, source_context) or "Recipient"
    signatory = _clean_text(inputs.get("sign_off")) or _clean_text(company_data.get("business_name")) or "Authorized Signatory"
    return {
        "letterhead": _source_value("letterhead", inputs, company_data, source_context) or _clean_text(company_data.get("business_name")) or "Sponsorship Letter",
        "recipient": recipient,
        "request_summary": _source_value("request_summary", inputs, company_data, source_context) or _placeholder("request summary"),
        "business_overview": _source_value("business_overview", inputs, company_data, source_context) or _placeholder("business overview"),
        "sponsorship_offer": _source_value("sponsorship_offer", inputs, company_data, source_context) or _placeholder("sponsorship offer"),
        "next_steps": _source_value("next_steps", inputs, company_data, source_context) or "Please let us know if you would like a follow-up conversation.",
        "sign_off": signatory,
    }


SECTION_BUILDERS = {
    "proposal": _proposal_sections,
    "invoice": _invoice_sections,
    "company_profile": _company_profile_sections,
    "meeting_summary": _meeting_summary_sections,
    "follow_up_summary": _follow_up_sections,
    "employment_letter": _employment_letter_sections,
    "sponsorship_letter": _sponsorship_letter_sections,
}


def compose_document(
    definition: DocumentTemplateDefinition,
    *,
    inputs: dict[str, object] | None,
    company_data: dict[str, object] | None,
    source_context: dict[str, object] | None,
) -> CompositionResult:
    normalized_inputs = extract_inputs_from_notes(definition.type, inputs or {})
    company_payload = company_data or {}
    context_payload = source_context or {}
    builder = SECTION_BUILDERS[definition.type]
    section_map = builder(normalized_inputs, company_payload, context_payload)

    missing_fields: list[str] = []
    warnings: list[str] = []
    for field in definition.required_fields:
        if not _source_value(field.key, normalized_inputs, company_payload, context_payload):
            missing_fields.append(field.key)

    if missing_fields:
        warnings.append(
            "Some critical fields are still missing. Review placeholders before sending or exporting."
        )

    title = section_map.get("title") or section_map.get("meeting_title") or definition.label
    sections = [
        SectionDraft(
            section_key=section.key,
            section_label=section.label,
            content=section_map.get(section.key, _placeholder(section.label)),
            metadata={"missing_fields": missing_fields} if missing_fields else None,
        )
        for section in definition.section_blueprint
    ]
    return CompositionResult(
        title=title,
        inputs=normalized_inputs,
        sections=sections,
        missing_fields=missing_fields,
        warnings=warnings,
    )


def apply_section_action(
    *,
    action: str,
    content: str,
    regenerated_content: str,
) -> str:
    text = content.strip() or regenerated_content.strip()
    if action in {"rewrite", "regenerate"}:
        return regenerated_content
    if action == "shorten":
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentence for sentence in sentences[:2] if sentence).strip() or text
    if action == "expand":
        addition = " Additional context can be added here once remaining factual details are confirmed."
        return text + addition
    if action == "more_formal":
        replacements = {
            "can't": "cannot",
            "won't": "will not",
            "we'll": "we will",
            "you're": "you are",
            "it's": "it is",
        }
        formal = text
        for source, target in replacements.items():
            formal = re.sub(source, target, formal, flags=re.IGNORECASE)
        if not formal.endswith("."):
            formal += "."
        return formal
    if action == "more_persuasive":
        prefix = "This creates a clearer path to decision and delivery. "
        return prefix + text
    if action == "bullets":
        parts = [part.strip() for part in re.split(r"[.\n]+", text) if part.strip()]
        return "\n".join(f"- {part}" for part in parts) if parts else text
    if action == "add_next_steps":
        suffix = "\n\nNext steps:\n- Review the draft\n- Confirm details\n- Reply with approval or required edits"
        return text + suffix
    return text


def tone_preface(tone_preset: str) -> str:
    if tone_preset == TONE_PRESET_FORMAL:
        return "Formal tone. Keep phrasing precise and restrained."
    if tone_preset == TONE_PRESET_PERSUASIVE:
        return "Persuasive tone. Emphasize clarity, confidence, and momentum."
    return "Professional tone. Keep the language calm, direct, and useful."
