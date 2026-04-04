"""Database layer — uses SQLite locally, Postgres in production.

Set DATABASE_URL=postgresql://... to use Postgres (asyncpg).
Otherwise defaults to SQLite at SQLITE_PATH (default: ./postagent.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

DATABASE_URL = os.environ.get("DATABASE_URL")

# ---------------------------------------------------------------------------
# Row wrapper — normalises access across SQLite rows and asyncpg Records
# ---------------------------------------------------------------------------


class _Row:
    """Dict-key access with automatic JSON/datetime parsing for SQLite rows.

    asyncpg Records already return native Python types, so we pass them
    through directly.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        val = self._data[key]
        if key in ("capabilities", "channels") and isinstance(val, str):
            return json.loads(val)
        if key in ("expires_at", "created_at", "updated_at") and isinstance(val, str):
            return datetime.fromisoformat(val)
        return val


# ---------------------------------------------------------------------------
# SQLite backend (default for local dev / demo)
# ---------------------------------------------------------------------------

_DB_PATH = os.environ.get("SQLITE_PATH", "postagent.db")
_sqlite_conn: sqlite3.Connection | None = None


def _get_sqlite_conn() -> sqlite3.Connection:
    global _sqlite_conn
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(_DB_PATH)
        _sqlite_conn.row_factory = sqlite3.Row
        _sqlite_conn.execute("PRAGMA journal_mode=WAL")
        _init_sqlite_tables(_sqlite_conn)
    return _sqlite_conn


