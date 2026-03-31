"""Public lead-capture schemas for published builder sites."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


class PublicLeadCaptureBody(BaseModel):
    model_config = {"extra": "ignore"}

    name: str
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    # Honeypot: bots often fill every field.
    website: str | None = None


class PublicLeadCaptureResponse(BaseModel):
    submission_id: str
    lead_id: str | None = None


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    text = str(value).strip()
    return text or None


def _pick_value(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in payload:
            value = _stringify(payload.get(key))
            if value:
                return value
    return None


def normalize_public_lead_payload(payload: Mapping[str, Any] | None) -> PublicLeadCaptureBody:
    data = dict(payload or {})
    first_name = _pick_value(data, "first_name", "firstName")
    last_name = _pick_value(data, "last_name", "lastName")
    name = _pick_value(data, "name", "full_name", "fullName")
    if not name and first_name:
        name = " ".join(part for part in (first_name, last_name) if part).strip()

    email = _pick_value(data, "email", "email_address", "emailAddress")
    phone = _pick_value(data, "phone", "phone_number", "phoneNumber", "whatsapp")
    website = _pick_value(data, "website")

    summary = _pick_value(
        data,
        "summary",
        "message",
        "details",
        "notes",
        "project_brief",
        "projectBrief",
    )

    ignored_keys = {
        "name",
        "full_name",
        "fullName",
        "first_name",
        "firstName",
        "last_name",
        "lastName",
        "email",
        "email_address",
        "emailAddress",
        "phone",
        "phone_number",
        "phoneNumber",
        "whatsapp",
        "website",
        "summary",
        "message",
        "details",
        "notes",
        "project_brief",
        "projectBrief",
    }
    extra_lines = [
        f"{key.replace('_', ' ').replace('-', ' ').title()}: {value}"
        for key, raw_value in data.items()
        if key not in ignored_keys
        if (value := _stringify(raw_value))
    ]
    if extra_lines:
        summary = f"{summary}\n\n" + "\n".join(extra_lines) if summary else "\n".join(extra_lines)

    return PublicLeadCaptureBody(
        name=name or "",
        email=email,
        phone=phone,
        summary=summary,
        website=website,
    )
