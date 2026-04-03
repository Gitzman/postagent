"""PostAgent client — MQTT + encryption + API integration."""

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import base58
import httpx
import paho.mqtt.client as mqtt
from nacl.public import PrivateKey
from nacl.signing import SigningKey

from postagent.client.crypto import decrypt_message, encrypt_message

MQTT_BROKER = os.environ.get("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = 1883
DEFAULT_API_URL = os.environ.get("POSTAGENT_API_URL", "https://postagent.fly.dev")


class PostAgent:
    """Client for registering, discovering, and messaging via PostAgent."""

    def __init__(
        self,
        keypair_path: str = "~/.postagent/keypair.json",
        api_url: str = DEFAULT_API_URL,
    ):
        self.api_url = api_url.rstrip("/")
        self.keypair_path = Path(keypair_path).expanduser()
        self.handle: str | None = None
        self._signing_key: SigningKey | None = None
        self._private_key: PrivateKey | None = None
        self._mqtt_client: mqtt.Client | None = None
        self._message_handler: Callable | None = None

        if self.keypair_path.exists():
            self._load_keypair()

    def _load_keypair(self) -> None:
        data = json.loads(self.keypair_path.read_text())
        seed = base58.b58decode(data["secret_key"])
        # Ed25519 signing key from 32-byte seed
        self._signing_key = SigningKey(seed[:32])
        # X25519 private key for encryption (derived from same seed)
        self._private_key = PrivateKey(seed[:32])
        self.handle = data.get("handle")

    def init_keypair(self) -> dict:
        """Generate a new Ed25519 keypair and save to disk."""
        self.keypair_path.parent.mkdir(parents=True, exist_ok=True)
        self._signing_key = SigningKey.generate()
        self._private_key = PrivateKey(bytes(self._signing_key)[:32])

        wallet = base58.b58encode(bytes(self._signing_key.verify_key)).decode()
        pub_key = base58.b58encode(bytes(self._private_key.public_key)).decode()

        data = {
            "secret_key": base58.b58encode(bytes(self._signing_key)).decode(),
            "wallet": wallet,
            "public_key": pub_key,
        }
        self.keypair_path.write_text(json.dumps(data, indent=2))
        return data

    @property
    def wallet(self) -> str:
        assert self._signing_key is not None, "No keypair loaded. Run init first."
        return base58.b58encode(bytes(self._signing_key.verify_key)).decode()

    @property
    def public_key_b58(self) -> str:
        assert self._private_key is not None, "No keypair loaded. Run init first."
        return base58.b58encode(bytes(self._private_key.public_key)).decode()

    def register(
        self,
        handle: str,
        capabilities: list[str] | None = None,
        price: float | None = None,
        currency: str = "USDC",
        description: str | None = None,
    ) -> dict:
        """Register this agent with the PostAgent API."""
        # Step 1: Get challenge
        resp = httpx.post(f"{self.api_url}/v1/challenge", json={"wallet": self.wallet})
        resp.raise_for_status()
        nonce = resp.json()["nonce"]

        # Step 2: Sign the nonce
        assert self._signing_key is not None
        sig = self._signing_key.sign(nonce.encode())
        proof = base58.b58encode(sig.signature).decode()

        # Step 3: Register
        body: dict = {
            "handle": handle,
            "wallet": self.wallet,
            "proof": proof,
            "public_key": self.public_key_b58,
            "capabilities": capabilities or [],
            "description": description,
        }
        if price is not None:
            body["pricing"] = {"amount": price, "currency": currency, "protocol": "x402"}

        resp = httpx.post(f"{self.api_url}/v1/register", json=body)
        resp.raise_for_status()

        self.handle = handle
        # Save handle back to keypair file
        if self.keypair_path.exists():
            data = json.loads(self.keypair_path.read_text())
            data["handle"] = handle
            self.keypair_path.write_text(json.dumps(data, indent=2))

        return resp.json()

    def resolve(self, handle: str) -> dict:
        """Look up an agent card by handle."""
        resp = httpx.get(f"{self.api_url}/v1/resolve/{handle}")
        resp.raise_for_status()
        return resp.json()

    def get_key(self, handle: str) -> str:
        """Get just the public key for an agent."""
        resp = httpx.get(f"{self.api_url}/v1/key/{handle}")
        resp.raise_for_status()
        return resp.json()["public_key"]

    def discover(self, capability: str, limit: int = 10) -> list[dict]:
        """Discover agents by capability tag."""
        resp = httpx.get(
            f"{self.api_url}/v1/discover",
            params={"capability": capability, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    def send(self, target_handle: str, payload: dict | str | bytes) -> None:
        """Encrypt and publish a message to another agent's inbox."""
        assert self.handle is not None, "Must register before sending."
        assert self._private_key is not None

        # Get recipient's public key
        recipient_pub_b58 = self.get_key(target_handle)
        recipient_pub_bytes = base58.b58decode(recipient_pub_b58)

        # Serialize payload
        if isinstance(payload, dict):
            message_bytes = json.dumps(payload).encode()
        elif isinstance(payload, str):
            message_bytes = payload.encode()
        else:
            message_bytes = payload

        # Encrypt
        encrypted = encrypt_message(message_bytes, recipient_pub_bytes, self._private_key)

        # Build envelope
        envelope = {
            "from": self.handle,
            "encrypted_payload": encrypted,
            "reply_to": f"postagent/agents/{self.handle}/inbox",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Publish via MQTT
        topic = f"postagent/agents/{target_handle}/inbox"
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.publish(topic, json.dumps(envelope).encode(), qos=1)
        client.disconnect()

    def reply(self, sender_handle: str, payload: dict | str | bytes) -> None:
        """Convenience method: send a message back to the sender."""
        self.send(sender_handle, payload)

    def listen(self, handler: Callable[[str, dict | bytes], None]) -> None:
        """Subscribe to inbox and call handler for each decrypted message. Blocking."""
        assert self.handle is not None, "Must register before listening."
        assert self._private_key is not None
        self._message_handler = handler

        topic = f"postagent/agents/{self.handle}/inbox"

        def on_connect(client, userdata, flags, reason_code, properties):
            client.subscribe(topic, qos=1)
            print(f"Listening on {topic}")

        def on_message(client, userdata, msg):
            try:
                envelope = json.loads(msg.payload.decode())
                sender = envelope["from"]

                # Get sender's encryption public key
                sender_pub_b58 = self.get_key(sender)
                sender_pub_bytes = base58.b58decode(sender_pub_b58)

                # Decrypt
                plaintext = decrypt_message(
                    envelope["encrypted_payload"],
                    sender_pub_bytes,
                    self._private_key,
                )

                # Try to parse as JSON
                try:
                    payload = json.loads(plaintext)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = plaintext

                handler(sender, payload)
            except Exception as e:
                print(f"Error processing message: {e}")

        self._mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_message = on_message
        self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

        # Publish online status
        status_topic = f"postagent/agents/{self.handle}/status"
        self._mqtt_client.will_set(status_topic, b"offline", qos=1, retain=True)
        self._mqtt_client.publish(status_topic, b"online", qos=1, retain=True)

        self._mqtt_client.loop_forever()

    def check(self, timeout: float = 5.0) -> list[dict]:
        """Subscribe to inbox, collect messages for `timeout` seconds, then return them.

        Non-blocking alternative to listen() — connects, waits briefly, disconnects.
        Returns a list of {"from": ..., "payload": ...} dicts.
        """
        assert self.handle is not None, "Must register before checking."
        assert self._private_key is not None

        messages: list[dict] = []
        topic = f"postagent/agents/{self.handle}/inbox"

        def on_connect(client, userdata, flags, reason_code, properties):
            client.subscribe(topic, qos=1)

        def on_message(client, userdata, msg):
            try:
                envelope = json.loads(msg.payload.decode())
                sender = envelope["from"]
                sender_pub_b58 = self.get_key(sender)
                sender_pub_bytes = base58.b58decode(sender_pub_b58)
                plaintext = decrypt_message(
                    envelope["encrypted_payload"],
                    sender_pub_bytes,
                    self._private_key,
                )
                try:
                    payload = json.loads(plaintext)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = plaintext
                messages.append({"from": sender, "payload": payload})
            except Exception as e:
                messages.append({"from": "system", "payload": f"Error: {e}"})

        import time

        # Persistent session with stable client ID so broker queues
        # QoS 1 messages while we're disconnected between checks
        client_id = f"postagent-{self.handle}-check"
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=False,
        )
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()

        time.sleep(timeout)

        client.loop_stop()
        client.disconnect()
        return messages

    def stop(self) -> None:
        """Stop listening."""
        if self._mqtt_client:
            if self.handle:
                status_topic = f"postagent/agents/{self.handle}/status"
                self._mqtt_client.publish(status_topic, b"offline", qos=1, retain=True)
            self._mqtt_client.disconnect()
