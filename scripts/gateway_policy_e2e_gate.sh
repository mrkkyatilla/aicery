#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export GATEWAY_JWT_ENABLED=true
export JWT_SECRET="${JWT_SECRET:-e2e-jwt-secret-32chars-minimum!!}"
export GATEWAY_RATE_LIMIT_ENABLED=true
export GATEWAY_RATE_LIMIT_PER_MINUTE=5
export GATEWAY_RATE_LIMIT_BACKEND=redis
export TRUST_GATEWAY_HEADERS=true
export RATE_LIMIT_AT_GATEWAY_ONLY=true
export HITL_ENABLED=false
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false
export GATEWAY_ADMIN_TOKEN="${GATEWAY_ADMIN_TOKEN:-admin-dev}"

echo "== Gateway policy E2E: infra =="
$COMPOSE up -d --wait postgres redis nats qdrant gateway-db --remove-orphans
$COMPOSE run --rm --build migrate
$COMPOSE run --rm --build gateway-migrate
DOCKER_BUILDKIT=1 $COMPOSE up -d --build --force-recreate --wait api gateway --remove-orphans

echo "== Gateway policy E2E: integration test =="
export JWT_ENABLED=true
pytest tests/integration/test_gateway_policy_e2e.py -m gateway_policy_e2e -q
echo "gate-gateway-policy-e2e OK"
