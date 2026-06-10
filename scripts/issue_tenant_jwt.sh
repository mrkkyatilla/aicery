#!/usr/bin/env bash
set -euo pipefail
ORG_ID="${1:?Usage: issue_tenant_jwt.sh <org-uuid>}"
python - <<PY
import os
import uuid
from gateway.services.jwt_auth import issue_tenant_token

os.environ.setdefault("JWT_SECRET", "change-me-in-production")
token = issue_tenant_token(uuid.UUID("${ORG_ID}"))
print(token)
PY
