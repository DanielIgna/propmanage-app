"""Stripe Checkout client (replaces emergentintegrations.payments.stripe.checkout) on the official SDK.

Same surface the codebase already uses:
    sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=...)
    session = await sc.create_checkout_session(CheckoutSessionRequest(amount=12.5, currency="ron", ...))
    status = await sc.get_checkout_status(session.session_id)
    event = await sc.handle_webhook(raw_body, stripe_signature_header)   # needs STRIPE_WEBHOOK_SECRET
`amount` is in major units (lei), like the previous wrapper.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import stripe

# Currencies without minor units (Stripe "zero-decimal").
_ZERO_DECIMAL = {"bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf",
                 "ugx", "vnd", "vuv", "xaf", "xof", "xpf"}


def _to_minor(amount: float, currency: str) -> int:
    return int(round(float(amount))) if currency.lower() in _ZERO_DECIMAL else int(round(float(amount) * 100))


def _from_minor(amount: Optional[int], currency: str) -> float:
    if amount is None:
        return 0.0
    return float(amount) if (currency or "").lower() in _ZERO_DECIMAL else amount / 100.0


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, Any]] = None
    product_name: str = "PropManage"


@dataclass
class CheckoutSessionResponse:
    session_id: str
    url: str


@dataclass
class CheckoutStatusResponse:
    status: str
    payment_status: str
    amount_total: float = 0.0
    currency: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookResponse:
    event_type: str
    event_id: str
    session_id: str
    payment_status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# Backwards-compatible names used by the old wrapper.
CheckoutSession = CheckoutSessionResponse
CheckoutStatus = CheckoutStatusResponse
WebhookEvent = WebhookResponse


class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str = ""):
        if not api_key:
            raise RuntimeError("STRIPE_API_KEY not configured")
        self.api_key = api_key
        self.webhook_url = webhook_url

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSessionResponse:
        meta = {str(k): str(v) for k, v in (req.metadata or {}).items()}
        params = {
            "mode": "payment",
            "line_items": [{
                "quantity": 1,
                "price_data": {
                    "currency": req.currency.lower(),
                    "unit_amount": _to_minor(req.amount, req.currency),
                    "product_data": {"name": meta.get("product_name") or req.product_name},
                },
            }],
            "success_url": req.success_url,
            "cancel_url": req.cancel_url,
            "metadata": meta,
            "payment_intent_data": {"metadata": meta},
        }
        session = await asyncio.to_thread(stripe.checkout.Session.create, api_key=self.api_key, **params)
        return CheckoutSessionResponse(session_id=session.id, url=session.url)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatusResponse:
        s = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id, api_key=self.api_key)
        return CheckoutStatusResponse(
            status=s.status or "", payment_status=s.payment_status or "",
            amount_total=_from_minor(s.amount_total, s.currency or ""), currency=s.currency or "",
            metadata=dict(s.metadata or {}),
        )

    async def handle_webhook(self, body: bytes, signature: str) -> WebhookResponse:
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET") or ""
        if not secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured; refusing unsigned webhook")
        event = stripe.Webhook.construct_event(body, signature, secret)  # raises on bad signature
        obj = event["data"]["object"]
        is_session = obj.get("object") == "checkout.session"
        return WebhookResponse(
            event_type=event["type"], event_id=event["id"],
            session_id=obj.get("id", "") if is_session else "",
            payment_status=obj.get("payment_status", "") if is_session else "",
            metadata=dict(obj.get("metadata") or {}),
        )
