"""Tests for the freemium handle model: ephemeral + permanent handles."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import base58
from fastapi.testclient import TestClient
from nacl.signing import SigningKey

from postagent.api.db import _Row
from postagent.api.main import app

client = TestClient(app)


def _make_agent_row(handle: str, expires_at: str | None = None) -> _Row:
    """Create a mock agent card row."""
    now = datetime.now(UTC).isoformat()
    return _Row(
        {
            "id": "test-id",
            "handle": handle,
            "wallet": "testwallet",
            "public_key": "testpk",
            "endpoint": None,
            "capabilities": "[]",
            "schema_url": None,
            "pricing_amount": None,
            "pricing_currency": None,
            "pricing_protocol": None,
            "description": None,
            "channels": "[]",
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
        }
    )


def _register_payload(handle: str = "testhandle") -> dict:
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()
    nonce = "a" * 64
    sig = sk.sign(nonce.encode())
    proof = base58.b58encode(sig.signature).decode()
    return {
        "handle": handle,
        "wallet": wallet,
        "proof": proof,
        "public_key": "fakepk",
        "nonce": nonce,
        "signing_key": sk,
    }


@patch("postagent.api.routers.register.db.insert_agent_card", new_callable=AsyncMock)
@patch("postagent.api.routers.register.db.delete_challenge", new_callable=AsyncMock)
@patch("postagent.api.routers.register.auth.verify_signature", return_value=True)
@patch("postagent.api.routers.register.db.get_challenge", new_callable=AsyncMock)
def test_register_sets_expires_at(mock_get_chal, mock_verify, mock_del, mock_insert):
    """Free registration should set expires_at ~24 hours from now."""
    future = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    mock_get_chal.return_value = _Row({"nonce": "a" * 64, "expires_at": future})

    data = _register_payload("ephemeral-test")
    resp = client.post(
        "/v1/register",
        json={
            "handle": data["handle"],
            "wallet": data["wallet"],
            "proof": data["proof"],
            "public_key": data["public_key"],
        },
    )

    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "registered"
    assert result["expires_at"] is not None

    # Verify expires_at is ~24h from now
    expires = datetime.fromisoformat(result["expires_at"])
    now = datetime.now(UTC)
    diff = expires - now
    assert timedelta(hours=23) < diff < timedelta(hours=25)

    # Verify insert_agent_card was called with expires_at
    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args
    assert call_kwargs.kwargs.get("expires_at") is not None


@patch("postagent.api.routers.resolve.db.get_agent_by_handle", new_callable=AsyncMock)
def test_resolve_shows_expires_at(mock_get):
    """Resolve should include expires_at in the response."""
    future = (datetime.now(UTC) + timedelta(hours=20)).isoformat()
    mock_get.return_value = _make_agent_row("ephemeral-agent", expires_at=future)

    resp = client.get("/v1/resolve/ephemeral-agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is not None
    assert "ephemeral-agent" == data["handle"]


@patch("postagent.api.routers.resolve.db.get_agent_by_handle", new_callable=AsyncMock)
def test_resolve_permanent_handle_no_expires(mock_get):
    """Permanent handles should have expires_at = null."""
    mock_get.return_value = _make_agent_row("permanent-agent", expires_at=None)

    resp = client.get("/v1/resolve/permanent-agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is None


@patch("postagent.api.routers.checkout.STRIPE_SECRET_KEY", "sk_test_fake")
@patch("postagent.api.routers.checkout.db.get_agent_by_handle", new_callable=AsyncMock)
def test_checkout_agent_not_found(mock_get):
    """Checkout for nonexistent agent should 404."""
    mock_get.return_value = None
    resp = client.post("/v1/checkout/nonexistent")
    assert resp.status_code == 404


@patch("postagent.api.routers.checkout.STRIPE_SECRET_KEY", "sk_test_fake")
@patch("postagent.api.routers.checkout.db.get_agent_by_handle", new_callable=AsyncMock)
def test_checkout_already_permanent(mock_get):
    """Checkout for already-permanent handle should 400."""
    mock_get.return_value = _make_agent_row("perm-agent", expires_at=None)
    resp = client.post("/v1/checkout/perm-agent")
    assert resp.status_code == 400
    assert "already permanent" in resp.json()["detail"]


@patch("postagent.api.routers.checkout.STRIPE_SECRET_KEY", "")
def test_checkout_stripe_not_configured():
    """Checkout without Stripe config should 503."""
    resp = client.post("/v1/checkout/anyhandle")
    assert resp.status_code == 503


@patch("postagent.api.routers.webhook.db.update_agent_expires_at", new_callable=AsyncMock)
@patch("postagent.api.routers.webhook.db.get_agent_by_handle", new_callable=AsyncMock)
@patch("postagent.api.routers.webhook.STRIPE_WEBHOOK_SECRET", "whsec_test")
def test_webhook_upgrades_handle(mock_get, mock_update):
    """Stripe webhook should set expires_at to null (permanent)."""
    mock_get.return_value = _make_agent_row("upgrade-me", expires_at="2026-04-05T00:00:00+00:00")

    event_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"handle": "upgrade-me"},
            }
        },
    }

    # Mock stripe.Webhook.construct_event to return our event
    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        resp = client.post(
            "/v1/webhook/stripe",
            content=b"fake-payload",
            headers={"stripe-signature": "fake-sig"},
        )

    assert resp.status_code == 200
    mock_update.assert_called_once_with("upgrade-me", expires_at=None)


@patch("postagent.api.routers.webhook.STRIPE_WEBHOOK_SECRET", "")
def test_webhook_no_secret():
    """Webhook without secret configured should 503."""
    resp = client.post(
        "/v1/webhook/stripe",
        content=b"fake",
        headers={"stripe-signature": "fake"},
    )
    assert resp.status_code == 503
