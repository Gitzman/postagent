"""MQTT broker auth endpoints for mosquitto-go-auth HTTP backend.

These endpoints let the MQTT broker validate connections and ACLs against
the PostAgent registry.  Agents authenticate with ``username=<handle>``
and ``password=<wallet>``.  The broker calls these endpoints on every
CONNECT and PUBLISH/SUBSCRIBE.
"""

from fastapi import APIRouter, Form, Response

from postagent.api import db

router = APIRouter(tags=["mqtt-auth"])


@router.post("/v1/mqtt/auth")
async def mqtt_user_auth(
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    """Validate an MQTT connection.

    mosquitto-go-auth sends ``username`` (handle) and ``password`` (wallet)
    as form-encoded fields.  Return 200 to allow, 403 to deny.
    """
    agent = await db.get_agent_by_handle(username)
    if agent is None:
        return Response(status_code=403)
    if agent["wallet"] != password:
        return Response(status_code=403)
    return Response(status_code=200)


@router.post("/v1/mqtt/superuser")
async def mqtt_superuser(
    username: str = Form(...),
) -> Response:
    """Superuser check — no agents are superusers."""
    return Response(status_code=403)


@router.post("/v1/mqtt/acl")
async def mqtt_acl_check(
    username: str = Form(...),
    topic: str = Form(...),
    acc: int = Form(...),  # 1=subscribe, 2=publish
) -> Response:
    """Check topic-level access.

    Agents may subscribe to ``postagent/agents/{their_handle}/#`` and
    publish to ``postagent/agents/{any_handle}/inbox``.
    """
    parts = topic.split("/")
    # All PostAgent topics start with postagent/agents/{handle}/...
    if len(parts) < 4 or parts[0] != "postagent" or parts[1] != "agents":
        return Response(status_code=403)

    target_handle = parts[2]

    if acc == 1:
        # Subscribe: only to your own topics
        if target_handle != username:
            return Response(status_code=403)
    elif acc == 2:
        # Publish: to any agent's inbox (for sending messages) or your own status
        subtopic = parts[3] if len(parts) > 3 else ""
        if subtopic == "inbox":
            pass  # anyone can publish to any inbox
        elif subtopic == "status" and target_handle == username:
            pass  # you can set your own status
        else:
            return Response(status_code=403)

    return Response(status_code=200)
