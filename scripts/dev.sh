#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uvicorn postagent.api.main:app --reload --host 0.0.0.0 --port 8000
