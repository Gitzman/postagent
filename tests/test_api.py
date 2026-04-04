"""Tests for FastAPI endpoints using mocked database."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import base58
from fastapi.testclient import TestClient
from nacl.signing import SigningKey

from postagent.api.db import _Row
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


# --- Deregister tests ---


def _make_wallet_and_proof(nonce: str) -> tuple[str, str]:
    """Generate a wallet and valid proof for a given nonce."""
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()
    sig = sk.sign(nonce.encode())
    proof = base58.b58encode(sig.signature).decode()
    return wallet, proof


@patch("postagent.api.routers.deregister.db.delete_agent_card", new_callable=AsyncMock)
@patch("postagent.api.routers.deregister.db.delete_challenge", new_callable=AsyncMock)
@patch("postagent.api.routers.deregister.db.get_challenge", new_callable=AsyncMock)
@patch("postagent.api.routers.deregister.db.get_agent_by_handle", new_callable=AsyncMock)
def test_deregister_success(mock_get_agent, mock_get_challenge, mock_del_challenge, mock_del_card):
    nonce = "abc123"
    wallet, proof = _make_wallet_and_proof(nonce)
    expires = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()

    mock_get_agent.return_value = _Row({"wallet": wallet, "handle": "alice"})
    mock_get_challenge.return_value = _Row({"nonce": nonce, "expires_at": expires})
    mock_del_card.return_value = True

    resp = client.request(
        "DELETE",
        "/v1/agents/alice",
        json={"wallet": wallet, "proof": proof},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["handle"] == "alice"
    assert data["status"] == "deleted"
    mock_del_card.assert_called_once_with("alice", wallet)


@patch("postagent.api.routers.deregister.db.get_agent_by_handle", new_callable=AsyncMock)
def test_deregister_wrong_wallet(mock_get_agent):
    mock_get_agent.return_value = _Row({"wallet": "real-wallet", "handle": "alice"})

    resp = client.request(
        "DELETE",
        "/v1/agents/alice",
        json={"wallet": "wrong-wallet", "proof": "fakeproof"},
    )
    assert resp.status_code == 401
    assert "Wallet does not match" in resp.json()["detail"]


@patch("postagent.api.routers.deregister.db.get_agent_by_handle", new_callable=AsyncMock)
def test_deregister_not_found(mock_get_agent):
    mock_get_agent.return_value = None

    resp = client.request(
        "DELETE",
        "/v1/agents/nonexistent",
        json={"wallet": "somewallet", "proof": "fakeproof"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
