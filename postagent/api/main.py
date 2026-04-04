"""FastAPI application for PostAgent."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from postagent.api import db
from postagent.api.routers import challenge, checkout, discover, key, register, resolve, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await db.close_pool()


app = FastAPI(
    title="PostAgent",
    description="Encrypted message broker for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(challenge.router)
app.include_router(register.router)
app.include_router(resolve.router)
app.include_router(discover.router)
app.include_router(key.router)
app.include_router(checkout.router)
app.include_router(webhook.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
