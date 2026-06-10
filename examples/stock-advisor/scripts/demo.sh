#!/usr/bin/env bash
# StockPilot showcase — inventory-advisor agent with custom stock tools
set -euo pipefail
EXAMPLE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$EXAMPLE/../.." && pwd)"
API_URL="${AICERY_API_URL:-http://localhost:8000}"
API_KEY="${AICERY_API_KEY:-dev}"
QUERY="${STOCK_ADVISOR_QUERY:-SKU-42 stok durumu ve tedarikçi bilgisi nedir?}"

cd "$REPO"

if ! curl -sf "${API_URL}/health" >/dev/null; then
  echo "API not reachable at ${API_URL}. From repo root: make up"
  exit 1
fi

AICERY="${REPO}/.venv/bin/aicery"
if [[ ! -x "$AICERY" ]]; then
  echo "Missing ${AICERY}. Run: make install"
  exit 1
fi

mkdir -p "${EXAMPLE}/.aicery"
if [[ ! -f "${EXAMPLE}/.aicery/api_key" ]]; then
  echo -n "${API_KEY}" > "${EXAMPLE}/.aicery/api_key"
  chmod 600 "${EXAMPLE}/.aicery/api_key"
fi

echo "== StockPilot: inventory-advisor agent =="
OUTPUT=$("$AICERY" agent run inventory-advisor \
  --config "${EXAMPLE}/aicery.yaml" \
  --input "$QUERY" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qiE 'Alpha Supply|qty.*12|Stock qty: 12|reorder'; then
  echo "PASS: stock-advisor demo (tool-backed stock/supplier output)"
  exit 0
fi

echo "FAIL: output did not show expected stock tool data (qty 12 / Alpha Supply)"
echo "Hint: PLUGIN_PATHS=examples/stock-advisor USE_MOCK_PROVIDER=true HITL_ENABLED=false"
exit 1
