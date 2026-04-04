"""GET /v1/resolve/{handle} — look up an agent card by handle."""

from fastapi import APIRouter, HTTPException

from postagent.api import db
from postagent.api.models import AgentCard

router = APIRouter()


def _record_to_card(row) -> AgentCard:
    expires_at_val = row["expires_at"]
    return AgentCard(
        id=str(row["id"]),
        handle=row["handle"],
        wallet=row["wallet"],
        public_key=row["public_key"],
        endpoint=row["endpoint"],
        capabilities=list(row["capabilities"]),
        schema_url=row["schema_url"],
        pricing_amount=row["pricing_amount"],
        pricing_currency=row["pricing_currency"],
        pricing_protocol=row["pricing_protocol"],
        description=row["description"],
        channels=row["channels"] or [],
        expires_at=expires_at_val.isoformat() if expires_at_val else None,
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.get("/v1/resolve/{handle}", response_model=AgentCard)
async def resolve_agent(handle: str) -> AgentCard:
    row = await db.get_agent_by_handle(handle)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return _record_to_card(row)
