#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Step 1/4: Format Check ==="
ruff format --check . || { echo "FAIL: formatting"; exit 1; }

echo "=== Step 2/4: Lint ==="
ruff check . || { echo "FAIL: linting"; exit 1; }

echo "=== Step 3/4: Type Check ==="
mypy postagent/ || { echo "FAIL: typecheck"; exit 1; }

echo "=== Step 4/4: Tests ==="
pytest tests/ -v || { echo "FAIL: tests"; exit 1; }

echo "=== All checks passed ==="
