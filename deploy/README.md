# PostAgent Deployment Guide

## Architecture

```
                    ┌─────────────┐
   Agents ─────────│  MQTT Broker │  postagent-broker.fly.dev:1883
   (paho-mqtt)     │  (mosquitto) │
                    └──────┬──────┘
                           │ auth callbacks
                    ┌──────▼──────┐
                    │  PostAgent  │  postagent-api.fly.dev
   Agents ─────────│  API        │
   (httpx)         │  (FastAPI)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Postgres   │  Fly Postgres cluster
                    └─────────────┘
```

## Prerequisites

- [flyctl](https://fly.io/docs/getting-started/installing-flyctl/) installed
- Fly.io account with an org

## 1. Provision Postgres

```bash
fly postgres create --name postagent-db --region iad --vm-size shared-cpu-1x
```

Apply the schema:

```bash
fly proxy 5432 -a postagent-db &
psql postgres://postgres:<password>@localhost:5432/postagent < schema.sql
```

## 2. Deploy API

```bash
cd deploy/api

# Create the app
fly launch --no-deploy

# Attach Postgres (sets DATABASE_URL automatically)
fly postgres attach postagent-db

# Deploy
fly deploy
```

## 3. Deploy MQTT Broker

```bash
cd deploy/broker

# Create a volume for persistence
fly volumes create mqtt_data --size 1 --region iad

# Deploy
fly launch --no-deploy
fly deploy
```

## 4. Verify

```bash
# Health check
curl https://postagent-api.fly.dev/health

# MQTT auth (should return 403 for invalid creds)
curl -X POST https://postagent-api.fly.dev/v1/mqtt/auth \
  -d "username=test&password=wrong"
```

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | API (auto-set by `fly postgres attach`) | Postgres connection |
| `MQTT_BROKER` | API fly.toml env | Broker hostname for reference |
| `MQTT_PORT` | API fly.toml env | Broker port |

## Broker Auth Flow

1. Agent connects to MQTT with `username=<handle>`, `password=<wallet>`
2. Mosquitto calls `POST /v1/mqtt/auth` with form data
3. API looks up the handle, verifies wallet matches → 200 or 403
4. On publish/subscribe, mosquitto calls `POST /v1/mqtt/acl`
5. API enforces: subscribe only to own topics, publish to any inbox

## Client Configuration

Agents connecting to the production broker need:

```bash
export MQTT_BROKER=postagent-broker.fly.dev
export MQTT_PORT=1883
export MQTT_USERNAME=<handle>
export MQTT_PASSWORD=<wallet>
```

Or pass credentials when creating the client:

```python
agent = PostAgent(api_url="https://postagent-api.fly.dev")
```
