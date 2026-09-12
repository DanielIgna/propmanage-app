"""ASM-001 · Copilotul Casei — AI Success Manager unificat.

COMPUNE motoarele existente (ZERO logică duplicată):
success_manager (decizie) · user_context (semnale) · subscription_health · storage_service
(ST-001) · ledger/opportunities/membership (PropBenefits) · trust_engine (Community) ·
Cartea Casei (_completeness) · ai_core (LLM cu fallback determinist).

Nou aici: Scorul Casei (0-100, explicabil) · Onboarding checklist · Explainability per
acțiune · AI Success Timeline (copilot_timeline) · Rezumat AI (cache copilot_reports).
"""
import hashlib
import logging
from datetime import datetime, timezone, timedelta

from db import db
from propbenefits import eligibility, ledger, opportunities
from propbenefits.ai_agents import success_manager
from propbenefits.health import subscription_health
from propbenefits.trust_engine import ambassador_status, deals_demand

logger = logging.getLogger("propmanage.copilot")


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _now()).isoformat()


# ---------------------------------------------------------------------------
# Explainability — De ce? · Ce câștigi? · Ce deblochezi? · Cât durează? · Impact casă
# ---------------------------------------------------------------------------
EXPLAIN = {
    "use_benefit": {"why": "Ai un beneficiu câștigat prin comunitate care așteaptă să fie folosit — nefolosit, expiră.",
                    "gain": "Valoarea beneficiului intră direct în casa ta.",
                    "unlocks": "Progres către următorul nivel de membru.",
                    "duration": "1 minut", "house_impact": "Beneficiile folosite cresc Scorul Casei."},
    "docs_for_benefit": {"why": "Cartea Casei este memoria permanentă a locuinței — documentele lipsă lasă goluri în istoric.",
                         "gain": "Istoric tehnic complet + acces la beneficii care cer documentație.",
                         "unlocks": "Beneficii condiționate de documentație (ex: consultanță Design Interior).",
                         "duration": "2 minute per document", "house_impact": "Până la +9 puncte la Scorul Casei."},
    "activate_twin": {"why": "Fără geamăn digital, casa ta nu poate fi vizualizată și documentată în 3D.",
                      "gain": "Acces la Campaniile Premium și Beneficiile Exclusive.",
                      "unlocks": "Digital Twin + nivel superior de membru.",
                      "duration": "10 minute", "house_impact": "Până la +20 puncte la Scorul Casei."},
    "house_health": {"why": "Fără scor de sănătate nu știi ce merită îngrijit primul în casa ta.",
                     "gain": "Diagnostic clar + verificări din campaniile active.",
                     "unlocks": "Scor House Health + puncte de progres + 5 GB stocare.",
                     "duration": "5 minute", "house_impact": "Până la +15 puncte la Scorul Casei."},
    "claim_opportunity": {"why": "Comunitatea a pregătit o oportunitate relevantă exact pentru casa ta.",
                          "gain": "Beneficiu direct în portofel, fără costuri ascunse.",
                          "unlocks": "Beneficiul campaniei + progres de membru.",
                          "duration": "1 minut", "house_impact": "Beneficiile active cresc Scorul Casei."},
    "renew_subscription": {"why": "Abonamentul expiră curând — beneficiile active și scorul House Health se opresc odată cu el.",
                           "gain": "Continuitate: beneficii, scor, stocare 5 GB.",
                           "unlocks": "Toate avantajele abonamentului rămân active.",
                           "duration": "2 minute", "house_impact": "Menține punctele House Health din Scorul Casei."},
    "invite_neighbor": {"why": "Un vecin activ înseamnă negocieri comunitare mai puternice pentru toți.",
                        "gain": "Beneficiu Comunitate pentru amândoi la activare.",
                        "unlocks": "Beneficiu referral + progres de membru.",
                        "duration": "1 minut", "house_impact": "Comunitatea activă crește valoarea deal-urilor pentru casa ta."},
    "storage_upgrade": {"why": "Spațiul de stocare al casei este aproape plin — documentele noi nu vor mai încăpea.",
                        "gain": "De 20 de ori mai mult spațiu (5 GB) prin House Health.",
                        "unlocks": "Stocare 5 GB + scor House Health + beneficii de abonat.",
                        "duration": "2 minute", "house_impact": "Cartea Casei poate crește fără limite."},
    "storage_cleanup": {"why": "Spațiul de stocare se apropie de limită.",
                        "gain": "Loc pentru documentele care contează.",
                        "unlocks": "Upload-uri noi fără blocaje.",
                        "duration": "5 minute", "house_impact": "Cartea Casei rămâne funcțională."},
    "recommend_specialist": {"why": "Specialistul care a lucrat la casa ta merită vizibilitate — iar comunitatea are nevoie de recomandări reale.",
                             "gain": "Beneficiu Comunitate când recomandarea produce o lucrare confirmată.",
                             "unlocks": "Progres către Community Ambassador.",
                             "duration": "1 minut", "house_impact": "Trust-ul comunității crește valoarea rețelei tale de specialiști."},
    "almost_ambassador": {"why": "Mai ai o singură recomandare validată până la statutul de Community Ambassador.",
                          "gain": "Badge + beneficiu de ambasador + prioritate la campanii exclusive.",
                          "unlocks": "Community Ambassador (primii 10 devin Founding Ambassador).",
                          "duration": "1 minut", "house_impact": "+4 puncte la Scorul Casei (comunitate)."},
    "support_deal": {"why": "Negocierea comunității are nevoie de susținători ca să obțină condiții mai bune pentru toți.",
                     "gain": "Acces prioritar la condițiile negociate.",
                     "unlocks": "Deal-ul avansează spre finalizare.",
                     "duration": "10 secunde", "house_impact": "Materialele și serviciile casei tale, la condiții de comunitate."},
}
GENERIC_EXPLAIN = {"why": "Este acțiunea cu cel mai mare impact pentru casa ta acum.",
                   "gain": "Progres real, măsurabil.", "unlocks": "Următorul pas din planul casei.",
                   "duration": "câteva minute", "house_impact": "Crește Scorul Casei."}


