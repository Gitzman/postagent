"""NaCl public-key encryption helpers."""

import base64

from nacl.public import Box, PrivateKey, PublicKey


def encrypt_message(
    message_bytes: bytes,
    recipient_pub_bytes: bytes,
    sender_priv_key: PrivateKey,
) -> str:
    """Encrypt a message using NaCl box. Returns base64-encoded ciphertext."""
    box = Box(sender_priv_key, PublicKey(recipient_pub_bytes))
    encrypted = box.encrypt(message_bytes)
    return base64.b64encode(encrypted).decode()


def decrypt_message(
    encrypted_b64: str,
    sender_pub_bytes: bytes,
    recipient_priv_key: PrivateKey,
) -> bytes:
    """Decrypt a base64-encoded NaCl box message. Returns plaintext bytes."""
    box = Box(recipient_priv_key, PublicKey(sender_pub_bytes))
    return box.decrypt(base64.b64decode(encrypted_b64))
