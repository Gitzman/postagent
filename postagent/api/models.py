"""Pydantic models for PostAgent API."""

from decimal import Decimal

import pydantic


class ChallengeRequest(pydantic.BaseModel):
    wallet: str


class ChallengeResponse(pydantic.BaseModel):
    nonce: str
    expires_at: str


class PricingInfo(pydantic.BaseModel):
    amount: Decimal
    currency: str = "USDC"
    protocol: str = "x402"


class RegisterRequest(pydantic.BaseModel):
    handle: str
    wallet: str
    proof: str
    public_key: str
    capabilities: list[str] = []
    pricing: PricingInfo | None = None
    description: str | None = None


class RegisterResponse(pydantic.BaseModel):
    handle: str
    status: str
    topic: str
    expires_at: str | None = None


class AgentCard(pydantic.BaseModel):
    id: str
    handle: str
    wallet: str
    public_key: str
    endpoint: str | None = None
    capabilities: list[str] = []
    schema_url: str | None = None
    pricing_amount: Decimal | None = None
    pricing_currency: str | None = None
    pricing_protocol: str | None = None
    description: str | None = None
    channels: list = []
    expires_at: str | None = None
    created_at: str
    updated_at: str


class CheckoutResponse(pydantic.BaseModel):
    checkout_url: str
    session_id: str


class KeyResponse(pydantic.BaseModel):
    handle: str
    public_key: str


class DeregisterRequest(pydantic.BaseModel):
    wallet: str
    proof: str


class DeregisterResponse(pydantic.BaseModel):
    handle: str
    status: str