def _with_explain(action: dict | None) -> dict | None:
    if not action:
        return None
    return {**action, "explain": {**GENERIC_EXPLAIN, **EXPLAIN.get(action.get("id"), {})}}


# ---------------------------------------------------------------------------
# Cartea Casei — REUSE _completeness (scorul real existent)
# ---------------------------------------------------------------------------
async def _book_completeness(uid: str) -> dict:
    prop = await db.properties.find_one({"owner_id": uid})
    if not prop:
        return {"score": 0, "max": 100, "next_step": None, "docs_count": 0, "has_property": False}
    try:
        from routes.property_documents import _completeness
        c = await _completeness(str(prop["_id"]), prop)
        return {**c, "has_property": True}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[copilot] completeness failed: {e}")
        return {"score": 0, "max": 100, "next_step": None, "docs_count": 0, "has_property": True}


async def _twin_progress(uid: str) -> dict:
    p = await db.digital_twin_projects.find_one({"owner_id": uid}, {"model_count": 1, "plan_count": 1, "name": 1})
    if not p:
        return {"pct": 0, "has_project": False, "hint": "Creează geamănul digital al casei"}
    pct = 40
    if (p.get("model_count") or 0) > 0:
        pct += 40
    if (p.get("plan_count") or 0) > 0:
        pct += 20
    hint = None
    if (p.get("model_count") or 0) == 0:
        hint = "Încarcă primul model 3D"
    elif (p.get("plan_count") or 0) == 0:
        hint = "Adaugă planurile 2D (PDF)"
    return {"pct": pct, "has_project": True, "hint": hint}


