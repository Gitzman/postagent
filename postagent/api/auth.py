"""Ed25519 challenge-response authentication."""

import secrets
from datetime import UTC, datetime, timedelta

import base58
from nacl.signing import VerifyKey


def generate_nonce() -> str:
    """Generate a 32-byte hex nonce."""
    return secrets.token_hex(32)


def nonce_expires_at(ttl_minutes: int = 5) -> str:
    """Return ISO timestamp for nonce expiry."""
    return (datetime.now(UTC) + timedelta(minutes=ttl_minutes)).isoformat()


def verify_signature(wallet_b58: str, nonce: str, proof_b58: str) -> bool:
    """Verify an Ed25519 signature of the nonce against the wallet public key.

    wallet_b58: base58-encoded Ed25519 public key
    nonce: the hex nonce string that was signed
    proof_b58: base58-encoded signature
    """
    try:
        pub_bytes = base58.b58decode(wallet_b58)
        sig_bytes = base58.b58decode(proof_b58)
        vk = VerifyKey(pub_bytes)
        vk.verify(nonce.encode(), sig_bytes)
        return True
    except Exception:
        return False
