#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export PLUGIN_PATHS=examples/stock-advisor
export USE_MOCK_PROVIDER=true
export HITL_ENABLED=false
export RATE_LIMIT_ENABLED=false

echo "== STOCK-PRODUCT: unit tests =="
pytest tools/tests/unit/test_showcase_stock_tools.py \
  runtime/tests/unit/test_inventory_advisor.py \
  runtime/tests/unit/test_inventory_advisor_trace.py -q

_inventory_ok() {
  curl -sf -H "X-API-Key: dev" "http://localhost:8000/v1/agents" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
ids = {a.get('id') for a in d.get('agents') or []}
assert 'inventory-advisor' in ids, ids
"
}

if ! curl -sf "http://localhost:8000/health" >/dev/null 2>&1 || ! _inventory_ok; then
  echo "== STOCK-PRODUCT gate: starting API (build) =="
  $COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
  $COMPOSE run --rm --build migrate
  DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans
fi

echo "== STOCK-PRODUCT: HTTP smoke =="
RUN_ID=$(curl -sf -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"agent_id":"inventory-advisor","input":"SKU-42 stok ve tedarik","execute":true}' \
  "http://localhost:8000/v1/runs" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

for _ in $(seq 1 60); do
  STATUS=$(curl -sf -H "X-API-Key: dev" "http://localhost:8000/v1/runs/${RUN_ID}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
    break
  fi
  sleep 0.5
done

TRACE=$(curl -sf -H "X-API-Key: dev" "http://localhost:8000/v1/runs/${RUN_ID}/trace")
printf '%s' "$TRACE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
tools = {s['name'] for s in d.get('steps', []) if s.get('type') == 'tool'}
assert 'get_stock' in tools, tools
assert 'search_suppliers' in tools, tools
print('trace tools OK:', sorted(tools))
"

echo "== STOCK-PRODUCT: demo.sh =="
bash examples/stock-advisor/scripts/demo.sh

echo "gate-stock-product OK"