# ---------------------------------------------------------------------------
# Scorul Casei — 0-100, compus DIN semnalele existente, complet explicabil
# ---------------------------------------------------------------------------
async def house_score(ctx: dict, book: dict, twin: dict, amb: dict) -> dict:
    uid = ctx["uid"]
    items = []

    def add(key, label, points, mx, hint=None):
        items.append({"key": key, "label": label, "points": round(points, 1), "max": mx,
                      "hint": hint if points < mx else None})

    add("cartea_casei", "Cartea Casei", book["score"] * 0.30, 30,
        (book.get("next_step") or {}).get("label") or "Adaugă proprietatea și primele documente")
    add("digital_twin", "Digital Twin", twin["pct"] * 0.20, 20, twin.get("hint"))
    hh_pts = (10 if ctx["hh_score"] else 0) + (5 if ctx["subscription_active"] else 0)
    add("house_health", "House Health", hh_pts, 15,
        "Activează House Health pentru scorul de sănătate" if hh_pts < 15 else None)
    maint = await db.maintenance_logs.count_documents({"user_id": uid}) \
        or await db.maintenance_logs.count_documents({"owner_id": uid})
    m_pts = (5 if maint else 0) + (5 if ctx["completed_jobs"] else 0)
    add("mentenanta", "Mentenanță & lucrări", m_pts, 10,
        "Prima lucrare prin platformă pornește istoricul" if m_pts < 10 else None)
    b_pts = (5 if ctx["campaigns_joined"] else 0) + (5 if ctx["benefits_used"] else 0)
    add("beneficii", "Beneficii", b_pts, 10,
        "Activează și folosește primul beneficiu" if b_pts < 10 else None)
    recs = await db.recommendations.count_documents({"owner_id": uid})
    signals = await db.pb_deal_signals.count_documents({"user_id": uid})
    c_pts = (4 if recs else 0) + (4 if amb.get("is_ambassador") else 0) + (2 if signals else 0)
    add("comunitate", "Comunitate", c_pts, 10,
        "Recomandă un specialist sau susține un deal" if c_pts < 10 else None)
    since30 = _iso(_now() - timedelta(days=30))
    nav30 = await db.ai_brain_navigation.count_documents({"user_id": uid, "ts": {"$gte": since30}})
    p_pts = (2.5 if ctx["ai_sessions"] else 0) + (2.5 if nav30 else 0)
    add("progres", "Activitate", p_pts, 5, None)

    score = int(round(sum(i["points"] for i in items)))
    missing = sorted([i for i in items if i["points"] < i["max"]], key=lambda i: i["max"] - i["points"], reverse=True)
    return {"score": min(100, score), "max": 100, "items": items,
            "top_gap": ({"label": missing[0]["label"], "hint": missing[0]["hint"],
                         "potential": round(missing[0]["max"] - missing[0]["points"], 1)} if missing else None)}


# ---------------------------------------------------------------------------
# Onboarding Coach — checklist din semnale reale
# ---------------------------------------------------------------------------
async def _checklist(ctx: dict) -> dict:
    uid = ctx["uid"]
    claimed = await db.pb_ledger.count_documents({"user_id": uid})
    signaled = await db.pb_deal_signals.count_documents({"user_id": uid})
    steps = [
        {"id": "create_book", "label": "Creează Cartea Casei", "done": ctx["properties"] > 0, "cta": "property"},
        {"id": "first_document", "label": "Încarcă primul document", "done": ctx["documents"] > 0, "cta": "property"},
        {"id": "first_benefit", "label": "Activează primul beneficiu", "done": claimed > 0, "cta": "benefits"},
        {"id": "discover_deals", "label": "Descoperă Community Deals", "done": signaled > 0, "cta": "benefits"},
        {"id": "first_request", "label": "Solicită prima ofertă", "done": ctx["completed_jobs"] > 0 or bool(
            await db.requests.find_one({"client_id": uid}, {"_id": 1})), "cta": "request"},
    ]
    done = sum(1 for s in steps if s["done"])
    return {"steps": steps, "done": done, "total": len(steps), "complete": done == len(steps)}


