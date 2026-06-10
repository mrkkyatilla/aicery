#!/usr/bin/env bash
# T2-E5-01 — research-docs example (mock API or live Gemini)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

API_URL="${AICERY_API_URL:-http://localhost:8000}"
API_KEY="${AICERY_API_KEY:-dev}"

if ! curl -sf "${API_URL}/health" >/dev/null; then
  echo "API not reachable at ${API_URL}. Run: make up (from repo root)"
  exit 1
fi

mkdir -p .aicery
if [[ ! -f .aicery/api_key ]]; then
  echo -n "${API_KEY}" > .aicery/api_key
  chmod 600 .aicery/api_key
fi

if command -v aicery >/dev/null 2>&1 && [[ -d "${ROOT}/../../.venv" || -d "${ROOT}/../../sdk" ]]; then
  REPO="$(cd "$ROOT/../.." && pwd)"
  if [[ -f "${REPO}/.venv/bin/aicery" ]]; then
    "${REPO}/.venv/bin/aicery" agent run research \
      --config aicery.yaml \
      --input "Summarize README.md in one sentence."
    exit $?
  fi
fi

# Fallback: curl + poll (no CLI install required)
RUN_ID=$(curl -sf -X POST "${API_URL}/v1/runs" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"research","input":"Summarize README.md in one sentence.","execute":true}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

for _ in $(seq 1 120); do
  STATUS=$(curl -sf -H "X-API-Key: ${API_KEY}" "${API_URL}/v1/runs/${RUN_ID}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
    curl -sf -H "X-API-Key: ${API_KEY}" "${API_URL}/v1/runs/${RUN_ID}" | python3 -m json.tool
    [[ "$STATUS" == "completed" ]]
    exit $?
  fi
  sleep 0.5
done
echo "timeout waiting for run ${RUN_ID}"
exit 1
