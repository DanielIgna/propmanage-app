"""PropBenefits · Health Engines — Subscription Health, Ecosystem Health, Subscription Impact Score.

Subscription Health: sănătatea abonamentului per utilizator (dacă scade, AI Success
Manager intervine). Ecosystem Health: scorul global al ecosistemului. Subscription
Impact Score: cât contribuie fiecare modul (CORE-001 catalog) la activare/retenție/
conversie/recomandări — vizibil în Discovery Center.
"""
from datetime import datetime, timezone, timedelta

from db import db
from propbenefits.config import get_config
from propbenefits.eligibility import user_context


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _now()).isoformat()


# ---------------------------------------------------------------------------
# Subscription Health — per utilizator
# ---------------------------------------------------------------------------
async def subscription_health(user: dict, ctx: dict = None) -> dict:
    ctx = ctx or await user_context(user)
    w = (await get_config())["subscription_health_weights"]
    since30 = _iso(_now() - timedelta(days=30))
    nav30 = await db.ai_brain_navigation.count_documents({"user_id": ctx["uid"], "ts": {"$gte": since30}})
    req30 = await db.requests.count_documents({"client_id": ctx["uid"], "created_at": {"$gte": since30}})

    factors = [
        {"key": "activity", "label": "Activitate (30 zile)",
         "ratio": min(1.0, (nav30 + req30 * 5) / 20)},
        {"key": "documents", "label": "Cartea casei",
         "ratio": min(1.0, ctx["documents"] / 5)},
        {"key": "house_health", "label": "House Health",
         "ratio": 1.0 if ctx["hh_score"] else 0.0},
        {"key": "digital_twin", "label": "Digital Twin",
         "ratio": 1.0 if ctx["twins"] > 0 else 0.0},
        {"key": "campaigns", "label": "Participare la campanii",
         "ratio": min(1.0, ctx["campaigns_joined"] / 2)},
        {"key": "benefits_used", "label": "Beneficii folosite",
         "ratio": min(1.0, ctx["benefits_used"] / 2)},
        {"key": "referrals", "label": "Recomandări făcute",
         "ratio": min(1.0, ctx["referrals_claimed"] / 2)},
        {"key": "ai_usage", "label": "Utilizare AI",
         "ratio": min(1.0, ctx["ai_sessions"] / 3)},
    ]
    score = 0.0
    for f in factors:
        f["weight"] = int(w.get(f["key"], 10))
        f["points"] = round(f["ratio"] * f["weight"], 1)
        score += f["points"]
    score = round(score)
    status = "healthy" if score >= 70 else "watch" if score >= 40 else "at_risk"
    return {"score": score, "status": status, "factors": factors,
            "subscription_active": ctx["subscription_active"],
            "subscription_expires_at": ctx.get("subscription_expires_at")}


async def health_snapshot_tick(limit: int = 500) -> dict:
    """Snapshot zilnic pentru abonații activi — alimentează lista at-risk din Admin."""
    scanned, at_risk = 0, 0
    async for sub in db.hh_subscriptions.find({"status": "active"}).limit(limit):
        user = await db.users.find_one({"$or": [{"id": sub["user_id"]}, {"email": sub["user_id"]}]}) \
               or await _user_by_any_id(sub["user_id"])
        if not user:
            continue
        user["id"] = user.get("id") or str(user["_id"])
        h = await subscription_health(user)
        scanned += 1
        at_risk += 1 if h["status"] == "at_risk" else 0
        await db.pb_subscription_health.update_one(
            {"user_id": user["id"]},
            {"$set": {"user_id": user["id"], "email": user.get("email"), "name": user.get("name"),
                      "score": h["score"], "status": h["status"], "updated_at": _iso()}},
            upsert=True)
    return {"scanned": scanned, "at_risk": at_risk}


