#!/usr/bin/env bash
# F1 çıkış kapısı — MVP_TEAMS_PHASES (manuel doğrulama)
set -euo pipefail

API="${AICERY_API_URL:-http://localhost:8000}"
KEY="${AICERY_API_KEY:-dev}"

echo "== health =="
curl -sf "${API}/health" | head -c 200
echo

echo "== create research run =="
RESP=$(curl -sf -X POST "${API}/v1/runs" \
  -H "X-API-Key: ${KEY}" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"research","input":"Read README.md and summarize","execute":true}')
echo "$RESP"
RUN_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== poll run ${RUN_ID} (max 120s) =="
for i in $(seq 1 120); do
  BODY=$(curl -sf -H "X-API-Key: ${KEY}" "${API}/v1/runs/${RUN_ID}")
  STATUS=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "  [${i}s] status=${STATUS}"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "cancelled" ]]; then
    echo "$BODY" | python3 -m json.tool
    if [[ "$STATUS" != "completed" ]]; then
      echo "FAIL: expected completed"
      exit 1
    fi
    TC=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_calls_count',0))")
    EV=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('events_count',0))")
    if [[ "$TC" -lt 1 ]]; then
      echo "FAIL: tool_calls_count < 1"
      exit 1
    fi
    if [[ "$EV" -lt 2 ]]; then
      echo "FAIL: events_count < 2 (F1 lifecycle)"
      exit 1
    fi
    echo "PASS: F1 exit gate"
    exit 0
  fi
  sleep 1
done

echo "FAIL: timeout waiting for terminal state"
exit 1
