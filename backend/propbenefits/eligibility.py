"""PropBenefits · Eligibility Engine (PB-001.5) — cine are dreptul la ce, pe date REALE."""
from datetime import datetime, timezone

from db import db

RULE_LABELS = {
    "subscription_active": "Abonament House Health activ",
    "has_digital_twin": "Digital Twin activat",
    "has_house_health": "Scor House Health calculat",
    "city": "Oraș eligibil",
    "property_type": "Tip de proprietate eligibil",
    "min_membership": "Nivel de membru minim",
    "min_properties": "Număr minim de proprietăți",
    "min_documents": "Documente în Cartea Casei",
    "min_completed_jobs": "Lucrări finalizate",
    "email_verified": "Email verificat",
}


def _now():
    return datetime.now(timezone.utc)


async def user_context(user: dict) -> dict:
    """Contextul complet al utilizatorului — o singură construcție, refolosită de toate motoarele."""
    uid = user.get("id") or str(user.get("_id", ""))
    props = await db.properties.find({"owner_id": uid}, {"_id": 0, "city": 1, "type": 1, "address": 1}).to_list(50)
    cities = set()
    for p in props:
        city = p.get("city") or (p.get("address", "").rsplit(",", 1)[-1].strip() if "," in p.get("address", "") else "")
        if city:
            cities.add(city.lower())
    sub = await db.hh_subscriptions.find_one({"user_id": uid, "status": "active"})
    sub_active = False
    if sub:
        try:
            sub_active = datetime.fromisoformat(str(sub.get("expires_at", "")).replace("Z", "+00:00")) > _now()
        except Exception:  # noqa: BLE001
            sub_active = True
    created = user.get("created_at", "")
    account_days = 0
    try:
        account_days = (_now() - datetime.fromisoformat(str(created).replace("Z", "+00:00"))).days
    except Exception:  # noqa: BLE001
        pass
    return {
        "uid": uid,
        "properties": len(props),
        "cities": cities,
        "property_types": {p.get("type") for p in props if p.get("type")},
        "subscription_active": sub_active,
        "subscription_expires_at": (sub or {}).get("expires_at"),
        "twins": await db.digital_twin_projects.count_documents({"owner_id": uid}),
        "hh_score": bool(await db.hh_scores.find_one({"user_id": uid}, {"_id": 1})),
        "documents": await db.property_documents.count_documents({"owner_id": uid, "deleted": {"$ne": True}}),
        "completed_jobs": await db.requests.count_documents(
            {"client_id": uid, "status": {"$in": ["completed", "confirmed"]}}),
        "referrals_claimed": await db.referral_invites.count_documents(
            {"inviter_id": uid, "claimed_by": {"$ne": None}}),
        "paid_transactions": await db.payment_transactions.count_documents(
            {"user_id": uid, "payment_status": "paid"}),
        "ai_sessions": await db.ai_sessions.count_documents({"user_id": uid}),
        "benefits_used": await db.pb_ledger.count_documents({"user_id": uid, "status": "used"}),
        "campaigns_joined": await db.pb_ledger.count_documents({"user_id": uid, "campaign_id": {"$ne": None}}),
        "email_verified": bool(user.get("email_verified")),
        "experience_tier": user.get("experience_tier") or "junior",
        "account_days": account_days,
        "is_ambassador": bool(user.get("pb_ambassador")),
        "recommendations_validated": await db.recommendations.count_documents({"owner_id": uid, "status": "validated"}),
    }


def evaluate(ctx: dict, rules: dict, level_rank: int = 0, level_ranks: dict = None) -> dict:
    """Evaluează regulile unei campanii pe contextul utilizatorului. Explicabil: passed/failed."""
    passed, failed = [], []

    def check(key, ok):
        (passed if ok else failed).append({"rule": key, "label": RULE_LABELS.get(key, key)})

    for key, val in (rules or {}).items():
        if key == "subscription_active" and val:
            check(key, ctx["subscription_active"])
        elif key == "has_digital_twin" and val:
            check(key, ctx["twins"] > 0)
        elif key == "has_house_health" and val:
            check(key, ctx["hh_score"])
        elif key == "city" and val:
            check(key, str(val).lower() in ctx["cities"])
        elif key == "property_type" and val:
            check(key, val in ctx["property_types"])
        elif key == "min_membership" and val:
            check(key, level_rank >= (level_ranks or {}).get(val, 0))
        elif key == "min_properties":
            check(key, ctx["properties"] >= int(val))
        elif key == "min_documents":
            check(key, ctx["documents"] >= int(val))
        elif key == "min_completed_jobs":
            check(key, ctx["completed_jobs"] >= int(val))
        elif key == "email_verified" and val:
            check(key, ctx["email_verified"])
    return {"eligible": len(failed) == 0, "passed": passed, "failed": failed}
