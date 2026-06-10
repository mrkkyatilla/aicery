#!/usr/bin/env bash
# First-token p95 load gate (E6 scorecard row 5)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API="${AICERY_API_URL:-http://localhost:8000}"

if ! curl -sf "${API}/health" >/dev/null 2>&1; then
  echo "API not reachable at ${API} — run: make up"
  exit 1
fi

pytest tests/load/test_first_token_p95.py -m load -q
