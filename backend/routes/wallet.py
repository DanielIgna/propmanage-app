"""PropManage router: wallet."""
import os
import logging
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["wallet"])

# ============= TRANSACTIONS / WALLET =============
@router.get("/transactions")
async def list_transactions(user: dict = Depends(get_current_user)):
    docs = await db.transactions.find({"user_id": user["id"]}).sort("created_at", -1).to_list(50)
    return [serialize_doc(d) for d in docs]

@router.post("/wallet/topup")
async def topup_wallet(amount: float, user: dict = Depends(get_current_user)):
    if amount <= 0 or amount > 10000:
        raise HTTPException(400, "Invalid amount")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$inc": {"wallet_balance": amount}}
    )
    await db.transactions.insert_one({
        "user_id": user["id"],
        "type": "topup",
        "amount": amount,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"ok": True, "added": amount}


# ============= STRIPE CHECKOUT pentru wallet topup =============
import uuid as _uuid

STRIPE_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
DEMO_STRIPE = (STRIPE_KEY == "sk_test_emergent") or (not STRIPE_KEY.startswith(("sk_test_", "sk_live_")))


class TopupCheckoutIn(BaseModel):
    amount: float = Field(gt=0, le=50000)
    origin: Optional[str] = None  # Public-facing origin from window.location.origin


@router.post("/wallet/topup-checkout-session")
async def topup_checkout_session(data: TopupCheckoutIn, request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for wallet topup. Returns demo URL in DEMO mode."""
    # Prefer client-supplied origin (set from window.location.origin) — bypasses k8s ingress rewrites.
    origin = (data.origin or "").rstrip("/") or request.headers.get("origin", "").rstrip("/") or request.headers.get("referer", "").rstrip("/")
    if not origin:
        raise HTTPException(400, "Missing origin")

    if DEMO_STRIPE:
        fake_session_id = f"cs_topup_demo_{_uuid.uuid4().hex[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": fake_session_id,
            "type": "wallet_topup",
            "client_id": user["id"],
            "user_email": user.get("email"),
            "amount": data.amount,
            "currency": "ron",
            "status": "initiated",
            "payment_status": "pending",
            "demo": True,
            "created_at": now_iso,
        })
        # Auto-fulfilled redirect (matches pattern of escrow demo)
        return {
            "checkout_url": f"{origin}/payment-success?type=topup&session_id={fake_session_id}&amount={data.amount}&demo=1",
            "session_id": fake_session_id,
            "demo_mode": True,
        }

    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    webhook_url = f"{origin}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=webhook_url)
    success_url = f"{origin}/payment-success?type=topup&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/client?topup=cancelled"
    checkout_req = CheckoutSessionRequest(
        amount=data.amount,
        currency="ron",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"type": "wallet_topup", "user_id": user["id"]},
    )
    try:
        session = await stripe_checkout.create_checkout_session(checkout_req)
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "type": "wallet_topup",
        "client_id": user["id"],
        "user_email": user.get("email"),
        "amount": data.amount,
        "currency": "ron",
        "status": "initiated",
        "payment_status": "pending",
        "created_at": now_iso,
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


@router.get("/wallet/topup-status/{session_id}")
async def topup_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Poll status of a wallet topup session; idempotently credit the wallet on first paid."""
    payment = await db.payment_transactions.find_one({"session_id": session_id, "client_id": user["id"], "type": "wallet_topup"})
    if not payment:
        raise HTTPException(404, "Topup session not found")

    # Already fulfilled
    if payment.get("payment_status") == "paid":
        return {"status": "complete", "payment_status": "paid", "amount": payment["amount"], "already_credited": True}

    now_iso = datetime.now(timezone.utc).isoformat()

    if payment.get("demo"):
        # Auto-credit wallet for demo
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": payment["amount"]}})
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed", "payment_status": "paid", "completed_at": now_iso}}
        )
        await db.transactions.insert_one({
            "user_id": user["id"], "type": "topup_stripe", "amount": payment["amount"],
            "session_id": session_id, "demo": True, "created_at": now_iso,
        })
        return {"status": "complete", "payment_status": "paid", "amount": payment["amount"], "demo_mode": True}

    # Real Stripe poll
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    origin = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/") or ""
    stripe_checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=f"{origin}/api/webhook/stripe")
    try:
        status_resp = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {e}")

    if status_resp.payment_status == "paid" and payment.get("payment_status") != "paid":
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": payment["amount"]}})
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed", "payment_status": "paid", "completed_at": now_iso}}
        )
        await db.transactions.insert_one({
            "user_id": user["id"], "type": "topup_stripe", "amount": payment["amount"],
            "session_id": session_id, "created_at": now_iso,
        })

    return {
        "status": status_resp.status,
        "payment_status": status_resp.payment_status,
        "amount": payment["amount"],
    }


