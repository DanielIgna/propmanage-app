"""Marketing Intelligence+ Engine — Board Decision 007 / Sprint GI-3.

Recomandări EXECUTIVE (nu grafice) din comportament real, fiecare cu:
motiv + nivel de încredere + impact estimat + KPI de validare (cerință Board 007).
  • WhatsApp/Send-Window Intelligence: „Trimite marți 18:00–20:00 — conversie +X% peste medie"
  • Channel performance: ce canal produce conversii
  • Message performance: ce campanie/mesaj convertește (growth_campaigns + A/B winners)
  • Commercial Intelligence: ce serviciu produce bani / convertește / se promovează / pierde clienți
  • Opportunity Queue: probabilitate × valoare × urgență (lead_scores × revenue_opportunities)
AI recomandă, omul aprobă (Contact Playbook separat). Rule-based, zero cost LLM la scan.
"""
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import pytz

from db import db
from growth_intelligence import validation_level, DOW_RO

logger = logging.getLogger("propmanage.marketing_intel")

BUCHAREST = pytz.timezone("Europe/Bucharest")
COMMERCIAL_SERVICES = ("digital_twin", "audit_tehnic", "design_interior", "design_tematic")

VALIDATION_LABELS = {
    "confirmed_real": "Confirmată de date reale",
    "partially_confirmed": "Confirmată parțial",
    "ai_hypothesis": "Ipoteză AI",
    "rejected": "Respinsă de date",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()


def _rec(title, reason, confidence, impact, kpi, category) -> dict:
    return {"id": uuid.uuid4().hex[:12], "title": title, "reason": reason,
            "confidence": confidence, "confidence_label": VALIDATION_LABELS.get(confidence, confidence),
            "impact_estimate": impact, "kpi": kpi, "category": category, "created_at": _now()}


# ============================================================================
# SEND WINDOWS — WhatsApp Intelligence (ferestre de 2h, uplift vs medie)
# ============================================================================
async def best_send_windows(days: int = 60) -> dict:
    sessions = await db.analytics_sessions.find({"day": {"$gte": _day_ago(days)}}).to_list(20000)
    grid = defaultdict(lambda: {"sessions": 0, "conv": 0})
    wa_grid = defaultdict(lambda: {"sessions": 0, "conv": 0})
    total = conv_total = 0
    for s in sessions:
        try:
            dt = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00")).astimezone(BUCHAREST)
        except Exception:  # noqa: BLE001
            continue
        key = (dt.weekday(), (dt.hour // 2) * 2)
        conv = 1 if s.get("funnel_account_created") else 0
        grid[key]["sessions"] += 1
        grid[key]["conv"] += conv
        total += 1
        conv_total += conv
        if (s.get("source") or "") == "whatsapp":
            wa_grid[key]["sessions"] += 1
            wa_grid[key]["conv"] += conv
    avg_rate = conv_total / total if total else 0

    def best(g, min_sessions=5):
        cands = []
        for (dow, h), v in g.items():
            if v["sessions"] < min_sessions:
                continue
            rate = v["conv"] / v["sessions"]
            uplift = round((rate - avg_rate) / avg_rate * 100) if avg_rate else None
            cands.append({"day": dow, "day_label": DOW_RO[dow], "hour_from": h, "hour_to": h + 2,
                          "sessions": v["sessions"], "conversions": v["conv"],
                          "uplift_pct": uplift, "rate_pct": round(rate * 100, 1)})
        if not cands:
            # fallback: fereastra cu cea mai mare activitate (fără prag conversie)
            if not g:
                return None
            (dow, h), v = max(g.items(), key=lambda x: x[1]["conv"] * 5 + x[1]["sessions"])
            return {"day": dow, "day_label": DOW_RO[dow], "hour_from": h, "hour_to": h + 2,
                    "sessions": v["sessions"], "conversions": v["conv"], "uplift_pct": None,
                    "rate_pct": round(v["conv"] / v["sessions"] * 100, 1) if v["sessions"] else 0}
        cands.sort(key=lambda c: (-(c["uplift_pct"] or -999), -c["conversions"], -c["sessions"]))
        return cands[0]

    def exec_text(w, channel):
        if not w:
            return {"text": f"Date insuficiente pentru {channel} — pornește cu Marți/Joi 18:00–20:00 (ipoteză)",
                    "window": None, "validation": "ai_hypothesis", "sample": 0}
        base = f"{w['day_label']} între {w['hour_from']:02d}:00–{w['hour_to']:02d}:00"
        if w["uplift_pct"] is not None and w["uplift_pct"] > 0:
            text = (f"Trimite mesajele {channel} {base} — conversia a fost cu {w['uplift_pct']}% "
                    f"peste medie în ultimele {days} zile ({w['conversions']} conturi din {w['sessions']} sesiuni)")
            strong = True
        else:
            text = f"{base} concentrează cea mai mare activitate {channel} ({w['sessions']} sesiuni, {w['conversions']} conversii)"
            strong = w["conversions"] > 0
        return {"text": text, "window": w, "validation": validation_level(w["sessions"], strong=strong), "sample": w["sessions"]}

    return {
        "avg_conversion_pct": round(avg_rate * 100, 1),
        "overall": exec_text(best(grid), "de campanie"),
        "whatsapp": exec_text(best(wa_grid, min_sessions=3), "WhatsApp"),
        "period_days": days, "sessions_analyzed": total,
    }


# ============================================================================
# CANALE + MESAJE
# ============================================================================
async def channel_performance(days: int = 60) -> dict:
    sessions = await db.analytics_sessions.find({"day": {"$gte": _day_ago(days)}}).to_list(20000)
    by_src = defaultdict(lambda: {"sessions": 0, "visitors": set(), "accounts": set(), "requests": set()})
    for s in sessions:
        src = by_src[s.get("source") or "direct"]
        src["sessions"] += 1
        src["visitors"].add(s["visitor_id"])
        if s.get("funnel_account_created"):
            src["accounts"].add(s["visitor_id"])
        if s.get("funnel_specialist_request"):
            src["requests"].add(s["visitor_id"])
    rows = [{"source": k, "sessions": v["sessions"], "visitors": len(v["visitors"]),
             "accounts": len(v["accounts"]), "requests": len(v["requests"]),
             "conv_pct": round(len(v["accounts"]) / len(v["visitors"]) * 100, 1) if v["visitors"] else 0.0}
            for k, v in sorted(by_src.items(), key=lambda x: -x[1]["sessions"])]
    converting = [r for r in rows if r["accounts"] > 0]
    best = max(converting, key=lambda r: r["conv_pct"]) if converting else (rows[0] if rows else None)
    return {"channels": rows, "best": best}


async def message_performance() -> dict:
    """Ce mesaj/campanie convertește — growth_campaigns + câștigători A/B semnificativi."""
    from routes.analytics_growth import _campaign_stats
    camps = []
    async for c in db.growth_campaigns.find({}).sort("created_at", -1).limit(50):
        st = (await _campaign_stats(c))["stats"]
        camps.append({"name": c.get("name"), "channel": c.get("channel"), "code": c.get("code"),
                      "visitors": st["unique_visitors"], "accounts": st["accounts_created"],
                      "conversion_pct": st["conversion_pct"], "notes": (c.get("notes") or "")[:120]})
    with_traffic = [c for c in camps if c["visitors"] >= 5]
    best_campaign = max(with_traffic, key=lambda c: c["conversion_pct"]) if with_traffic else None
    ab_winners = []
    async for e in db.ab_experiments.find({}):
        from routes.analytics_growth import _ab_results
        res = await _ab_results(e["key"], e.get("goal") or "account_created")
        if res.get("winner"):
            ab_winners.append({"name": e.get("name"), "winner": res["winner"], "uplift_pct": res.get("uplift_pct")})
    return {"campaigns": camps[:10], "best_campaign": best_campaign, "ab_winners": ab_winners}


# ============================================================================
# COMMERCIAL INTELLIGENCE — 4 răspunsuri directe
# ============================================================================
async def commercial_intelligence(days: int = 90) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    revenue = defaultdict(float)
    req_count = defaultdict(int)
    async for r in db.requests.find({"created_at": {"$gte": cutoff}}, {"category": 1, "status": 1, "escrow_amount": 1}):
        cat = r.get("category") or "altele"
        req_count[cat] += 1
        if r.get("status") == "confirmed":
            revenue[cat] += float(r.get("escrow_amount") or 0)
    top_revenue = max(revenue.items(), key=lambda x: x[1]) if revenue else None

    opp = defaultdict(lambda: {"created": 0, "accepted": 0})
    async for o in db.revenue_opportunities.find({}, {"service": 1, "status": 1}):
        st = opp[o.get("service") or "?"]
        st["created"] += 1
        if o.get("status") == "accepted":
            st["accepted"] += 1
    conv_rows = [{"service": k, **v, "conv_pct": round(v["accepted"] / v["created"] * 100, 1) if v["created"] else 0.0}
                 for k, v in opp.items()]
    best_conv = max([r for r in conv_rows if r["created"] >= 2], key=lambda r: r["conv_pct"], default=None)

    # trend cereri 30z vs 30z anterioare → ce se promovează acum
    d30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    d60 = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    recent = defaultdict(int)
    prev = defaultdict(int)
    async for r in db.requests.find({"created_at": {"$gte": d60}}, {"category": 1, "created_at": 1}):
        cat = r.get("category") or "altele"
        (recent if r["created_at"] >= d30 else prev)[cat] += 1
    trends = [{"category": c, "recent": recent[c], "prev": prev.get(c, 0),
               "trend_pct": round((recent[c] - prev.get(c, 0)) / prev[c] * 100) if prev.get(c) else None}
              for c in recent]
    rising = max([t for t in trends if t["recent"] >= 3], key=lambda t: (t["trend_pct"] or 0), default=None)

    # ce serviciu pierde clienți — dispute per categorie
    disputes_by_cat = defaultdict(int)
    async for d in db.disputes.find({}, {"request_id": 1}):
        try:
            from bson import ObjectId
            req = await db.requests.find_one({"_id": ObjectId(d.get("request_id") or "0" * 24)}, {"category": 1})
            if req:
                disputes_by_cat[req.get("category") or "altele"] += 1
        except Exception:  # noqa: BLE001
            continue
    losing = max(disputes_by_cat.items(), key=lambda x: x[1]) if disputes_by_cat else None

    return {
        "top_revenue": {"category": top_revenue[0], "revenue_ron": round(top_revenue[1], 2)} if top_revenue else None,
        "best_converting": best_conv,
        "promote_now": rising,
        "losing_clients": {"category": losing[0], "disputes": losing[1]} if losing else None,
        "requests_by_category": dict(req_count),
        "period_days": days,
    }


# ============================================================================
# OPPORTUNITY QUEUE — probabilitate × valoare × urgență
# ============================================================================
SIGNAL_SERVICE_MAP = {"twin_viewed": "digital_twin", "audit_viewed": "audit_tehnic"}


async def build_opportunity_queue(limit: int = 30) -> list:
    from revenue_hunter import SERVICES
    items = []
    seen_owners = set()

    async for o in db.revenue_opportunities.find({"status": "active"}).sort("score", -1).limit(120):
        lead = await db.lead_scores.find_one({"user_id": o.get("owner_id")}) if o.get("owner_id") else None
        prob = (lead or {}).get("conv_probability_pct") or 35
        tier = (lead or {}).get("tier")
        urgent = tier == "hot" or any(s.get("signal") == "request_abandoned" for s in (lead or {}).get("signals") or [])
        value = float(o.get("estimated_value_ron") or 0)
        items.append({
            "type": "opportunity", "ref_id": o["id"],
            "name": (lead or {}).get("user_name") or (lead or {}).get("user_email") or o.get("property_name") or "Proprietar",
            "probability_pct": prob, "service": o.get("service"),
            "service_label": o.get("service_label"), "value_ron": value,
            "urgency": "high" if urgent else ("medium" if tier == "qualified" else "low"),
            "lead_tier": tier, "signals": [s["label"] for s in ((lead or {}).get("signals") or [])[:5]],
            "priority": round(prob / 100 * value * (1.3 if urgent else 1.0), 1),
        })
        if o.get("owner_id"):
            seen_owners.add(o["owner_id"])

    # lead-uri fierbinți/calificate fără oportunitate activă → serviciu dedus din semnale
    async for lead in db.lead_scores.find({"tier": {"$in": ["hot", "qualified"]}}).sort("score", -1).limit(50):
        if lead.get("user_id") and lead["user_id"] in seen_owners:
            continue
        sigs = {s["signal"] for s in lead.get("signals") or []}
        service = next((SIGNAL_SERVICE_MAP[s] for s in SIGNAL_SERVICE_MAP if s in sigs), "audit_tehnic")
        meta = SERVICES.get(service) or {}
        prob = lead.get("conv_probability_pct") or 50
        value = float(meta.get("value") or 800)
        urgent = lead["tier"] == "hot" or "request_abandoned" in sigs
        items.append({
            "type": "lead", "ref_id": lead["visitor_id"],
            "name": lead.get("user_name") or lead.get("user_email") or f"Vizitator {str(lead['visitor_id'])[:8]}…",
            "probability_pct": prob, "service": service, "service_label": meta.get("label", service),
            "value_ron": value, "urgency": "high" if urgent else "medium",
            "lead_tier": lead["tier"], "signals": [s["label"] for s in (lead.get("signals") or [])[:5]],
            "priority": round(prob / 100 * value * (1.3 if urgent else 1.0), 1),
        })

    items.sort(key=lambda i: -i["priority"])
    return items[:limit]


# ============================================================================
# SCAN COMPLET — recomandări executive
# ============================================================================
async def run_marketing_scan(trigger: str = "manual") -> dict:
    windows = await best_send_windows(60)
    channels = await channel_performance(60)
    messages = await message_performance()
    commercial = await commercial_intelligence(90)
    growth = await db.growth_insights.find_one({"_id": "latest"}) or {}
    abandon = (growth.get("abandon_pages") or [])[:1]

    recs = []
    wa = windows["whatsapp"]
    recs.append(_rec("Fereastra optimă pentru mesajele WhatsApp", wa["text"], wa["validation"],
                     "Mai multe conturi noi per mesaj trimis", "accounts_created", "whatsapp"))
    ov = windows["overall"]
    recs.append(_rec("Fereastra optimă pentru postări și campanii", ov["text"], ov["validation"],
                     "Trafic calificat în intervalul de conversie maximă", "sessions", "marketing"))
    if channels["best"]:
        b = channels["best"]
        recs.append(_rec(f"Canalul care produce conversii: «{b['source']}»",
                         f"{b['conv_pct']}% conversie ({b['accounts']} conturi din {b['visitors']} vizitatori, {b['sessions']} sesiuni)",
                         validation_level(b["visitors"], strong=b["accounts"] > 0),
                         "Realocarea bugetului/efortului pe acest canal crește conturile noi", "conv_pct", "marketing"))
    if messages["best_campaign"]:
        m = messages["best_campaign"]
        recs.append(_rec(f"Mesajul care convertește: campania «{m['name']}»",
                         f"{m['conversion_pct']}% conversie pe {m['visitors']} vizitatori (canal {m['channel']}) — refolosește structura mesajului",
                         validation_level(m["visitors"], strong=m["accounts"] > 0),
                         "Șablonul câștigător aplicat pe următoarele campanii", "conversion_pct", "marketing"))
    if commercial["promote_now"]:
        p = commercial["promote_now"]
        trend = f"+{p['trend_pct']}% vs 30 zile anterioare" if p.get("trend_pct") is not None else f"{p['recent']} cereri în 30 zile"
        recs.append(_rec(f"Serviciul de promovat acum: «{p['category']}»", f"Cerere în creștere: {trend}",
                         validation_level(p["recent"] + (p.get("prev") or 0), strong=p["recent"] >= 3),
                         "Campanie pe cerere existentă = conversie mai ieftină", "specialist_requests", "comercial"))
    if commercial["top_revenue"]:
        t = commercial["top_revenue"]
        recs.append(_rec(f"Serviciul care produce cei mai mulți bani: «{t['category']}»",
                         f"{t['revenue_ron']:,.0f} RON venit confirmat în {commercial['period_days']} zile",
                         "confirmed_real", "Menține capacitatea de specialiști pe această categorie", "revenue", "comercial"))
    if abandon:
        a = abandon[0]
        recs.append(_rec(f"Pagina care pierde cei mai mulți utilizatori: «{a['path']}»",
                         f"{a['exits']} ieșiri ({a['exit_share_pct']}% din sesiuni) — repar-o înaintea următoarei campanii",
                         a.get("validation", "ai_hypothesis"),
                         "Fiecare % de abandon recuperat = trafic de campanie valorificat", "bounce_rate_pct", "ux"))

    queue = await build_opportunity_queue(30)
    doc = {
        "generated_at": _now(), "trigger": trigger,
        "send_windows": windows, "channels": channels, "messages": messages,
        "commercial": commercial, "recommendations": recs,
        "queue_size": len(queue), "queue_value_ron": round(sum(i["value_ron"] for i in queue), 2),
    }
    await db.marketing_insights.update_one({"_id": "latest"}, {"$set": doc}, upsert=True)
    await db.marketing_insights_history.insert_one({**doc})
    try:
        from event_bus import emit
        await emit("marketing.scan_completed", payload={"trigger": trigger, "recommendations": len(recs),
                                                        "queue_size": len(queue)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[marketing_intel] event emit failed: {e}")
    logger.info(f"[marketing_intel] scan done ({trigger}): {len(recs)} recomandări, queue={len(queue)}")
    return {k: v for k, v in doc.items() if k != "_id"}
