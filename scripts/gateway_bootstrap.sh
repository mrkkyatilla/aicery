#!/usr/bin/env bash
# Create dev org, API key, and workspace on local gateway.
set -euo pipefail
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8081}"
ADMIN_TOKEN="${GATEWAY_ADMIN_TOKEN:-admin-dev}"

ORG=$(curl -sf -X POST "$GATEWAY_URL/admin/orgs" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"dev-org"}')
ORG_ID=$(echo "$ORG" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

KEY=$(curl -sf -X POST "$GATEWAY_URL/admin/orgs/$ORG_ID/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN")
WS=$(curl -sf -X POST "$GATEWAY_URL/admin/orgs/$ORG_ID/workspaces" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"default","runtime_workspace_id":"local"}')

echo "org_id=$ORG_ID"
echo "$KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('tenant_api_key=', d['key'])"
echo "$WS" | python3 -c "import sys,json; d=json.load(sys.stdin); print('workspace=', d['runtime_workspace_id'])"
