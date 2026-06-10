#!/usr/bin/env bash
# E8 — smoke test billing UI + API (local gateway on :8081)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
GATEWAY="${GATEWAY_URL:-http://localhost:8081}"

echo "== Billing UI smoke =="

if ! curl -sf "$GATEWAY/health" >/dev/null 2>&1; then
  echo "SKIP: gateway not on $GATEWAY (run: make up)"
  exit 0
fi

code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/ui/billing")
if [[ "$code" != "200" ]]; then
  echo "FAIL: GET /ui/billing → HTTP $code (run: make up)"
  exit 1
fi
echo "GET /ui/billing: OK"

for path in styles.css app.js success cancel; do
  c=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/ui/billing/$path")
  if [[ "$c" != "200" ]]; then
    echo "FAIL: GET /ui/billing/$path → HTTP $c"
    exit 1
  fi
done
echo "static assets: OK"

if [[ -z "${TENANT_KEY:-}" ]]; then
  echo "Hint: export TENANT_KEY from: bash scripts/gateway_bootstrap.sh"
  echo "SKIP: /billing/me (no TENANT_KEY)"
  exit 0
fi

me=$(curl -sf "$GATEWAY/billing/me" -H "X-Api-Key: $TENANT_KEY")
echo "$me" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'tier' in d and 'usage' in d"
echo "GET /billing/me: OK"
echo ""
echo "Open dashboard: $GATEWAY/ui/billing"
echo "Billing UI smoke passed."
