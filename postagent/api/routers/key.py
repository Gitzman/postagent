"""GET /v1/key/{handle} — fast path to get just the public key."""

from fastapi import APIRouter, HTTPException

from postagent.api import db
from postagent.api.models import KeyResponse

router = APIRouter()


@router.get("/v1/key/{handle}", response_model=KeyResponse)
async def get_key(handle: str) -> KeyResponse:
    row = await db.get_agent_by_handle(handle)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return KeyResponse(handle=row["handle"], public_key=row["public_key"])
