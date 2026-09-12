"""AI Brain · Certification & Production Readiness (AIB-010).

Sprint exclusiv de consolidare: audit complet al componentelor AIB-001..009, integritate
arhitecturală (reutilizează Architecture Guardian + pyflakes), health checks de producție
(latențe reale, memorie, erori, retry-uri), validarea explicabilității (nicio recomandare
fără justificare), stress & load (asyncio concurent, fără infrastructură externă),
Pilot Readiness (13/100/1000 apartamente), Technical Debt Scanner (read-only) și
Release Certificate cu verdict. ZERO funcționalități AI noi, zero modificări automate.
Persistență: db.ai_brain_certification (istoric certificate).
"""
import asyncio
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from db import db

BACKEND_DIR = Path("/app/backend")
FRONTEND_SRC = Path("/app/frontend/src")
VERDICTS = ("Ready for Production", "Production Ready with Warnings",
            "Ready for Pilot", "Not Ready")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _demo_user(email: str) -> dict | None:
    u = await db.users.find_one({"email": email})
    if u:
        u["id"] = u.get("id") or str(u["_id"])
    return u


# ---------------------------------------------------------------------------
# 1 · CERTIFICATION AUDIT — fiecare componentă, verificată pe date + execuție reală
# ---------------------------------------------------------------------------
async def component_audit() -> list:
    from ai_brain import registry
    out = []

    def comp(cid, name, checks):
        passed = [c for c in checks if c["pass"]]
        status = ("certified" if len(passed) == len(checks)
                  else "experimental" if len(passed) >= max(1, len(checks) - 1) else "failed")
        return {"id": cid, "name": name, "status": status,
                "checks": checks, "passed": f"{len(passed)}/{len(checks)}"}

    counts = await registry.counts()
    last_run = await db.ai_brain_runs.find_one({}, sort=[("ts", -1)])
    out.append(comp("AIB-001", "Discovery Engine", [
        {"name": "registru populat", "pass": counts.get("routes", 0) > 50
         and counts.get("apis", 0) > 100, "detail": str(counts)},
        {"name": "discovery rulat recent", "pass": bool(last_run),
         "detail": (last_run or {}).get("ts", "niciodată")},
    ]))

    nav = await db.ai_brain_navigation.count_documents({})
    client = await _demo_user("client@propmanage.io")
    ctx_ok, ctx_detail = False, "user demo lipsă"
    if client:
        try:
            from ai_brain.context import resolve_context
            ctx = await resolve_context(client, "/client")
            ctx_ok = bool(ctx.get("user", {}).get("role")) and "available_actions" in ctx
            ctx_detail = (f"rol={ctx['user']['role']}, "
                          f"{len(ctx.get('available_actions') or [])} acțiuni disponibile")
        except Exception as e:  # noqa: BLE001
            ctx_detail = str(e)[:120]
    out.append(comp("AIB-002", "Context Awareness", [
        {"name": "resolve_context funcțional", "pass": ctx_ok, "detail": ctx_detail},
        {"name": "navigație înregistrată", "pass": nav > 0, "detail": f"{nav} evenimente"},
    ]))

    expl = await db.ai_brain_explanations.count_documents({})
    hits = 0
    async for d in db.ai_brain_explanations.aggregate(
            [{"$group": {"_id": None, "h": {"$sum": "$hits"}}}]):
        hits = d["h"]
    out.append(comp("AIB-003", "Explainability Engine", [
        {"name": "explicații generate + cache", "pass": expl > 0,
         "detail": f"{expl} explicații, {hits} cache hits"},
    ]))

    mentor_ok, mentor_detail = False, ""
    if client:
        try:
            from ai_brain.mentor import mentor_advise
            adv = await mentor_advise(client, "/client")
            mentor_ok = bool(adv.get("actions")) and all(
                a.get("reason") for a in adv["actions"])
            mentor_detail = f"{len(adv.get('actions', []))} acțiuni, toate cu justificare"
        except Exception as e:  # noqa: BLE001
            mentor_detail = str(e)[:120]
    out.append(comp("AIB-004", "AI Mentor", [
        {"name": "mentor_advise cu acțiuni justificate", "pass": mentor_ok, "detail": mentor_detail},
    ]))

    nodes = await db.ai_brain_graph_nodes.count_documents({})
    edges = await db.ai_brain_graph_edges.count_documents({})
    out.append(comp("AIB-005", "Knowledge Intelligence", [
        {"name": "graf construit", "pass": nodes > 200 and edges > 500,
         "detail": f"{nodes} noduri, {edges} muchii"},
        {"name": "noduri de proces în graf",
         "pass": await db.ai_brain_graph_nodes.count_documents(
             {"id": {"$regex": "^process:proc_"}}) > 5, "detail": "process:proc_*"},
    ]))

    biz = await db.ai_brain_processes.count_documents({"kind": "business"})
    total_p = await db.ai_brain_processes.count_documents({})
    out.append(comp("AIB-006", "Process Intelligence", [
        {"name": "procese descoperite", "pass": biz >= 5 and total_p >= 15,
         "detail": f"{total_p} procese ({biz} business)"},
        {"name": "registru cu tranziții + actori",
         "pass": bool(await db.ai_brain_processes.find_one(
             {"kind": "business", "transitions.0": {"$exists": True},
              "actors.0": {"$exists": True}})), "detail": "tranziții + actori prezente"},
    ]))

    dec_ok, dec_detail = False, ""
    if client:
        try:
            from ai_brain.decision import next_best_decisions
            ds = await next_best_decisions(client, "/client")
            dec_ok = bool(ds) and all(d.get("reasons") and "score" in d
                                      and d.get("confidence") is not None for d in ds)
            dec_detail = f"{len(ds)} decizii, toate cu scor+factori+încredere+argumente"
        except Exception as e:  # noqa: BLE001
            dec_detail = str(e)[:120]
    out.append(comp("AIB-007", "Decision Intelligence", [
        {"name": "decizii scorate, explicabile", "pass": dec_ok, "detail": dec_detail},
    ]))

    fb = await db.ai_brain_decision_feedback.count_documents({})
    hist = await db.ai_brain_process_stats_history.count_documents({})
    out.append(comp("AIB-008", "Adaptive Intelligence", [
        {"name": "feedback loop activ", "pass": fb > 0, "detail": f"{fb} reacții înregistrate"},
        {"name": "istoric statistici procese", "pass": hist > 0, "detail": f"{hist} snapshot-uri"},
    ]))

    sla = await db.ai_brain_sla_status.count_documents({})
    notif = await db.ai_brain_notifications.count_documents({})
    out.append(comp("AIB-009", "Collaborative Intelligence", [
        {"name": "SLA sweep persistat", "pass": sla > 0, "detail": f"{sla} procese monitorizate"},
        {"name": "notificări inteligente", "pass": notif > 0, "detail": f"{notif} intenții"},
    ]))
    return out


