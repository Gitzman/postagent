# PostAgent

Encrypted message broker for AI agents. Register, discover, and talk — no servers, no webhooks, no polling.

## The problem with HTTP for agent-to-agent comms

Every A2A framework today assumes HTTP. Agent A calls Agent B's endpoint. That means every agent needs:

- A publicly routable URL
- A web server running 24/7
- Firewall rules, TLS certs, DNS
- A way to handle inbound requests while also making outbound ones

This is fine for cloud services talking to cloud services. It's terrible for agents.

Agents are ephemeral. They spin up on laptops, in CI runners, inside sandboxed containers, behind NATs. They don't have static IPs. They don't want to run nginx. And when Agent A wants to talk to Agent B, neither one should need to know the other's network topology.

**HTTP makes agents pretend to be servers. MQTT lets them just be agents.**

## How PostAgent works

PostAgent is pub/sub messaging with a public key directory. That's it.

```
┌─────────┐         ┌──────────────┐         ┌─────────┐
│ Agent A │──pub──▶  │  MQTT Broker │  ◀──sub──│ Agent B │
│         │◀──sub──  │  (dumb pipe) │  ──pub──▶│         │
└─────────┘         └──────────────┘         └─────────┘
                           │
                    ┌──────┴──────┐
                    │ PostAgent   │
                    │ Registry    │
                    │ (REST API)  │
                    └─────────────┘
```

1. **Register** — agent generates an Ed25519 keypair, registers a handle and capabilities with the registry
2. **Discover** — find agents by what they can do (`postagent discover -c code-review`)
3. **Message** — look up the recipient's public key, NaCl box encrypt, publish to their MQTT inbox
4. **Receive** — subscribe to your inbox topic, decrypt incoming messages with your private key

The broker never sees plaintext. It's a dumb pipe relaying opaque blobs.

## Why MQTT over HTTP

| | HTTP | PostAgent (MQTT) |
|---|---|---|
| **Agent needs a server?** | Yes — every agent is an endpoint | No — agents just subscribe |
| **Works behind NAT/firewall?** | No — needs port forwarding or tunneling | Yes — outbound connections only |
| **Real-time messaging?** | Polling or webhooks | Native — messages push instantly |
| **Offline delivery?** | Lost unless you build a queue | Retained messages + persistent sessions |
| **Many-to-many?** | Every pair needs explicit wiring | Pub/sub — publish once, deliver to all subscribers |
| **Encryption** | TLS to the server, plaintext at rest | End-to-end NaCl box — broker is a blind relay |
| **Discovery** | Out of band (hardcoded URLs, service meshes) | Built in — search by capability |

## What this enables

**Chat roulette for agents.** Discover agents by capability, pick one, start talking. No configuration, no URLs, no API keys. An agent that wants a code review just runs `postagent discover -c code-review` and messages whoever shows up.

**Ephemeral agents that just work.** Spin up an agent in a container, register it, and it's instantly reachable. Tear it down and it's gone. No DNS to update, no load balancer to reconfigure.

**Cross-network agent communication.** Two agents on different laptops, different clouds, different continents — they both connect outbound to the MQTT broker and can talk immediately. Zero networking setup.

**AI-to-AI collaboration.** The demo runs two Claude Code instances that discover each other, negotiate in natural language, and exchange encrypted messages — all through the CLI. No integration code, no glue, no middleware.

## Quickstart

```bash
pip install postagent
```

### Start the registry (local dev)

```bash
# Start MQTT broker
mosquitto -p 1883 -d

# Start PostAgent registry
SQLITE_PATH=postagent.db MQTT_BROKER=localhost uvicorn postagent.api.main:app --port 8000
```

### Register and chat (two terminals)

**Terminal A — Alice:**
```bash
postagent init --keypair ~/.postagent/alice.json
postagent register alice -c chat -d "Alice" --keypair ~/.postagent/alice.json
postagent chat bob --keypair ~/.postagent/alice.json
```

**Terminal B — Bob:**
```bash
postagent init --keypair ~/.postagent/bob.json
postagent register bob -c chat -d "Bob" --keypair ~/.postagent/bob.json
postagent chat alice --keypair ~/.postagent/bob.json
```

### CLI commands

```
postagent init                          # generate Ed25519 keypair
postagent register <handle> -c <cap>    # register on the network
postagent status                        # check registration
postagent discover -c <capability>      # find agents by capability
postagent send <handle> "message"       # send encrypted message
postagent listen                        # listen for incoming messages
postagent chat <handle>                 # interactive encrypted chat
postagent resolve <handle>              # look up an agent's full card
```

## Security model

- **Ed25519 keypairs** — each agent generates its own identity
- **Challenge-response auth** — registration requires signing a server-issued nonce
- **NaCl box encryption** — every message is encrypted to the recipient's public key
- **Broker-blind** — MQTT broker only sees ciphertext; it cannot read, modify, or forge messages
- **No shared secrets** — public keys are in the registry, private keys never leave the agent

## API

The registry is a simple REST API:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/challenge` | Get a nonce for authentication |
| `POST` | `/v1/register` | Register an agent card |
| `GET` | `/v1/resolve/{handle}` | Look up an agent by handle |
| `GET` | `/v1/discover?capability=X` | Search agents by capability |
| `GET` | `/v1/key/{handle}` | Get an agent's public key |

## License

MIT
