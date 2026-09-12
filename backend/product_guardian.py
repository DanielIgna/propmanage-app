"""Product Guardian — PM-GUARDIAN-003: modul de produs al Guardian Kernel.

Motoare REALE (fără stub-uri):
  1. CTA Validator        — toate link-urile interne literale din frontend vs tabela de rute App.js
  2. Role Consistency     — fiecare rol din db.users are o rută home validă (roleHome = /{role})
  3. ServiceGate Validator— serviceId-urile folosite în cod există în configurația site_menu
  4. First Value Engine   — conversii reale din DB: client → proprietate → cerere → plată
  5. Conversion Engine    — funnel landing → register/login din analytics_events (30 zile)
  6. Product Health Score — scor unic + ceo_summary per rulare

Lifecycle identic cu Architecture Guardian: task-uri CTO (upsert pe key, auto-resolve,
recurrence). LEARNING: la a 3-a recurență a aceleiași probleme → escaladare CTO automată.
"""
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from db import db

logger = logging.getLogger("propmanage.product_guardian")

FRONTEND_SRC = Path("/app/frontend/src")

LINK_RES = (
    re.compile(r'\bto="(/[^"]*)"'),
    re.compile(r'\bhref="(/[^"]*)"'),
    re.compile(r'navigate\(\s*["\'](/[^"\']*)["\']'),
    re.compile(r'window\.location(?:\.href)?\s*=\s*["\'](/[^"\']*)["\']'),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _issue(key, severity, risk, title, detail, expected, impact, plan="") -> dict:
    return {"key": key, "severity": severity, "risk": risk, "title": title, "detail": detail,
            "expected": expected, "business_impact": impact, "migration_plan": plan}


def _route_table() -> tuple:
    """(exact_paths, dynamic_regexes) din App.js."""
    app = _read(FRONTEND_SRC / "App.js")
    exact, dynamic = set(), []
    for path in re.findall(r'path="([^"]+)"', app):
        if path == "*":
            continue
        if ":" in path or "*" in path:
            rx = re.sub(r":[^/]+", "[^/]+", path).replace("*", ".*")
            dynamic.append(re.compile(f"^{rx}/?$"))
        else:
            exact.add(path.rstrip("/") or "/")
    return exact, dynamic


def _link_ok(link: str, exact: set, dynamic: list) -> bool:
    path = link.split("?")[0].split("#")[0]
    if not path or path.startswith(("/api", "//")):
        return True
    path = path.rstrip("/") or "/"
    if path in exact:
        return True
    return any(rx.match(path) for rx in dynamic)


# ============================================================================
# 1. CTA VALIDATOR — link-uri interne moarte, pe toată platforma
# ============================================================================
def check_dead_links(issues):
    exact, dynamic = _route_table()
    dead: dict = {}
    for p in FRONTEND_SRC.rglob("*.jsx"):
        if "node_modules" in p.parts or "ui" in p.relative_to(FRONTEND_SRC).parts[:2]:
            continue
        text = "\n".join(ln for ln in _read(p).splitlines() if not ln.strip().startswith("//"))
        for rx in LINK_RES:
            for m in rx.finditer(text):
                link = m.group(1)
                if "${" in link or _link_ok(link, exact, dynamic):
                    continue
                dead.setdefault(link, set()).add(str(p.relative_to(FRONTEND_SRC)))
    for link, files in dead.items():
        issues.append(_issue(
            f"dead_link:{link}", "high", "low",
            f"CTA cu destinație inexistentă: {link}",
            f"Link intern '{link}' nu corespunde niciunei rute din App.js. Folosit în: {', '.join(sorted(files)[:4])}.",
            "Fiecare CTA duce la o rută existentă.",
            "Utilizatorul apasă și aterizează pe pagina principală (catch-all) — conversie pierdută, încredere erodată.",
            f"Corectează destinația în {sorted(files)[0]} sau adaugă ruta lipsă în App.js."))


# ============================================================================
# 2. ROLE CONSISTENCY — fiecare rol are o rută home validă
# ============================================================================
async def check_role_homes(issues):
    exact, dynamic = _route_table()
    auth = _read(FRONTEND_SRC / "pages" / "Auth.jsx")
    m = re.search(r"roleHome\s*=\s*\(role\)\s*=>\s*\(\{(.*?)\}\[role\]", auth, re.S)
    role_home = dict(re.findall(r"(\w+):\s*\"(/[^\"]+)\"", m.group(1))) if m else {}
    roles = await db.users.distinct("role")
    for role in roles:
        if not role:
            continue
        home = role_home.get(role, f"/{role}")
        if not _link_ok(home, exact, dynamic):
            n = await db.users.count_documents({"role": role})
            issues.append(_issue(
                f"role_no_home:{role}", "critical", "medium",
                f"Rol fără dashboard: {role}",
                f"{n} utilizatori au rolul '{role}' dar ruta home '{home}' nu există — după login sunt aruncați pe landing.",
                "Fiecare rol din users are o rută home funcțională (roleHome din Auth.jsx).",
                "Utilizatorii rolului nu-și pot accesa contul — blocaj total de produs.",
                f"Adaugă ruta '{home}' în App.js sau mapează rolul '{role}' în roleHome (Auth.jsx)."))


# ============================================================================
# 3. SERVICEGATE VALIDATOR — id-urile din cod există în configurație
# ============================================================================
async def check_service_gates(issues):
    used = set()
    for p in FRONTEND_SRC.rglob("*.jsx"):
        if "node_modules" in p.parts:
            continue
        used |= set(re.findall(r'serviceId="([\w-]+)"', _read(p)))
    if not used:
        return
    menu = await db.site_menu.find_one({"key": "main"}) or {}
    valid = set()
    for group in menu.get("items") or []:
        valid.add(group.get("id"))
        for c in group.get("children") or []:
            valid.add(c.get("id"))
    for sid in used - valid:
        issues.append(_issue(
            f"unknown_service_gate:{sid}", "high", "medium",
            f"ServiceGate cu id necunoscut: {sid}",
            f"Codul folosește <ServiceGate serviceId=\"{sid}\"> dar '{sid}' nu există în site_menu — gate-ul decide greșit (blochează sau expune pagina).",
            "Fiecare serviceId din cod există în configurația Service Manager.",
            "Feature leakage în Beta sau pagină blocată pe nedrept — ambele stricăexperiența.",
            f"Adaugă serviciul '{sid}' în Menu Manager sau corectează id-ul în cod."))


# ============================================================================
# 4. FIRST VALUE ENGINE — conversii reale din DB
# ============================================================================
async def first_value_metrics() -> dict:
    clients_total = await db.users.count_documents({"role": "client"})
    owners = {p.get("owner_id") for p in await db.properties.find({}, {"owner_id": 1}).to_list(2000)}
    requesters = {r.get("client_id") for r in await db.requests.find({}, {"client_id": 1}).to_list(2000)}
    payers = {t.get("client_id") or t.get("user_id")
              for t in await db.payment_transactions.find({"payment_status": "paid"}, {"client_id": 1, "user_id": 1}).to_list(2000)}
    owners.discard(None); requesters.discard(None); payers.discard(None)
    m = {
        "clients_total": clients_total,
        "clients_with_property": len(owners),
        "clients_with_request": len(requesters),
        "clients_paid": len(payers),
    }
    m["pct_property"] = round(100 * len(owners) / clients_total, 1) if clients_total else 0
    m["pct_request"] = round(100 * len(requesters) / clients_total, 1) if clients_total else 0
    m["pct_paid"] = round(100 * len(payers) / clients_total, 1) if clients_total else 0
    return m


async def check_first_value(issues, metrics):
    if metrics["clients_total"] >= 20 and metrics["pct_property"] < 15:
        issues.append(_issue(
            "ttfv_property_dropoff", "medium", "medium",
            f"Doar {metrics['pct_property']}% din clienți au adăugat o proprietate",
            f"{metrics['clients_with_property']}/{metrics['clients_total']} clienți au ≥1 proprietate — primul pas de valoare e ratat de majoritate.",
            "Minim 15% din clienți trec de primul pas (Time To First Property).",
            "Fără proprietate nu există twin, cereri sau plăți — funnel-ul moare la pasul 1.",
            "Optimizează onboarding-ul: CTA «Adaugă proprietatea» imediat după înregistrare + wizard ghidat."))


# ============================================================================
# 5. CONVERSION ENGINE — funnel din analytics_events (30 zile)
# ============================================================================
async def conversion_metrics() -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline = [
        {"$match": {"type": "pageview", "ts": {"$gte": since}}},
        {"$group": {"_id": "$session_id", "paths": {"$addToSet": "$path"}}},
    ]
    sessions = await db.analytics_events.aggregate(pipeline).to_list(5000)
    landing = [s for s in sessions if "/" in (s.get("paths") or [])]
    converted = [s for s in landing if any(p in ("/register", "/login") for p in s["paths"])]
    return {
        "sessions_30d": len(sessions),
        "landing_sessions": len(landing),
        "landing_to_auth": len(converted),
        "landing_to_auth_pct": round(100 * len(converted) / len(landing), 1) if landing else 0,
    }


async def check_conversion(issues, metrics):
    if metrics["landing_sessions"] >= 100 and metrics["landing_to_auth_pct"] < 1:
        issues.append(_issue(
            "landing_conversion_low", "medium", "medium",
            f"Conversia landing → register/login e {metrics['landing_to_auth_pct']}%",
            f"Din {metrics['landing_sessions']} sesiuni pe landing (30 zile), doar {metrics['landing_to_auth']} ajung la register/login.",
            "Minim 1% din sesiunile de landing intră în funnel-ul de auth.",
            "Trafic plătit/organic irosit — vizitatorii pleacă fără să intre în produs.",
            "Testează hero CTA (A/B există în ab.js), simplifică above-the-fold, mută social proof mai sus."))


# ============================================================================
# 6. PROCESS HEALTH — AIB-006 · Process Intelligence (procese de business blocate)
# ============================================================================
async def check_process_health(issues):
    async for p in db.ai_brain_processes.find({"kind": "business"}):
        st = p.get("stats") or {}
        total, stale = st.get("total", 0), st.get("stale_count", 0)
        if total >= 10 and stale >= max(5, total * 0.5):
            top = (st.get("abandon_points") or [{}])[0]
            issues.append(_issue(
                f"process_stalled_{p['id']}", "medium", "medium",
                f"Procesul «{p['name']}» are {stale}/{total} instanțe blocate >14 zile",
                f"Etapa cu cele mai multe abandonuri: «{top.get('state', '?')}» ({top.get('stuck', 0)} instanțe). "
                f"Actori implicați: {', '.join(p.get('actors') or [])}.",
                "Instanțele proceselor de business avansează în <14 zile sau ating o stare terminală.",
                "Utilizatorii abandonează fluxul — valoare pierdută și percepție de produs blocat.",
                "Analizează etapa problematică în AI Brain → Process Explorer și adaugă remindere/simplificare."))


# ============================================================================
# 7. ADAPTIVE FEEDBACK — AIB-008 (recomandări ineficiente, degradare, blocaje recurente)
# ============================================================================
async def check_adaptive_intelligence(issues):
    from ai_brain.adaptive import POSITIVE, NEGATIVE
    # recomandări ineficiente: kind cu volum și acceptare foarte mică
    kinds: dict = {}
    async for d in db.ai_brain_decision_feedback.aggregate([
            {"$match": {"kind": {"$ne": None}}},
            {"$group": {"_id": {"kind": "$kind", "action": "$action"}, "n": {"$sum": 1}}}]):
        k = d["_id"]["kind"]
        kinds.setdefault(k, {"pos": 0, "neg": 0})
        if d["_id"]["action"] in POSITIVE:
            kinds[k]["pos"] += d["n"]
        elif d["_id"]["action"] in NEGATIVE:
            kinds[k]["neg"] += d["n"]
    for k, v in kinds.items():
        n = v["pos"] + v["neg"]
        if n >= 10 and v["pos"] / n < 0.2:
            issues.append(_issue(
                f"ineffective_recommendations_{k}", "medium", "low",
                f"Recomandările «{k}» sunt ignorate în {round(100 * (1 - v['pos'] / n))}% din cazuri",
                f"{n} reacții reale: doar {v['pos']} urmate. Adaptive Engine le-a scăzut deja scorul.",
                "Recomandările AI Brain au o rată de urmare de minim 20%.",
                "Recomandări irelevante erodează încrederea în AI Mentor.",
                "Analizează kind-ul în AI Brain → Adaptive Intelligence și regândește generatorul."))
    # degradare procese: rata de stagnare a crescut față de snapshot-ul anterior
    pids = await db.ai_brain_process_stats_history.distinct("process_id")
    for pid in pids:
        hist = [h async for h in db.ai_brain_process_stats_history.find(
            {"process_id": pid}).sort("ts", -1).limit(2)]
        if len(hist) == 2 and hist[0]["total"] >= 10 and hist[1]["total"]:
            r_now = hist[0]["stale"] / hist[0]["total"]
            r_prev = hist[1]["stale"] / hist[1]["total"]
            if r_now - r_prev > 0.15:
                issues.append(_issue(
                    f"process_degradation_{pid}", "medium", "medium",
                    f"Procesul «{pid}» se degradează: stagnare {round(r_prev * 100)}% → {round(r_now * 100)}%",
                    f"Rata instanțelor blocate a crescut cu {round((r_now - r_prev) * 100)}pp între analize.",
                    "Rata de stagnare a proceselor de business nu crește între analize.",
                    "Degradarea tăcută a unui proces = utilizatori pierduți fără alarmă.",
                    "Vezi AI Brain → Process Explorer pentru etapa problematică și cauzele blocajelor."))


# ============================================================================
# 8. SLA INTELLIGENCE — AIB-009 (depășiri SLA raportate de Collaborative Intelligence)
# ============================================================================
async def check_sla_breaches(issues):
    async for s in db.ai_brain_sla_status.find({}, {"_id": 0}):
        over = s["counts"]["breached"] + s["counts"]["abandoned"]
        if s["active"] >= 5 and over / s["active"] > 0.3:
            top = (s.get("breaches") or [{}])[0]
            issues.append(_issue(
                f"sla_breach_{s['process_id']}", "medium", "medium",
                f"«{s['process_name']}»: {over}/{s['active']} instanțe active au depășit SLA-ul",
                f"Responsabili blocanți: {', '.join(top.get('responsible_now') or ['—'])}. "
                f"Escaladare propusă: {((top.get('escalations') or [{}])[0]).get('action', 'reminder')}.",
                "Instanțele active respectă SLA-ul empiric (2× durata medie a etapei).",
                "Depășirile SLA repetate duc la abandon și pierderea încrederii în platformă.",
                "Vezi AI Brain → Collaboration Explorer pentru escaladările propuse per instanță."))


# ============================================================================
# 9. AI BRAIN CERTIFICATION — AIB-010 (verdictul ultimei certificări)
# ============================================================================
async def check_ai_brain_certification(issues):
    cert = await db.ai_brain_certification.find_one({}, sort=[("generated_at", -1)])
    if not cert:
        issues.append(_issue(
            "ai_brain_not_certified", "medium", "low",
            "AI Brain nu a fost certificat încă (AIB-010)",
            "Nicio rulare de certificare găsită în db.ai_brain_certification.",
            "AI Brain are un certificat de release valid înainte de pilot.",
            "Fără certificare, problemele de stabilitate/explicabilitate rămân nedetectate.",
            "Rulează certificarea din AI Brain → Production Readiness."))
        return
    if cert.get("verdict") == "Not Ready":
        issues.append(_issue(
            "ai_brain_cert_not_ready", "high", "high",
            "Certificarea AI Brain a eșuat: verdict «Not Ready»",
            f"Probleme critice: {'; '.join((cert.get('critical_issues') or [])[:3])}",
            "AI Brain trece certificarea cu verdict minim «Ready for Pilot».",
            "Lansarea pilotului cu un AI Brain necertificat riscă experiențe eronate.",
            "Rezolvă problemele critice din certificat și re-rulează certificarea."))
    for k, v in (cert.get("scores") or {}).items():
        if v < 70:
            issues.append(_issue(
                f"ai_brain_score_low_{k}", "medium", "medium",
                f"Scor AI Brain scăzut: {k} = {v}/100",
                "Sub pragul de 70 acceptat pentru pilot.",
                f"{k} ≥ 70 la certificare.",
                "Scorurile scăzute indică riscuri de fiabilitate în producție.",
                "Vezi detaliile în AI Brain → Production Readiness."))


# ============================================================================
# RUN — kernel lifecycle (identic cu Architecture Guardian) + learning 3-strikes
# ============================================================================
async def run_product_guardian(trigger: str = "cron") -> dict:
    issues: list = []
    try:
        check_dead_links(issues)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[product-guardian] dead_links failed: {e}")
    fv, conv = {}, {}
    for acheck in (check_role_homes, check_service_gates, check_process_health,
                   check_adaptive_intelligence, check_sla_breaches,
                   check_ai_brain_certification):
        try:
            await acheck(issues)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[product-guardian] {acheck.__name__} failed: {e}")
    try:
        fv = await first_value_metrics()
        await check_first_value(issues, fv)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[product-guardian] first_value failed: {e}")
    try:
        conv = await conversion_metrics()
        await check_conversion(issues, conv)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[product-guardian] conversion failed: {e}")

    ignores = {d["key"] async for d in db.product_guardian_ignores.find({}, {"key": 1})}
    issues = [i for i in issues if i["key"] not in ignores]

    now = _now()
    seen_keys, new_tasks, strikes = set(), 0, []
    for iss in issues:
        seen_keys.add(iss["key"])
        existing = await db.product_guardian_tasks.find_one({"key": iss["key"], "status": "open"})
        if existing:
            await db.product_guardian_tasks.update_one(
                {"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "detail": iss["detail"]}})
            continue
        prev = await db.product_guardian_tasks.find_one(
            {"key": iss["key"], "status": "resolved"}, sort=[("resolved_at", -1)])
        recurrence = (prev.get("recurrence", 0) + 1) if prev else 0
        if recurrence:
            iss["severity"] = "critical" if iss["severity"] in ("high", "critical") else "high"
        if recurrence >= 3:
            strikes.append(iss["title"])
        await db.product_guardian_tasks.insert_one({
            "id": uuid.uuid4().hex, **iss, "status": "open", "assigned_to": "cto_ai",
            "recurrence": recurrence, "created_at": now, "last_seen_at": now, "trigger": trigger,
        })
        new_tasks += 1

    res = await db.product_guardian_tasks.update_many(
        {"status": "open", "key": {"$nin": list(seen_keys) or ["__none__"]}},
        {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": "product_guardian"}})
    auto_resolved = res.modified_count

    by_sev = {s: sum(1 for i in issues if i["severity"] == s) for s in ("critical", "high", "medium", "low")}
    score = max(5, 100 - 15 * by_sev["critical"] - 8 * by_sev["high"] - 3 * by_sev["medium"] - 1 * by_sev["low"])
    arch = await db.architecture_guardian_runs.find_one({}, {"architecture_score": 1}, sort=[("ts", -1)])
    platform_score = round((score + (arch or {}).get("architecture_score", score)) / 2)
    ceo_summary = (
        f"Produs {score}/100 · Platformă {platform_score}/100 · {len(issues)} probleme "
        f"({by_sev['critical']} critice) · funnel: {fv.get('pct_property', '?')}% clienți cu proprietate, "
        f"{fv.get('pct_paid', '?')}% au plătit · landing→auth {conv.get('landing_to_auth_pct', '?')}%"
    )
    run = {
        "id": uuid.uuid4().hex, "ts": now, "trigger": trigger,
        "issues_found": len(issues), "new_tasks": new_tasks, "auto_resolved": auto_resolved,
        "by_severity": by_sev, "product_score": score, "platform_score": platform_score,
        "first_value": fv, "conversion": conv, "ceo_summary": ceo_summary,
    }
    await db.product_guardian_runs.insert_one({**run})

    from orchestrator.engine import write_ledger, notify_admins
    from orchestrator.governance import record_decision
    await write_ledger({
        "signal_kind": "product_guardian", "playbook_id": "product_guardian",
        "playbook_name": "Product Guardian",
        "steps": [{"action": "audit_product", "ok": by_sev["critical"] == 0, "detail": ceo_summary
                   + f" · {new_tasks} task-uri noi, {auto_resolved} auto-rezolvate"}],
        "outcome": "auto_resolved" if by_sev["critical"] == 0 else "escalated",
        "minutes_saved": 10 + 3 * auto_resolved, "escalated": by_sev["critical"] > 0, "test": False,
    })
    await record_decision({
        "signal_kind": "product_guardian", "playbook_id": "product_guardian",
        "playbook_name": "Product Guardian", "authority_level": 4,
        "execution_mode": "execute", "confidence": 0.9, "decided": "executed",
        "outcome": "auto_resolved" if by_sev["critical"] == 0 else "escalated",
        "escalated": by_sev["critical"] > 0,
        "context": {"issues": len(issues), "score": score}, "test": False,
    })
    if strikes:
        await notify_admins("🚨 Product Guardian: probleme recurente (3+ apariții)",
                            "Escaladare CTO automată: " + "; ".join(strikes[:3]),
                            link="/admin/repair-center")
    if by_sev["critical"] > 0 and new_tasks:
        crit = [i["title"] for i in issues if i["severity"] == "critical"][:3]
        await notify_admins("🚨 Product Guardian: probleme critice de produs", "; ".join(crit),
                            link="/admin/repair-center")
    logger.info(f"[product-guardian] {ceo_summary}")
    run.pop("_id", None)
    return run
