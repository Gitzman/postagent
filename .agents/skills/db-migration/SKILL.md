---
name: db-migration
description: Validate database schema changes when schema.sql or db.py is modified. Checks for destructive operations, verifies queries match schema, and tests migrations.
trigger: When schema.sql or postagent/api/db.py changes
output: Migration safety report — destructive change warnings, query/schema alignment check
---

# Database Migration Verification

## Architecture
PostAgent uses dual database backends:
- **SQLite** (local dev/deploy) — tables auto-created in `db.py:_init_sqlite_tables()`
- **Postgres** (production) — schema defined in `schema.sql`

Both must stay in sync. SQLite uses `?` params and JSON-serialized arrays; Postgres uses `$N` params and native `TEXT[]` arrays.

## Steps
1. Diff `schema.sql` against the last committed version
2. Diff `postagent/api/db.py` — check both the SQLite table creation and Postgres query paths
3. Flag any destructive operations (DROP, ALTER column type, remove NOT NULL)
4. Verify all queries in `db.py` reference valid tables/columns from both schemas
5. If adding a column: ensure it's added to both the SQLite `CREATE TABLE` in `db.py` AND `schema.sql`
6. Run `pytest tests/test_api.py -v` to verify queries work against SQLite

## Decision Model
- Additive changes (new tables, new columns, new indexes) are safe but must be applied to BOTH backends
- Destructive changes require explicit acknowledgment
- Query/schema mismatches are blocking
- SQLite `_init_sqlite_tables()` is the source of truth for dev; `schema.sql` is the source of truth for production
