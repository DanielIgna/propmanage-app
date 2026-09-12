"""PropBenefits · Summaries (PB-002 — PropBenefits Everywhere).

Sumarele contextuale per rol: platforma ADUCE beneficiile în context, utilizatorul
nu le caută. În primele 30 de secunde: ce valoare am azi, ce câștig dacă rămân,
ce pot activa acum, ce e aproape deblocat, ce negociază comunitatea pentru mine.
"""
from datetime import datetime, timezone, timedelta

from db import db
from propbenefits import eligibility, ledger, opportunities
from propbenefits.community_deals import list_deals, DISCLAIMER

SLOGAN = "PropManage nu vinde reduceri. Construiește valoare pentru proprietari prin puterea comunității."


def _iso(dt=None):
    return (dt or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# CLIENT — Benefits Pulse (primele 30 de secunde)
# ---------------------------------------------------------------------------
async def client_pulse(user: dict) -> dict:
    from propbenefits.ai_agents import success_manager
    ctx = await eligibility.user_context(user)
    feed = await opportunities.feed(user, limit=3)
    wallet = await ledger.wallet_summary(user["id"])
    waived = await db.requests.count_documents({"client_id": user["id"], "lead_fee_waived": True})
    saved = round(sum(b.get("value_estimate", 0) for b in wallet["used"]) + waived * 45, 2)
    sm = await success_manager(user)
    deals = await list_deals(user_id=user["id"])
    negotiating = [d for d in deals if d["status"] in ("negociere", "pilot")]
    # Plan / membership status — REUSE hh_plans (preț REAL din cod, niciodată inventat)
    sub_active = bool(ctx.get("subscription_active"))
    cheapest_paid = None
    if not sub_active:
        pp = await db.hh_plans.find_one({"active": True, "price_eur": {"$gt": 0}}, sort=[("price_eur", 1)])
        if pp:
            cheapest_paid = {"name": pp.get("name"), "slug": pp.get("slug"),
                             "price_eur": pp.get("price_eur"), "billing_period": pp.get("billing_period", "monthly")}
    level = feed["membership"]["level"]
    return {
        "slogan": SLOGAN,
        "membership": feed["membership"]["level"],
        "plan": {
            "subscription_active": sub_active,
            "membership_level": level.get("name") if isinstance(level, dict) else level,
            "cheapest_paid": cheapest_paid,
        },
        "available": {"count": len(feed["opportunities"]) + wallet["counts"].get("available", 0),
                      "in_wallet": wallet["counts"].get("available", 0),
                      "value": round(wallet["total_value_available"]
                                     + sum(o.get("value_estimate", 0) for o in feed["opportunities"]), 2)},
        "saved_value": saved,
        "saved_detail": {"benefits_used_value": round(saved - waived * 45, 2), "lead_fees_waived": waived},
        "top_opportunity": feed["opportunities"][0] if feed["opportunities"] else None,
        "almost_unlocked": feed["locked"][:2],
        "community_deals": {"total": len(deals), "negotiating": len(negotiating),
                            "preview": [{"emoji": d["emoji"], "title": d["title"], "status": d["status"]}
                                        for d in negotiating[:3]],
                            "disclaimer": DISCLAIMER},
        "next_action": sm.get("next_action"),
        "health": sm.get("health"),
    }


# ---------------------------------------------------------------------------
# SPECIALIST — beneficii care aduc cereri
# ---------------------------------------------------------------------------
PROFILE_FIELDS = ["name", "phone", "city", "services", "bio", "company_name"]


async def specialist_summary(user: dict) -> dict:
    uid = user.get("id") or str(user.get("_id", ""))
    filled = sum(1 for f in PROFILE_FIELDS if user.get(f))
    profile_pct = round(100 * filled / len(PROFILE_FIELDS))
    verified = bool(user.get("verified"))
    since30 = _iso(datetime.now(timezone.utc) - timedelta(days=30))
    jobs30 = await db.requests.count_documents(
        {"assigned_specialist_id": uid, "status": {"$in": ["completed", "confirmed"]},
         "updated_at": {"$gte": since30}})
    camp = await db.pb_campaigns.find_one({"status": "active"}, {"_id": 0, "title": 1, "kind": 1, "priority": 1},
                                          sort=[("priority", -1)])
    messages = []
    if profile_pct < 100:
        messages.append({"id": "sp_profile",
                         "title": f"Profilul tău este completat {profile_pct}%",
                         "value": "Profilurile complete primesc semnificativ mai multe cereri — clienții aleg specialiștii pe care îi pot cunoaște.",
                         "cta_path": "/specialist?tab=profil", "impact": 9})
    if not verified:
        messages.append({"id": "sp_verified",
                         "title": "Devino Specialist Verificat",
                         "value": "Badge-ul Verificat crește încrederea și te urcă în recomandările AI către clienți.",
                         "cta_path": "/specialist?tab=profil", "impact": 8})
    if camp:
        messages.append({"id": "sp_campaign",
                         "title": f"Campania lunii: „{camp['title']}”",
                         "value": "Clienții cu acest beneficiu caută specialiști chiar acum — fii disponibil și preia cererile campaniei.",
                         "cta_path": "/specialist", "impact": 7})
    if jobs30 >= 2:
        messages.append({"id": "sp_partner",
                         "title": "Ești un partener activ al comunității",
                         "value": f"{jobs30} lucrări finalizate în ultima lună — partenerii activi primesc prioritate în campaniile viitoare PropBenefits.",
                         "cta_path": "/specialist", "impact": 5})
    else:
        messages.append({"id": "sp_partner_grow",
                         "title": "Beneficii pentru partenerii activi",
                         "value": "Specialiștii care finalizează constant lucrări primesc prioritate în campaniile PropBenefits și acces la cererile comunității.",
                         "cta_path": "/specialist", "impact": 4})
    messages.sort(key=lambda m: -m["impact"])
    return {"slogan": SLOGAN, "profile_pct": profile_pct, "verified": verified,
            "jobs_30d": jobs30, "messages": messages[:3]}


# ---------------------------------------------------------------------------
# ADMINISTRATOR — beneficiile clădirii
# ---------------------------------------------------------------------------
async def building_summary(user: dict, building_id: str) -> dict:
    from bson import ObjectId
    b = await db.buildings.find_one({"_id": ObjectId(building_id)}) if ObjectId.is_valid(building_id) else None
    if not b:
        return {"error": "Clădire inexistentă."}
    props = await db.properties.find({"building_id": building_id}, {"owner_id": 1}).to_list(200)
    owner_ids = list({p["owner_id"] for p in props if p.get("owner_id")})
    participating = len(await db.pb_ledger.distinct("user_id", {"user_id": {"$in": owner_ids}})) if owner_ids else 0
    subs = await db.hh_subscriptions.count_documents({"user_id": {"$in": owner_ids}, "status": "active"}) if owner_ids else 0
    camps = await db.pb_campaigns.find({"status": "active", "kind": {"$in": ["community", "local", "seasonal"]}},
                                       {"_id": 0, "id": 1, "title": 1, "kind": 1, "benefit": 1}).to_list(10)
    deals = await list_deals()
    supporters_in_building = 0
    if owner_ids:
        async for d in db.pb_community_deals.find({"active": True}, {"supporter_ids": 1}):
            supporters_in_building += len(set(d.get("supporter_ids") or []) & set(owner_ids))
    unlock_together = []
    if len(owner_ids) >= 3:
        unlock_together.append(f"Cu {len(owner_ids)} apartamente în clădire, o campanie comună de mentenanță (ex. verificarea centralelor) devine mult mai valoroasă pentru fiecare.")
    if subs < len(owner_ids):
        unlock_together.append(f"{subs}/{len(owner_ids)} apartamente au abonament activ — fiecare abonat nou crește puterea de negociere a întregii clădiri.")
    unlock_together.append("Susținerea Community Deals de către locatari accelerează acordurile comerciale pentru toată clădirea.")
    return {
        "slogan": SLOGAN,
        "building": {"name": b.get("name"), "apartments": len(props), "owners": len(owner_ids)},
        "participation": {"participating_owners": participating, "active_subscriptions": subs},
        "building_campaigns": camps,
        "deals_supported_from_building": supporters_in_building,
        "deals_negotiating": len([d for d in deals if d["status"] in ("negociere", "pilot")]),
        "unlock_together": unlock_together,
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# MARKETPLACE — flags per serviciu: 🟢 activ · 🟡 prin abonament · 🔒 blocat
# ---------------------------------------------------------------------------
async def marketplace_flags(user: dict) -> dict:
    from propbenefits import membership, campaigns
    ctx = await eligibility.user_context(user)
    mem = await membership.compute_membership(ctx)
    ranks = await membership.level_ranks()
    flags = []
    for c in await campaigns.active_campaigns():
        ev = eligibility.evaluate(ctx, c.get("eligibility") or {}, mem["level"]["rank"], ranks)
        already = await ledger.user_claims_for_campaign(ctx["uid"], c["id"]) if c.get("max_per_user") else 0
        if ev["eligible"] and (not c.get("max_per_user") or already < c["max_per_user"]):
            flag, label = "active", "Beneficiu Activ"
        elif already and c.get("max_per_user") and already >= c["max_per_user"]:
            flag, label = "used", "Beneficiu folosit"
        elif any(f["rule"] == "subscription_active" for f in ev["failed"]) and len(ev["failed"]) == 1:
            flag, label = "subscription", "Disponibil prin abonament"
        else:
            flag, label = "locked", "Se deblochează după: " + ", ".join(f["label"] for f in ev["failed"][:2])
        flags.append({"campaign_id": c["id"], "title": c["title"], "kind": c["kind"],
                      "benefit_title": (c.get("benefit") or {}).get("title"),
                      "flag": flag, "label": label})
    order = {"active": 0, "subscription": 1, "locked": 2, "used": 3}
    flags.sort(key=lambda f: order.get(f["flag"], 9))
    return {"flags": flags, "slogan": SLOGAN}


# ---------------------------------------------------------------------------
# Context banners — House Health & Digital Twin (AI vorbește despre casă)
# ---------------------------------------------------------------------------
async def context_banner(user: dict, surface: str) -> dict:
    from propbenefits import membership, campaigns
    ctx = await eligibility.user_context(user)
    mem = await membership.compute_membership(ctx)
    ranks = await membership.level_ranks()
    kind_map = {"house_health": ["house_health", "active_benefit"], "digital_twin": ["digital_twin", "audit"]}
    target_kinds = kind_map.get(surface, [])
    camp, eligible = None, False
    for c in await campaigns.active_campaigns():
        if c["kind"] in target_kinds:
            ev = eligibility.evaluate(ctx, c.get("eligibility") or {}, mem["level"]["rank"], ranks)
            camp = c
            eligible = ev["eligible"]
            break
    if surface == "house_health":
        effects = ["Scorul House Health al casei tale crește",
                   "Beneficiul rămâne activ în portofelul tău", "Primești puncte de progres spre nivelul următor"]
        headline = (f"Verificarea prin campania „{camp['title']}” lucrează pentru casa ta" if camp
                    else "Campaniile House Health revin în curând")
    else:
        effects = ["Acces la Campaniile Premium", "Beneficii Exclusive rezervate membrilor cu twin",
                   "Un nivel superior de membru (+15 puncte)"]
        headline = ("Casa ta are deja geamăn digital — campaniile exclusive îți sunt deschise" if ctx["twins"] > 0
                    else "Finalizează Digital Twin al casei tale și deblochezi:")
    return {"surface": surface, "headline": headline, "effects": effects,
            "campaign": ({"id": camp["id"], "title": camp["title"],
                          "benefit_title": (camp.get("benefit") or {}).get("title"),
                          "eligible": eligible} if camp else None),
            "slogan": SLOGAN}
