"""Waitlist services."""

import html
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_service_action
from app.core.logging import get_logger
from app.modules.waitlist.models import WaitlistSignup

logger = get_logger("klarnow.waitlist")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _escape_html(value: str) -> str:
    return html.escape(value, quote=True)


@dataclass(frozen=True)
class WaitlistSubscribeResult:
    signup: WaitlistSignup
    already_subscribed: bool


def _merge_signup_details(
    db: Session,
    signup: WaitlistSignup,
    *,
    first_name: str | None,
    role: str | None,
    source: str | None,
) -> WaitlistSignup:
    changed = False
    if first_name and signup.first_name != first_name:
        signup.first_name = first_name
        changed = True
    if role and signup.role != role:
        signup.role = role
        changed = True
    if source and signup.source != source:
        signup.source = source
        changed = True
    if changed:
        db.commit()
        db.refresh(signup)
    return signup


def send_waitlist_notification_email(
    *,
    email: str,
    first_name: str | None,
    role: str | None,
    source: str | None,
    created_at: datetime | None = None,
) -> bool:
    settings = get_settings()
    to_email = settings.waitlist_notification_to_email.strip()
    if not to_email or not settings.resend_api_key:
        logger.info(
            "Waitlist notification email disabled recipient=%s resend=%s",
            bool(to_email),
            bool(settings.resend_api_key),
        )
        return False

    submitted_at = (created_at or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    ).isoformat()
    safe_name = _escape_html(first_name or "-")
    safe_email = _escape_html(email)
    safe_role = _escape_html(role or "-")
    safe_source = _escape_html(source or "-")

    html_body = (
        "<h2>New waitlist signup</h2>"
        f"<p><strong>Submitted at:</strong> {_escape_html(submitted_at)}</p>"
        f"<p><strong>Name:</strong> {safe_name}</p>"
        f"<p><strong>Email:</strong> {safe_email}</p>"
        f"<p><strong>Role:</strong> {safe_role}</p>"
        f"<p><strong>Source:</strong> {safe_source}</p>"
    )

    try:
        import resend
    except Exception as exc:
        logger.warning("Waitlist notification email unavailable error=%s", exc)
        return False

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email or "onboarding@resend.dev",
                "to": to_email,
                "subject": "New Klarnow waitlist signup",
                "html": html_body,
            }
        )
        return True
    except Exception as exc:
        logger.warning("Waitlist notification email send failed error=%s", exc)
        return False


@log_service_action()
def subscribe(
    db: Session,
    *,
    email: str,
    first_name: str | None = None,
    role: str | None = None,
    source: str | None = None,
) -> WaitlistSubscribeResult:
    normalized_email = _normalize_email(email)
    cleaned_first_name = _clean_optional_text(first_name)
    cleaned_role = _clean_optional_text(role)
    cleaned_source = _clean_optional_text(source)

    existing = (
        db.query(WaitlistSignup)
        .filter(WaitlistSignup.email == normalized_email)
        .first()
    )
    if existing:
        signup = _merge_signup_details(
            db,
            existing,
            first_name=cleaned_first_name,
            role=cleaned_role,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    signup = WaitlistSignup(
        email=normalized_email,
        first_name=cleaned_first_name,
        role=cleaned_role,
        source=cleaned_source,
    )
    db.add(signup)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WaitlistSignup)
            .filter(WaitlistSignup.email == normalized_email)
            .first()
        )
        if existing is None:
            raise
        signup = _merge_signup_details(
            db,
            existing,
            first_name=cleaned_first_name,
            role=cleaned_role,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    db.refresh(signup)
    return WaitlistSubscribeResult(signup=signup, already_subscribed=False)
