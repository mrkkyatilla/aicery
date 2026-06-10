#!/usr/bin/env bash
# PolicyScan showcase — index policies → research agent
set -euo pipefail
EXAMPLE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$EXAMPLE/../.." && pwd)"
API_URL="${AICERY_API_URL:-http://localhost:8000}"
API_KEY="${AICERY_API_KEY:-dev}"
INDEX_PATH="examples/compliance-scan/data/policies/"
QUERY="${COMPLIANCE_SCAN_QUERY:-KYC checklist taraması: kyc-checklist.md dosyasındaki zorunlu maddeleri özetle; üçüncü taraf veri paylaşımı kuralını belirt.}"
WORKSPACE_ID="${DEFAULT_WORKSPACE_ID:-local}"

cd "$REPO"

if ! curl -sf "${API_URL}/health" >/dev/null; then
  echo "API not reachable at ${API_URL}. From repo root: make up"
  exit 1
fi

# Unattended demo: API with HITL_ENABLED=false (research may suspend when HITL is on).

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

echo "== PolicyScan: index ${INDEX_PATH} =="
INDEX_JSON=$("$AICERY" workspace index "$INDEX_PATH" \
  --config "${EXAMPLE}/aicery.yaml" \
  --workspace-id "$WORKSPACE_ID" 2>&1)
echo "$INDEX_JSON"
if echo "$INDEX_JSON" | grep -q 'files=0'; then
  echo "FAIL: no files indexed (check API WORKSPACE_ROOT=/workspace and repo mount)"
  exit 1
fi

echo "== PolicyScan: research agent =="
OUTPUT=$("$AICERY" agent run research \
  --config "${EXAMPLE}/aicery.yaml" \
  --input "$QUERY" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qiE '90 gün|90 gun|kimlik|üçüncü taraf|onay|kyc'; then
  echo "PASS: compliance-scan demo (output cites KYC checklist)"
  exit 0
fi

echo "FAIL: output did not cite KYC policy (expected: 90 gün / kimlik / üçüncü taraf / onay / kyc)"
echo "Hint: USE_MOCK_PROVIDER=true, SEMANTIC_SEARCH_ENABLED=true, Qdrant up"
exit 1