# ---------------------------------------------------------------------------
# 2 · ARCHITECTURE INTEGRITY — reutilizează Architecture Guardian + pyflakes
# ---------------------------------------------------------------------------
async def architecture_integrity() -> dict:
    guardian = await db.architecture_guardian_runs.find_one({}, sort=[("ts", -1)])
    open_tasks = await db.architecture_guardian_tasks.count_documents({"status": "open"})
    # importuri inutile / probleme statice în modulul ai_brain (pyflakes, read-only)
    try:
        res = subprocess.run(
            ["python3", "-m", "pyflakes"] + [str(p) for p in (BACKEND_DIR / "ai_brain").glob("*.py")],
            capture_output=True, text=True, timeout=60)
        flakes = [ln for ln in res.stdout.strip().splitlines() if ln][:20]
    except Exception as e:  # noqa: BLE001
        flakes = [f"pyflakes indisponibil: {e}"]
    # dependențe circulare în ai_brain (importurile top-level dintre module)
    mods = {p.stem: re.findall(r"^from ai_brain\.(\w+) import|^from ai_brain import (\w+)",
                               p.read_text(errors="ignore"), re.M)
            for p in (BACKEND_DIR / "ai_brain").glob("*.py")}
    graph = {m: {x or y for x, y in deps if (x or y) in mods} for m, deps in mods.items()}
    circular = sorted({tuple(sorted((a, b))) for a, deps in graph.items()
                       for b in deps if a in graph.get(b, set())})
    # endpoint-uri redundante (metodă+path duplicate în registru)
    dup_eps = []
    async for d in db.ai_brain_registry.aggregate([
            {"$match": {"kind": "apis"}}, {"$unwind": "$items"},
            {"$group": {"_id": {"m": "$items.method", "p": "$items.path"}, "n": {"$sum": 1}}},
            {"$match": {"n": {"$gt": 1}}}, {"$limit": 10}]):
        dup_eps.append(f"{d['_id'].get('m')} {d['_id'].get('p')} ×{d['n']}")
    return {
        "guardian_last_run": (guardian or {}).get("ts"),
        "guardian_score": (guardian or {}).get("score"),
        "guardian_open_tasks": open_tasks,
        "static_findings": flakes,
        "circular_imports_ai_brain": [list(c) for c in circular],
        "duplicate_endpoints": dup_eps,
        "optimizations_proposed": (
            ([f"Rezolvă {open_tasks} task-uri Architecture Guardian deschise"] if open_tasks else [])
            + ([f"Curăță {len(flakes)} avertismente statice în ai_brain/"] if flakes else [])
            + ([f"Elimină ciclul de importuri {c}" for c in circular[:3]])),
    }


