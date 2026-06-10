#!/usr/bin/env bash
# Runbook Copilot showcase — index runbooks → research agent
set -euo pipefail
EXAMPLE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$EXAMPLE/../.." && pwd)"
API_URL="${AICERY_API_URL:-http://localhost:8000}"
API_KEY="${AICERY_API_KEY:-dev}"
INDEX_PATH="examples/runbook-agent/data/runbooks/"
QUERY="${RUNBOOK_AGENT_QUERY:-checkout API p95 > 2s alarmı. api-latency.md runbook dosyasına göre olası nedenler ve önerilen adımları özetle.}"
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

echo "== Runbook Copilot: index ${INDEX_PATH} =="
INDEX_JSON=$("$AICERY" workspace index "$INDEX_PATH" \
  --config "${EXAMPLE}/aicery.yaml" \
  --workspace-id "$WORKSPACE_ID" 2>&1)
echo "$INDEX_JSON"
if echo "$INDEX_JSON" | grep -q 'files=0'; then
  echo "FAIL: no files indexed (check API WORKSPACE_ROOT=/workspace and repo mount)"
  exit 1
fi

echo "== Runbook Copilot: research agent =="
OUTPUT=$("$AICERY" agent run research \
  --config "${EXAMPLE}/aicery.yaml" \
  --input "$QUERY" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qiE 'scale|cache|connection pool|rollback|checkout'; then
  echo "PASS: runbook-agent demo (output cites runbook remediation)"
  exit 0
fi

echo "FAIL: output did not cite runbook data (expected: scale / cache / connection pool / rollback / checkout)"
echo "Hint: USE_MOCK_PROVIDER=true, SEMANTIC_SEARCH_ENABLED=true, Qdrant up"
exit 1
