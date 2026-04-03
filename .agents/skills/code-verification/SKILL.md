---
name: code-verification
description: Run the mandatory verification stack when changes affect runtime code, tests, or build/test behavior. Formats, lints, typechecks, and runs tests. Must pass before any PR.
trigger: When runtime code (.py files in postagent/), tests, or build configuration changes
output: Structured pass/fail report with logs for each stage
---

# Code Verification

## Steps
1. Run `scripts/verify.sh` which executes in order:
   - `ruff format --check .` (formatting)
   - `ruff check .` (linting)
   - `mypy postagent/` (type checking)
   - `pytest tests/ -v` (tests)
2. If any step fails, collect the output and report which step failed and why.
3. If formatting fails, run `ruff format .` to auto-fix, then re-verify.

## Decision Model
- All four checks must pass for verification to succeed.
- Formatting issues are auto-fixable — fix and re-run.
- Lint/type/test failures require model interpretation to fix.

## What the Model Does (not the script)
- Interprets error messages and determines root cause
- Decides whether a test failure is a real bug or a test that needs updating
- Compares intended behavior with actual output
