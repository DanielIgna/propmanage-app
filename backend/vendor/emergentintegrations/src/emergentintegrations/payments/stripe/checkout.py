from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CheckoutSession:
    session_id: str
    url: str


@dataclass
class CheckoutStatus:
    status: str
    payment_status: str


@dataclass
class WebhookEvent:
    session_id: str
    payment_status: str
    event_type: str = "checkout.session.completed"


class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str = ""):
        self.api_key = api_key
        self.webhook_url = webhook_url

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSession:
        raise RuntimeError(
            "StripeCheckout stub: set a real STRIPE_API_KEY or use demo mode (sk_test_emergent)."
        )

    async def get_checkout_status(self, session_id: str) -> CheckoutStatus:
        raise RuntimeError("StripeCheckout stub: checkout status unavailable in local stub.")

    async def handle_webhook(self, body: bytes, signature: str) -> WebhookEvent:
        raise RuntimeError("StripeCheckout stub: webhook handling unavailable in local stub.")
