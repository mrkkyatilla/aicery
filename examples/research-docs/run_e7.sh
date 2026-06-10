#!/usr/bin/env bash
# E7 golden demo — index example docs → research agent → cite MVP_SCOPE.md
set -euo pipefail
EXAMPLE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$EXAMPLE/../.." && pwd)"
API_URL="${AICERY_API_URL:-http://localhost:8000}"
API_KEY="${AICERY_API_KEY:-dev}"
INDEX_PATH="examples/research-docs/docs/"
QUERY="${E7_GOLDEN_QUERY:-What is MVP scope? Use workspace search, then read examples/research-docs/docs/MVP_SCOPE.md and list must-have areas including semantic workspace search.}"
WORKSPACE_ID="${DEFAULT_WORKSPACE_ID:-local}"

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

echo "== E7 golden: index ${INDEX_PATH} =="
INDEX_JSON=$("$AICERY" workspace index "$INDEX_PATH" \
  --config "${EXAMPLE}/aicery.yaml" \
  --workspace-id "$WORKSPACE_ID" 2>&1)
echo "$INDEX_JSON"
if echo "$INDEX_JSON" | grep -q 'files=0'; then
  echo "FAIL: no files indexed (check API WORKSPACE_ROOT=/workspace and repo mount)"
  exit 1
fi

echo "== E7 golden: research agent =="
OUTPUT=$("$AICERY" agent run research \
  --config "${EXAMPLE}/aicery.yaml" \
  --input "$QUERY" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qiE 'golden target|semantic workspace search|explicitly out of scope'; then
  echo "PASS: E7 golden demo (output cites examples/research-docs/docs/MVP_SCOPE.md)"
  exit 0
fi

echo "FAIL: output did not cite golden MVP_SCOPE.md content (expected: golden target / semantic workspace search)"
echo "Hint: ensure SEMANTIC_SEARCH_ENABLED=true, Qdrant up, API rebuilt after E7"
exit 1
