"""DELETE /v1/agents/{handle} — deregister an agent after proving wallet ownership."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from postagent.api import auth, db
from postagent.api.models import DeregisterRequest, DeregisterResponse

router = APIRouter()


@router.delete("/v1/agents/{handle}", response_model=DeregisterResponse)
async def deregister_agent(handle: str, req: DeregisterRequest) -> DeregisterResponse:
    # Verify the agent exists
    agent = await db.get_agent_by_handle(handle)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")

    # Verify the caller owns this handle's wallet
    if agent["wallet"] != req.wallet:
        raise HTTPException(status_code=401, detail="Wallet does not match this handle.")

    # Fetch and validate challenge
    challenge = await db.get_challenge(req.wallet)
    if challenge is None:
        raise HTTPException(status_code=400, detail="No challenge found. Request one first.")

    if challenge["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
        await db.delete_challenge(req.wallet)
        raise HTTPException(status_code=400, detail="Challenge expired. Request a new one.")

    # Verify Ed25519 signature
    if not auth.verify_signature(req.wallet, challenge["nonce"], req.proof):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    # Consume the challenge
    await db.delete_challenge(req.wallet)

    # Delete the agent card
    await db.delete_agent_card(handle, req.wallet)

    return DeregisterResponse(handle=handle, status="deleted")
