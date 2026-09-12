"""House Health — F4.3: Stripe Checkout for subscription-style purchases.

Implementation notes:
    The `emergentintegrations` Stripe wrapper only supports one-shot Checkout
    Sessions (not native Stripe Subscription mode). We model each "subscription
    purchase" as a single payment that grants N days of access (extending
    ``hh_subscriptions.expires_at``). Recurring auto-renewal can be added later
    by switching to the official Stripe API with a paid Stripe account.

Endpoints:
    POST /api/house-health/checkout-session  (body: {plan_slug, origin_url})
        -> Returns {url, session_id}. Frontend redirects to ``url``.
    GET  /api/house-health/checkout-status/{session_id}
        -> Polled by frontend after redirect-back to confirm status and
           atomically activate the subscription. Idempotent.
    POST /api/webhook/stripe
        -> Server-side fallback that flips ``payment_transactions.payment_status``
           and activates ``hh_subscriptions`` even if the user closes the tab.

Security:
    - The price is ALWAYS taken from the plan stored in ``hh_plans`` server-side.
      Frontend only sends ``plan_slug`` (no amounts).
    - success_url / cancel_url are built from the ``origin_url`` posted by
      the client (i.e. window.location.origin) — never hardcoded.
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import db
from deps import get_current_user

logger = logging.getLogger("propmanage.house_health.billing")

router = APIRouter(prefix="/api/house-health", tags=["house-health-billing"])


def _stripe():
    """Lazy import to avoid breaking server startup if the lib isn't installed."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(503, "Stripe nu este configurat (lipsește STRIPE_API_KEY).")
    return StripeCheckout, api_key


def _billing_days(billing_period: str) -> int:
    if billing_period == "yearly":
        return 365
    if billing_period == "one_time":
        return 90  # 3 months access for one-time payments
    return 30  # monthly default


class CheckoutSessionIn(BaseModel):
    plan_slug: str
    origin_url: str


@router.post("/checkout-session")
async def create_checkout_session(
    payload: CheckoutSessionIn,
    request: Request,
    user=Depends(get_current_user),
):
    from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest

    plan = await db.hh_plans.find_one({"slug": payload.plan_slug, "active": True})
    if not plan:
        raise HTTPException(404, "Plan inexistent sau inactiv.")

    StripeCheckout, api_key = _stripe()
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/house-health/upgrade/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/house-health/upgrade"

    amount = float(plan.get("price_eur") or 0)
    if amount <= 0:
        raise HTTPException(400, "Planul are preț 0 — nu se poate procesa checkout.")
    currency = (plan.get("currency") or "EUR").lower()
    metadata = {
        "user_id": user["id"],
        "user_email": user.get("email", ""),
        "plan_slug": plan["slug"],
        "plan_id": plan["id"],
        "billing_period": plan.get("billing_period", "monthly"),
        "source": "house_health_checkout",
    }

    req = CheckoutSessionRequest(
        amount=amount,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session = await stripe_checkout.create_checkout_session(req)

    # Persist transaction in INITIATED state BEFORE returning to client.
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user.get("email"),
        "amount": amount,
        "currency": currency,
        "payment_status": "initiated",
        "status": "open",
        "metadata": metadata,
        "plan_slug": plan["slug"],
        "plan_id": plan["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "activated": False,  # set true after we extend hh_subscriptions
    })

    logger.info(
        "[house_health.billing] checkout session created session=%s user=%s plan=%s amount=%.2f%s",
        session.session_id, user.get("email"), plan["slug"], amount, currency,
    )

    return {"url": session.url, "session_id": session.session_id}