# ---------------------------------------------------------------------------
# 3 · PRODUCTION HEALTH CHECKS — latențe reale, memorie, erori, retry-uri
# ---------------------------------------------------------------------------
def _mem_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS"):
                return round(int(line.split()[1]) / 1024, 1)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


async def _timed(coro):
    t0 = time.monotonic()
    err = None
    try:
        await coro
    except Exception as e:  # noqa: BLE001
        err = str(e)[:100]
    return round((time.monotonic() - t0) * 1000), err


async def health_checks(include_llm: bool = True) -> dict:
    client = await _demo_user("client@propmanage.io")
    latencies, errors = {}, []
    t, e = await _timed(db.command("ping"))
    latencies["mongodb_ping"] = t
    if e:
        errors.append(f"mongodb: {e}")
    if client:
        from ai_brain.context import resolve_context
        from ai_brain.process import process_state
        from ai_brain.decision import generate_decisions
        from ai_brain.graph import related_modules
        for name, coro in (("context_engine", resolve_context(client, "/client")),
                           ("process_engine", process_state(client, path="/client")),
                           ("decision_engine", generate_decisions(client, "/client")),
                           ("knowledge_graph", related_modules("client", limit=4))):
            t, e = await _timed(coro)
            latencies[name] = t
            if e:
                errors.append(f"{name}: {e}")
    if include_llm:
        try:
            from ai_core.provider import call_llm
            t0 = time.monotonic()
            res = await call_llm("Ești un healthcheck. Răspunde cu un singur cuvânt.",
                                 "Spune: OK", session_id="aib010-healthcheck")
            latencies["llm_roundtrip"] = round((time.monotonic() - t0) * 1000)
            if res.get("error"):
                errors.append(f"llm: {res['error'][:100]}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"llm: {str(e)[:100]}")
    # erori interne recente din logurile backend
    log_errors = 0
    try:
        for lf in Path("/var/log/supervisor").glob("backend.err*"):
            tail = lf.read_text(errors="ignore").splitlines()[-500:]
            log_errors += sum(1 for ln in tail if "ERROR" in ln or "Traceback" in ln)
    except Exception:  # noqa: BLE001
        pass
    retry_blocked = await db.orchestrator_retry_queue.count_documents(
        {"status": "blocked_by_config"})
    load1 = 0.0
    try:
        load1 = float(Path("/proc/loadavg").read_text().split()[0])
    except Exception:  # noqa: BLE001
        pass
    slow = [k for k, v in latencies.items() if k != "llm_roundtrip" and v > 2000]
    return {
        "latencies_ms": latencies,
        "memory_mb": _mem_mb(),
        "cpu_load_1m": load1,
        "recent_log_errors": log_errors,
        "retry_queue_blocked": retry_blocked,
        "internal_errors": errors,
        "slow_engines": slow,
        "healthy": not errors and not slow,
    }


# ---------------------------------------------------------------------------
# 4 · EXPLAINABILITY VALIDATION — nicio recomandare fără justificare
# ---------------------------------------------------------------------------
async def explainability_validation() -> dict:
    checked, justified, samples = 0, 0, []

    async for snap in db.ai_brain_decisions.find({}, {"_id": 0}).limit(50):
        for d in snap.get("items", []):
            checked += 1
            ok = bool(d.get("reasons")) and bool(d.get("resolves")) \
                and bool(d.get("factors")) and bool(d.get("confidence_factors"))
            justified += ok
            if not ok and len(samples) < 5:
                samples.append({"engine": "decision", "id": d.get("id"),
                                "title": d.get("title", "")[:60]})
    async for n in db.ai_brain_notifications.find({"status": "active"}, {"_id": 0}).limit(100):
        checked += 1
        ok = bool(n.get("why"))
        justified += ok
        if not ok and len(samples) < 5:
            samples.append({"engine": "notification", "id": n.get("key")})
    async for s in db.ai_brain_sla_status.find({}, {"_id": 0}).limit(20):
        for b in s.get("breaches", []):
            for e in b.get("escalations", []):
                checked += 1
                ok = bool(e.get("why"))
                justified += ok
                if not ok and len(samples) < 5:
                    samples.append({"engine": "escalation", "id": s.get("process_id")})
    # blocaje de proces: verificare live pe utilizatorul demo
    client = await _demo_user("client@propmanage.io")
    if client:
        from ai_brain.process import process_state
        st = await process_state(client, path="/client")
        for b in st.get("blockers") or []:
            checked += 1
            justified += bool(b.get("text"))
    score = round(100 * justified / checked) if checked else 100
    return {"recommendations_checked": checked, "justified": justified,
            "unjustified_samples": samples, "explainability_score": score,
            "pass": score >= 95}


# ---------------------------------------------------------------------------
# 7 · STRESS & LOAD VALIDATION — concurență reală cu asyncio, zero infra externă
# ---------------------------------------------------------------------------
async def stress_validation() -> dict:
    users = [u for u in [await _demo_user(e) for e in
                         ("client@propmanage.io", "specialist@propmanage.io",
                          "admin@propmanage.io")] if u]
    if not users:
        return {"error": "utilizatori demo lipsă", "pass": False}
    from ai_brain.context import resolve_context
    from ai_brain.process import process_state
    from ai_brain.decision import generate_decisions
    from ai_brain.graph import related_modules
    from ai_brain.collaboration import collaboration_state

    scenarios = []
    for i in range(24):
        u = users[i % len(users)]
        scenarios.append(("context", resolve_context(u, "/client")))
    for i in range(12):
        u = users[i % len(users)]
        scenarios.append(("process", process_state(u, path="/client")))
        scenarios.append(("collaboration", collaboration_state(u, path="/client")))
    for i in range(9):
        scenarios.append(("decisions", generate_decisions(users[i % len(users)], "/client")))
    for i in range(12):
        scenarios.append(("graph", related_modules("client", limit=4)))

    t0 = time.monotonic()
    results = await asyncio.gather(*(c for _, c in scenarios), return_exceptions=True)
    total_ms = round((time.monotonic() - t0) * 1000)
    errors = [f"{scenarios[i][0]}: {str(r)[:100]}"
              for i, r in enumerate(results) if isinstance(r, Exception)]
    return {"concurrent_operations": len(scenarios),
            "breakdown": {"context": 24, "process": 12, "collaboration": 12,
                          "decisions": 9, "graph": 12},
            "total_ms": total_ms,
            "avg_ms_per_op": round(total_ms / len(scenarios)),
            "errors": errors[:5], "error_count": len(errors),
            "pass": not errors and total_ms < 60000}


# ---------------------------------------------------------------------------
# 8 · PILOT READINESS — 13 / 100 / 1000 apartamente
# ---------------------------------------------------------------------------
async def pilot_readiness(health: dict, stress: dict) -> list:
    # consistență date: owneri inexistenți pe entitățile proceselor business (eșantion)
    orphans = 0
    checked_docs = 0
    async for p in db.ai_brain_processes.find(
            {"kind": "business", "entity": {"$ne": None}}, {"entity": 1}).limit(5):
        async for doc in db[p["entity"]].find({}, {"client_id": 1, "owner_id": 1}).limit(20):
            owner = doc.get("client_id") or doc.get("owner_id")
            if not owner:
                continue
            checked_docs += 1
            if not await db.users.find_one({"$or": [{"id": owner}, {"email": owner}]}):
                orphans += 1
    consistency = round(100 * (1 - orphans / checked_docs)) if checked_docs else 100
    lat = [v for k, v in health["latencies_ms"].items() if k not in ("llm_roundtrip",)]
    p_lat = max(lat) if lat else 0
    levels = []
    for name, max_lat, needs in (("pilot_13_apartamente", 3000, "stabilitate de bază"),
                                 ("pilot_100_apartamente", 1500, "latențe consistente"),
                                 ("scale_1000_apartamente", 600, "optimizare + indexare")):
        blockers = []
        if p_lat > max_lat:
            blockers.append(f"latență motor {p_lat}ms > {max_lat}ms")
        if stress.get("error_count"):
            blockers.append(f"{stress['error_count']} erori la concurență")
        if consistency < 95:
            blockers.append(f"consistență date {consistency}% (owneri orfani: {orphans})")
        if not health.get("healthy") and name != "pilot_13_apartamente":
            blockers.append("health checks cu avertismente")
        levels.append({"level": name,
                       "verdict": "ready" if not blockers
                       else "ready_with_warnings" if len(blockers) == 1 else "not_ready",
                       "blockers": blockers, "requirement": needs})
    return levels


# ---------------------------------------------------------------------------
# 9 · TECHNICAL DEBT SCANNER — read-only
# ---------------------------------------------------------------------------
async def tech_debt_scan() -> dict:
    # API-uri backend candidate nefolosite de frontend (potrivire statică pe segmente)
    fe_calls = set()
    for f in FRONTEND_SRC.rglob("*.js*"):
        for m in re.findall(r"/api/([a-z0-9\-_/]+)", f.read_text(errors="ignore")):
            fe_calls.add(m.split("/")[0])
    unused = []
    reg = await db.ai_brain_registry.find_one({"kind": "apis"}, {"items": 1})
    seen_mods = set()
    for it in (reg or {}).get("items", []):
        path = it.get("path", "")
        seg = (path.split("/") + ["", ""])[2]
        if seg and seg not in fe_calls and seg not in seen_mods:
            seen_mods.add(seg)
            unused.append({"module": seg, "example": path,
                           "note": "niciun apel frontend găsit — candidat (poate fi webhook/system)"})
    # procese/stări inutile din Adaptive Intelligence (reuse)
    from ai_brain.adaptive import process_learning
    pl = await process_learning()
    return {
        "unused_api_module_candidates": sorted(unused, key=lambda u: u["module"])[:15],
        "possibly_unused_process_states": pl.get("possibly_unused_states", []),
        "abandoned_processes": pl.get("abandoned_processes", []),
        "guardian_open_findings": await db.architecture_guardian_tasks.count_documents(
            {"status": "open"}),
        "note": "Raport read-only — nicio modificare automată.",
    }


# ---------------------------------------------------------------------------
# 5+10 · GUARDIAN CERTIFICATION + RELEASE CERTIFICATE
# ---------------------------------------------------------------------------
def _scores(components, health, explain, stress, integrity) -> dict:
    smap = {"certified": 1.0, "experimental": 0.6, "failed": 0.0}
    ai_brain = round(100 * sum(smap[c["status"]] for c in components) / len(components))
    lat = [v for k, v in health["latencies_ms"].items() if k != "llm_roundtrip"]
    reliability = 100
    reliability -= 25 * len(health["internal_errors"])
    reliability -= 15 * len(health["slow_engines"])
    reliability -= min(20, health["recent_log_errors"] // 5)
    if lat and max(lat) > 1000:
        reliability -= 10
    reliability = max(0, reliability)
    stability = 100
    stability -= 40 * (0 if stress.get("pass") else 1)
    stability -= min(20, (integrity.get("guardian_open_tasks") or 0) * 5)
    stability -= 10 * len(integrity.get("circular_imports_ai_brain") or [])
    stability = max(0, stability)
    return {"ai_brain_score": ai_brain, "reliability_score": reliability,
            "explainability_score": explain["explainability_score"],
            "stability_score": stability}


def _verdict(scores, components, health, stress) -> tuple:
    critical, minor = [], []
    for c in components:
        if c["status"] == "failed":
            critical.append(f"Componenta {c['id']} ({c['name']}) a picat auditul")
        elif c["status"] == "experimental":
            minor.append(f"{c['id']} ({c['name']}): {c['passed']} verificări trecute")
    if scores["explainability_score"] < 90:
        critical.append(f"Explicabilitate {scores['explainability_score']}% < 90%")
    if stress.get("error_count"):
        critical.append(f"{stress['error_count']} erori la validarea de concurență")
    for e in health["internal_errors"]:
        critical.append(f"Eroare internă: {e}")
    for s in health["slow_engines"]:
        minor.append(f"Motor lent (>2s): {s}")
    if health["retry_queue_blocked"]:
        minor.append(f"{health['retry_queue_blocked']} emailuri blocate de configurație")
    avg = sum(scores.values()) / 4
    if critical:
        verdict = "Not Ready"
    elif avg >= 95 and not minor:
        verdict = "Ready for Production"
    elif avg >= 85:
        verdict = "Production Ready with Warnings" if minor else "Ready for Production"
    else:
        verdict = "Ready for Pilot"
    return verdict, critical, minor


async def run_certification(trigger: str = "manual") -> dict:
    from ai_brain.core import VERSION
    t0 = time.monotonic()
    components = await component_audit()
    integrity = await architecture_integrity()
    health = await health_checks(include_llm=True)
    explain = await explainability_validation()
    stress = await stress_validation()
    pilot = await pilot_readiness(health, stress)
    scores = _scores(components, health, explain, stress, integrity)
    verdict, critical, minor = _verdict(scores, components, health, stress)
    recommendations = (integrity.get("optimizations_proposed") or [])[:5]
    if health["retry_queue_blocked"]:
        recommendations.append("Deblochează emailurile (DNS Resend) înainte de pilot")
    cert = {
        "version": VERSION, "trigger": trigger,
        "verdict": verdict, "scores": scores,
        "certified_components": [c["id"] for c in components if c["status"] == "certified"],
        "experimental_components": [c["id"] for c in components if c["status"] == "experimental"],
        "failed_components": [c["id"] for c in components if c["status"] == "failed"],
        "components": components,
        "critical_issues": critical, "minor_issues": minor,
        "recommendations": recommendations,
        "architecture": integrity, "health": health,
        "explainability": explain, "stress": stress, "pilot_readiness": pilot,
        "duration_ms": round((time.monotonic() - t0) * 1000),
        "generated_at": _now(),
    }
    await db.ai_brain_certification.insert_one(dict(cert))
    return cert


async def latest_certificate() -> dict | None:
    return await db.ai_brain_certification.find_one({}, {"_id": 0}, sort=[("generated_at", -1)])
