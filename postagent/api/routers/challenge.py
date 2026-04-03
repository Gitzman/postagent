"""POST /v1/challenge — issue a nonce for wallet authentication."""

from fastapi import APIRouter

from postagent.api import auth, db
from postagent.api.models import ChallengeRequest, ChallengeResponse

router = APIRouter()


@router.post("/v1/challenge", response_model=ChallengeResponse)
async def create_challenge(req: ChallengeRequest) -> ChallengeResponse:
    nonce = auth.generate_nonce()
    expires_at = auth.nonce_expires_at()
    await db.upsert_challenge(req.wallet, nonce, expires_at)
    return ChallengeResponse(nonce=nonce, expires_at=expires_at)
