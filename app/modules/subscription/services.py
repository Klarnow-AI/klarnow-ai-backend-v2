"""Subscription service for managing plans and credits."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.subscription.models import (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_STANDARD,
    SUBSCRIPTION_STATUS_ACTIVE,
    Subscription,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PLAN_CREDITS = {
    PLAN_FREE: 0,
    PLAN_STANDARD: 5,
    PLAN_PREMIUM: 30,
}


@log_service_action()
def get_user_subscription(db: Session, user_id: UUID) -> Subscription:
    """Get user's subscription. Creates free subscription if none exists."""
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    if not subscription:
        # Create free subscription
        subscription = create_subscription(db, user_id, PLAN_FREE)
    
    return subscription


@log_service_action()
def create_subscription(db: Session, user_id: UUID, plan: str) -> Subscription:
    """Create subscription for user."""
    credits = PLAN_CREDITS.get(plan, 0)
    
    cycle_start = utc_now()
    cycle_end = cycle_start + timedelta(days=30) if plan != PLAN_FREE else None
    
    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        credits_remaining=credits,
        credits_total=credits,
        cycle_start_date=cycle_start,
        cycle_end_date=cycle_end,
        status=SUBSCRIPTION_STATUS_ACTIVE,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@log_service_action()
def deduct_credit(db: Session, user_id: UUID, amount: int = 1) -> Subscription:
    """Deduct credits from user's subscription."""
    subscription = get_user_subscription(db, user_id)
    
    if subscription.credits_remaining < amount:
        raise ValueError("Insufficient credits")
    
    subscription.credits_remaining -= amount
    db.commit()
    db.refresh(subscription)
    return subscription


@log_service_action()
def check_credits(db: Session, user_id: UUID) -> int:
    """Get remaining credits for user."""
    subscription = get_user_subscription(db, user_id)
    return subscription.credits_remaining


@log_service_action()
def upgrade_subscription(db: Session, user_id: UUID, new_plan: str) -> Subscription:
    """Upgrade user's subscription plan."""
    subscription = get_user_subscription(db, user_id)
    
    old_plan = subscription.plan
    subscription.plan = new_plan
    subscription.credits_total = PLAN_CREDITS[new_plan]
    subscription.credits_remaining = PLAN_CREDITS[new_plan]
    subscription.cycle_start_date = utc_now()
    subscription.cycle_end_date = utc_now() + timedelta(days=30)
    
    db.commit()
    db.refresh(subscription)
    return subscription


@log_service_action()
def can_export(db: Session, user_id: UUID) -> bool:
    """Check if user has credits to export."""
    subscription = get_user_subscription(db, user_id)
    return subscription.credits_remaining > 0