# ---------------------------------------------------------------------------
# Rezumat AI — ai_core (REUSE) cu fallback determinist, cache pe context
# ---------------------------------------------------------------------------
def _fallback_summary(d: dict) -> str:
    parts = [f"Casa ta este documentată în proporție de {d['book_score']}%, cu un Scor al Casei de {d['score']}/100."]
    if d["benefits_available"]:
        parts.append(f"Ai {d['benefits_available']} {'beneficiu activ' if d['benefits_available'] == 1 else 'beneficii active'}.")
    if d["deals_negotiating"]:
        parts.append(f"Comunitatea negociază acum {d['deals_negotiating']} oferte pentru membri.")
    if d["next_title"]:
        parts.append(f"Pasul cu cel mai mare impact: {d['next_title']}")
    return " ".join(parts)


async def _ai_summary(uid: str, d: dict) -> dict:
    sig = f"{d['score']}|{d['book_score']}|{d['benefits_available']}|{d['deals_negotiating']}|{d['next_id']}|{d['storage_pct']}"
    # MD5 utilizat exclusiv ca CACHE KEY (invalidare rezumat AI la schimbare context) — NU pentru securitate.
    # Non-security digest: coliziunile nu au impact (cel mult regenerare LLM). nosec B303.
    h = hashlib.md5(sig.encode(), usedforsecurity=False).hexdigest()
    cached = await db.copilot_reports.find_one({"user_id": uid}, {"_id": 0})
    if cached and cached.get("hash") == h and cached.get("generated_at", "") > _iso(_now() - timedelta(hours=6)):
        return {"text": cached["text"], "source": "ai_cached"}
    try:
        from ai_core.provider import call_llm
        r = await call_llm(
            "Ești Copilotul Casei pentru PropManage (România). Vorbești DOAR în română, cald, simplu, "
            "FĂRĂ termeni tehnici, despre CASA utilizatorului (nu despre platformă). Maxim 4 propoziții scurte. "
            "Structură: unde se află casa acum → ce valoare are deja → ce poate câștiga → care e pasul următor. "
            "Nu inventa cifre — folosește DOAR datele primite.",
            f"Datele reale ale casei: Scorul Casei {d['score']}/100 · Cartea Casei {d['book_score']}% "
            f"({d['documents']} documente) · Digital Twin {d['twin_pct']}% · beneficii active {d['benefits_available']} "
            f"(dintre care expiră curând: {d['benefits_expiring']}) · negocieri comunitare active {d['deals_negotiating']} "
            f"({d['deals_titles']}) · stocare folosită {d['storage_pct']}% · nivel membru {d['membership']} · "
            f"pasul recomandat: {d['next_title'] or 'explorează beneficiile'}. Scrie rezumatul.")
        text = (r.get("text") or "").strip()
        if text:
            await db.copilot_reports.update_one({"user_id": uid},
                                                {"$set": {"hash": h, "text": text, "generated_at": _iso()}}, upsert=True)
            return {"text": text, "source": "ai"}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[copilot] LLM summary failed: {e}")
    return {"text": _fallback_summary(d), "source": "deterministic"}


# ---------------------------------------------------------------------------
# AI Success Timeline — istoric recomandări + efecte reale
# ---------------------------------------------------------------------------
async def _timeline_tick(uid: str, current_ids: set, top: dict | None, signals: dict) -> None:
    async for e in db.copilot_timeline.find({"user_id": uid, "status": "recommended"}):
        if e["action_id"] in current_ids:
            continue
        old = e.get("signals") or {}
        parts = []
        dd = signals.get("documents", 0) - old.get("documents", 0)
        ds = signals.get("house_score", 0) - old.get("house_score", 0)
        db_ = signals.get("benefits_available", 0) - old.get("benefits_available", 0)
        if dd > 0:
            parts.append(f"+{dd} documente")
        if ds > 0:
            parts.append(f"Scorul Casei +{ds}")
        if db_ > 0:
            parts.append(f"+{db_} beneficii")
        await db.copilot_timeline.update_one({"_id": e["_id"]}, {"$set": {
            "status": "done", "done_at": _iso(),
            "effect": " · ".join(parts) if parts else "Acțiune finalizată ✓",
        }})
    if top and not await db.copilot_timeline.find_one(
            {"user_id": uid, "action_id": top["id"], "status": "recommended"}, {"_id": 1}):
        await db.copilot_timeline.insert_one({
            "user_id": uid, "action_id": top["id"], "title": top["title"],
            "status": "recommended", "recommended_at": _iso(), "signals": signals,
        })


