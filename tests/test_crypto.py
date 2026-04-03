"""Tests for NaCl encryption helpers."""

from nacl.public import PrivateKey

from postagent.client.crypto import decrypt_message, encrypt_message


def test_encrypt_decrypt_roundtrip():
    """Two keypairs can exchange encrypted messages."""
    sender_key = PrivateKey.generate()
    recipient_key = PrivateKey.generate()

    plaintext = b"hello from agent-a"

    encrypted = encrypt_message(
        plaintext,
        bytes(recipient_key.public_key),
        sender_key,
    )

    # Encrypted output should be base64, not plaintext
    assert encrypted != plaintext.decode()

    decrypted = decrypt_message(
        encrypted,
        bytes(sender_key.public_key),
        recipient_key,
    )

    assert decrypted == plaintext


def test_different_messages_produce_different_ciphertext():
    sender_key = PrivateKey.generate()
    recipient_key = PrivateKey.generate()

    enc1 = encrypt_message(b"message one", bytes(recipient_key.public_key), sender_key)
    enc2 = encrypt_message(b"message two", bytes(recipient_key.public_key), sender_key)

    assert enc1 != enc2
