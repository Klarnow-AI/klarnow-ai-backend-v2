"""Billing API routes.

Provides endpoints for:
- POST /checkout          - Create Stripe Checkout session
- POST /portal            - Create Stripe Billing Portal session
- GET  /status            - Get current user's billing status
- GET  /tiers             - List all available tiers
- POST /webhook           - Stripe webhook handler
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.logging import get_logger
from app.modules.packs.models import User
from app.modules.billing.constants import TIERS, VALID_TIERS
from app.modules.billing.services import (
    create_billing_portal_session,
    create_checkout_session,
    get_user_tier,
    get_tier_limits,
)
from app.modules.billing.webhook import process_webhook_event

logger = get_logger("klarnow.billing.routes")
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    tier: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    tier: str
    tier_name: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    limits: dict


class TierResponse(BaseModel):
    key: str
    name: str
    price_gbp: int
    description: str
    features: list[str]
    limits: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for upgrading to a paid tier."""
    if body.tier not in VALID_TIERS or body.tier == "free":
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid tier for checkout: {body.tier}"},
        )

    url = create_checkout_session(
        db=db,
        user=current_user,
        tier=body.tier,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    body: PortalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Billing Portal session for subscription management."""
    url = create_billing_portal_session(
        db=db,
        user=current_user,
        return_url=body.return_url,
    )

    return PortalResponse(portal_url=url)


@router.get("/status", response_model=BillingStatusResponse)
def get_billing_status(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's billing/tier status."""
    tier = get_user_tier(current_user)
    tier_def = TIERS.get(tier, TIERS["free"])

    return BillingStatusResponse(
        tier=tier,
        tier_name=tier_def.name,
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        limits=tier_def.limits,
    )


@router.get("/tiers", response_model=list[TierResponse])
def list_tiers():
    """List all available subscription tiers with features and pricing."""
    return [
        TierResponse(
            key=t.key,
            name=t.name,
            price_gbp=t.price_gbp,
            description=t.description,
            features=list(t.features),
            limits=t.limits,
        )
        for t in TIERS.values()
    ]


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """Handle incoming Stripe webhook events."""
    if not stripe_signature:
        return JSONResponse(status_code=400, content={"detail": "Missing stripe-signature header"})

    payload = await request.body()

    try:
        result = process_webhook_event(db, payload, stripe_signature)
        return result
    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        logger.error("Webhook processing error: %s", e)
        return JSONResponse(status_code=500, content={"detail": "Webhook processing failed"})