async def timeline(uid: str, limit: int = 20) -> dict:
    items = []
    async for e in db.copilot_timeline.find({"user_id": uid}, {"_id": 0, "signals": 0}) \
            .sort("recommended_at", -1).limit(limit):
        items.append(e)
    return {"items": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Dashboard-ul Copilotului — o singură compunere a tuturor motoarelor
# ---------------------------------------------------------------------------
async def copilot_dashboard(user: dict) -> dict:
    uid = user.get("id") or str(user.get("_id", ""))
    ctx = await eligibility.user_context(user)
    sm = await success_manager(user)
    sub = await subscription_health(user, ctx)
    wallet = await ledger.wallet_summary(uid)
    feed = await opportunities.feed(user, limit=3)
    amb = await ambassador_status(uid)
    book = await _book_completeness(uid)
    twin = await _twin_progress(uid)
    score = await house_score(ctx, book, twin, amb)
    checklist = await _checklist(ctx)

    # Beneficii: active · expiră curând (14z) · aproape deblocate
    soon = _iso(_now() + timedelta(days=14))
    expiring = [b for b in wallet["available"] if b.get("expires_at") and b["expires_at"] <= soon]
    benefits = {
        "available": wallet["counts"].get("available", 0),
        "available_value": wallet.get("total_value_available", 0),
        "expiring_soon": [{"title": b["title"], "expires_at": b.get("expires_at")} for b in expiring[:2]],
        "almost_unlocked": [{"title": o.get("title"), "unlock_hint": o.get("unlock_hint") or (o.get("why") or [""])[0]}
                            for o in (feed.get("locked") or [])[:2]],
        "used": wallet["counts"].get("used", 0),
    }

    # Comunitate: ambasador + founding + deal-uri care au nevoie de susținători + implicarea userului
    demand = await deals_demand()
    negotiating = [d for d in demand if d["status"] in ("negociere", "in_lucru", "pilot")]
    needing = []
    for d in negotiating:
        needed = max(0, (d.get("target_supporters") or 25) - d["counts"]["sustin"])
        if needed > 0:
            needing.append({"id": d["id"], "emoji": d.get("emoji"), "title": d["title"],
                            "needed": needed, "status": d["status"]})
    my_signals = await db.pb_deal_signals.count_documents({"user_id": uid})
    community = {
        "ambassador": amb,
        "deals_negotiating": len(negotiating),
        "deals_needing_support": needing[:3],
        "my_supported_deals": my_signals,
    }

    # Storage Health (ST-001, REUSE)
    storage = None
    try:
        from storage_service import usage_snapshot
        snap = await usage_snapshot(user)
        storage = {"personal": snap["personal"], "digital_twin": snap.get("digital_twin"),
                   "upgrade_available": snap.get("upgrade_available")}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[copilot] storage snapshot failed: {e}")

    # Subscription Coach — upgrade DOAR cu valoare reală (anti-spam)
    upgrade_reasons = []
    if not ctx["subscription_active"]:
        st_pct = (storage or {}).get("personal", {}).get("pct", 0)
        if st_pct >= 80:
            upgrade_reasons.append(f"Ai folosit {st_pct}% din spațiu — House Health îți oferă 5 GB.")
        if ctx["documents"] >= 10:
            upgrade_reasons.append(f"Ai {ctx['documents']} documente — casa ta merită scorul de sănătate și spațiul extins.")
        if benefits["available"] >= 2:
            upgrade_reasons.append("Beneficiile tale active acoperă deja valoarea abonamentului.")
    subscription = {
        "active": ctx["subscription_active"],
        "expires_at": ctx.get("subscription_expires_at"),
        "score": sub["score"], "status": sub["status"],
        "factors": sub["factors"],
        "upgrade_suggestion": upgrade_reasons[0] if upgrade_reasons else None,
    }

    # Explainability pe acțiunile Success Manager (motorul rămâne neschimbat)
    next_action = _with_explain(sm.get("next_action"))
    secondary = [_with_explain(a) for a in sm.get("secondary") or []]
    community_action = _with_explain(sm.get("community_action"))

    # SH-001: Journey + Readiness + lanț de efecte pe recomandarea principală (compunere)
    journey = None
    try:
        from propbenefits.house_journey import journey_summary, chain_for_action
        journey = await journey_summary(user, ctx=ctx, book=book, twin=twin)
        if next_action:
            next_action["explain"]["chain"] = chain_for_action(next_action["id"], journey)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[copilot] journey section failed: {e}")

    # SH-001: „Ce fac pentru un scor mai bun?" — top 3 îmbunătățiri din gap-urile factorilor
    _factor_hints = {
        "activity": "Folosește platforma săptămânal — cere o ofertă sau verifică starea casei",
        "documents": "Încarcă documente în Cartea Casei",
        "house_health": "Generează scorul House Health",
        "digital_twin": "Pornește Digital Twin-ul casei",
        "campaigns": "Participă la o campanie activă",
        "benefits_used": "Folosește un beneficiu din portofel",
        "referrals": "Recomandă un vecin sau un specialist",
        "ai_usage": "Întreabă Copilotul despre casa ta",
    }
    sub_improvements = sorted(sub["factors"], key=lambda f: f["weight"] - f["points"], reverse=True)[:3]
    sub_improvements = [{"label": f["label"], "gain": round(f["weight"] - f["points"], 1),
                         "hint": _factor_hints.get(f["key"])} for f in sub_improvements if f["weight"] - f["points"] > 0]
    subscription["improvements"] = sub_improvements

    # Timeline: închide recomandările rezolvate + loghează recomandarea curentă
    current_ids = {a["id"] for a in [next_action, community_action, *secondary] if a}
    # Coordonare anti-duplicat cu Renewal Reminder Email: dacă servim nudge-ul
    # de renewal, scriem ledger-ul comun (fereastră 24h).
    if "renew_subscription" in current_ids:
        try:
            from routes.renewal_reminders import record_copilot_renew_nudge
            await record_copilot_renew_nudge(uid)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[copilot] renew nudge ledger failed: {e}")
    signals = {"documents": ctx["documents"], "benefits_available": benefits["available"],
               "house_score": score["score"]}
    try:
        await _timeline_tick(uid, current_ids, next_action, signals)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[copilot] timeline tick failed: {e}")
    tl = await timeline(uid, limit=6)

    summary = await _ai_summary(uid, {
        "score": score["score"], "book_score": book["score"], "documents": ctx["documents"],
        "twin_pct": twin["pct"], "benefits_available": benefits["available"],
        "benefits_expiring": len(expiring), "deals_negotiating": len(negotiating),
        "deals_titles": ", ".join(d["title"] for d in negotiating[:2]) or "—",
        "storage_pct": (storage or {}).get("personal", {}).get("pct", 0),
        "membership": feed["membership"]["level"].get("name") if isinstance(feed["membership"].get("level"), dict) else feed["membership"].get("level"),
        "next_title": (next_action or {}).get("title"), "next_id": (next_action or {}).get("id"),
    })

    return {
        "house_score": score,
        "summary": summary,
        "next_action": next_action,
        "secondary": secondary,
        "community_action": community_action,
        "checklist": checklist,
        "progress": {
            "book": {"pct": book["score"], "docs_count": book.get("docs_count", 0),
                     "next_step": book.get("next_step")},
            "twin": twin,
            "membership": feed["membership"],
        },
        "benefits": benefits,
        "community": community,
        "storage": storage,
        "subscription": subscription,
        "journey": journey,
        "timeline": tl,
        "generated_at": _iso(),
    }