async def _user_by_any_id(uid: str):
    from bson import ObjectId
    try:
        return await db.users.find_one({"_id": ObjectId(uid)})
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Ecosystem Health — global
# ---------------------------------------------------------------------------
async def ecosystem_health() -> dict:
    targets = (await get_config())["ecosystem_targets"]
    since30 = _iso(_now() - timedelta(days=30))
    now = _iso()

    subs_active = await db.hh_subscriptions.count_documents({"status": "active", "expires_at": {"$gt": now}})
    total_clients = await db.users.count_documents({"role": "client"})
    active_users_30 = len(await db.ai_brain_navigation.distinct("user_id", {"ts": {"$gte": since30}}))
    retention_pct = round(100 * active_users_30 / total_clients) if total_clients else 0
    twins = await db.digital_twin_projects.count_documents({})
    hh_subs = subs_active
    camps = await db.pb_campaigns.count_documents({"status": "active"})
    partners = await db.city_partners.count_documents({"archived": {"$ne": True}})
    specialists_active = await db.users.count_documents({"role": "specialist", "verified": True})
    benefits_active = await db.pb_ledger.count_documents({"status": "available"})

    comps = [
        {"key": "subscriptions", "label": "Abonamente active", "value": subs_active,
         "target": targets["subscriptions"], "weight": 25},
        {"key": "retention", "label": "Retenție 30 zile (%)", "value": retention_pct,
         "target": targets["retention_pct"], "weight": 20},
        {"key": "twins", "label": "Digital Twins", "value": twins,
         "target": targets["twins"], "weight": 10},
        {"key": "house_health", "label": "Abonamente House Health", "value": hh_subs,
         "target": targets["hh_subs"], "weight": 10},
        {"key": "campaigns", "label": "Campanii active", "value": camps,
         "target": targets["campaigns_active"], "weight": 10},
        {"key": "city_partners", "label": "City Partners", "value": partners,
         "target": targets["city_partners"], "weight": 5},
        {"key": "specialists", "label": "Specialiști verificați", "value": specialists_active,
         "target": targets["specialists_active"], "weight": 10},
        {"key": "opportunities", "label": "Beneficii active în portofele", "value": benefits_active,
         "target": 20, "weight": 10},
    ]
    score = 0.0
    for c in comps:
        c["ratio"] = round(min(1.0, c["value"] / c["target"]) if c["target"] else 0.0, 2)
        c["points"] = round(c["ratio"] * c["weight"], 1)
        score += c["points"]
    score = round(score)
    return {"score": score,
            "status": "healthy" if score >= 70 else "growing" if score >= 40 else "early",
            "components": comps, "generated_at": _iso(),
            "north_star": {"label": "Țintă arhitecturală", "value": subs_active, "target": 3000}}


# ---------------------------------------------------------------------------
# North Star — 3.000 de abonamente ACTIVE și SĂNĂTOASE (obiectiv comun al agenților)
# ---------------------------------------------------------------------------
async def north_star() -> dict:
    now = _iso()
    since30 = _iso(_now() - timedelta(days=30))
    active = await db.hh_subscriptions.count_documents({"status": "active", "expires_at": {"$gt": now}})
    sub_uids = await db.hh_subscriptions.distinct("user_id", {"status": "active", "expires_at": {"$gt": now}})
    healthy = await db.pb_subscription_health.count_documents({"user_id": {"$in": sub_uids}, "score": {"$gte": 70}}) if sub_uids else 0
    using = len([u for u in await db.ai_brain_navigation.distinct("user_id", {"ts": {"$gte": since30}}) if u in set(sub_uids)]) if sub_uids else 0
    maintaining = len(await db.maintenance_tasks.distinct("user_id", {"user_id": {"$in": sub_uids}})) if sub_uids else 0
    benefiting = len(await db.pb_ledger.distinct("user_id", {"user_id": {"$in": sub_uids}})) if sub_uids else 0
    referring = len(await db.referral_invites.distinct("inviter_id", {"inviter_id": {"$in": sub_uids}, "claimed_by": {"$ne": None}})) if sub_uids else 0
    return {
        "label": "3.000 de abonamente active și sănătoase",
        "target": 3000,
        "active": active,
        "healthy": healthy,
        "progress_pct": round(100 * healthy / 3000, 2),
        "dimensions": [
            {"key": "using", "label": "Folosesc platforma (30z)", "value": using},
            {"key": "maintaining", "label": "Își întrețin locuința", "value": maintaining},
            {"key": "benefiting", "label": "Beneficiază de campanii", "value": benefiting},
            {"key": "referring", "label": "Recomandă alți membri", "value": referring},
        ],
        "definition": "Nu doar 3.000 de abonamente — 3.000 de abonați care folosesc platforma, își întrețin locuințele, beneficiază de campanii și recomandă alți membri. Fiecare abonat crește puterea de negociere a comunității.",
        "generated_at": now,
    }


