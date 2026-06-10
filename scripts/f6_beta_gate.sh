#!/usr/bin/env bash
# E6 F3 beta / Go-No-Go gate — T3-E6-01 (50 concurrent) + security smoke
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f deploy/docker-compose.yml)
API="${AICERY_API_URL:-http://localhost:8000}"
KEY="${AICERY_API_KEY:-dev}"

source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  make install
}

echo "== E6 beta gate: unit smoke (replay + failover) =="
pytest runtime/tests/unit/test_trace_replay.py::test_replay_determinism_two_runs_identical_hashes \
  runtime/tests/unit/test_provider_failover.py -q
echo "replay + failover unit: OK"

echo "== E6 beta gate: stack (mock provider, rate limit off for load) =="
export DOCKER_BUILDKIT=1
"${COMPOSE[@]}" up -d --wait postgres redis nats qdrant 2>/dev/null || true
"${COMPOSE[@]}" run --rm --build migrate 2>/dev/null || true

API_UP=false
if curl -sf "${API}/health" >/dev/null 2>&1; then
  API_UP=true
fi

BUILD_FLAG=()
if [[ "${F6_FORCE_BUILD:-0}" == "1" ]] || [[ "$API_UP" == "false" ]]; then
  BUILD_FLAG=(--build)
fi

if ! RATE_LIMIT_ENABLED=false USE_MOCK_PROVIDER=true \
  "${COMPOSE[@]}" up -d "${BUILD_FLAG[@]}" --wait api; then
  echo ""
  echo "API container failed to start."
  if [[ "${#BUILD_FLAG[@]}" -gt 0 ]]; then
    echo "Docker build often fails with: uv pip install ... exit code 2 (PyPI timeout)."
    echo "  - Retry: DOCKER_BUILDKIT=1 docker compose -f deploy/docker-compose.yml build api"
    echo "  - Or skip rebuild if API already works: F6_FORCE_BUILD=0 make gate-f6"
    echo "  - Check network/DNS to files.pythonhosted.org"
  fi
  exit 1
fi

for _ in $(seq 1 30); do
  if curl -sf "${API}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -sf "${API}/health" | head -c 120
echo

echo "== E6 beta gate: security smoke =="
NO_KEY_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/v1/runs" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"echo","input":"x","execute":false}')
if [[ "$NO_KEY_CODE" != "401" && "$NO_KEY_CODE" != "422" ]]; then
  echo "FAIL: POST /v1/runs without API key expected 401/422, got ${NO_KEY_CODE}"
  exit 1
fi
BAD_KEY_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/v1/runs" \
  -H "X-API-Key: invalid-key-not-dev" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"echo","input":"x","execute":false}')
if [[ "$BAD_KEY_CODE" != "401" ]]; then
  echo "FAIL: invalid API key expected 401, got ${BAD_KEY_CODE}"
  exit 1
fi
echo "security smoke: OK (no key=${NO_KEY_CODE}, bad key=${BAD_KEY_CODE})"

echo "== E6 beta gate: T3-E6-01 — ${BETA_LOAD_CONCURRENCY:-50} concurrent echo runs =="
BETA_LOAD_CONCURRENCY="${BETA_LOAD_CONCURRENCY:-50}" \
BETA_LOAD_WALL_SEC="${BETA_LOAD_WALL_SEC:-600}" \
  pytest tests/load/test_concurrent_beta_50.py -m load -q
echo "beta load: OK"

echo ""
echo "E6 beta gate passed."
echo "Combined scorecard: make gate-gonogo  (gate-f3 + gate-e7-p2 + gate-f6)"
echo "Optional: make gate-e7-live · make gate-graph-steps · make gate-p95"
