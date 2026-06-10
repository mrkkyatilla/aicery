#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export HITL_ENABLED=true
export LANGGRAPH_CHECKPOINT_BACKEND=postgres
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false

echo "== HITL Postgres gate: infra =="
$COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
$COMPOSE run --rm --build migrate
CURRENT=$(cd runtime && DATABASE_URL=postgresql+psycopg://aicery:aicery@localhost:5433/aicery alembic current 2>/dev/null | tail -1 || true)
if [[ "${CURRENT}" != *"010_langgraph_checkpoints"* ]]; then
  echo "FAIL: runtime alembic expected 010_langgraph_checkpoints, got: ${CURRENT:-<empty>}"
  exit 1
fi
DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans

echo "== HITL Postgres gate: integration test =="
pytest tests/integration/test_hitl_postgres_checkpoint.py -m hitl_postgres -q
echo "gate-hitl-postgres OK"
