"""Feedback routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.modules.packs.models import User

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class BugReportBody(BaseModel):
    message: str = Field(..., min_length=10, max_length=4000)
    path: str | None = Field(default=None, max_length=512)


class BugReportResponse(BaseModel):
    status: str = "sent"


@router.post("/bug-report", response_model=BugReportResponse, status_code=status.HTTP_200_OK)
def send_bug_report(
    body: BugReportBody,
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.resend_api_key:
        raise BadRequestError("Email service is not configured")
    if not settings.support_email:
        raise BadRequestError("Support email is not configured")

    submitted_at = datetime.now(timezone.utc).isoformat()
    safe_path = body.path.strip() if body.path else "-"
    safe_message = body.message.strip()
    safe_user_id = _escape_html(str(current_user.id))
    safe_user_email = _escape_html(current_user.email or "-")

    html = (
        "<h2>New bug report</h2>"
        f"<p><strong>Submitted at:</strong> {_escape_html(submitted_at)}</p>"
        f"<p><strong>User ID:</strong> {safe_user_id}</p>"
        f"<p><strong>User Email:</strong> {safe_user_email}</p>"
        f"<p><strong>Path:</strong> {_escape_html(safe_path)}</p>"
        "<p><strong>Message:</strong></p>"
        f"<pre>{_escape_html(safe_message)}</pre>"
    )

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.resend_from_email or "onboarding@resend.dev",
                "to": settings.support_email,
                "subject": "Klarnow bug report",
                "html": html,
            }
        )
    except Exception as exc:
        raise BadRequestError("Failed to send bug report email") from exc

    return BugReportResponse()
