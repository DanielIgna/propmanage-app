"""Growth Intelligence Engine — Board Decision 004/005/006 (Sprint GI-1).

Agent permanent care analizează comportamentul REAL al utilizatorilor
(analytics_sessions / analytics_events / requests / revenue_opportunities) și produce:
  • top probleme UX (bounce mare, timp mic, căderi de funnel)
  • paginile cu cel mai mare abandon
  • traseele reale ale utilizatorilor
  • Behavioral Intelligence: ora/ziua optimă (postări, WhatsApp), comparație surse, serviciu top
  • recomandări concrete, fiecare cu NIVEL DE VALIDARE (Board 006):
    confirmed_real | partially_confirmed | ai_hypothesis | rejected
Rule-based v1 — zero cost LLM (ierarhia de cost, Prompt 003). Datele reale = sursa de adevăr.
"""
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import pytz

from db import db

logger = logging.getLogger("propmanage.growth_intel")

BUCHAREST = pytz.timezone("Europe/Bucharest")
DOW_RO = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"]
MIN_SAMPLE = 20  # Board 006: sub acest prag orice concluzie rămâne Ipoteză AI


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()


def validation_level(sample: int, strong: bool = True) -> str:
    """Board 006: nivel de validare pe baza volumului de date reale + tăriei semnalului."""
    if sample >= MIN_SAMPLE:
        return "confirmed_real" if strong else "partially_confirmed"
    return "ai_hypothesis"


# ============================================================================
# ANALIZE — toate pe date reale
# ============================================================================
async def _load_sessions(days: int) -> list:
    return await db.analytics_sessions.find({"day": {"$gte": _day_ago(days)}}).to_list(20000)


async def analyze_ux_problems(sessions: list, days: int) -> list:
    """Probleme UX: bounce mare pe pagini de intrare, timp foarte mic, căderi de funnel."""
    problems = []
    entry = defaultdict(lambda: {"entries": 0, "bounces": 0})
    for s in sessions:
        e = entry[s.get("entry_path") or "/"]
        e["entries"] += 1
        if (s.get("pageviews") or 0) <= 1:
            e["bounces"] += 1
    for path, e in sorted(entry.items(), key=lambda x: -x[1]["entries"]):
        pct = round(e["bounces"] / e["entries"] * 100, 1) if e["entries"] else 0
        if e["entries"] >= 5 and pct >= 55:
            problems.append({
                "type": "bounce", "path": path,
                "label": f"«{path}» pierde {pct}% din vizitatori după o singură pagină",
                "evidence": f"{e['bounces']}/{e['entries']} sesiuni de intrare au părăsit imediat",
                "sample": e["entries"], "validation": validation_level(e["entries"]),
            })

    # timp mediu foarte mic pe pagini cu trafic
    pages = defaultdict(lambda: {"views": 0, "dur": 0})
    q = {"day": {"$gte": _day_ago(days)}, "type": {"$in": ["pageview", "heartbeat"]}}
    async for ev in db.analytics_events.find(q, {"path": 1, "type": 1, "duration_ms": 1}):
        p = pages[ev.get("path") or "/"]
        if ev["type"] == "pageview":
            p["views"] += 1
        else:
            p["dur"] += ev.get("duration_ms", 0)
    for path, p in pages.items():
        if p["views"] >= 10:
            avg_s = round(p["dur"] / p["views"] / 1000)
            if avg_s < 8:
                problems.append({
                    "type": "low_time", "path": path,
                    "label": f"«{path}» ține vizitatorii doar {avg_s}s — mesaj neclar sau CTA neobservat",
                    "evidence": f"{p['views']} vizualizări, timp mediu {avg_s}s",
                    "sample": p["views"], "validation": validation_level(p["views"]),
                })

    # cea mai mare cădere de funnel (vizită → cont)
    visitors = {s["visitor_id"] for s in sessions}
    signup = {s["visitor_id"] for s in sessions if s.get("funnel_signup_started")}
    accounts = {s["visitor_id"] for s in sessions if s.get("funnel_account_created")}
    if len(visitors) >= 5 and not accounts:
        problems.append({
            "type": "funnel", "path": "/register",
            "label": f"Trafic fără conversie: {len(visitors)} vizitatori, zero conturi create",
            "evidence": f"{len(signup)} au început înregistrarea, niciunul nu a finalizat" if signup
                        else "Nimeni nu a apăsat pe înregistrare",
            "sample": len(visitors), "validation": validation_level(len(visitors)),
        })
    return sorted(problems, key=lambda p: -p["sample"])[:8]


