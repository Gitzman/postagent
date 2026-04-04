"""POST /v1/webhook/stripe — handle Stripe payment confirmations."""

import os

from fastapi import APIRouter, HTTPException, Request

from postagent.api import db

router = APIRouter()

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


@router.post("/v1/webhook/stripe")
async def stripe_webhook(request: Request) -> dict:
    import stripe

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload.")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature.")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle = session.get("metadata", {}).get("handle")

        if not handle:
            raise HTTPException(status_code=400, detail="No handle in session metadata.")

        # Upgrade handle to permanent (expires_at = null)
        agent = await db.get_agent_by_handle(handle)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found.")

        await db.update_agent_expires_at(handle, expires_at=None)

    return {"status": "ok"}
