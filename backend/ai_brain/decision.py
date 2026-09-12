"""AI Brain · Decision Intelligence Engine (AIB-007).

Consilier decizional: analizează acțiunile posibile ale utilizatorului și le transformă
în DECIZII scorate, argumentate și simulabile — FĂRĂ auto-execuție.
Reutilizează integral: Context Engine (AIB-002), Explainability/LLM (AIB-003),
AI Mentor (AIB-004), Knowledge Graph (AIB-005), Process Intelligence (AIB-006).
Candidați: tranziții de proces executabile de rol, deblocări de blockers, acțiuni mentor,
priorități platformă (admin). Scoruri = factori calculați din starea REALĂ a aplicației.
Simulator: impact estimat (module/procese/utilizatori/stări) derivat din graf + registry,
zero modificări în DB. Snapshot decizii per utilizator în db.ai_brain_decisions.
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from db import db
from ai_brain.context import _effective_guards
from ai_brain.process import (ADMIN_ROLES, OWNER_FIELDS, _find_entity, get_process,
                              list_processes, process_state)

FRONTEND_SRC = Path("/app/frontend/src")

# Structura scorului (ponderile sunt arhitectură; FACTORII se calculează din date reale)
WEIGHTS = {"urgency": 0.25, "impact": 0.20, "unblocking": 0.15,
           "readiness": 0.15, "progress": 0.10, "risk_of_inaction": 0.15}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _did(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode(), usedforsecurity=False).hexdigest()[:12]


def _role_homes() -> dict:
    try:
        auth = (FRONTEND_SRC / "pages" / "Auth.jsx").read_text(errors="ignore")
        m = re.search(r"roleHome\s*=\s*\(role\)\s*=>\s*\(\{(.*?)\}\[role\]", auth, re.S)
        return dict(re.findall(r"(\w+):\s*\"(/[^\"]+)\"", m.group(1))) if m else {}
    except Exception:  # noqa: BLE001
        return {}


# ---------------------------------------------------------------------------
# FACTORI — calculați exclusiv din starea reală (proces, blockers, graf, stats)
# ---------------------------------------------------------------------------
async def _graph_reach(node_id: str) -> int:
    n = await db.ai_brain_graph_edges.count_documents(
        {"$or": [{"source": node_id}, {"target": node_id}]})
    return n


async def _downstream_processes(pid: str) -> list:
    """Procese care depind de acesta (references către el sau flows_to din el)."""
    out = set()
    async for p in db.ai_brain_processes.find(
            {"relations": {"$elemMatch": {"to": pid, "rel": "references"}}}, {"id": 1, "name": 1}):
        out.add(p["name"])
    async for e in db.ai_brain_graph_edges.find(
            {"source": f"process:{pid}", "rel": "flows_to"}, {"target": 1}):
        out.add(e["target"].split(":", 1)[1].replace("proc_", "").replace("_", " "))
    return sorted(out)[:4]


def _factors(st: dict, proc: dict, transition: dict | None, can_execute: bool) -> tuple:
    """(factors 0..1, reasons) — derivate din starea procesului și statisticile reale."""
    factors = {k: 0.0 for k in WEIGHTS}
    reasons = []
    blockers = st.get("blockers") or []
    stats = (proc or {}).get("stats") or {}

    stalled = next((b for b in blockers if b["kind"] == "stalled"), None)
    expired = next((b for b in blockers if b["kind"] == "expired"), None)
    if expired:
        factors["urgency"] = 1.0
        reasons.append(expired["text"])
    elif stalled:
        factors["urgency"] = min(stalled.get("days", 0) / 30, 1.0)
        reasons.append(stalled["text"])
    elif blockers:
        factors["urgency"] = 0.5
        reasons.append(blockers[0]["text"])

    factors["readiness"] = 1.0 if can_execute else (0.3 if blockers else 0.6)
    if can_execute:
        reasons.append("Poți executa acest pas chiar acum — ai permisiunea și datele necesare.")

    total_steps = st.get("total_steps") or 0
    idx = st.get("step_index", -1)
    if total_steps and idx >= 0:
        factors["progress"] = (idx + 1) / total_steps
        if factors["progress"] >= 0.5:
            reasons.append(f"Ești la pasul {idx + 1}/{total_steps} — aproape de finalizare.")

    total = stats.get("total", 0)
    if total:
        factors["risk_of_inaction"] = min(stats.get("stale_count", 0) / total, 1.0)
        if factors["risk_of_inaction"] > 0.4:
            reasons.append(f"{stats['stale_count']}/{total} instanțe ale acestui proces "
                           "stagnează >14 zile — amânarea e cauza principală de abandon.")

    if transition and transition["to"] in (proc or {}).get("terminal_states", []):
        reasons.append(f"Pasul «{transition['to']}» finalizează procesul.")
        factors["progress"] = max(factors["progress"], 0.9)
    return factors, reasons


def _score(factors: dict) -> int:
    return round(100 * sum(WEIGHTS[k] * v for k, v in factors.items()))


# ---------------------------------------------------------------------------
# 1 · DECISION ENGINE — candidați din starea reală
# ---------------------------------------------------------------------------
async def _decision_from_transition(user, proc, st, t, guards, homes) -> dict:
    can = t["actor"] in guards
    factors, reasons = _factors(st, proc, t, can)
    # impact din graf: conexiunile reale ale procesului
    reach = await _graph_reach(f"process:{proc['id']}")
    factors["impact"] = min(reach / 20, 1.0)
    downstream = await _downstream_processes(proc["id"])
    factors["unblocking"] = min(len(downstream) / 3, 1.0)
    if downstream:
        reasons.append(f"Avansarea alimentează procesele: {', '.join(downstream)}.")
    after = [x["to"] for x in proc["transitions"] if x["from"] == t["to"]][:3]
    return {
        "id": _did(proc["id"], t["to"], "transition"),
        "kind": "process_transition",
        "title": f"Avansează «{proc['name']}» în etapa «{t['to']}»",
        "process_id": proc["id"], "process_name": proc["name"],
        "entity": st.get("entity"),
        "transition": {"from": t["from"] or st.get("current_state"), "to": t["to"],
                       "actor": t["actor"], "endpoint": t["endpoint"]},
        "cta_path": homes.get(user.get("role"), f"/{user.get('role')}"),
        "actors": [t["actor"]],
        "dependencies": [b["text"] for b in (st.get("blockers") or [])[:2]],
        "resolves": (st.get("blockers") or [{}])[0].get("text")
                    or f"Procesul stă în etapa «{st.get('current_state')}».",
        "avoids_risk": f"Evită stagnarea — {(proc.get('stats') or {}).get('stale_count', 0)} "
                       "instanțe similare sunt deja abandonate." if (proc.get("stats") or {}).get("stale_count") else
                       "Evită pierderea contextului și a momentului potrivit.",
        "produces_impact": f"{reach} conexiuni în Knowledge Graph"
                           + (f"; deblochează: {', '.join(downstream)}" if downstream else ""),
        "after": after or [x for x in (st.get("remaining_steps") or []) if x != t["to"]][:2],
        "factors": factors, "reasons": reasons, "score": _score(factors),
        "can_execute": can,
    }


async def _decision_start_process(user, proc, st, guards, homes) -> dict | None:
    starters = [t for t in st.get("next_actions") or []
                if t["actor"] in guards and t["endpoint"]["method"] != "GET"]
    if not starters:
        return None
    t = starters[0]
    factors, reasons = _factors(st, proc, t, True)
    downstream = await _downstream_processes(proc["id"])
    factors["unblocking"] = min(len(downstream) / 3, 1.0) or 0.3
    factors["impact"] = min(await _graph_reach(f"process:{proc['id']}") / 20, 1.0)
    if not st.get("blockers"):
        reasons.append(f"Poți porni «{proc['name']}» — nu există nicio dependență lipsă.")
    return {
        "id": _did(proc["id"], "start"),
        "kind": "process_start",
        "title": f"Pornește procesul «{proc['name']}»",
        "process_id": proc["id"], "process_name": proc["name"], "entity": None,
        "transition": {"from": None, "to": t["to"], "actor": t["actor"], "endpoint": t["endpoint"]},
        "cta_path": homes.get(user.get("role"), f"/{user.get('role')}"),
        "actors": [t["actor"]],
        "dependencies": [b["text"] for b in (st.get("blockers") or [])[:2]],
        "resolves": "Procesul nu a fost pornit încă — prima etapă e la un pas distanță.",
        "avoids_risk": "Evită să rămâi în urmă față de fluxul recomandat al platformei.",
        "produces_impact": f"Deschide etapele: {', '.join((st.get('remaining_steps') or [])[:4])}",
        "after": (st.get("remaining_steps") or [])[:3],
        "factors": factors, "reasons": reasons, "score": _score(factors),
        "can_execute": True,
    }


def _decision_from_mentor(a: dict, i: int) -> dict:
    factors = {"urgency": 0.6 if a.get("priority") == 1 else 0.4, "impact": 0.5,
               "unblocking": 0.5 if a.get("priority") == 1 else 0.3,
               "readiness": 1.0, "progress": 0.0, "risk_of_inaction": 0.4}
    return {
        "id": _did("mentor", a["id"]),
        "source_action_id": a["id"],
        "kind": "mentor_action",
        "title": a["title"], "process_id": None, "process_name": None, "entity": None,
        "transition": None, "cta_path": a["cta_path"], "actors": [],
        "dependencies": [], "resolves": a["reason"],
        "avoids_risk": "Evită un cont incomplet — fundația celorlalte procese.",
        "produces_impact": "Deblochează recomandările și procesele următoare.",
        "after": [], "factors": factors, "reasons": [a["reason"]],
        "score": _score(factors), "can_execute": True,
    }


async def _admin_decisions(user) -> list:
    out = []
    # aprobări restante: stări cu instanțe reale care așteaptă o tranziție de admin
    async for p in db.ai_brain_processes.find({"kind": {"$in": ["business", "internal"]}}, {"_id": 0}):
        stats = p.get("stats") or {}
        for t in p.get("transitions", []):
            if t["actor"] not in ADMIN_ROLES or not t["from"] or t["endpoint"]["method"] == "GET":
                continue
            waiting = (stats.get("by_status") or {}).get(t["from"], 0)
            if waiting < 1:
                continue
            factors = {"urgency": min(waiting / 10, 1.0), "impact": 0.5,
                       "unblocking": min(waiting / 5, 1.0), "readiness": 1.0,
                       "progress": 0.5,
                       "risk_of_inaction": min(stats.get("stale_count", 0) / max(stats.get("total", 1), 1), 1.0)}
            out.append({
                "id": _did(p["id"], t["from"], "approval"),
                "kind": "pending_approval",
                "title": f"{waiting} instanțe «{p['name']}» așteaptă decizia ta în starea «{t['from']}»",
                "process_id": p["id"], "process_name": p["name"], "entity": None,
                "transition": t, "cta_path": "/admin", "actors": [t["actor"]],
                "dependencies": [],
                "resolves": f"{waiting} utilizatori sunt blocați în «{t['from']}» până decizi.",
                "avoids_risk": "Evită abandonul utilizatorilor blocați în aprobare.",
                "produces_impact": f"Deblochează {waiting} instanțe → «{t['to']}».",
                "after": [t["to"]], "factors": factors, "reasons":
                    [f"{waiting} instanțe reale așteaptă în «{t['from']}» tranziția spre «{t['to']}»."],
                "score": _score(factors), "can_execute": True,
            })
    # guardian kernel: task-uri deschise = decizii de remediere
    for coll, name in (("architecture_guardian_tasks", "Arhitectură"),
                       ("product_guardian_tasks", "Produs")):
        n = await db[coll].count_documents({"status": "open"})
        if n:
            factors = {"urgency": min(n / 5, 1.0), "impact": 0.7, "unblocking": 0.5,
                       "readiness": 1.0, "progress": 0.0, "risk_of_inaction": 0.7}
            out.append({
                "id": _did("guardian", coll), "kind": "guardian_task",
                "title": f"Rezolvă {n} task-uri Guardian ({name})",
                "process_id": None, "process_name": f"Guardian {name}", "entity": None,
                "transition": None, "cta_path": "/admin/repair-center", "actors": ["admin"],
                "dependencies": [], "resolves": f"{n} probleme deschise găsite de Guardian Kernel.",
                "avoids_risk": "Evită degradarea scorului de platformă și regresii.",
                "produces_impact": "Crește scorul de arhitectură/produs monitorizat de guardieni.",
                "after": [], "factors": factors, "reasons":
                    [f"Guardian {name} raportează {n} task-uri deschise."],
                "score": _score(factors), "can_execute": True,
            })
    # AIB-009: escaladări din ultimul SLA sweep (Collaborative Intelligence)
    async for s in db.ai_brain_sla_status.find(
            {"$expr": {"$gt": [{"$add": ["$counts.breached", "$counts.abandoned"]}, 0]}},
            {"_id": 0}).limit(10):
        over = s["counts"]["breached"] + s["counts"]["abandoned"]
        top = (s.get("breaches") or [{}])[0]
        factors = {"urgency": min(over / 10, 1.0), "impact": 0.6,
                   "unblocking": min(over / 5, 1.0), "readiness": 1.0, "progress": 0.5,
                   "risk_of_inaction": min(s["counts"]["abandoned"] / max(s["active"], 1) + 0.3, 1.0)}
        esc0 = (top.get("escalations") or [{}])[0]
        out.append({
            "id": _did(s["process_id"], "sla_escalation"), "kind": "escalation",
            "title": f"Deblochează {over} instanțe peste SLA în «{s['process_name']}»",
            "process_id": s["process_id"], "process_name": s["process_name"], "entity": None,
            "transition": None, "cta_path": "/admin", "actors": s.get("actors") or [],
            "dependencies": [],
            "resolves": f"{over} instanțe au depășit SLA-ul empiric; responsabili: "
                        f"{', '.join((top.get('responsible_now') or ['—']))}.",
            "avoids_risk": "Evită abandonul utilizatorilor blocați și degradarea procesului.",
            "produces_impact": f"Recomandare: {esc0.get('action', 'reminder')} — "
                               f"{esc0.get('why', 'deblochează fluxul')}",
            "after": [e.get("action") for b in (s.get("breaches") or [])[:1]
                      for e in (b.get("escalations") or [])[:3]],
            "factors": factors, "reasons":
                [f"SLA Intelligence: {over}/{s['active']} instanțe active au depășit SLA-ul."],
            "score": _score(factors), "can_execute": True,
        })
    return out


async def generate_decisions(user: dict, path: str = "") -> list:
    role = user.get("role") or ""
    guards = _effective_guards(user)
    homes = _role_homes()
    decisions = []

    if role in ADMIN_ROLES:
        decisions.extend(await _admin_decisions(user))
    else:
        procs = await list_processes(kind="business")
        for proc in procs:
            if not proc.get("entity"):
                continue
            relevant = any(t["actor"] in guards for t in proc["transitions"])
            if not relevant:
                continue
            st = await process_state(user, process_id=proc["id"])
            if st.get("status") == "completed":
                continue
            if st.get("status") == "not_started":
                d = await _decision_start_process(user, proc, st, guards, homes)
                if d:
                    decisions.append(d)
                continue
            mine = [t for t in st.get("next_actions") or []
                    if t["actor"] in guards and t["endpoint"]["method"] != "GET"]
            for t in mine[:1]:
                decisions.append(await _decision_from_transition(user, proc, st, t, guards, homes))
        # acțiunile mentor (AIB-004) devin decizii candidate
        from ai_brain.mentor import next_best_actions
        for i, a in enumerate(await next_best_actions(user)):
            decisions.append(_decision_from_mentor(a, i))

    seen, unique = set(), []
    for d in sorted(decisions, key=lambda d: -d["score"]):
        if d["id"] not in seen:
            seen.add(d["id"])
            unique.append(d)
    return unique[:7]


async def next_best_decisions(user: dict, path: str = "") -> list:
    """Generează + recalibrează adaptiv (AIB-008) + persistă snapshot-ul."""
    items = await generate_decisions(user, path)
    uid = user.get("id") or str(user.get("_id", ""))
    old_snap = await db.ai_brain_decisions.find_one({"user_id": uid}, {"_id": 0})
    try:
        from ai_brain.adaptive import reconcile_snapshot, enrich_decisions
        items = await reconcile_snapshot(user, old_snap, items)
        items = await enrich_decisions(user, items)
    except Exception:  # noqa: BLE001
        pass
    await db.ai_brain_decisions.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "role": user.get("role"), "path": path,
                  "items": items, "generated_at": _now()}},
        upsert=True)
    return items


async def _load_decision(user: dict, decision_id: str) -> dict | None:
    uid = user.get("id") or str(user.get("_id", ""))
    snap = await db.ai_brain_decisions.find_one({"user_id": uid}, {"_id": 0})
    for d in (snap or {}).get("items", []):
        if d["id"] == decision_id:
            return d
    return None


# ---------------------------------------------------------------------------
# 5 · DECISION SIMULATOR — impact estimat, ZERO modificări
# ---------------------------------------------------------------------------
async def simulate_decision(user: dict, decision_id: str) -> dict:
    d = await _load_decision(user, decision_id)
    if not d:
        return {"found": False, "reason": "Decizie inexistentă — regenerează lista de decizii."}
    modules, processes, users_affected, state_changes = set(), set(), set(), []

    if d.get("process_id"):
        proc = await get_process(d["process_id"])
        node = f"process:{d['process_id']}"
        async for e in db.ai_brain_graph_edges.find({"source": node, "rel": "in_module"}, {"target": 1}):
            modules.add(e["target"].split(":", 1)[1])
        for r in (proc or {}).get("relations", []):
            processes.add(r["to"].replace("proc_", "").replace("_", " "))
        async for e in db.ai_brain_graph_edges.find(
                {"$or": [{"source": node, "rel": "flows_to"}, {"target": node, "rel": "flows_to"}]}):
            other = e["target"] if e["source"] == node else e["source"]
            processes.add(other.split(":", 1)[1].replace("proc_", "").replace("_", " "))
        t = d.get("transition")
        if t and proc:
            to = t["to"]
            terminal = to in proc.get("terminal_states", [])
            state_changes.append({"entity": proc["entity"],
                                  "from": t.get("from"), "to": to,
                                  "terminal": terminal})
            nxt_actors = sorted({x["actor"] for x in proc["transitions"] if x["from"] == to})
            users_affected |= set(nxt_actors)
            for x in proc["transitions"]:
                if x["from"] == to:
                    state_changes.append({"entity": proc["entity"], "from": to, "to": x["to"],
                                          "estimated": True, "actor": x["actor"]})
        # utilizatori concreți de pe entitatea reală
        if d.get("entity"):
            doc = await _find_entity(proc, user, d["entity"].get("id"))
            for f in OWNER_FIELDS:
                if doc and doc.get(f):
                    users_affected.add(f.removesuffix("_id"))
    else:
        seg = (d.get("cta_path") or "/").split("?")[0].split("/")
        module = next((s for s in seg if s), "root")
        modules.add(module)
        async for e in db.ai_brain_graph_edges.find(
                {"target": f"module:{module}", "rel": "in_module"}, {"source": 1}).limit(50):
            k = e["source"].split(":")[0]
            if k == "api":
                processes.add(module)

    return {
        "found": True, "decision_id": decision_id, "title": d["title"],
        "simulated": True, "executed": False,
        "affected_modules": sorted(modules),
        "affected_processes": sorted(processes),
        "affected_users": sorted(users_affected) or ["tu"],
        "estimated_state_changes": state_changes[:6],
        "impact_summary": d.get("produces_impact"),
        "risk_if_skipped": d.get("avoids_risk"),
        "simulated_at": _now(),
    }


# ---------------------------------------------------------------------------
# 4 · DECISION EXPLANATION — LLM ancorat pe decizie + proces + graf (cu fallback)
# ---------------------------------------------------------------------------
def _fallback_explanation(d: dict, sim: dict, alternatives: list) -> str:
    parts = [f"## De ce îți recomand «{d['title']}»",
             "\n".join(f"- {r}" for r in d["reasons"]) or f"- Scor {d['score']}/100.",
             f"## Ce rezolvă\n{d['resolves']}",
             f"## Ce risc eviți\n{d['avoids_risk']}",
             f"## Ce se întâmplă dacă nu faci nimic\nRămâi în aceeași etapă; {d['avoids_risk'].lower()}"]
    if sim.get("found"):
        parts.append("## Impact estimat\n"
                     f"Module: {', '.join(sim['affected_modules']) or '—'} · "
                     f"Procese: {', '.join(sim['affected_processes']) or '—'}")
    if alternatives:
        parts.append("## Alternative\n" + "\n".join(
            f"- {a['title']} (scor {a['score']}/100)" for a in alternatives[:3]))
    return "\n\n".join(parts)


async def explain_decision(user: dict, decision_id: str, question: str = "") -> dict:
    d = await _load_decision(user, decision_id)
    if not d:
        return {"found": False, "explanation": "Decizia nu mai există — regenerează lista de decizii."}
    uid = user.get("id") or str(user.get("_id", ""))
    snap = await db.ai_brain_decisions.find_one({"user_id": uid}, {"_id": 0})
    alternatives = [a for a in (snap or {}).get("items", []) if a["id"] != decision_id][:3]
    sim = await simulate_decision(user, decision_id)
    pstate = await process_state(user, process_id=d["process_id"]) if d.get("process_id") else None

    role = user.get("role") or ""
    key = hashlib.sha1(f"decision|{role}|{decision_id}|{d['score']}|{question.strip().lower()[:80]}".encode(), usedforsecurity=False).hexdigest()
    cached = await db.ai_brain_explanations.find_one({"key": key}, {"_id": 0})
    if cached:
        await db.ai_brain_explanations.update_one({"key": key}, {"$inc": {"hits": 1}})
        return {"found": True, "explanation": cached["text"], "cached": True, "decision": d}

    from ai_core.provider import call_llm
    from ai_brain.explain import SYSTEM_PROMPT
    user_msg = (
        f"Utilizatorul (rol: {role}) întreabă despre decizia recomandată: "
        f"«{question or 'De ce îmi recomanzi asta și ce se întâmplă dacă nu fac nimic?'}»\n"
        "Răspunde EXCLUSIV pe baza datelor de mai jos. Structură (Markdown, română):\n"
        "## De ce această decizie (factorii reali, cu valorile lor)\n"
        "## Ce rezolvă și ce risc eviți\n## Ce se întâmplă dacă nu faci nimic\n"
        "## Impact estimat (din simulare)\n## Alternative (cu scorurile lor)\n\n"
        f"DECIZIA: {d}\n\nSIMULARE IMPACT: {sim}\n\n"
        f"STAREA PROCESULUI: {pstate}\n\nALTERNATIVE: "
        f"{[{'title': a['title'], 'score': a['score'], 'resolves': a['resolves']} for a in alternatives]}"
    )
    res = await call_llm(SYSTEM_PROMPT, user_msg, session_id=f"decision-{key[:12]}")
    if res.get("error") or not res.get("text"):
        return {"found": True, "explanation": _fallback_explanation(d, sim, alternatives),
                "cached": False, "model": "fallback", "decision": d}
    await db.ai_brain_explanations.update_one(
        {"key": key},
        {"$set": {"key": key, "kind": "decision", "role": role, "text": res["text"],
                  "model": res.get("model", ""), "created_at": _now()}, "$setOnInsert": {"hits": 0}},
        upsert=True)
    return {"found": True, "explanation": res["text"], "cached": False,
            "model": res.get("model"), "decision": d}


# ---------------------------------------------------------------------------
# 6 · PRIORITY ENGINE — prioritățile platformei (admin), din date reale
# ---------------------------------------------------------------------------
async def platform_priorities() -> list:
    items = []
    async for p in db.ai_brain_processes.find({"kind": "business"}, {"_id": 0}):
        st = p.get("stats") or {}
        total, stale = st.get("total", 0), st.get("stale_count", 0)
        if total and stale:
            top = (st.get("abandon_points") or [{}])[0]
            items.append({
                "kind": "blocked_process", "process_id": p["id"], "title":
                    f"«{p['name']}»: {stale}/{total} instanțe blocate >14 zile",
                "detail": f"Punct principal de abandon: «{top.get('state', '?')}» ({top.get('stuck', 0)}).",
                "severity": round(100 * stale / total),
            })
    arch = await db.architecture_guardian_tasks.count_documents({"status": "open"})
    prod = await db.product_guardian_tasks.count_documents({"status": "open"})
    if arch + prod:
        items.append({"kind": "guardian_tasks", "process_id": None,
                      "title": f"{arch + prod} task-uri Guardian deschise",
                      "detail": f"Arhitectură: {arch} · Produs: {prod}.", "severity": min((arch + prod) * 10, 90)})
    blocked = await db.orchestrator_retry_queue.count_documents({"status": "blocked_by_config"})
    if blocked:
        items.append({"kind": "blocked_emails", "process_id": None,
                      "title": f"{blocked} emailuri blocate de configurație",
                      "detail": "Se livrează cu un click după fix.", "severity": min(blocked * 15, 95)})
    return sorted(items, key=lambda i: -i["severity"])[:10]


def decision_rules() -> dict:
    """Regulile de generare + structura scorului — pentru Decision Explorer (transparență)."""
    return {
        "weights": WEIGHTS,
        "generators": [
            {"kind": "process_transition", "rule": "Tranziție de proces executabilă de rolul "
             "utilizatorului, din starea reală a entității lui (Process Intelligence)."},
            {"kind": "process_start", "rule": "Proces business nepornit, fără dependențe lipsă, "
             "cu prima tranziție executabilă de rol."},
            {"kind": "mentor_action", "rule": "Acțiune deterministă AI Mentor (AIB-004) pe starea "
             "reală din DB, convertită în decizie candidată."},
            {"kind": "pending_approval", "rule": "Admin: instanțe reale care așteaptă o tranziție "
             "de admin (by_status × tranziții cu actor admin)."},
            {"kind": "guardian_task", "rule": "Admin: task-uri deschise din Guardian Kernel."},
        ],
        "factors": {
            "urgency": "Blocaje reale: expirat=1.0, stagnare=zile/30, alt blocaj=0.5.",
            "impact": "Conexiunile procesului în Knowledge Graph (muchii/20).",
            "unblocking": "Câte procese din aval depind de acesta (references/flows_to).",
            "readiness": "Permisiune + date disponibile pentru execuție imediată.",
            "progress": "Poziția în proces (pas curent/total) — finalul e prioritar.",
            "risk_of_inaction": "Rata reală de stagnare a procesului (stale/total).",
        },
    }
