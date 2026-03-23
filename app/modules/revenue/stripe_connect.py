"""Stripe Connect onboarding: create account, account link, and status."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.packs.models import User


def get_stripe_api_key() -> str:
    return get_settings().stripe_secret_key or ""


def create_connect_account_and_onboarding_link(
    db: Session,
    user: User,
    return_path: str = "/invoices",
    refresh_path: str = "/invoices",
) -> tuple[str | None, str | None]:
    """
    Create a Stripe Connect Express account for the user (if needed), persist account_id,
    and return an AccountLink URL. Returns (url, error_message). If url is set, redirect the user to it.
    """
    import stripe

    key = get_stripe_api_key()
    if not key:
        return None, "Stripe is not configured"

    stripe.api_key = key

    try:
        if user.stripe_connect_account_id:
            account_id = user.stripe_connect_account_id
        else:
            account = stripe.Account.create(
                type="express",
                country="US",
                email=user.email,
            )
            account_id = account.id
            user.stripe_connect_account_id = account_id
            db.commit()

        base_url = get_settings().frontend_url or "http://localhost:3000"
        return_url = base_url.rstrip("/") + return_path
        refresh_url = base_url.rstrip("/") + refresh_path

        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return link.url, None
    except stripe.StripeError as e:
        return None, str(e)


def retrieve_account_details(account_id: str) -> dict | None:
    """Retrieve Connect account; return dict with id, details_submitted, charges_enabled, etc."""
    import stripe

    key = get_stripe_api_key()
    if not key:
        return None

    stripe.api_key = key
    try:
        account = stripe.Account.retrieve(account_id)
        return {
            "id": account.id,
            "details_submitted": getattr(account, "details_submitted", False),
            "charges_enabled": getattr(account, "charges_enabled", False),
        }
    except stripe.StripeError:
        return None
