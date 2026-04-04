"""Tests for MQTT broker auth endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from postagent.api.main import app

client = TestClient(app)


def _mock_agent(handle: str = "alice", wallet: str = "wallet123"):
    """Return a mock agent row."""
    mock = AsyncMock()
    mock.__getitem__ = lambda self, key: {"handle": handle, "wallet": wallet}[key]
    return mock


@patch("postagent.api.routers.mqtt_auth.db.get_agent_by_handle", new_callable=AsyncMock)
def test_auth_valid_credentials(mock_get):
    mock_get.return_value = _mock_agent()
    resp = client.post("/v1/mqtt/auth", data={"username": "alice", "password": "wallet123"})
    assert resp.status_code == 200


@patch("postagent.api.routers.mqtt_auth.db.get_agent_by_handle", new_callable=AsyncMock)
def test_auth_unknown_handle(mock_get):
    mock_get.return_value = None
    resp = client.post("/v1/mqtt/auth", data={"username": "unknown", "password": "x"})
    assert resp.status_code == 403


@patch("postagent.api.routers.mqtt_auth.db.get_agent_by_handle", new_callable=AsyncMock)
def test_auth_wrong_wallet(mock_get):
    mock_get.return_value = _mock_agent()
    resp = client.post("/v1/mqtt/auth", data={"username": "alice", "password": "wrong"})
    assert resp.status_code == 403


def test_superuser_always_denied():
    resp = client.post("/v1/mqtt/superuser", data={"username": "alice"})
    assert resp.status_code == 403


def test_acl_subscribe_own_inbox():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "postagent/agents/alice/inbox", "acc": "1"},
    )
    assert resp.status_code == 200


def test_acl_subscribe_other_inbox_denied():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "postagent/agents/bob/inbox", "acc": "1"},
    )
    assert resp.status_code == 403


def test_acl_publish_to_any_inbox():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "postagent/agents/bob/inbox", "acc": "2"},
    )
    assert resp.status_code == 200


def test_acl_publish_own_status():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "postagent/agents/alice/status", "acc": "2"},
    )
    assert resp.status_code == 200


def test_acl_publish_other_status_denied():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "postagent/agents/bob/status", "acc": "2"},
    )
    assert resp.status_code == 403


def test_acl_invalid_topic_denied():
    resp = client.post(
        "/v1/mqtt/acl",
        data={"username": "alice", "topic": "random/topic", "acc": "1"},
    )
    assert resp.status_code == 403
