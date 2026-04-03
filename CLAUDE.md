# CLAUDE.md — PostAgent

## Project Overview
PostAgent is an encrypted message broker for AI agents. MQTT pub/sub with a public key directory. Agents register with a wallet/keypair, get an MQTT topic, and exchange end-to-end encrypted messages.

**Current state**: Working prototype. API, client library, CLI, and e2e demo all functional. Not yet deployed — runs locally with SQLite + local mosquitto.

### Code Locations
- `postagent/api/` — FastAPI server (registration, discovery, challenge-response auth)
- `postagent/api/routers/` — One file per endpoint: challenge, register, resolve, discover, key
- `postagent/api/db.py` — Database layer (SQLite for local dev, Postgres-ready for production)
- `postagent/api/auth.py` — Ed25519 challenge-response verification
- `postagent/api/models.py` — Pydantic request/response models
- `postagent/client/agent.py` — PostAgent client class (MQTT, encryption, API integration)
- `postagent/client/crypto.py` — NaCl box encrypt/decrypt helpers
- `postagent/cli/main.py` — Typer CLI: init, register, listen, send, discover, resolve, chat
- `schema.sql` — Postgres DDL (reference schema; SQLite tables auto-created by db.py)
- `scripts/` — Deterministic shell scripts for verification and dev tasks
- `.agents/skills/` — Agentic skill definitions for structured workflows

### Demo Setup
- `demo/alice/CLAUDE.md` — Instructions for Claude Code instance "Alice"
- `demo/bob/CLAUDE.md` — Instructions for Claude Code instance "Bob"
- `scripts/e2e-demo.py` — Automated two-agent encrypted message exchange

## Tech Stack
- Python 3.11+ / FastAPI / asyncpg (prod) / SQLite (dev) / PyNaCl / paho-mqtt / Typer
- Postgres for production (Fly.io)
- MQTT: local mosquitto for dev, test.mosquitto.org for remote

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `SQLITE_PATH` | `postagent.db` | SQLite database path (use `:memory:` for tests) |
| `DATABASE_URL` | — | Postgres DSN (when switching to production) |
| `MQTT_BROKER` | `test.mosquitto.org` | MQTT broker hostname |

## Mandatory Skill Usage

### When runtime code, tests, or build behavior changes:
Run `code-verification` skill — formats, lints, typechecks, and tests the project.

### When schema.sql or db.py changes:
Run `db-migration` skill — validates schema, checks for destructive changes, tests queries.

### When code work is ready for review:
Run `pr-draft-summary` skill — collects branch, diff, and commit info into a structured PR description.

### When testing agent-to-agent messaging:
Run `e2e-test` skill — registers two agents, exchanges encrypted messages, validates round-trip.

## Build & Test Commands
```bash
source .venv/bin/activate       # Always use the project venv
scripts/verify.sh               # Full verification: format + lint + typecheck + test
scripts/test.sh                 # Run pytest only
scripts/format.sh               # Run ruff format
scripts/lint.sh                 # Run ruff check
scripts/typecheck.sh            # Run mypy
scripts/dev.sh                  # Start FastAPI dev server (port 8000)
```

## Running Locally
```bash
# 1. Start mosquitto (must be installed via apt)
mosquitto -p 1883 -d

# 2. Start API server
source .venv/bin/activate
SQLITE_PATH=postagent.db MQTT_BROKER=localhost uvicorn postagent.api.main:app --port 8000

# 3a. CLI demo (two terminals):
#   Terminal A: postagent init --keypair ~/.postagent/alice.json && postagent register alice ... && postagent chat bob --keypair ~/.postagent/alice.json
#   Terminal B: postagent init --keypair ~/.postagent/bob.json && postagent register bob ... && postagent chat alice --keypair ~/.postagent/bob.json

# 3b. Claude Code demo (two terminals):
#   Terminal A: cd demo/alice && claude
#   Terminal B: cd demo/bob && claude
#   Each Claude instance uses the postagent CLI via its CLAUDE.md instructions
```

## API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/challenge` | Get a nonce for wallet authentication |
| POST | `/v1/register` | Register an agent card (requires signed challenge) |
| GET | `/v1/resolve/{handle}` | Look up an agent card by handle |
| GET | `/v1/discover?capability=X` | Search agents by capability tag |
| GET | `/v1/key/{handle}` | Fast path: get just the public key |
| GET | `/health` | Health check |

## Compatibility Rules
- Python 3.11+ required
- All public keys are base58-encoded Ed25519
- MQTT topics follow: `postagent/agents/{handle}/inbox|status|card`
- Message payloads are NaCl box encrypted, base64-encoded
- API versioned under `/v1/`

## What NOT to Build (Yet)
- No broker infrastructure — use mosquitto locally or test.mosquitto.org
- No payment processing — pricing metadata only, Stripe x402 later
- No message parsing/search/labeling — the agent is the LLM
- No wallet creation — agents bring their own keypairs
- No frontend
- No rate limiting or caching

## Next Steps
- [ ] Publish pip package to PyPI
- [ ] Deploy API to Fly.io with Postgres
- [ ] Switch to production MQTT broker
- [ ] Add message persistence / history
- [ ] README with curl + CLI walkthrough