# ---------------------------------------------------------------------------
# Subscription Impact Score — per modul (vizibil în Discovery Center)
# ---------------------------------------------------------------------------
IMPACT_DECLARED = {
    # cheile modulelor CORE-001 → contribuție 0-10 la: activare, retenție, conversie, recomandări
    "prop_benefits":       {"activation": 9, "retention": 10, "conversion": 8, "referrals": 9},
    "house_health":        {"activation": 9, "retention": 9, "conversion": 6, "referrals": 4},
    "digital_twin":        {"activation": 8, "retention": 8, "conversion": 6, "referrals": 5},
    "maintenance_calendar": {"activation": 6, "retention": 9, "conversion": 6, "referrals": 3},
    "document_vault":      {"activation": 7, "retention": 8, "conversion": 4, "referrals": 3},
    "buildings_community": {"activation": 8, "retention": 8, "conversion": 7, "referrals": 9},
    "referral":            {"activation": 7, "retention": 5, "conversion": 8, "referrals": 10},
    "trusted_specialists": {"activation": 5, "retention": 9, "conversion": 7, "referrals": 6},
    "marketplace_core":    {"activation": 8, "retention": 7, "conversion": 9, "referrals": 5},
    "marketplace_public":  {"activation": 7, "retention": 4, "conversion": 9, "referrals": 6},
    "property_passport":   {"activation": 5, "retention": 4, "conversion": 8, "referrals": 8},
    "fair_price":          {"activation": 6, "retention": 6, "conversion": 8, "referrals": 4},
    "loyalty_tiers":       {"activation": 4, "retention": 8, "conversion": 5, "referrals": 5},
    "tokens_wallet":       {"activation": 5, "retention": 6, "conversion": 5, "referrals": 3},
    "subscriptions_billing": {"activation": 10, "retention": 7, "conversion": 7, "referrals": 2},
    "city_partners":       {"activation": 6, "retention": 4, "conversion": 6, "referrals": 5},
    "ai_brain":            {"activation": 3, "retention": 6, "conversion": 3, "referrals": 2},
    "guardian":            {"activation": 1, "retention": 3, "conversion": 1, "referrals": 1},
    "orchestrator":        {"activation": 3, "retention": 5, "conversion": 3, "referrals": 3},
}
IMPACT_WEIGHTS = {"activation": 0.30, "retention": 0.30, "conversion": 0.25, "referrals": 0.15}


async def subscription_impact_scores() -> dict:
    from ai_brain.product_intelligence import get_product_map
    pmap = await get_product_map()
    completeness = {m["key"]: m["completeness"] for m in pmap["modules"]}
    names = {m["key"]: m["name"] for m in pmap["modules"]}
    items = []
    for key, d in IMPACT_DECLARED.items():
        potential = round(sum(d[k] * IMPACT_WEIGHTS[k] for k in IMPACT_WEIGHTS) * 10)
        realized = round(potential * completeness.get(key, 0) / 100)
        items.append({"key": key, "name": names.get(key, key), "impact": d,
                      "potential": potential, "realized": realized,
                      "completeness": completeness.get(key, 0),
                      "gap": potential - realized})
    items.sort(key=lambda i: -i["gap"])
    return {"items": items, "weights": IMPACT_WEIGHTS, "generated_at": _iso(),
            "note": "Realized = potențial × completitudine (CORE-001). Gap = impactul de abonament încă necâștigat — unde merită investit."}
