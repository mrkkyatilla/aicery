#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  make install
}

make unit
echo "F2 unit gate: OK"

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  curl -sf -H "X-API-Key: dev" http://localhost:8000/v1/agents | grep -q '"agents"'
  echo "GET /v1/agents: OK"
else
  echo "GET /v1/agents: SKIP (API not up — run make up)"
fi

if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  pytest runtime/tests/live/test_echo_live_api.py runtime/tests/live/test_research_live_api.py -m live -q
  echo "live-api: OK"
else
  echo "live-api: SKIP (set GEMINI_API_KEY)"
fi

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  pytest tests/integration/test_f2_chain_events.py -m integration -q
  echo "chain events integration: OK"
  if [[ -x examples/research-docs/run.sh ]]; then
    bash examples/research-docs/run.sh
    echo "research-docs example: OK"
  fi
else
  echo "integration examples: SKIP (make up)"
fi

echo "F2 exit gate passed."
