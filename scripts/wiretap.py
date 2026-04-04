#!/usr/bin/env python3
"""PostAgent Wiretap — watch encrypted agent conversations in real time.

Subscribes to all PostAgent MQTT traffic. If you provide both agents'
keypair files, it decrypts messages live. Otherwise shows metadata only.

Usage:
  # Metadata only (no decryption):
  python scripts/wiretap.py

  # Decrypt Alice ↔ Bob conversation:
  python scripts/wiretap.py --alice ~/.postagent/alice.json --bob ~/.postagent/bob.json

  # Watch a specific agent's inbox:
  python scripts/wiretap.py --topic "postagent/agents/alice/inbox"
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import base58
import paho.mqtt.client as mqtt
from nacl.public import Box, PrivateKey, PublicKey

MQTT_BROKER = os.environ.get("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = 1883


def load_keypair(path: str) -> tuple[PrivateKey, str]:
    """Load a keypair file and return (private_key, handle)."""
    data = json.loads(Path(path).expanduser().read_text())
    seed = base58.b58decode(data["secret_key"])
    return PrivateKey(seed[:32]), data.get("handle", "unknown")


def decrypt_payload(
    encrypted_b64: str, sender_pub_bytes: bytes, recipient_privkey: PrivateKey
) -> str:
    """Decrypt a NaCl box encrypted payload."""
    import base64

    encrypted = base64.b64decode(encrypted_b64)
    sender_pub = PublicKey(sender_pub_bytes)
    box = Box(recipient_privkey, sender_pub)
    plaintext = box.decrypt(encrypted)
    try:
        return json.loads(plaintext)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return plaintext.decode()


def main():
    parser = argparse.ArgumentParser(description="Watch PostAgent MQTT traffic")
    parser.add_argument("--alice", help="Path to Alice's keypair (for decryption)")
    parser.add_argument("--bob", help="Path to Bob's keypair (for decryption)")
    parser.add_argument("--topic", default="postagent/agents/#", help="MQTT topic filter")
    parser.add_argument("--broker", default=MQTT_BROKER, help="MQTT broker hostname")
    parser.add_argument(
        "--api",
        default=os.environ.get("POSTAGENT_API_URL", "https://postagent.fly.dev"),
        help="PostAgent API URL (for resolving public keys)",
    )
    args = parser.parse_args()

    # Load keypairs if provided
    keys = {}  # handle -> PrivateKey
    if args.alice:
        privkey, handle = load_keypair(args.alice)
        keys[handle] = privkey
        print(f"  Loaded keypair: {handle} ({args.alice})")
    if args.bob:
        privkey, handle = load_keypair(args.bob)
        keys[handle] = privkey
        print(f"  Loaded keypair: {handle} ({args.bob})")

    can_decrypt = len(keys) > 0

    # Cache for public keys
    pub_key_cache: dict[str, bytes] = {}

    def get_public_key(handle: str) -> bytes | None:
        if handle in pub_key_cache:
            return pub_key_cache[handle]
        try:
            import httpx

            resp = httpx.get(f"{args.api}/v1/key/{handle}")
            resp.raise_for_status()
            pub_b58 = resp.json()["public_key"]
            pub_bytes = base58.b58decode(pub_b58)
            pub_key_cache[handle] = pub_bytes
            return pub_bytes
        except Exception:
            return None

    print("\n  PostAgent Wiretap")
    print(f"  Broker: {args.broker}:{MQTT_PORT}")
    print(f"  Topic:  {args.topic}")
    print(f"  Decrypt: {'YES' if can_decrypt else 'NO (provide --alice/--bob keypairs)'}")
    print(f"  {'─' * 60}\n")

    def on_connect(client, userdata, flags, rc, props):
        client.subscribe(args.topic, qos=1)

    def on_message(client, userdata, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        topic = msg.topic

        # Status messages (online/offline)
        if topic.endswith("/status"):
            status = msg.payload.decode("utf-8", errors="replace")
            agent = topic.split("/")[-2]
            icon = "●" if status == "online" else "○"
            print(f"  {ts}  {icon} {agent} is {status}")
            return

        # Inbox messages
        try:
            envelope = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"  {ts}  ? {topic} (non-JSON payload)")
            return

        sender = envelope.get("from", "?")
        recipient = topic.split("/")[-2]
        encrypted_payload = envelope.get("encrypted_payload", "")

        print(f"  {ts}  ✉ {sender} → {recipient}  ({len(encrypted_payload)} chars encrypted)")

        # Try to decrypt
        if can_decrypt and encrypted_payload:
            # To decrypt: we need the recipient's private key and sender's public key
            recipient_key = keys.get(recipient)
            if recipient_key:
                sender_pub = get_public_key(sender)
                if sender_pub:
                    try:
                        plaintext = decrypt_payload(encrypted_payload, sender_pub, recipient_key)
                        if isinstance(plaintext, dict) and "msg" in plaintext:
                            print(f"         💬 {plaintext['msg']}")
                        elif isinstance(plaintext, dict):
                            print(f"         💬 {json.dumps(plaintext)}")
                        else:
                            print(f"         💬 {plaintext}")
                    except Exception as e:
                        print(f"         🔒 decrypt failed: {e}")
                else:
                    print(f"         🔒 (can't resolve {sender}'s public key)")
            else:
                print(f"         🔒 (no private key for {recipient})")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, MQTT_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n  Bye!")
        client.disconnect()


if __name__ == "__main__":
    main()
