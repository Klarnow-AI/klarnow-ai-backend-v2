"""Stripe webhook handler.

Processes subscription lifecycle events:
- checkout.session.completed -> activate tier
- customer.subscription.updated -> sync tier changes
- customer.subscription.deleted -> downgrade to free
- invoice.payment_failed -> handle payment failure
"""
from __future__ import annotations

import stripe
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.packs.models import User
from app.modules.billing.services import update_user_tier, downgrade_to_free
from app.modules.billing.constants import TIER_PRICE_MAP

logger = get_logger("klarnow.billing.webhook")

# Reverse map: price_id -> tier
_PRICE_TO_TIER: dict[str, str] = {
    v: k for k, v in TIER_PRICE_MAP.items() if v is not None
}


def _resolve_tier_from_subscription(subscription: stripe.Subscription) -> str | None:
    """Determine the tier from a Stripe subscription's price."""
    # Check metadata first
    tier = subscription.metadata.get("tier") if subscription.metadata else None
    if tier:
        return tier

    # Fall back to price ID lookup
    if subscription.items and subscription.items.data:
        price_id = subscription.items.data[0].price.id
        return _PRICE_TO_TIER.get(price_id)

    return None


def _find_user_by_customer_id(db: Session, customer_id: str) -> User | None:
    """Look up a user by their stripe_customer_id."""
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def _find_user_by_metadata(db: Session, metadata: dict) -> User | None:
    """Look up a user by user_id in webhook metadata."""
    user_id = metadata.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def handle_checkout_completed(db: Session, session: stripe.checkout.Session) -> None:
    """Handle checkout.session.completed: activate subscription tier."""
    if session.mode != "subscription":
        return

    user = _find_user_by_metadata(db, session.metadata or {})
    if not user:
        user = _find_user_by_customer_id(db, session.customer)
    if not user:
        logger.warning("Checkout completed but no user found: session=%s", session.id)
        return

    # Set customer ID if not already set
    if not user.stripe_customer_id:
        user.stripe_customer_id = session.customer
        db.commit()

    tier = (session.metadata or {}).get("tier")
    subscription_id = session.subscription

    if tier:
        update_user_tier(db, user, tier, stripe_subscription_id=subscription_id)
        logger.info(
            "Checkout completed: user=%s tier=%s subscription=%s",
            user.id, tier, subscription_id,
        )


def handle_subscription_updated(db: Session, subscription: stripe.Subscription) -> None:
    """Handle customer.subscription.updated: sync tier on plan changes."""
    customer_id = subscription.customer
    user = _find_user_by_customer_id(db, customer_id)
    if not user:
        user = _find_user_by_metadata(db, subscription.metadata or {})
    if not user:
        logger.warning("Subscription updated but no user found: sub=%s", subscription.id)
        return

    if subscription.status in ("active", "trialing"):
        tier = _resolve_tier_from_subscription(subscription)
        if tier:
            update_user_tier(db, user, tier, stripe_subscription_id=subscription.id)
    elif subscription.status in ("canceled", "unpaid", "incomplete_expired"):
        downgrade_to_free(db, user)


def handle_subscription_deleted(db: Session, subscription: stripe.Subscription) -> None:
    """Handle customer.subscription.deleted: downgrade to free."""
    customer_id = subscription.customer
    user = _find_user_by_customer_id(db, customer_id)
    if not user:
        user = _find_user_by_metadata(db, subscription.metadata or {})
    if not user:
        logger.warning("Subscription deleted but no user found: sub=%s", subscription.id)
        return

    downgrade_to_free(db, user)
    logger.info("Subscription deleted: user=%s downgraded to free", user.id)


def handle_invoice_payment_failed(db: Session, invoice: stripe.Invoice) -> None:
    """Handle invoice.payment_failed: log warning, optionally downgrade."""
    customer_id = invoice.customer
    user = _find_user_by_customer_id(db, customer_id)
    if not user:
        logger.warning("Payment failed but no user found: invoice=%s", invoice.id)
        return

    logger.warning(
        "Payment failed: user=%s customer=%s invoice=%s",
        user.id, customer_id, invoice.id,
    )
    # Note: Stripe will retry. Only downgrade on subscription.deleted.


def process_webhook_event(db: Session, payload: bytes, sig_header: str) -> dict:
    """Verify and process a Stripe webhook event.

    Returns a dict with the processing result.
    """
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook signature verification failed")
        raise ValueError("Invalid webhook signature")

    event_type = event.type
    data_object = event.data.object

    logger.info("Processing webhook event=%s id=%s", event_type, event.id)

    if event_type == "checkout.session.completed":
        handle_checkout_completed(db, data_object)
    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(db, data_object)
    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(db, data_object)
    elif event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(db, data_object)
    else:
        logger.debug("Unhandled webhook event type: %s", event_type)

    return {"status": "ok", "event_type": event_type}
