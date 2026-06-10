#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export HITL_ENABLED=false
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false

echo "== Marketplace: unit tests =="
pytest runtime/tests/unit/test_marketplace_api.py \
  runtime/tests/unit/test_openapi_snapshot.py -q

_marketplace_ok() {
  curl -sf -H "X-API-Key: dev" "http://localhost:8000/v1/marketplace/plugins" >/dev/null 2>&1
}

if ! curl -sf "http://localhost:8000/health" >/dev/null 2>&1 || ! _marketplace_ok; then
  echo "== Marketplace gate: starting API (build) =="
  $COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
  $COMPOSE run --rm --build migrate
  DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans
fi

echo "== Marketplace: HTTP smoke =="
BODY=$(curl -sf -H "X-API-Key: dev" "http://localhost:8000/v1/marketplace/plugins")
printf '%s' "$BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
plugins = d.get('plugins') or []
assert len(plugins) >= 3, f'expected >=3 plugins, got {len(plugins)}'
slugs = {p['slug'] for p in plugins}
assert 'workspace-analyst' in slugs or 'stock-advisor' in slugs
for p in plugins:
    assert p.get('trust_level') in ('verified', 'community'), p
    for key in ('id', 'slug', 'name', 'type', 'version', 'trust_level'):
        assert key in p, f'missing {key} on {p.get(\"slug\")}'
print('marketplace smoke OK:', len(plugins), 'plugins')
"

echo "gate-marketplace OK"
