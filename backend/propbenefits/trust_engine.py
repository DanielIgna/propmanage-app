"""PropBenefits · Community Trust & Recommendation Engine (PB-003).

Liantul dintre PropBenefits, Community Deals, Success Manager, Marketplace,
specialiști, Digital Twin și House Health. EXTINDE PB-001/PB-002 și colecția
existentă `recommendations` (folosită deja de trust rollup din Marketplace) —
zero cod duplicat. Reward Engine = pb_ledger (REUSE). Graph = ai_brain graph (REUSE).
"""
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta

from bson import ObjectId

from db import db
from propbenefits import ledger
from propbenefits.config import get_config

logger = logging.getLogger("propmanage.propbenefits")

DEAL_SIGNALS = ["sustin", "interesat", "vreau_oferta", "notifica_ma"]
SIGNAL_WEIGHTS = {"sustin": 1.0, "interesat": 2.0, "notifica_ma": 1.5, "vreau_oferta": 3.0}
SIGNAL_LABELS = {"sustin": "Susțin", "interesat": "Interesat", "vreau_oferta": "Vreau ofertă", "notifica_ma": "Notifică-mă"}
REC_TARGETS = ["specialist", "lucrare", "serviciu"]
AI_LABELS = {
    "calitate": ["calitate", "impecabil", "profesionist", "atent", "curat"],
    "punctualitate": ["punctual", "la timp", "rapid", "prompt"],
    "comunicare": ["comunicare", "explicat", "amabil", "politicos", "raspuns"],
    "pret_corect": ["pret", "corect", "ieftin", "rezonabil", "transparent"],
    "incredere": ["incredere", "recomand", "sigur", "serios", "garantie"],
}


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _now()).isoformat()


# ---------------------------------------------------------------------------
# 1. Recommendation Engine — după lucrare, cu clasificare AI
# ---------------------------------------------------------------------------
def _classify_keywords(text: str) -> list:
    t = (text or "").lower()
    return [label for label, kws in AI_LABELS.items() if any(k in t for k in kws)]


async def _classify_ai(text: str) -> list:
    try:
        from ai_core.provider import call_llm
        r = await call_llm(
            "Clasifici o recomandare (română) pentru un specialist în construcții. "
            f"Returnează DOAR etichetele potrivite din: {', '.join(AI_LABELS)}. Format: etichete separate prin virgulă, nimic altceva.",
            text, max_tokens=40)
        labels = [x.strip() for x in re.split(r"[,\n]", r.get("text", "")) if x.strip() in AI_LABELS]
        if labels:
            return labels
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[trust] AI classify fallback: {e}")
    return _classify_keywords(text) or ["incredere"]


async def submit_recommendation(user: dict, payload: dict) -> dict:
    rid = str(payload.get("request_id") or "")
    req = await db.requests.find_one({"_id": ObjectId(rid)}) if ObjectId.is_valid(rid) else None
    if not req:
        return {"error": "Lucrare inexistentă.", "code": 404}
    if req.get("client_id") != user["id"]:
        return {"error": "Poți recomanda doar propriile lucrări.", "code": 403}
    if req.get("status") not in ("completed", "confirmed"):
        return {"error": "Recomandarea se face după finalizarea lucrării.", "code": 409}
    if not req.get("specialist_id"):
        return {"error": "Lucrarea nu are un specialist asignat.", "code": 409}
    if await db.recommendations.find_one({"request_id": rid, "owner_id": user["id"]}, {"_id": 1}):
        return {"error": "Ai recomandat deja această lucrare.", "code": 409}

    targets = [t for t in (payload.get("targets") or ["specialist"]) if t in REC_TARGETS] or ["specialist"]
    reason = str(payload.get("reason") or "").strip()
    doc = {
        "id": uuid.uuid4().hex[:12],
        "owner_id": user["id"], "owner_name": user.get("name", ""),
        "specialist_id": req["specialist_id"], "specialist_name": req.get("specialist_name", ""),
        "request_id": rid, "category": req.get("category"),
        "note": reason, "targets": targets,
        "photos": [str(p) for p in (payload.get("photos") or [])][:6],
        "source": "job", "status": "pending", "effects": [],
        "ai_labels": await _classify_ai(reason) if reason else [],
        "created_at": _iso(), "validated_at": None,
    }
    await db.recommendations.insert_one({**doc})
    amb = await ambassador_status(user["id"])
    return {"ok": True, "recommendation": doc, "ambassador": amb,
            "message": "Recomandarea ta întărește comunitatea — beneficiul se activează când recomandarea produce o lucrare confirmată."}


