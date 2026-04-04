"""POST /v1/checkout/{handle} — create a Stripe Checkout Session to upgrade a handle."""

import os

from fastapi import APIRouter, HTTPException

from postagent.api import db
from postagent.api.models import CheckoutResponse

router = APIRouter()

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
HANDLE_PRICE_CENTS = 100  # $1 USD


@router.post("/v1/checkout/{handle}", response_model=CheckoutResponse)
async def create_checkout(handle: str) -> CheckoutResponse:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    # Verify the handle exists
    agent = await db.get_agent_by_handle(handle)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found. Register first.")

    if agent["expires_at"] is None:
        raise HTTPException(status_code=400, detail="Handle is already permanent.")

    import stripe

    stripe.api_key = STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"PostAgent permanent handle: {handle}",
                        "description": "Upgrade from ephemeral (24h) to permanent.",
                    },
                    "unit_amount": HANDLE_PRICE_CENTS,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        metadata={"handle": handle},
        success_url="https://postagent.fly.dev/checkout/success?handle={CHECKOUT_SESSION_ID}",
        cancel_url="https://postagent.fly.dev/checkout/cancel",
    )

    return CheckoutResponse(checkout_url=session.url or "", session_id=session.id)
