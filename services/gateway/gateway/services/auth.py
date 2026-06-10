from __future__ import annotations

import secrets
import uuid

import bcrypt
from sqlalchemy.orm import Session

from gateway.adapters.db.models import ApiKeyORM, OrgORM
from gateway.adapters.db.repositories import ApiKeyRepository


class InvalidApiKeyError(Exception):
    pass


class TenantContext:
    def __init__(self, org: OrgORM, api_key: ApiKeyORM | None = None) -> None:
        self.org = org
        self.api_key = api_key

    @property
    def org_id(self) -> uuid.UUID:
        return self.org.id


def hash_api_key(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_api_key(plaintext: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode(), key_hash.encode())
    except ValueError:
        return False


def generate_api_key() -> str:
    return f"aic_{secrets.token_urlsafe(32)}"


def resolve_tenant(session: Session, plaintext_key: str) -> TenantContext:
    repo = ApiKeyRepository(session)
    for row in repo.list_all_active():
        if verify_api_key(plaintext_key, row.key_hash):
            org = session.get(OrgORM, row.org_id)
            if org is None:
                break
            return TenantContext(org=org, api_key=row)
    raise InvalidApiKeyError("Invalid API key")
