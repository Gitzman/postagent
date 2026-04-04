CREATE TABLE agent_cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT UNIQUE NOT NULL,
    wallet          TEXT UNIQUE NOT NULL,
    public_key      TEXT NOT NULL,
    endpoint        TEXT,
    capabilities    TEXT[] NOT NULL DEFAULT '{}',
    schema_url      TEXT,
    pricing_amount  DECIMAL,
    pricing_currency TEXT DEFAULT 'USDC',
    pricing_protocol TEXT DEFAULT 'x402',
    description     TEXT,
    channels        JSONB DEFAULT '[]',
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capabilities ON agent_cards USING GIN (capabilities);

CREATE TABLE challenges (
    wallet      TEXT PRIMARY KEY,
    nonce       TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL
);
