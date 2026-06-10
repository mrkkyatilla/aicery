import uuid

from gateway.adapters.db.repositories import ApiKeyRepository, OrgRepository
from gateway.adapters.db.session import get_session_factory
from gateway.services.auth import generate_api_key, hash_api_key, resolve_tenant, verify_api_key


def test_api_key_hash_roundtrip():
    key = generate_api_key()
    hashed = hash_api_key(key)
    assert verify_api_key(key, hashed)
    assert not verify_api_key("wrong", hashed)


def test_resolve_tenant():
    factory = get_session_factory()
    session = factory()
    try:
        org = OrgRepository(session).create("test-org")
        plaintext = generate_api_key()
        ApiKeyRepository(session).create(
            org_id=org.id,
            key_hash=hash_api_key(plaintext),
            key_prefix=plaintext[:12],
            name="default",
        )
        ctx = resolve_tenant(session, plaintext)
        assert ctx.org_id == org.id
    finally:
        session.close()
