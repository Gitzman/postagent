"""Tests for Ed25519 challenge-response auth."""

import base58
from nacl.signing import SigningKey

from postagent.api.auth import generate_nonce, verify_signature


def test_verify_valid_signature():
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()
    nonce = generate_nonce()

    sig = sk.sign(nonce.encode())
    proof = base58.b58encode(sig.signature).decode()

    assert verify_signature(wallet, nonce, proof) is True


def test_verify_invalid_signature():
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()
    nonce = generate_nonce()

    # Sign with a different key
    wrong_sk = SigningKey.generate()
    sig = wrong_sk.sign(nonce.encode())
    proof = base58.b58encode(sig.signature).decode()

    assert verify_signature(wallet, nonce, proof) is False


def test_verify_tampered_nonce():
    sk = SigningKey.generate()
    wallet = base58.b58encode(bytes(sk.verify_key)).decode()
    nonce = generate_nonce()

    sig = sk.sign(nonce.encode())
    proof = base58.b58encode(sig.signature).decode()

    assert verify_signature(wallet, "tampered_nonce", proof) is False