async def _activate_subscription_if_paid(session_id: str) -> dict:
    """Atomically activate the subscription for a paid session.

    Returns the updated payment_transaction document. Idempotent: the same
    session_id may be hit by both webhook and polling; we only activate once.

    Gracefully degrades if Stripe doesn't recognize the session (which happens
    in the Emergent test sandbox where session IDs may not persist between
    separate API calls). In that case we return the cached transaction state.
    """
    StripeCheckout, api_key = _stripe()
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")

    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Tranzacția nu există.")

    try:
        status = await stripe_checkout.get_checkout_status(session_id)
        new_payment_status = status.payment_status
        new_status = status.status
        amount_total_cents = status.amount_total
        currency = status.currency
    except Exception as e:  # noqa: BLE001
        # Stripe session unrecoverable — return cached state without activation.
        logger.info(
            "[house_health.billing] get_checkout_status fallback for %s: %s",
            session_id, e,
        )
        return {
            "session_id": session_id,
            "payment_status": tx.get("payment_status", "pending"),
            "status": tx.get("status", "open"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency"),
            "activated": bool(tx.get("activated")),
            "already_activated": bool(tx.get("activated")),
            "stripe_unavailable": True,
        }

    # Idempotency guard
    if tx.get("activated"):
        # Already activated — just sync latest payment_status if changed
        if tx.get("payment_status") != new_payment_status:
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": new_payment_status, "status": new_status}},
            )
        return {
            "session_id": session_id,
            "payment_status": new_payment_status,
            "status": new_status,
            "already_activated": True,
        }

    update = {
        "payment_status": new_payment_status,
        "status": new_status,
        "last_polled_at": datetime.now(timezone.utc).isoformat(),
    }

    activated = False
    if new_payment_status == "paid":
        # Activate / extend subscription
        plan_id = tx.get("plan_id")
        plan = await db.hh_plans.find_one({"id": plan_id}) if plan_id else None
        billing_period = (plan or {}).get("billing_period", "monthly")
        days = _billing_days(billing_period)

        existing = await db.hh_subscriptions.find_one({"user_id": tx["user_id"]})
        now = datetime.now(timezone.utc)
        # Extend from the later of "now" and existing expires_at
        base = now
        if existing and existing.get("expires_at"):
            try:
                cur = datetime.fromisoformat(existing["expires_at"].replace("Z", "+00:00"))
                if cur > now:
                    base = cur
            except Exception:  # noqa: BLE001
                pass
        new_expires = (base + timedelta(days=days)).isoformat()
        await db.hh_subscriptions.update_one(
            {"user_id": tx["user_id"]},
            {"$set": {
                "user_id": tx["user_id"],
                "plan": tx.get("plan_slug"),
                "plan_id": plan_id,
                "status": "active",
                "expires_at": new_expires,
                "last_payment_session_id": session_id,
                "last_payment_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }, "$setOnInsert": {"created_at": now.isoformat()}},
            upsert=True,
        )
        update["activated"] = True
        update["activated_at"] = now.isoformat()
        update["expires_at"] = new_expires
        activated = True
        # PB-001.4: abonament activat → activează beneficiile de referral în așteptare
        try:
            from propbenefits.referral_ext import activate_for_user
            await activate_for_user(tx["user_id"])
        except Exception:  # noqa: BLE001
            pass

        await db.hh_audit_log.insert_one({
            "user_id": tx["user_id"],
            "action": "subscription_activated",
            "session_id": session_id,
            "plan_slug": tx.get("plan_slug"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency"),
            "expires_at": new_expires,
            "timestamp": now.isoformat(),
        })
        logger.info(
            "[house_health.billing] subscription activated user=%s plan=%s expires=%s",
            tx.get("user_email"), tx.get("plan_slug"), new_expires,
        )

    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    return {
        "session_id": session_id,
        "payment_status": new_payment_status,
        "status": new_status,
        "amount": float(amount_total_cents) / 100.0 if amount_total_cents else tx.get("amount"),
        "currency": currency,
        "activated": activated,
        "already_activated": False,
    }


@router.get("/checkout-status/{session_id}")
async def checkout_status(session_id: str, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Sesiunea de plată nu există.")
    if tx.get("user_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Nu ai acces la această tranzacție.")
    return await _activate_subscription_if_paid(session_id)


# Notă (Architecture Guardian): handler-ul webhook duplicat de aici a fost eliminat.
# POST /api/webhook/stripe canonic e în routes/payments.py și apelează
# _activate_subscription_if_paid() pentru abonamentele House Health.


# ============================================================================
# Stripe auto-provisioning for plans (option (b) — auto-create Stripe Product
# + Price when admin saves a plan). Uses the official `stripe` Python SDK with
# the same STRIPE_API_KEY. Best-effort: if the key doesn't have privileges to
# create Products/Prices, we just store an empty stripe_price_id and continue —
# the checkout flow uses amount+currency directly anyway, so this is purely a
# convenience for admins who want to use real Stripe Price IDs later.
# ============================================================================
async def auto_provision_stripe_price(plan_doc: dict) -> Optional[str]:
    """Create a Stripe Product + Price for the plan if not already linked.

    Returns the new stripe_price_id or None on failure (non-blocking).
    """
    if plan_doc.get("stripe_price_id"):
        return plan_doc["stripe_price_id"]
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("sk_test_emergent", ""):
        # The Emergent placeholder key works only via the wrapper library,
        # not the official SDK. Skip silently.
        logger.info(
            "[house_health.billing] auto-provision skipped for plan %s (placeholder key)",
            plan_doc.get("slug"),
        )
        return None
    try:
        import stripe as stripe_sdk
        stripe_sdk.api_key = api_key
        product = stripe_sdk.Product.create(
            name=f"House Health · {plan_doc.get('name')}",
            description=plan_doc.get("description") or None,
            metadata={"plan_slug": plan_doc.get("slug"), "plan_id": plan_doc.get("id")},
        )
        amount_cents = int(round(float(plan_doc.get("price_eur") or 0) * 100))
        price_kwargs = {
            "product": product.id,
            "unit_amount": amount_cents,
            "currency": (plan_doc.get("currency") or "EUR").lower(),
        }
        period = plan_doc.get("billing_period", "monthly")
        if period in ("monthly", "yearly"):
            price_kwargs["recurring"] = {"interval": "month" if period == "monthly" else "year"}
        price = stripe_sdk.Price.create(**price_kwargs)
        logger.info(
            "[house_health.billing] auto-provisioned Stripe price for plan %s → %s",
            plan_doc.get("slug"), price.id,
        )
        return price.id
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "[house_health.billing] auto-provision Stripe price FAILED for plan %s: %s",
            plan_doc.get("slug"), e,
        )
        return None


# ============================================================================
# Default plans seeder — runs once on startup if hh_plans is empty.
# ============================================================================
DEFAULT_PLANS = [
    {
        "slug": "basic",
        "name": "Basic",
        "description": "Acces la modulul House Health pentru o singură proprietate.",
        "price_eur": 9.0,
        "currency": "EUR",
        "billing_period": "monthly",
        "trial_days": 7,
        "features": [
            "1 Digital Twin inclus",
            "Documentație tehnică (1 GB storage)",
            "1 evaluare/an",
            "Score & istoric",
        ],
        "lead_commission_pct": 15,
        "sort_order": 1,
        "active": True,
    },
    {
        "slug": "pro",
        "name": "Pro",
        "description": "Pentru proprietari cu nevoi recurente de mentenanță.",
        "price_eur": 29.0,
        "currency": "EUR",
        "billing_period": "monthly",
        "trial_days": 14,
        "features": [
            "Până la 3 Digital Twins",
            "Storage extins (5 GB)",
            "4 evaluări/an",
            "Recomandări prioritate Urgent în marketplace cu comision redus",
            "Suport email prioritar",
        ],
        "lead_commission_pct": 10,
        "sort_order": 2,
        "active": True,
    },
    {
        "slug": "premium",
        "name": "Premium",
        "description": "Soluție completă pentru investitori imobiliari.",
        "price_eur": 79.0,
        "currency": "EUR",
        "billing_period": "monthly",
        "trial_days": 14,
        "features": [
            "Digital Twins nelimitate",
            "Storage nelimitat",
            "Evaluări nelimitate",
            "Twin Orchestrator AI inclus",
            "Comision marketplace lead minim (5%)",
            "Suport telefon & dedicated CSM",
        ],
        "lead_commission_pct": 5,
        "sort_order": 3,
        "active": True,
    },
]


async def seed_default_plans():
    """Idempotent seed: skips slugs that already exist."""
    import uuid
    inserted = 0
    for tmpl in DEFAULT_PLANS:
        existing = await db.hh_plans.find_one({"slug": tmpl["slug"]})
        if existing:
            continue
        doc = dict(tmpl)
        doc["id"] = uuid.uuid4().hex
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["created_by"] = "seed"
        await db.hh_plans.insert_one(doc)
        inserted += 1
    if inserted:
        logger.info("[house_health.billing] seeded %d default plans", inserted)
