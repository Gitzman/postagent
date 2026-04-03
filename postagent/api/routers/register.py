"""POST /v1/register — register an agent card after proving wallet ownership."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from postagent.api import auth, db
from postagent.api.models import RegisterRequest, RegisterResponse

router = APIRouter()


@router.post("/v1/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest) -> RegisterResponse:
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

    # Insert agent card
    pricing_amount = float(req.pricing.amount) if req.pricing else None
    pricing_currency = req.pricing.currency if req.pricing else None
    pricing_protocol = req.pricing.protocol if req.pricing else None

    try:
        await db.insert_agent_card(
            handle=req.handle,
            wallet=req.wallet,
            public_key=req.public_key,
            capabilities=req.capabilities,
            pricing_amount=pricing_amount,
            pricing_currency=pricing_currency,
            pricing_protocol=pricing_protocol,
            description=req.description,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Handle or wallet already registered.")
        raise

    topic = f"postagent/agents/{req.handle}/inbox"
    return RegisterResponse(handle=req.handle, status="registered", topic=topic)
