"""Intent & Lead Intelligence Engine — Board Decision GI-2 (004/005/006 + extensia Intent Score).

Nu doar Lead Score (login/click/pagini) — INTENT SCORE: corelează toate semnalele reale:
  • semnale explicite (evenimente intent din tracker): twin_viewed, audit_viewed,
    request_started, request_abandoned, offer_requested, whatsapp_opened, ...
  • semnale derivate din comportament (fără instrumentare nouă — Board 006):
    reveniri în aceeași zi / multi-zi, revenire după campanie, interes repetat pe aceeași
    pagină, timp de engagement, navigare adâncă, cont creat.
Clasificare: visitor → prospect → qualified → hot → client.
Consumatori: Revenue Hunter (prioritizare automată) + AI Command Center (alerte lead-uri fierbinți).
Board 006: modelul de scoring v1 este marcat ai_hypothesis până la calibrarea Learning Engine (GI-4).
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.lead_intel")

# Semnale explicite de intenție (evenimente type=intent din tracker) — puncte o singură dată
INTENT_WEIGHTS = {
    "offer_requested": 25,
    "request_started": 20,
    "request_abandoned": 12,   # intenție reală + fricțiune → prioritate follow-up
    "twin_viewed": 15,
    "whatsapp_opened": 15,
    "audit_viewed": 12,
    "specialist_compared": 10,
    "guide_downloaded": 8,
}
# Semnale derivate din sesiuni/pageviews (date deja colectate)
DERIVED_WEIGHTS = {
    "account_created": 15,
    "multi_day_return": 12,
    "campaign_return": 10,
    "repeat_page_interest": 10,
    "same_day_return": 8,
    "engaged_time": 8,
    "deep_navigation": 5,
}
BOUNCE_ONLY_PENALTY = -10

SIGNAL_LABELS = {
    "offer_requested": "A cerut ofertă",
    "request_started": "A început o cerere",
    "request_abandoned": "A abandonat o cerere (follow-up!)",
    "twin_viewed": "A explorat Digital Twin",
    "audit_viewed": "A citit auditul / House Health",
    "whatsapp_opened": "A deschis WhatsApp",
    "specialist_compared": "A comparat specialiști",
    "guide_downloaded": "A citit ghiduri",
    "account_created": "Cont creat",
    "multi_day_return": "Revine în zile diferite",
    "same_day_return": "Revine în aceeași zi",
    "campaign_return": "S-a întors după mesajul din campanie",
    "repeat_page_interest": "Vizite repetate la același conținut",
    "engaged_time": "Timp de engagement ridicat (3+ min)",
    "deep_navigation": "Navigare adâncă (5+ pagini)",
    "bounce_only": "Doar sesiuni bounce",
}

TIER_LABELS = {
    "visitor": "Vizitator", "prospect": "Prospect", "qualified": "Lead calificat",
    "hot": "Lead fierbinte", "client": "Client",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()


def _tier(score: int, is_client: bool) -> str:
    if is_client:
        return "client"
    if score >= 60:
        return "hot"
    if score >= 40:
        return "qualified"
    if score >= 20:
        return "prospect"
    return "visitor"


def _score_visitor(sessions: list, intents: set, paths_by_session: dict) -> tuple:
    """Returnează (score, signals[]) — fiecare semnal cu puncte + detaliu explicabil."""
    signals = []
    score = 0
    for sig in intents:
        w = INTENT_WEIGHTS.get(sig)
        if w:
            signals.append({"signal": sig, "label": SIGNAL_LABELS.get(sig, sig), "points": w})
            score += w

    days = {s.get("day") for s in sessions if s.get("day")}
    day_counts = defaultdict(int)
    for s in sessions:
        day_counts[s.get("day")] += 1

    derived = []
    if any(s.get("funnel_account_created") for s in sessions):
        derived.append("account_created")
    if len(days) >= 2:
        derived.append("multi_day_return")
    if any(c >= 2 for c in day_counts.values()):
        derived.append("same_day_return")
    if len(days) >= 2 and any((s.get("source") or "") in ("whatsapp", "qr") or s.get("campaign_code") for s in sessions):
        derived.append("campaign_return")
    total_dur = sum(s.get("duration_ms") or 0 for s in sessions)
    if total_dur >= 180_000:
        derived.append("engaged_time")
    total_pv = sum(s.get("pageviews") or 0 for s in sessions)
    if total_pv >= 5:
        derived.append("deep_navigation")
    # interes repetat: aceeași pagină (non-generică) în 2+ sesiuni distincte
    page_sessions = defaultdict(set)
    for sid, paths in paths_by_session.items():
        for p in paths:
            if p not in ("/", "/login", "/register", ""):
                page_sessions[p].add(sid)
    if any(len(v) >= 2 for v in page_sessions.values()):
        derived.append("repeat_page_interest")

    for sig in derived:
        w = DERIVED_WEIGHTS[sig]
        signals.append({"signal": sig, "label": SIGNAL_LABELS[sig], "points": w})
        score += w

    if sessions and all((s.get("pageviews") or 0) <= 1 for s in sessions) and not intents:
        signals.append({"signal": "bounce_only", "label": SIGNAL_LABELS["bounce_only"], "points": BOUNCE_ONLY_PENALTY})
        score += BOUNCE_ONLY_PENALTY

    return max(0, min(100, score)), sorted(signals, key=lambda x: -x["points"])


async def run_lead_scan(trigger: str = "manual", days: int = 30) -> dict:
    """Scanează toți vizitatorii activi → lead_scores. Emite lead.hot_detected la trecerea în hot."""
    cutoff_day = _day_ago(days)
    sessions_by_visitor = defaultdict(list)
    async for s in db.analytics_sessions.find({"day": {"$gte": cutoff_day}}):
        sessions_by_visitor[s["visitor_id"]].append(s)

    # evenimente intent + pageview paths per sesiune
    session_visitor = {s["session_id"]: v for v, ss in sessions_by_visitor.items() for s in ss}
    intents_by_visitor = defaultdict(set)
    paths_by_visitor_session: dict = defaultdict(lambda: defaultdict(list))
    q = {"day": {"$gte": cutoff_day}, "type": {"$in": ["intent", "pageview"]}}
    async for ev in db.analytics_events.find(q, {"type": 1, "session_id": 1, "intent_signal": 1, "path": 1}):
        v = session_visitor.get(ev.get("session_id"))
        if not v:
            continue
        if ev["type"] == "intent" and ev.get("intent_signal"):
            intents_by_visitor[v].add(ev["intent_signal"])
        elif ev["type"] == "pageview":
            paths_by_visitor_session[v][ev["session_id"]].append(ev.get("path") or "/")

    # identități vizitator → user
    identities = {}
    async for i in db.visitor_identities.find({}):
        identities[i["visitor_id"]] = i

    scanned = hot_new = 0
    tiers = defaultdict(int)
    for visitor_id, sessions in sessions_by_visitor.items():
        scanned += 1
        intents = set(intents_by_visitor.get(visitor_id) or set())
        # abandon derivat: a început dar nu a finalizat nicio cerere
        if "request_started" in intents and "offer_requested" not in intents \
                and not any(s.get("funnel_specialist_request") for s in sessions):
            intents.add("request_abandoned")
        score, signals = _score_visitor(sessions, intents, paths_by_visitor_session.get(visitor_id) or {})

        ident = identities.get(visitor_id) or {}
        user_id = ident.get("user_id") or next((s.get("user_id") for s in sessions if s.get("user_id")), None)
        user_name = user_email = None
        is_client = False
        if user_id:
            from bson import ObjectId
            try:
                u = await db.users.find_one({"_id": ObjectId(user_id)}, {"name": 1, "email": 1})
                if u:
                    user_name, user_email = u.get("name"), u.get("email")
                is_client = bool(await db.requests.find_one({"client_id": user_id}, {"_id": 1}))
            except Exception:  # noqa: BLE001
                pass

        tier = _tier(score, is_client)
        tiers[tier] += 1
        sources = sorted({s.get("source") or "direct" for s in sessions})
        prev = await db.lead_scores.find_one({"_id": visitor_id}, {"tier": 1})
        doc = {
            "visitor_id": visitor_id, "user_id": user_id,
            "user_name": user_name, "user_email": user_email,
            "score": score, "tier": tier, "tier_label": TIER_LABELS[tier],
            "conv_probability_pct": None if tier == "client" else min(92, round(score * 0.85)),
            "signals": signals, "sources": sources,
            "sessions": len(sessions),
            "last_seen": max((s.get("last_seen_at") or s.get("started_at") or "") for s in sessions),
            "updated_at": _now(),
        }
        await db.lead_scores.update_one({"_id": visitor_id}, {"$set": doc}, upsert=True)
        if tier == "hot" and (prev or {}).get("tier") != "hot":
            hot_new += 1
            try:
                from event_bus import emit
                await emit("lead.hot_detected", payload={"visitor_id": visitor_id, "score": score,
                                                         "user_email": user_email, "signals": [s["signal"] for s in signals[:5]]})
            except Exception:  # noqa: BLE001
                pass

    summary = {"trigger": trigger, "period_days": days, "scanned": scanned,
               "tiers": dict(tiers), "new_hot": hot_new, "generated_at": _now()}
    await db.lead_scores_meta.update_one({"_id": "latest_scan"}, {"$set": summary}, upsert=True)
    try:
        from event_bus import emit
        await emit("lead.scan_completed", payload={"scanned": scanned, "hot": tiers.get("hot", 0), "trigger": trigger})
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[lead_intel] scan done ({trigger}): {scanned} vizitatori, tiers={dict(tiers)}, hot noi={hot_new}")
    return summary