async def analyze_abandon_pages(days: int) -> list:
    """Paginile de ieșire — ultimul pageview al fiecărei sesiuni."""
    last_by_session: dict = {}
    q = {"day": {"$gte": _day_ago(days)}, "type": "pageview"}
    async for ev in db.analytics_events.find(q, {"path": 1, "session_id": 1, "ts": 1}).sort("ts", 1):
        last_by_session[ev["session_id"]] = ev.get("path") or "/"
    exits = defaultdict(int)
    for path in last_by_session.values():
        exits[path] += 1
    total = len(last_by_session) or 1
    return [{"path": p, "exits": n, "exit_share_pct": round(n / total * 100, 1),
             "validation": validation_level(n, strong=n >= 5)}
            for p, n in sorted(exits.items(), key=lambda x: -x[1])[:8]]


async def analyze_journeys(days: int) -> list:
    """Traseele reale: secvențe de pagini per sesiune (max 4 pași)."""
    steps: dict = defaultdict(list)
    q = {"day": {"$gte": _day_ago(days)}, "type": "pageview"}
    async for ev in db.analytics_events.find(q, {"path": 1, "session_id": 1, "ts": 1}).sort("ts", 1):
        s = steps[ev["session_id"]]
        path = ev.get("path") or "/"
        if not s or s[-1] != path:
            s.append(path)
    journeys = defaultdict(int)
    for s in steps.values():
        journeys[" → ".join(s[:4])] += 1
    return [{"journey": j, "sessions": n} for j, n in sorted(journeys.items(), key=lambda x: -x[1])[:8]]


