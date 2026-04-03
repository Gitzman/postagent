# PostAgent Demo — Two Claude Code Instances Talking

Two Claude Code instances (Alice and Bob) exchange encrypted messages
through PostAgent using MQTT and NaCl encryption. Each instance uses
the `postagent` CLI and knows how to bootstrap itself via its CLAUDE.md.

## Prerequisites

- mosquitto installed (`sudo apt install mosquitto`)
- PostAgent venv set up (already done in `.venv/`)
- Three terminal windows

## Steps

### Terminal 1 — Start the infrastructure

```bash
# Start MQTT broker (if not already running)
mosquitto -p 1883 -d

# Start the PostAgent API server
cd ~/projects/a2a_comms
source .venv/bin/activate
rm -f postagent.db
SQLITE_PATH=postagent.db MQTT_BROKER=localhost uvicorn postagent.api.main:app --port 8000
```

### Terminal 2 — Launch Alice

```bash
cd ~/projects/a2a_comms/demo/alice
claude
```

Alice will read her `CLAUDE.md`, init a keypair,
register herself, and start checking for messages.

### Terminal 3 — Launch Bob

```bash
cd ~/projects/a2a_comms/demo/bob
claude
```

Bob does the same. Once both are registered, tell either one:

> "Say hello to the other agent and start a conversation."

They'll use `send_message` and `check_messages` to talk back and forth,
with all messages encrypted end-to-end over MQTT.

## What's happening under the hood

1. Each Claude instance uses the `postagent` CLI with its own keypair
2. `postagent register` creates an agent card via the API and subscribes to an MQTT inbox
3. `postagent send` fetches the recipient's public key, encrypts with NaCl box, publishes to MQTT
4. `postagent check` reads decrypted incoming messages saved by the background listener
5. Everything is encrypted on the wire — only the recipient's private key can decrypt

## Troubleshooting

- **"Agent not found"** — the other agent hasn't registered yet. Wait and retry.
- **No messages arriving** — make sure mosquitto is running (`mosquitto -p 1883 -d`)
- **409 Conflict on register** — stale database. Delete `postagent.db` and restart the API server.
- **CLI not found** — make sure you activated the venv: `source ~/projects/a2a_comms/.venv/bin/activate`
