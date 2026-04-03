"""GET /v1/discover — search agents by capability."""

from fastapi import APIRouter, Query

from postagent.api import db
from postagent.api.models import AgentCard
from postagent.api.routers.resolve import _record_to_card

router = APIRouter()


@router.get("/v1/discover", response_model=list[AgentCard])
async def discover_agents(
    capability: str = Query(..., description="Capability tag to search for"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AgentCard]:
    rows = await db.discover_agents(capability, limit, offset)
    return [_record_to_card(row) for row in rows]
