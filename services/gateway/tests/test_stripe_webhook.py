import uuid

from gateway.adapters.db.repositories import OrgRepository
from gateway.adapters.db.session import get_session_factory
from gateway.adapters.stripe.webhooks import handle_stripe_event


def test_checkout_session_completed_updates_tier(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    factory = get_session_factory()
    session = factory()
    try:
        org = OrgRepository(session).create("stripe-org")
        handle_stripe_event(
            session,
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "metadata": {"org_id": str(org.id), "tier": "pro"},
                    }
                },
            },
        )
        updated = OrgRepository(session).get(org.id)
        assert updated is not None
        assert updated.tier == "pro"
    finally:
        session.close()
