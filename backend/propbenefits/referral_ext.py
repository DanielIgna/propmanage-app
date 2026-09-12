"""PropBenefits · Referral Extension (PB-001.4) — EXTINDE trust_growth, nu îl recreează.

Beneficiile se acordă DOAR după activarea abonamentului SAU primul serviciu plătit —
NU la simpla creare a contului. Colecție: pb_referral_pending.
"""
import logging
import uuid
from datetime import datetime, timezone

from db import db
from propbenefits.config import get_config
from propbenefits import ledger

logger = logging.getLogger("propmanage.propbenefits")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def on_referral_claimed(inviter_id: str, invitee_id: str, invitee_name: str = ""):
    """Hook chemat din trust_growth.claim — creează dreptul ÎN AȘTEPTARE (idempotent)."""
    exists = await db.pb_referral_pending.find_one({"invitee_id": invitee_id})
    if exists:
        return
    await db.pb_referral_pending.insert_one({
        "id": uuid.uuid4().hex[:12], "inviter_id": inviter_id, "invitee_id": invitee_id,
        "invitee_name": invitee_name, "status": "pending_activation",
        "created_at": _now(), "activated_at": None,
    })


async def _user_activated(uid: str) -> bool:
    sub = await db.hh_subscriptions.find_one({"user_id": uid, "status": "active"}, {"_id": 1})
    if sub:
        return True
    paid = await db.payment_transactions.find_one({"user_id": uid, "payment_status": "paid"}, {"_id": 1})
    return bool(paid)


async def _activate(pending: dict) -> bool:
    cfg = (await get_config())["referral_benefit"]
    if not cfg.get("enabled", True):
        return False
    res = await db.pb_referral_pending.update_one(
        {"id": pending["id"], "status": "pending_activation"},
        {"$set": {"status": "activated", "activated_at": _now()}})
    if not res.modified_count:
        return False
    exp = cfg.get("expires_days", 90)
    await ledger.grant(pending["inviter_id"], cfg["inviter"], source="referral", expires_days=exp)
    await ledger.grant(pending["invitee_id"], cfg["invitee"], source="referral", expires_days=exp)
    try:
        from services import notify
        await notify(pending["inviter_id"], "Beneficiu Comunitate activat 🎁",
                     f"{pending.get('invitee_name') or 'Vecinul invitat'} s-a activat — beneficiul tău te așteaptă în portofelul de beneficii.",
                     type_="success", link="/client?tab=benefits")
        await notify(pending["invitee_id"], "Beneficiul tău de bun venit e activ 🎁",
                     "Pentru că ai venit printr-o recomandare, ai primit un beneficiu de bun venit.",
                     type_="success", link="/client?tab=benefits")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[propbenefits.referral] notify failed: {e}")
    return True


async def activate_for_user(user_id: str) -> bool:
    """Hook direct — chemat la activarea abonamentului (house_health_billing)."""
    pending = await db.pb_referral_pending.find_one({"invitee_id": user_id, "status": "pending_activation"})
    if not pending:
        return False
    return await _activate(pending)


async def referral_activation_tick() -> int:
    """Plasă de siguranță zilnică — verifică toate drepturile în așteptare."""
    activated = 0
    async for p in db.pb_referral_pending.find({"status": "pending_activation"}):
        if await _user_activated(p["invitee_id"]):
            if await _activate(p):
                activated += 1
    return activated
