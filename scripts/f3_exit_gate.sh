#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  make install
}

if [[ "${GONOGO_SKIP_UNIT:-0}" != "1" ]]; then
  make unit
  echo "F3 unit gate: OK"
else
  echo "F3 unit gate: SKIP (GONOGO_SKIP_UNIT=1 — unit already ran)"
fi

aicery graph echo >/dev/null
echo "aicery graph: OK"

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  # Stable replay integration: mock provider (no Gemini quota/rate limits).
  USE_MOCK_PROVIDER=true docker compose -f deploy/docker-compose.yml up -d --wait api 2>/dev/null || true
  pytest tests/integration/test_f3_trace_replay.py -m integration -q
  echo "F3 integration: OK"
else
  echo "F3 integration: SKIP (make up)"
fi

pytest runtime/tests/unit/test_provider_failover.py runtime/tests/unit/test_rate_limit.py -q
echo "failover + rate limit unit: OK"

echo "F3 exit gate passed."