def _init_sqlite_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_cards (
            id              TEXT PRIMARY KEY,
            handle          TEXT UNIQUE NOT NULL,
            wallet          TEXT UNIQUE NOT NULL,
            public_key      TEXT NOT NULL,
            endpoint        TEXT,
            capabilities    TEXT NOT NULL DEFAULT '[]',
            schema_url      TEXT,
            pricing_amount  REAL,
            pricing_currency TEXT DEFAULT 'USDC',
            pricing_protocol TEXT DEFAULT 'x402',
            description     TEXT,
            channels        TEXT DEFAULT '[]',
            expires_at      TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS challenges (
            wallet      TEXT PRIMARY KEY,
            nonce       TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Postgres backend (production)
# ---------------------------------------------------------------------------

_pg_pool: Any = None  # asyncpg.Pool when initialised


async def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        import asyncpg

        _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pg_pool


# ---------------------------------------------------------------------------
# Public async API (same interface whether SQLite or Postgres)
# ---------------------------------------------------------------------------

_use_pg = DATABASE_URL is not None


async def get_pool():
    """Initialise and return the connection pool (or SQLite connection)."""
    if _use_pg:
        return await _get_pg_pool()
    return _get_sqlite_conn()


async def close_pool() -> None:
    global _sqlite_conn, _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
    if _sqlite_conn:
        _sqlite_conn.close()
        _sqlite_conn = None


# --- Challenges ---


async def upsert_challenge(wallet: str, nonce: str, expires_at: str) -> None:
    if _use_pg:
        pool = await _get_pg_pool()
        await pool.execute(
            """
            INSERT INTO challenges (wallet, nonce, expires_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (wallet) DO UPDATE SET nonce = $2, expires_at = $3
            """,
            wallet,
            nonce,
            expires_at,
        )
    else:
        conn = _get_sqlite_conn()
        conn.execute(
            """
            INSERT INTO challenges (wallet, nonce, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT (wallet) DO UPDATE SET nonce = ?, expires_at = ?
            """,
            (wallet, nonce, expires_at, nonce, expires_at),
        )
        conn.commit()


async def get_challenge(wallet: str) -> _Row | None:
    if _use_pg:
        pool = await _get_pg_pool()
        row = await pool.fetchrow(
            "SELECT nonce, expires_at FROM challenges WHERE wallet = $1", wallet
        )
        return _Row(dict(row)) if row else None
    else:
        conn = _get_sqlite_conn()
        row = conn.execute(
            "SELECT nonce, expires_at FROM challenges WHERE wallet = ?", (wallet,)
        ).fetchone()
        return _Row(dict(row)) if row else None


async def delete_challenge(wallet: str) -> None:
    if _use_pg:
        pool = await _get_pg_pool()
        await pool.execute("DELETE FROM challenges WHERE wallet = $1", wallet)
    else:
        conn = _get_sqlite_conn()
        conn.execute("DELETE FROM challenges WHERE wallet = ?", (wallet,))
        conn.commit()


# --- Agent Cards ---


async def insert_agent_card(
    handle: str,
    wallet: str,
    public_key: str,
    capabilities: list[str],
    pricing_amount: float | None,
    pricing_currency: str | None,
    pricing_protocol: str | None,
    description: str | None,
    expires_at: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    if _use_pg:
        pool = await _get_pg_pool()
        await pool.execute(
            """
            INSERT INTO agent_cards (handle, wallet, public_key, capabilities,
                pricing_amount, pricing_currency, pricing_protocol, description,
                expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            handle,
            wallet,
            public_key,
            capabilities,
            pricing_amount,
            pricing_currency,
            pricing_protocol,
            description,
            expires_at,
            now,
            now,
        )
    else:
        conn = _get_sqlite_conn()
        conn.execute(
            """
            INSERT INTO agent_cards (id, handle, wallet, public_key, capabilities,
                pricing_amount, pricing_currency, pricing_protocol, description,
                expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                handle,
                wallet,
                public_key,
                json.dumps(capabilities),
                pricing_amount,
                pricing_currency,
                pricing_protocol,
                description,
                expires_at,
                now,
                now,
            ),
        )
        conn.commit()


async def update_agent_expires_at(handle: str, expires_at: str | None) -> None:
    """Update the expires_at field for an agent card (used by Stripe webhook)."""
    now = datetime.now(UTC).isoformat()
    if _use_pg:
        pool = await _get_pg_pool()
        await pool.execute(
            "UPDATE agent_cards SET expires_at = $1, updated_at = $2 WHERE handle = $3",
            expires_at,
            now,
            handle,
        )
    else:
        conn = _get_sqlite_conn()
        conn.execute(
            "UPDATE agent_cards SET expires_at = ?, updated_at = ? WHERE handle = ?",
            (expires_at, now, handle),
        )
        conn.commit()


async def get_agent_by_handle(handle: str) -> _Row | None:
    if _use_pg:
        pool = await _get_pg_pool()
        row = await pool.fetchrow("SELECT * FROM agent_cards WHERE handle = $1", handle)
        return _Row(dict(row)) if row else None
    else:
        conn = _get_sqlite_conn()
        row = conn.execute("SELECT * FROM agent_cards WHERE handle = ?", (handle,)).fetchone()
        return _Row(dict(row)) if row else None


async def delete_agent_card(handle: str, wallet: str) -> bool:
    """Delete an agent card if the wallet matches. Returns True if a row was deleted."""
    if _use_pg:
        pool = await _get_pg_pool()
        result = await pool.execute(
            "DELETE FROM agent_cards WHERE handle = $1 AND wallet = $2",
            handle,
            wallet,
        )
        # asyncpg returns e.g. "DELETE 1" or "DELETE 0"
        return result.endswith("1")
    else:
        conn = _get_sqlite_conn()
        cur = conn.execute(
            "DELETE FROM agent_cards WHERE handle = ? AND wallet = ?",
            (handle, wallet),
        )
        conn.commit()
        return cur.rowcount > 0


async def discover_agents(capability: str, limit: int = 10, offset: int = 0) -> list[_Row]:
    if _use_pg:
        pool = await _get_pg_pool()
        rows = await pool.fetch(
            """
            SELECT * FROM agent_cards
            WHERE $1 = ANY(capabilities)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            capability,
            limit,
            offset,
        )
        return [_Row(dict(r)) for r in rows]
    else:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            """
            SELECT * FROM agent_cards
            WHERE capabilities LIKE ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (f'%"{capability}"%', limit, offset),
        ).fetchall()
        return [_Row(dict(r)) for r in rows]
