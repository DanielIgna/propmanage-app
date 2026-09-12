"""PropManage router: payments."""
import os
import logging
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from db import db
from deps import get_current_user, require_role
from services import log_event
from email_service import (
    send_template, tpl_escrow_funded,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["payments"])


import stripe
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")

# ============= STRIPE ESCROW =============# ============= STRIPE ESCROW =============

STRIPE_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
# Demo mode if key is the Emergent placeholder or doesn't look like a real Stripe key
DEMO_STRIPE = (STRIPE_KEY == "sk_test_emergent") or (not STRIPE_KEY.startswith(("sk_test_", "sk_live_")))

@router.post("/payments/checkout-session")
async def create_checkout_session(request_id: str, request: Request, user: dict = Depends(require_role("client"))):
    """Create Stripe Checkout session for escrow funding (real or demo)"""
    req = await db.requests.find_one({"_id": ObjectId(request_id), "client_id": user["id"]})
    if not req:
        raise HTTPException(404, "Request not found")
    if req.get("status") not in ["open", "assigned"]:
        raise HTTPException(400, "Request not eligible for payment")

    # Amount is SERVER-SIDE only (security) - derived from request budget
    amount = float(req.get("budget_estimate") or 100.0)
    if amount <= 0 or amount > 100000:
        raise HTTPException(400, "Invalid amount")

    # Origin from frontend (used for redirect URLs)
    origin = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/")
    if not origin:
        raise HTTPException(400, "Missing origin header")

    # DEMO mode: stripe_test_emergent placeholder - simulate success
    if DEMO_STRIPE:
        fake_session_id = f"cs_demo_{uuid.uuid4().hex[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": fake_session_id,
            "request_id": request_id,
            "client_id": user["id"],
            "user_email": user.get("email"),
            "amount": amount,
            "currency": "ron",
            "status": "completed",
            "payment_status": "paid",
            "metadata": {"request_id": request_id, "client_id": user["id"]},
            "demo": True,
            "created_at": now_iso,
            "completed_at": now_iso,
        })
        await db.requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"escrow_amount": amount, "escrow_status": "held", "paid_at": now_iso}}
        )
        await db.transactions.insert_one({
            "user_id": user["id"], "type": "escrow_deposit", "amount": -amount,
            "request_id": request_id, "session_id": fake_session_id, "demo": True,
            "created_at": now_iso,
        })
        await log_event(request_id, "escrow.paid", actor=user, payload={"amount": amount, "demo_mode": True})
        # Notify specialist + email
        if req.get("specialist_id"):
            spec_u = await db.users.find_one({"_id": ObjectId(req["specialist_id"])})
            if spec_u and spec_u.get("email"):
                await send_template(
                    tpl_escrow_funded, spec_u.get("name", ""), req.get("title", ""), amount, user.get("name", "Client"),
                    to=spec_u["email"],
                )
        return {"checkout_url": f"{origin}/client?payment=success&request={request_id}&session_id={fake_session_id}&demo=1", "session_id": fake_session_id, "demo_mode": True}

    # REAL Stripe via emergentintegrations
    host_url = origin
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=webhook_url)
    success_url = f"{origin}/client?payment=success&request={request_id}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/client?payment=cancelled&request={request_id}"
    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency="ron",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "request_id": request_id,
            "client_id": user["id"],
            "specialist_id": req.get("specialist_id") or "",
        },
    )
    try:
        session = await stripe_checkout.create_checkout_session(checkout_req)
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "request_id": request_id,
        "client_id": user["id"],
        "user_email": user.get("email"),
        "amount": amount,
        "currency": "ron",
        "status": "initiated",
        "payment_status": "pending",
        "metadata": checkout_req.metadata,
        "created_at": now_iso,
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


