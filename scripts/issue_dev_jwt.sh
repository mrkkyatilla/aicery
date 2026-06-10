#!/usr/bin/env bash
# Issue a dev JWT for local API calls (JWT_ENABLED=true on runtime).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export JWT_SECRET="${JWT_SECRET:-dev-secret}"
export JWT_ENABLED="${JWT_ENABLED:-true}"

python3 - <<'PY'
import os
from runtime.api.jwt_auth import issue_token
from runtime.config import Settings

settings = Settings(
    jwt_enabled=True,
    jwt_secret=os.environ["JWT_SECRET"],
    jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
)
sub = os.environ.get("JWT_SUB", "dev-user")
ws = os.environ.get("JWT_WORKSPACE_ID")
print(issue_token(sub, workspace_id=ws, settings=settings))
PY
