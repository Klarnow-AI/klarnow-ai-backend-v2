"""Billing service layer for Stripe subscription management."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.packs.models import User
from app.modules.billing.constants import TIERS, TIER_PRICE_MAP, VALID_TIERS

logger = get_logger("klarnow.billing")


def _configure_stripe() -> None:
    """Set the Stripe API key from settings."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key


def get_or_create_stripe_customer(db: Session, user: User) -> str:
    """Get existing Stripe customer or create a new one.

    Returns the stripe_customer_id.
    """
    _configure_stripe()

    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )

    user.stripe_customer_id = customer.id
    db.commit()
    db.refresh(user)

    logger.info("Created Stripe customer=%s for user=%s", customer.id, user.id)
    return customer.id


def create_checkout_session(
    db: Session,
    user: User,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for a subscription.

    Returns the checkout session URL.
    """
    _configure_stripe()

    if tier not in VALID_TIERS or tier == "free":
        raise ValueError(f"Cannot create checkout for tier: {tier}")

    price_id = TIER_PRICE_MAP.get(tier)
    if not price_id:
        raise ValueError(f"No Stripe price configured for tier: {tier}")

    customer_id = get_or_create_stripe_customer(db, user)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user.id),
            "tier": tier,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "tier": tier,
            },
        },
    )

    logger.info(
        "Created checkout session=%s for user=%s tier=%s",
        session.id, user.id, tier,
    )
    return session.url


def create_billing_portal_session(db: Session, user: User, return_url: str) -> str:
    """Create a Stripe Billing Portal session for self-service management.

    Returns the portal session URL.
    """
    _configure_stripe()

    customer_id = get_or_create_stripe_customer(db, user)

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )

    return session.url


def update_user_tier(
    db: Session,
    user: User,
    tier: str,
    stripe_subscription_id: str | None = None,
) -> User:
    """Update a user's subscription tier."""
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}")

    user.tier = tier
    user.tier_updated_at = datetime.now(timezone.utc)
    if stripe_subscription_id is not None:
        user.stripe_subscription_id = stripe_subscription_id

    db.commit()
    db.refresh(user)

    logger.info("Updated user=%s tier=%s subscription=%s", user.id, tier, stripe_subscription_id)
    return user


def downgrade_to_free(db: Session, user: User) -> User:
    """Downgrade user to free tier (on cancellation or payment failure)."""
    user.tier = "free"
    user.tier_updated_at = datetime.now(timezone.utc)
    user.stripe_subscription_id = None

    db.commit()
    db.refresh(user)

    logger.info("Downgraded user=%s to free tier", user.id)
    return user


def get_user_tier(user: User) -> str:
    """Get the user's current tier, defaulting to 'free'."""
    return user.tier if user.tier in VALID_TIERS else "free"


def get_tier_limits(tier: str) -> dict:
    """Get the limits dict for a given tier."""
    tier_def = TIERS.get(tier)
    if not tier_def:
        return TIERS["free"].limits
    return tier_def.limits
