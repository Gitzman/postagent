---
name: db-migration
description: Validate database schema changes when schema.sql or db.py is modified. Checks for destructive operations, verifies queries match schema, and tests migrations.
trigger: When schema.sql or postagent/api/db.py changes
output: Migration safety report — destructive change warnings, query/schema alignment check
---

# Database Migration Verification

## Steps
1. Diff `schema.sql` against the last committed version
2. Flag any destructive operations (DROP, ALTER column type, remove NOT NULL)
3. Verify all queries in `db.py` reference valid tables/columns from schema
4. If Postgres is available, run `scripts/db-verify.sh` to apply schema and test queries

## Decision Model
- Additive changes (new tables, new columns, new indexes) are safe
- Destructive changes require explicit acknowledgment
- Query/schema mismatches are blocking
