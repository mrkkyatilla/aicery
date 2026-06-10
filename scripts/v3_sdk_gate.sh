#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export HITL_ENABLED=false
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false

if ! curl -sf "http://localhost:8000/health" >/dev/null 2>&1; then
  echo "== V3 SDK gate: starting API =="
  $COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
  $COMPOSE run --rm --build migrate
  DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans
fi

echo "== V3 SDK: npm install + build + unit tests =="
cd sdk/typescript
chmod +x scripts/codegen.sh
npm install
npm run build
npm test

echo "== V3 SDK: integration smoke =="
npm run test:integration

echo "gate-v3-sdk OK"