async def analyze_behavior(days: int = 60) -> dict:
    """Behavioral Intelligence: ore/zile optime, comparație surse, serviciu top (Board 004 Stream B)."""
    sessions = await _load_sessions(days)
    grid = defaultdict(lambda: {"sessions": 0, "conv": 0})
    wa_grid = defaultdict(lambda: {"sessions": 0, "conv": 0})
    src_visitors = defaultdict(set)
    src_accounts = defaultdict(set)
    for s in sessions:
        try:
            dt = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00")).astimezone(BUCHAREST)
        except Exception:  # noqa: BLE001
            continue
        key = (dt.weekday(), dt.hour)
        conv = 1 if s.get("funnel_account_created") else 0
        grid[key]["sessions"] += 1
        grid[key]["conv"] += conv
        src = s.get("source") or "direct"
        src_visitors[src].add(s["visitor_id"])
        if conv:
            src_accounts[src].add(s["visitor_id"])
        if src == "whatsapp":
            wa_grid[key]["sessions"] += 1
            wa_grid[key]["conv"] += conv

    n = len(sessions)

    def best_slot(g: dict, label: str) -> dict:
        if not g:
            return {"text": f"Date insuficiente pentru {label} — recomandare implicită: Marți sau Joi, 19:00-20:30",
                    "sample": 0, "validation": "ai_hypothesis"}
        (dow, hour), v = max(g.items(), key=lambda x: x[1]["conv"] * 5 + x[1]["sessions"])
        sample = sum(x["sessions"] for x in g.values())
        return {"day": dow, "day_label": DOW_RO[dow], "hour": hour,
                "text": f"{DOW_RO[dow]} în jurul orei {hour:02d}:00",
                "evidence": f"{v['sessions']} sesiuni și {v['conv']} conversii în acest interval (din {sample} analizate)",
                "sample": sample, "validation": validation_level(sample, strong=v["conv"] > 0)}

    # comparație surse (conversie cont per sursă)
    src_rows = []
    for src, vis in sorted(src_visitors.items(), key=lambda x: -len(x[1])):
        acc = len(src_accounts.get(src) or set())
        src_rows.append({"source": src, "visitors": len(vis), "accounts": acc,
                         "conv_pct": round(acc / len(vis) * 100, 1) if vis else 0.0})
    comparison = {"sources": src_rows, "text": "", "validation": "ai_hypothesis", "sample": n}
    ranked = [r for r in src_rows if r["visitors"] >= 5]
    if len(ranked) >= 2:
        ranked.sort(key=lambda r: -r["conv_pct"])
        a, b = ranked[0], ranked[1]
        if b["conv_pct"] > 0:
            diff = round((a["conv_pct"] - b["conv_pct"]) / b["conv_pct"] * 100)
            comparison["text"] = f"«{a['source']}» convertește cu {diff}% mai bine decât «{b['source']}» ({a['conv_pct']}% vs {b['conv_pct']}%)"
        else:
            comparison["text"] = f"«{a['source']}» e singura sursă cu conversii ({a['conv_pct']}%) — «{b['source']}» încă la zero"
        comparison["validation"] = validation_level(a["visitors"] + b["visitors"], strong=a["accounts"] > 0)
    elif src_rows:
        comparison["text"] = f"«{src_rows[0]['source']}» domină traficul ({src_rows[0]['visitors']} vizitatori) — prea puține date pe alte surse pentru comparație"
    else:
        comparison["text"] = "Fără trafic în fereastra analizată — distribuie primul link de campanie WhatsApp"

    # serviciul cu cea mai mare tracțiune (Revenue First — Board 004 Stream F)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    by_cat = defaultdict(int)
    async for r in db.requests.find({"created_at": {"$gte": cutoff}}, {"category": 1}):
        by_cat[(r.get("category") or "altele")] += 1
    top_service = {"text": "Nicio cerere în fereastra analizată", "validation": "ai_hypothesis", "sample": 0}
    if by_cat:
        cat, cnt = max(by_cat.items(), key=lambda x: x[1])
        total_req = sum(by_cat.values())
        top_service = {"category": cat, "requests": cnt, "total_requests": total_req,
                       "text": f"«{cat}» generează cele mai multe cereri ({cnt} din {total_req} în {days} zile)",
                       "sample": total_req, "validation": validation_level(total_req, strong=cnt >= 3)}

    # conversia oportunităților Revenue Hunter per serviciu comercial
    opp_stats = defaultdict(lambda: {"created": 0, "accepted": 0})
    async for o in db.revenue_opportunities.find({}, {"service": 1, "status": 1}):
        st = opp_stats[o.get("service") or "?"]
        st["created"] += 1
        if o.get("status") == "accepted":
            st["accepted"] += 1
    opportunities = [{"service": k, **v,
                      "conv_pct": round(v["accepted"] / v["created"] * 100, 1) if v["created"] else 0.0}
                     for k, v in sorted(opp_stats.items(), key=lambda x: -x[1]["accepted"])]

    return {
        "sample_sessions": n, "period_days": days,
        "best_post_time": best_slot(grid, "postări"),
        "best_whatsapp_time": best_slot(wa_grid, "mesaje WhatsApp"),
        "source_comparison": comparison,
        "top_service": top_service,
        "opportunity_conversion": opportunities,
    }


# ============================================================================
# RECOMANDĂRI + SCAN COMPLET
# ============================================================================
def _rec(title: str, why: str, category: str, validation: str, evidence: str, kpi: str) -> dict:
    return {"id": uuid.uuid4().hex[:12], "title": title, "why": why, "category": category,
            "validation": validation, "evidence": evidence, "kpi": kpi, "created_at": _now()}


