"""Create and finalize Stripe Invoice on a connected account (Direct Charges)."""

from __future__ import annotations

from app.core.config import get_settings


def get_stripe_api_key() -> str:
    return get_settings().stripe_secret_key or ""


def create_invoice_on_connected_account(
    stripe_account_id: str,
    invoice,
    customer_email: str | None,
    customer_name: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Create Stripe Customer (if needed) and Invoice on the connected account; finalize and return
    hosted_invoice_url. Uses Direct Charges (Stripe-Account header).

    Returns (stripe_invoice_id, hosted_invoice_url, error_message).
    """
    import stripe

    key = get_stripe_api_key()
    if not key:
        return None, None, "Stripe is not configured"

    stripe.api_key = key

    try:
        # Create or retrieve customer on the connected account
        customer_params = {}
        if customer_email:
            customer_params["email"] = customer_email
        if customer_name:
            customer_params["name"] = customer_name
        if not customer_params:
            customer_params["name"] = "Customer"

        customer = stripe.Customer.create(
            **customer_params,
            stripe_account=stripe_account_id,
        )
        customer_id = customer.id

        # Parse amount: Stripe expects amount in cents for USD, etc.
        amount_str = (invoice.amount or "0").replace(",", "")
        try:
            amount_float = float(amount_str)
        except ValueError:
            return None, None, "Invalid invoice amount"
        # Stripe uses smallest currency unit (cents for USD)
        currency_upper = (invoice.currency or "usd").upper()
        if currency_upper in ("USD", "EUR", "GBP", "CAD", "AUD", "NZD", "CHF", "SGD", "HKD", "JPY"):
            if currency_upper == "JPY":
                amount_cents = int(round(amount_float))
            else:
                amount_cents = int(round(amount_float * 100))
        else:
            amount_cents = int(round(amount_float * 100))

        # Create invoice item (line item) then invoice
        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=amount_cents,
            currency=(invoice.currency or "usd").lower(),
            description=_invoice_description(invoice),
            stripe_account=stripe_account_id,
        )

        inv = stripe.Invoice.create(
            customer=customer_id,
            collection_method="send_invoice",
            days_until_due=30,
            stripe_account=stripe_account_id,
        )
        if invoice.due_date:
            from datetime import datetime, timezone
            due_dt = datetime.combine(invoice.due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            stripe.Invoice.modify(
                inv.id,
                due_date=int(due_dt.timestamp()),
                stripe_account=stripe_account_id,
            )
            inv = stripe.Invoice.retrieve(inv.id, stripe_account=stripe_account_id)

        # Finalize so we get hosted_invoice_url
        inv = stripe.Invoice.finalize_invoice(inv.id, stripe_account=stripe_account_id)
        hosted_url = inv.hosted_invoice_url
        if not hosted_url and inv.invoice_pdf:
            hosted_url = inv.invoice_pdf
        return inv.id, hosted_url, None
    except stripe.StripeError as e:
        return None, None, str(e)


def _invoice_description(invoice) -> str:
    content = invoice.content or {}
    if isinstance(content, dict):
        desc = content.get("description") or content.get("notes")
        if isinstance(desc, str) and desc.strip():
            return desc.strip()[:500]
    return f"Invoice for {invoice.amount} {invoice.currency}"