async def my_recommendations(user_id: str) -> dict:
    items = await db.recommendations.find({"owner_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"items": items, "ambassador": await ambassador_status(user_id)}


# ---------------------------------------------------------------------------
# 4. Recommendation Rewards — DOAR la efect real (contact/ofertă/lucrare/confirmată)
# ---------------------------------------------------------------------------
async def _detect_effects(rec: dict) -> list:
    """Efecte produse de recomandare: cereri ale ALTOR clienți către specialist după recomandare."""
    effects = []
    q = {"specialist_id": rec["specialist_id"], "client_id": {"$ne": rec["owner_id"]},
         "created_at": {"$gte": rec["created_at"]}}
    contact = await db.requests.find_one({**q}, {"status": 1})
    if contact:
        effects.append("contact")
    if await db.requests.find_one({**q, "status": {"$in": ["assigned", "in_progress", "completed", "confirmed"]}}, {"_id": 1}):
        effects.append("lucrare")
    if await db.requests.find_one({**q, "status": {"$in": ["completed", "confirmed"]}}, {"_id": 1}):
        effects.append("lucrare_confirmata")
    offers = await db.requests.find_one({**q, "offers.0": {"$exists": True}}, {"_id": 1})
    if offers:
        effects.append("oferta")
    return effects


async def validate_recommendations_tick() -> dict:
    cfg = await get_config()
    reward = cfg.get("recommendation_reward", {})
    validated = 0
    async for rec in db.recommendations.find({"source": "job", "status": "pending"}):
        effects = await _detect_effects(rec)
        if effects != rec.get("effects"):
            await db.recommendations.update_one({"_id": rec["_id"]}, {"$set": {"effects": effects}})
        if "lucrare_confirmata" in effects:
            res = await db.recommendations.update_one(
                {"_id": rec["_id"], "status": "pending"},
                {"$set": {"status": "validated", "validated_at": _iso()}})
            if res.modified_count:
                validated += 1
                if reward.get("enabled", True):
                    await ledger.grant(rec["owner_id"], reward.get("benefit", {}),
                                       source="recommendation", expires_days=reward.get("expires_days", 90))
                try:
                    from services import notify
                    await notify(rec["owner_id"], "Recomandarea ta a produs o lucrare confirmată 🤝",
                                 f"Comunitatea a câștigat prin recomandarea ta pentru {rec.get('specialist_name') or 'specialist'} — beneficiul tău e în portofel.",
                                 type_="success", link="/client?tab=benefits")
                except Exception:  # noqa: BLE001
                    pass
                await _check_ambassador_promotion(rec["owner_id"])
    return {"validated": validated}


# ---------------------------------------------------------------------------
# 3. Community Ambassador — beneficii, nu bani
# ---------------------------------------------------------------------------
async def ambassador_status(user_id: str) -> dict:
    cfg = (await get_config()).get("ambassador", {})
    threshold = int(cfg.get("min_validated", 2))
    founding_max = int(cfg.get("founding_max", 10))
    validated = await db.recommendations.count_documents({"owner_id": user_id, "status": "validated"})
    pending = await db.recommendations.count_documents({"owner_id": user_id, "source": "job", "status": "pending"})
    u = await db.users.find_one({"id": user_id}, {"pb_ambassador": 1, "pb_founding_ambassador": 1, "pb_founding_rank": 1}) or {}
    founding_taken = await db.users.count_documents({"pb_founding_ambassador": True})
    return {"is_ambassador": bool(u.get("pb_ambassador")), "validated": validated,
            "pending": pending, "threshold": threshold,
            "remaining": max(0, threshold - validated),
            "badge": cfg.get("badge", "Community Ambassador"),
            "perks": cfg.get("perks", []),
            # ASM-001: Founding Ambassador — primii N (cronologic) ambasadori validați, badge permanent
            "is_founding": bool(u.get("pb_founding_ambassador")),
            "founding_rank": u.get("pb_founding_rank"),
            "founding_badge": cfg.get("founding_badge", "Founding Ambassador"),
            "founding_slots_left": max(0, founding_max - founding_taken)}


async def _check_ambassador_promotion(user_id: str):
    cfg = (await get_config()).get("ambassador", {})
    threshold = int(cfg.get("min_validated", 2))
    validated = await db.recommendations.count_documents({"owner_id": user_id, "status": "validated"})
    if validated < threshold:
        return False
    res = await db.users.update_one({"id": user_id, "pb_ambassador": {"$ne": True}},
                                    {"$set": {"pb_ambassador": True, "pb_ambassador_at": _iso()}})
    if not res.modified_count:
        return False
    # ASM-001: Founding Ambassador — primii N cronologic; badge unic, permanent, apoi locurile se închid
    founding_max = int(cfg.get("founding_max", 10))
    founding_taken = await db.users.count_documents({"pb_founding_ambassador": True})
    is_founding = False
    if founding_taken < founding_max:
        fres = await db.users.update_one({"id": user_id, "pb_founding_ambassador": {"$ne": True}},
                                         {"$set": {"pb_founding_ambassador": True,
                                                   "pb_founding_rank": founding_taken + 1,
                                                   "pb_founding_at": _iso()}})
        is_founding = bool(fres.modified_count)
    await ledger.grant(user_id, cfg.get("benefit", {}), source="ambassador", expires_days=120)
    try:
        from services import notify
        if is_founding:
            await notify(user_id, "Ești Founding Ambassador 🏆",
                         f"Ești printre primii {founding_max} membri care au construit încrederea comunității — badge-ul Founding Ambassador este al tău permanent.",
                         type_="success", link="/client?tab=benefits")
        else:
            await notify(user_id, "Ești acum Community Ambassador 🏅",
                         "Recomandările tale confirmate construiesc comunitatea — ai primit beneficiul de ambasador și prioritate la campaniile exclusive.",
                         type_="success", link="/client?tab=benefits")
    except Exception:  # noqa: BLE001
        pass
    return True


# ---------------------------------------------------------------------------
# 2. Trust Score — compus, explicabil, cache-uit (pb_trust_scores)
# ---------------------------------------------------------------------------
async def trust_score(specialist_id: str) -> dict:
    recs_validated = await db.recommendations.count_documents({"specialist_id": specialist_id, "status": "validated"})
    recs_total = await db.recommendations.count_documents({"specialist_id": specialist_id})
    confirmed = await db.requests.count_documents({"specialist_id": specialist_id, "status": {"$in": ["completed", "confirmed"]}})
    ratings = [r["rating"] async for r in db.reviews.find({"specialist_id": specialist_id, "rating": {"$gte": 1}}, {"rating": 1})]
    satisfaction = round(sum(ratings) / len(ratings), 2) if ratings else None
    u = await db.users.find_one({"$or": [{"id": specialist_id}, {"_id": ObjectId(specialist_id) if ObjectId.is_valid(specialist_id) else None}]},
                                {"created_at": 1, "verified": 1, "experience_tier": 1}) or {}
    age_days = 0
    try:
        age_days = (_now() - datetime.fromisoformat(str(u.get("created_at", "")).replace("Z", "+00:00"))).days
    except Exception:  # noqa: BLE001
        pass
    since30 = _iso(_now() - timedelta(days=30))
    recent = await db.requests.count_documents({"specialist_id": specialist_id, "created_at": {"$gte": since30}})

    factors = [
        {"key": "recomandari_validate", "label": "Recomandări validate", "value": recs_validated,
         "points": round(min(1.0, recs_validated / 3) * 20, 1), "max": 20},
        {"key": "lucrari_confirmate", "label": "Lucrări confirmate", "value": confirmed,
         "points": round(min(1.0, confirmed / 10) * 25, 1), "max": 25},
        {"key": "satisfactie", "label": "Rata de satisfacție", "value": satisfaction,
         "points": round((satisfaction / 5) * 20, 1) if satisfaction else 0, "max": 20},
        {"key": "experienta", "label": "Experiență (total recomandări + verificare)", "value": recs_total,
         "points": round(min(1.0, (recs_total + (2 if u.get("verified") else 0)) / 6) * 15, 1), "max": 15},
        {"key": "vechime", "label": "Vechime în comunitate", "value": age_days,
         "points": round(min(1.0, age_days / 365) * 10, 1), "max": 10},
        {"key": "activitate", "label": "Activitate recentă (30z)", "value": recent,
         "points": round(min(1.0, recent / 3) * 10, 1), "max": 10},
    ]
    score = round(sum(f["points"] for f in factors))
    return {"specialist_id": specialist_id, "score": score, "factors": factors,
            "recommendations": recs_total, "recommendations_validated": recs_validated,
            "confirmed_jobs": confirmed, "satisfaction": satisfaction, "updated_at": _iso()}


async def trust_scores_tick(limit: int = 300) -> int:
    spec_ids = set(await db.requests.distinct("specialist_id", {"specialist_id": {"$ne": None}}))
    spec_ids |= set(await db.recommendations.distinct("specialist_id"))
    n = 0
    for sid in list(spec_ids)[:limit]:
        ts = await trust_score(sid)
        ambassadors = len([o for o in await db.recommendations.distinct(
            "owner_id", {"specialist_id": sid, "status": "validated"})
            if (await db.users.find_one({"id": o, "pb_ambassador": True}, {"_id": 1}))])
        community_value = 0.0
        async for rec in db.recommendations.find({"specialist_id": sid, "status": "validated"}, {"owner_id": 1}):
            async for b in db.pb_ledger.find({"user_id": rec["owner_id"], "source": {"$in": ["recommendation", "ambassador"]}},
                                             {"value_estimate": 1}):
                community_value += b.get("value_estimate", 0)
        await db.pb_trust_scores.update_one(
            {"specialist_id": sid},
            {"$set": {**{k: ts[k] for k in ("score", "recommendations", "recommendations_validated",
                                            "confirmed_jobs", "satisfaction", "updated_at")},
                      "specialist_id": sid, "ambassadors": ambassadors,
                      "community_value": round(community_value, 2)}},
            upsert=True)
        n += 1
    return n


async def explain_specialist(specialist_id: str) -> dict:
    """AI Brain explicabil: DE CE recomand acest specialist."""
    ts = await trust_score(specialist_id)
    top_recs = await db.recommendations.find({"specialist_id": specialist_id, "note": {"$ne": ""}},
                                             {"_id": 0, "note": 1, "ai_labels": 1, "owner_name": 1, "status": 1}) \
        .sort("created_at", -1).to_list(3)
    reasons = []
    for f in ts["factors"]:
        if f["points"] >= f["max"] * 0.6:
            reasons.append(f"{f['label']}: {f['value']}")
    labels = {}
    async for r in db.recommendations.find({"specialist_id": specialist_id}, {"ai_labels": 1}):
        for lbl in r.get("ai_labels") or []:
            labels[lbl] = labels.get(lbl, 0) + 1
    return {"trust_score": ts["score"], "factors": ts["factors"], "why": reasons,
            "community_says": sorted(labels, key=labels.get, reverse=True)[:3],
            "voices": top_recs,
            "explanation": (f"Trust Score {ts['score']}/100 — calculat din {ts['confirmed_jobs']} lucrări confirmate, "
                            f"{ts['recommendations_validated']} recomandări validate de efecte reale și activitatea din comunitate. "
                            "Scorul e generat automat din date, nu din autoevaluare.")}


# ---------------------------------------------------------------------------
# 5. Community Deals — semnale multiple + estimare AI a cererii
# ---------------------------------------------------------------------------
async def signal_deal(deal_id: str, user_id: str, signal: str) -> dict:
    if signal not in DEAL_SIGNALS:
        return {"error": f"Semnal invalid — permise: {', '.join(DEAL_SIGNALS)}", "code": 400}
    deal = await db.pb_community_deals.find_one({"id": deal_id}, {"_id": 1, "title": 1})
    if not deal:
        return {"error": "Deal inexistent.", "code": 404}
    await db.pb_deal_signals.update_one(
        {"deal_id": deal_id, "user_id": user_id},
        {"$addToSet": {"signals": signal}, "$set": {"updated_at": _iso()},
         "$setOnInsert": {"created_at": _iso()}},
        upsert=True)
    if signal == "sustin":
        await db.pb_community_deals.update_one({"id": deal_id}, {"$addToSet": {"supporter_ids": user_id}})
    d = await deal_demand_one(deal_id)
    return {"ok": True, "signal": signal, "demand": d,
            "message": f"Semnalul tău crește puterea de negociere pentru „{deal['title']}”."}


async def _signals_counts(deal_id: str) -> dict:
    counts = {s: 0 for s in DEAL_SIGNALS}
    async for row in db.pb_deal_signals.find({"deal_id": deal_id}, {"signals": 1}):
        for s in row.get("signals") or []:
            if s in counts:
                counts[s] += 1
    return counts


async def deal_demand_one(deal_id: str) -> dict:
    counts = await _signals_counts(deal_id)
    deal = await db.pb_community_deals.find_one({"id": deal_id}, {"supporter_ids": 1}) or {}
    counts["sustin"] = max(counts["sustin"], len(deal.get("supporter_ids") or []))
    score = round(sum(counts[s] * SIGNAL_WEIGHTS[s] for s in DEAL_SIGNALS), 1)
    level = "ridicat" if score >= 20 else "moderat" if score >= 8 else "în creștere" if score >= 3 else "incipient"
    return {"counts": counts, "demand_score": score, "interest_level": level,
            "participants": sum(counts.values())}


async def deals_demand() -> list:
    out = []
    async for d in db.pb_community_deals.find({"active": True, "status": {"$ne": "arhivat"}}, {"_id": 0, "supporter_ids": 0}):
        demand = await deal_demand_one(d["id"])
        out.append({**d, **demand})
    out.sort(key=lambda x: -x["demand_score"])
    for i, d in enumerate(out, 1):
        d["negotiation_priority"] = i
    return out


async def explain_deal(deal_id: str, user_ctx: dict = None) -> dict:
    d = await db.pb_community_deals.find_one({"id": deal_id}, {"_id": 0, "supporter_ids": 0})
    if not d:
        return {"error": "Deal inexistent."}
    demand = await deal_demand_one(deal_id)
    why = [f"Interes {demand['interest_level']}: {demand['participants']} membri au semnalat acest deal.",
           f"Prioritate de negociere calculată din cerere reală (scor {demand['demand_score']})."]
    if user_ctx:
        if user_ctx.get("properties", 0) > 0:
            why.append("Ai proprietăți în platformă — beneficiul se aplică direct casei tale.")
        if user_ctx.get("subscription_active"):
            why.append("Ca abonat, ai prioritate la lansarea acordului.")
    return {"deal": d, "demand": demand, "why": why,
            "explanation": "Recomandarea e generată din cererea reală a comunității, nu din promisiuni comerciale."}


# ---------------------------------------------------------------------------
# 6. AI Trust Graph — REUSE ai_brain_graph_nodes/edges
# ---------------------------------------------------------------------------
TRUST_RELS = ["recommended", "executed_for", "supports_deal", "benefit_granted", "referred"]


async def sync_trust_graph(cap: int = 800) -> dict:
    await db.ai_brain_graph_edges.delete_many({"rel": {"$in": TRUST_RELS}})
    await db.ai_brain_graph_nodes.delete_many({"kind": {"$in": ["trust_client", "trust_specialist", "trust_deal", "trust_benefit"]}})
    nodes, edges = {}, []

    def add_node(nid, kind, label):
        nodes[nid] = {"id": nid, "kind": kind, "label": label}

    async for r in db.recommendations.find({}, {"owner_id": 1, "owner_name": 1, "specialist_id": 1,
                                                "specialist_name": 1, "status": 1}).limit(cap):
        c, s = f"client:{r['owner_id']}", f"specialist:{r['specialist_id']}"
        add_node(c, "trust_client", r.get("owner_name") or "Client")
        add_node(s, "trust_specialist", r.get("specialist_name") or "Specialist")
        edges.append({"source": c, "target": s, "rel": "recommended",
                      "weight": 2 if r.get("status") == "validated" else 1})
    async for req in db.requests.find({"specialist_id": {"$ne": None}, "status": {"$in": ["completed", "confirmed"]}},
                                      {"client_id": 1, "specialist_id": 1}).limit(cap):
        c, s = f"client:{req['client_id']}", f"specialist:{req['specialist_id']}"
        add_node(c, "trust_client", "Client")
        add_node(s, "trust_specialist", "Specialist")
        edges.append({"source": s, "target": c, "rel": "executed_for", "weight": 1})
    async for row in db.pb_deal_signals.find({}, {"deal_id": 1, "user_id": 1}).limit(cap):
        c, dnode = f"client:{row['user_id']}", f"deal:{row['deal_id']}"
        add_node(c, "trust_client", "Client")
        add_node(dnode, "trust_deal", "Community Deal")
        edges.append({"source": c, "target": dnode, "rel": "supports_deal", "weight": 1})
    async for b in db.pb_ledger.find({}, {"user_id": 1, "benefit_key": 1}).limit(cap):
        c, bn = f"client:{b['user_id']}", f"benefit:{b['benefit_key']}"
        add_node(c, "trust_client", "Client")
        add_node(bn, "trust_benefit", b["benefit_key"])
        edges.append({"source": bn, "target": c, "rel": "benefit_granted", "weight": 1})
    async for p in db.pb_referral_pending.find({}, {"inviter_id": 1, "invitee_id": 1}).limit(cap):
        a, b2 = f"client:{p['inviter_id']}", f"client:{p['invitee_id']}"
        add_node(a, "trust_client", "Client")
        add_node(b2, "trust_client", "Client")
        edges.append({"source": a, "target": b2, "rel": "referred", "weight": 1})

    if nodes:
        for nd in nodes.values():
            await db.ai_brain_graph_nodes.update_one({"id": nd["id"]}, {"$set": nd}, upsert=True)
    if edges:
        await db.ai_brain_graph_edges.insert_many(edges)
    return {"nodes": len(nodes), "edges": len(edges)}


# ---------------------------------------------------------------------------
# 8. Community Growth Dashboard — AI răspunde la întrebările Fondatorului
# ---------------------------------------------------------------------------
async def community_growth() -> dict:
    demand = await deals_demand()
    top_deal = demand[0] if demand else None
    to_start = next((d for d in demand if d["status"] in ("in_lucru", "negociere")), None)
    cat_demand = {}
    for d in demand:
        cat_demand[d.get("category") or "—"] = cat_demand.get(d.get("category") or "—", 0) + d["demand_score"]
    top_cat = max(cat_demand, key=cat_demand.get) if cat_demand else None
    partner_deal = next((d for d in demand if d.get("category") == "Parteneriat local"), None)

    ambassadors = await db.users.find({"pb_ambassador": True}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(20)
    for a in ambassadors:
        a["validated"] = await db.recommendations.count_documents({"owner_id": a["id"], "status": "validated"})
    rec_pending = await db.recommendations.count_documents({"source": "job", "status": "pending"})
    rec_validated = await db.recommendations.count_documents({"status": "validated"})

    engaged_ids = set(await db.recommendations.distinct("owner_id")) | set(await db.pb_deal_signals.distinct("user_id"))
    engaged_healthy = await db.pb_subscription_health.count_documents({"user_id": {"$in": list(engaged_ids)}, "score": {"$gte": 70}}) if engaged_ids else 0
    others_healthy = await db.pb_subscription_health.count_documents({"user_id": {"$nin": list(engaged_ids)}, "score": {"$gte": 70}})
    others_total = await db.pb_subscription_health.count_documents({"user_id": {"$nin": list(engaged_ids)}})

    answers = {
        "most_valuable_deal": ({"deal": top_deal["title"], "demand_score": top_deal["demand_score"],
                                "interest": top_deal["interest_level"],
                                "answer": f"„{top_deal['title']}” — cererea cea mai mare din comunitate (scor {top_deal['demand_score']}, interes {top_deal['interest_level']})."}
                               if top_deal else {"answer": "Încă nu există semnale suficiente."}),
        "negotiation_to_start": ({"deal": to_start["title"],
                                  "answer": f"Pornește negocierea pentru „{to_start['title']}” — prioritate #{to_start['negotiation_priority']} după cererea reală."}
                                 if to_start else {"answer": "Toate negocierile cu cerere sunt deja pornite."}),
        "top_demand_category": ({"category": top_cat, "answer": f"Categoria „{top_cat}” concentrează cea mai mare cerere (scor {round(cat_demand[top_cat], 1)})."}
                                if top_cat else {"answer": "Fără date încă."}),
        "partner_to_contact": ({"answer": f"„{partner_deal['title']}” are {partner_deal['participants']} membri interesați — partenerul local merită contactat acum."}
                               if partner_deal and partner_deal["participants"] else
                               {"answer": "Niciun semnal puternic pentru parteneri locali încă — activează un deal City Partner."}),
        "active_ambassadors": {"count": len(ambassadors), "items": ambassadors,
                               "answer": f"{len(ambassadors)} ambasadori activi." if ambassadors else "Niciun ambasador încă — primele recomandări validate vor promova primii ambasadori."},
        "retention_impact": {
            "engaged_members": len(engaged_ids), "engaged_healthy": engaged_healthy,
            "others_healthy": others_healthy, "others_total": others_total,
            "answer": (f"{len(engaged_ids)} membri implicați în recomandări/deals — dintre ei {engaged_healthy} au abonamente sănătoase. "
                       "Implicarea în comunitate este cel mai puternic semnal de retenție.")},
    }
    return {"answers": answers, "deals_demand": demand,
            "recommendations": {"pending": rec_pending, "validated": rec_validated},
            "generated_at": _iso()}
