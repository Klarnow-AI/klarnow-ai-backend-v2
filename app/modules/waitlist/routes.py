"""Public waitlist routes."""

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.core.errors import BadRequestError
from app.modules.waitlist.schemas import (
    WaitlistSubscribeBody,
    WaitlistSubscribeResponse,
)
from app.modules.waitlist.services import send_waitlist_notification_email, subscribe

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])


@router.post("/subscribe", response_model=WaitlistSubscribeResponse)
def subscribe_to_waitlist(
    body: WaitlistSubscribeBody,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
):
    """Subscribe an email address to the public waitlist."""
    if body.website and body.website.strip():
        raise BadRequestError("Invalid form submission")

    result = subscribe(
        db,
        email=str(body.email),
        first_name=body.first_name,
        role=body.role,
        source=body.source,
    )
    if not result.already_subscribed:
        background_tasks.add_task(
            send_waitlist_notification_email,
            email=result.signup.email,
            first_name=result.signup.first_name,
            role=result.signup.role,
            source=result.signup.source,
            created_at=result.signup.created_at,
        )
    response.status_code = (
        status.HTTP_200_OK
        if result.already_subscribed
        else status.HTTP_201_CREATED
    )
    return WaitlistSubscribeResponse(
        already_subscribed=result.already_subscribed,
    )
