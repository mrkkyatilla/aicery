#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export ROUTER_LLM_ENABLED=true
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false

echo "== ROUTER-LLM: unit + golden tests =="
pytest runtime/tests/unit/test_llm_router.py \
  runtime/tests/unit/test_router_llm_golden.py \
  runtime/tests/unit/test_route_llm_api.py \
  runtime/tests/unit/test_agent_router.py -q

_router_llm_ok() {
  local body
  body=$(curl -sf -H "X-API-Key: dev" -H "Content-Type: application/json" \
    -d '{"input":"What does our refund policy say?"}' "http://localhost:8000/v1/route" 2>/dev/null) || return 1
  printf '%s' "$body" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d.get('agent_id') == 'research', d
reason = d.get('reason') or ''
assert reason.startswith('llm:') or reason.startswith('rule:'), reason
"
}

if ! curl -sf "http://localhost:8000/health" >/dev/null 2>&1 || ! _router_llm_ok; then
  echo "== ROUTER-LLM gate: starting API (build) =="
  $COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
  $COMPOSE run --rm --build migrate
  DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans
fi

echo "== ROUTER-LLM: HTTP smoke =="
for payload in \
  '{"input":"What does our refund policy say?"}' \
  '{"input":"hello"}' \
  '{"input":"Summarize README"}'; do
  BODY=$(curl -sf -H "X-API-Key: dev" -H "Content-Type: application/json" \
    -d "$payload" "http://localhost:8000/v1/route")
  printf '%s' "$BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d.get('agent_id'), d
conf = d.get('confidence')
assert isinstance(conf, (int, float)) and 0 <= conf <= 1, d
assert d.get('reason'), d
print('smoke OK:', d['agent_id'], d['reason'][:40])
"
done

REFUND=$(curl -sf -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"input":"What does our refund policy say?"}' "http://localhost:8000/v1/route")
printf '%s' "$REFUND" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['agent_id'] == 'research', d
reason = d.get('reason') or ''
assert reason.startswith('llm:') or reason.startswith('rule:'), reason
print('semantic route OK:', reason)
"

echo "gate-router-llm OK"