@router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Poll Stripe Checkout status. Idempotent: only fulfills escrow once."""
    payment = await db.payment_transactions.find_one({"session_id": session_id})
    if not payment:
        raise HTTPException(404, "Payment session not found")

    # Demo short-circuit
    if payment.get("demo"):
        return {
            "status": "complete",
            "payment_status": "paid",
            "amount": payment["amount"],
            "currency": payment.get("currency", "ron"),
            "request_id": payment["request_id"],
            "demo_mode": True,
        }

    # Idempotency: if already completed, return cached
    if payment.get("status") == "completed" and payment.get("payment_status") == "paid":
        return {
            "status": "complete",
            "payment_status": "paid",
            "amount": payment["amount"],
            "currency": payment.get("currency", "ron"),
            "request_id": payment["request_id"],
        }

    origin = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/") or ""
    stripe_checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=f"{origin}/api/webhook/stripe")
    try:
        status_resp = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {e}")

    now_iso = datetime.now(timezone.utc).isoformat()
    payment_status_val = status_resp.payment_status
    session_status = status_resp.status

    # Fulfill on first 'paid' transition only
    if payment_status_val == "paid" and payment.get("payment_status") != "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "completed",
                "payment_status": "paid",
                "completed_at": now_iso,
            }}
        )
        await db.requests.update_one(
            {"_id": ObjectId(payment["request_id"])},
            {"$set": {"escrow_amount": payment["amount"], "escrow_status": "held", "paid_at": now_iso}}
        )
        await db.transactions.insert_one({
            "user_id": payment["client_id"],
            "type": "escrow_deposit",
            "amount": -payment["amount"],
            "request_id": payment["request_id"],
            "session_id": session_id,
            "created_at": now_iso,
        })
        # Log activity event (system actor since this happens after Stripe redirect)
        try:
            client_doc = await db.users.find_one({"_id": ObjectId(payment["client_id"])})
            await log_event(payment["request_id"], "escrow.paid",
                            actor={"id": payment["client_id"], "name": client_doc.get("name") if client_doc else "Client", "role": "client"},
                            payload={"amount": payment["amount"], "session_id": session_id})
        except Exception:
            pass
    elif session_status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired", "payment_status": "unpaid"}}
        )

    return {
        "status": session_status,
        "payment_status": payment_status_val,
        "amount": payment["amount"],
        "currency": payment.get("currency", "ron"),
        "request_id": payment["request_id"],
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for payment confirmation"""
    if DEMO_STRIPE:
        return {"received": True, "demo": True}
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    origin = request.headers.get("origin") or ""
    stripe_checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=f"{origin}/api/webhook/stripe")
    try:
        evt = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        try:
            from orchestrator.engine import emit_signal
            await emit_signal("webhook_fail", {"source": "stripe", "error": str(e)[:300]})
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(400, f"Webhook error: {e}")
    if evt.payment_status == "paid":
        payment = await db.payment_transactions.find_one({"session_id": evt.session_id})
        if payment and payment.get("payment_status") != "paid":
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"status": "completed", "payment_status": "paid", "completed_at": now_iso}}
            )
            await db.requests.update_one(
                {"_id": ObjectId(payment["request_id"])},
                {"$set": {"escrow_amount": payment["amount"], "escrow_status": "held", "paid_at": now_iso}}
            )
            await db.transactions.insert_one({
                "user_id": payment["client_id"], "type": "escrow_deposit", "amount": -payment["amount"],
                "request_id": payment["request_id"], "session_id": evt.session_id, "via_webhook": True,
                "created_at": now_iso,
            })
        # Verified Estate orders (Phase A — first revenue)
        try:
            from routes.verified_estate import mark_order_paid as _ve_mark_paid
            await _ve_mark_paid(evt.session_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"VE order webhook processing failed: {e}")
        # House Health subscriptions (webhook canonic unic — Architecture Guardian:
        # handler-ul duplicat din house_health_billing nu era servit niciodată de FastAPI)
        try:
            from routes.house_health_billing import _activate_subscription_if_paid
            await _activate_subscription_if_paid(evt.session_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"House Health webhook processing failed: {e}")
    return {"received": True, "event_type": evt.event_type, "session_id": evt.session_id}


