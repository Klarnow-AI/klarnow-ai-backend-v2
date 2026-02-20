"""Subscription API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.subscription import services
from app.modules.subscription.models import Subscription


router = APIRouter(prefix="/api/v1/subscription", tags=["subscription"])


class SubscriptionRead(BaseModel):
    id: UUID
    user_id: UUID
    plan: str
    credits_remaining: int
    credits_total: int
    status: str
    
    class Config:
        from_attributes = True


class UpgradeRequest(BaseModel):
    new_plan: str


@router.get("", response_model=SubscriptionRead)
def get_subscription(
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription."""
    subscription = services.get_user_subscription(db, current_user_id)
    return subscription


@router.get("/credits", response_model=dict)
def get_credits(
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get remaining credits."""
    credits = services.check_credits(db, current_user_id)
    return {"credits_remaining": credits}


@router.post("/upgrade", response_model=SubscriptionRead)
def upgrade_plan(
    request: UpgradeRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upgrade subscription plan."""
    subscription = services.upgrade_subscription(db, current_user_id, request.new_plan)
    return subscription