async def run_growth_scan(trigger: str = "manual", days: int = 30) -> dict:
    """Ciclul Board 006: Observă → Învață → Recomandă. Persistă + emite eveniment."""
    sessions = await _load_sessions(days)
    ux_problems = await analyze_ux_problems(sessions, days)
    abandon = await analyze_abandon_pages(days)
    journeys = await analyze_journeys(days)
    behavior = await analyze_behavior(days=60)

    from value_loop import value_loop_summary
    vl = await value_loop_summary()

    recs = []
    if ux_problems:
        p = ux_problems[0]
        recs.append(_rec(f"Repară pagina «{p['path']}»", p["label"], "ux", p["validation"], p["evidence"], "bounce_rate_pct"))
    bwt = behavior["best_whatsapp_time"]
    recs.append(_rec(
        f"Trimite mesajele WhatsApp {bwt.get('text', 'Marți la 19:00')}",
        "Intervalul cu cea mai mare activitate/conversie a vizitatorilor din WhatsApp.",
        "marketing", bwt["validation"], bwt.get("evidence", "Date insuficiente — ipoteză de pornire"), "accounts_created"))
    sc = behavior["source_comparison"]
    if sc["text"]:
        recs.append(_rec("Realocă efortul de promovare pe sursa câștigătoare", sc["text"],
                         "marketing", sc["validation"], f"{len(sc['sources'])} surse comparate pe {sc['sample']} sesiuni", "conv_pct"))
    ts = behavior["top_service"]
    if ts.get("category"):
        recs.append(_rec(f"Promovează serviciul «{ts['category']}» în următoarea campanie", ts["text"],
                         "comercial", ts["validation"], ts["text"], "specialist_requests"))
    pending_opps = await db.revenue_opportunities.count_documents({"status": "active"})
    if pending_opps:
        pipe_val = 0.0
        async for o in db.revenue_opportunities.find({"status": "active"}, {"value": 1}):
            pipe_val += float(o.get("value") or 0)
        recs.append(_rec(f"Împinge cele {pending_opps} oportunități comerciale active (pipeline {pipe_val:,.0f} RON)",
                         "Revenue First: serviciile comerciale finanțează dezvoltarea platformei.",
                         "comercial", "confirmed_real",
                         f"{pending_opps} oportunități generate de Revenue Hunter, neacceptate încă", "revenue"))
    if vl["properties_total"]:
        cov = round(vl["properties_scored"] / vl["properties_total"] * 100)
        if cov < 50:
            recs.append(_rec("Crește acoperirea PVI prin audituri și documentare Twin",
                             f"Doar {cov}% din proprietăți au PVI calculat — restul nu văd încă valoarea documentării.",
                             "ceo", "confirmed_real",
                             f"{vl['properties_scored']}/{vl['properties_total']} proprietăți scorate, PVI mediu {vl['avg_pvi']}", "avg_pvi"))

    visitors = {s["visitor_id"] for s in sessions}
    bounces = sum(1 for s in sessions if (s.get("pageviews") or 0) <= 1)
    doc = {
        "generated_at": _now(), "trigger": trigger, "period_days": days,
        "kpi_snapshot": {
            "sessions": len(sessions), "visitors": len(visitors),
            "bounce_rate_pct": round(bounces / len(sessions) * 100, 1) if sessions else 0.0,
            "avg_pvi": vl["avg_pvi"], "active_opportunities": pending_opps,
        },
        "ux_problems": ux_problems, "abandon_pages": abandon, "journeys": journeys,
        "behavior": behavior, "recommendations": recs,
    }
    await db.growth_insights.update_one({"_id": "latest"}, {"$set": doc}, upsert=True)
    await db.growth_insights_history.insert_one({**doc})
    try:
        from event_bus import emit
        await emit("growth.scan_completed", payload={
            "trigger": trigger, "recommendations": len(recs), "sessions": len(sessions),
            "confirmed_real": sum(1 for r in recs if r["validation"] == "confirmed_real"),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[growth_intel] event emit failed: {e}")
    logger.info(f"[growth_intel] scan done ({trigger}): {len(sessions)} sesiuni, {len(recs)} recomandări")
    return {k: v for k, v in doc.items() if k != "_id"}
