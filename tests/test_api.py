"""Tests for FastAPI endpoints using mocked database."""

from unittest.mock import AsyncMock, patch

import base58
from fastapi.testclient import TestClient
from nacl.signing import SigningKey

from postagent.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("postagent.api.routers.challenge.db.upsert_challenge", new_callable=AsyncMock)
def test_challenge(mock_upsert):
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()

    resp = client.post("/v1/challenge", json={"wallet": wallet})
    assert resp.status_code == 200
    data = resp.json()
    assert "nonce" in data
    assert "expires_at" in data
    assert len(data["nonce"]) == 64  # 32 bytes hex


def test_register_reserved_handle():
    resp = client.post(
        "/v1/register",
        json={
            "handle": "google",
            "wallet": "fakewallet",
            "proof": "fakeproof",
            "public_key": "fakepk",
        },
    )
    assert resp.status_code == 422
    assert "reserved" in resp.json()["detail"]


def test_register_invalid_handle_format():
    resp = client.post(
        "/v1/register",
        json={
            "handle": "A",
            "wallet": "fakewallet",
            "proof": "fakeproof",
            "public_key": "fakepk",
        },
    )
    assert resp.status_code == 422


@patch("postagent.api.routers.resolve.db.get_agent_by_handle", new_callable=AsyncMock)
def test_resolve_not_found(mock_get):
    mock_get.return_value = None
    resp = client.get("/v1/resolve/nonexistent")
    assert resp.status_code == 404


@patch("postagent.api.routers.discover.db.discover_agents", new_callable=AsyncMock)
def test_discover_empty(mock_discover):
    mock_discover.return_value = []
    resp = client.get("/v1/discover", params={"capability": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []
