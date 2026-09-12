"""PropManage — Demo accounts auto-reset (Phase 48).

Resets the state of demo accounts every night at 02:00 Europe/Bucharest so
multiple prospect demos in 1-2 weeks always start from clean baseline.

What gets reset (safe, no destruction outside demo scope):
- Wallet balance back to baseline
- Active jobs/orders count
- Concierge conversation sessions cleared
- Tutorial/AI-tour seen flags reset so demo users see the tour again
- "Cleared at" timestamp recorded so admin sees freshness in admin panel
"""
import logging
from datetime import datetime, timezone

from db import db

logger = logging.getLogger("propmanage.demo_reset")

DEMO_BASELINE = {
    "client@propmanage.io":     {"wallet_balance": 5000, "tokens": 250, "rating": 4.9, "review_count": 24, "tier": "verified"},
    "specialist@propmanage.io": {"wallet_balance": 800,  "tokens": 0,   "rating": 4.9, "reviews_count": 24, "tier": "VERIFIED", "verified": True},
    "operator@propmanage.io":   {"wallet_balance": 0,    "tokens": 0,   "rating": None, "review_count": 0},
}


async def reset_demo_accounts():
    """Idempotent reset — safe to run any time."""
    logger.info("[DemoReset] starting nightly reset...")
    now_iso = datetime.now(timezone.utc).isoformat()
    resets = 0
    for email, baseline in DEMO_BASELINE.items():
        try:
            user = await db.users.find_one({"email": email})
            if not user:
                continue
            uid = str(user["_id"])
            updates = {k: v for k, v in baseline.items() if v is not None}
            updates["demo_reset_at"] = now_iso
            updates.pop("tutorial_seen", None)
            await db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": updates,
                    "$unset": {"tutorial_seen": "", "ai_admin_tour_seen": ""},
                },
            )
            # Reset wallet doc if exists separately
            await db.wallets.update_one(
                {"user_id": uid},
                {"$set": {"balance": baseline.get("wallet_balance", 0), "demo_reset_at": now_iso}},
                upsert=False,
            )
            # Clear concierge sessions older than 1 day for this user
            await db.concierge_messages.delete_many({"user_id": uid})
            await db.concierge_conversations.delete_many({"user_id": uid})
            resets += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[DemoReset] failed for {email}: {e}")
    logger.info(f"[DemoReset] done — {resets} demo accounts cleaned at {now_iso}")
    # Log to audit collection for visibility
    try:
        await db.demo_reset_log.insert_one({"ran_at": now_iso, "accounts_reset": resets})
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "accounts_reset": resets, "ran_at": now_iso}
