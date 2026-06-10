from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from gateway.adapters.db.session import get_session_factory
from gateway.adapters.stripe.webhooks import handle_stripe_event
from gateway.config import Settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    settings = Settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    factory = get_session_factory()
    session: Session = factory()
    try:
        handle_stripe_event(session, event if isinstance(event, dict) else event.to_dict())
    finally:
        session.close()
    return {"received": True}
