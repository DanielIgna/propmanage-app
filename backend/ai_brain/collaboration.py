"""AI Brain · Collaborative Intelligence Engine (AIB-009).

Coordonare inteligentă între actori (client, specialist, operator, admin, guardian, sistem)
— FĂRĂ execuție automată: observă, explică, prioritizează, recomandă.
Componente: Responsibility Engine (cine e responsabil / cine urmează / cine întârzie),
Intelligent Handoff (transferuri de responsabilitate derivate din tranzițiile reale),
Notification Intelligence (intenții deduplicate + prioritizate, cu «de ce e importantă»),
SLA Intelligence (SLA empiric = 2× durata medie observată a etapei, fallback 72h),
Collaboration Timeline, Escalation Engine (propuneri argumentate, zero execuție).
Reutilizează integral AIB-002..008. Persistență: db.ai_brain_notifications (dedupe),
db.ai_brain_sla_status (sweep-uri pentru Guardian + Explorer).
"""
import hashlib
from datetime import datetime, timezone

from db import db
from ai_brain.process import (ADMIN_ROLES, OWNER_FIELDS, _active_process, _find_entity,
                              _next_transitions, _parse_dt, _timeline, get_process)

DEFAULT_SLA_H = 72.0
GENERIC_ACTORS = {"public", "authenticated"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 5 · SLA INTELLIGENCE — SLA empiric per etapă
# ---------------------------------------------------------------------------
def sla_hours(proc: dict, status: str) -> tuple:
    avg = (proc.get("stats") or {}).get("avg_hours_from_start") or {}
    steps = proc.get("steps") or []
    if status in steps:
        cur = avg.get(f"{status}_at") or (0.0 if status in proc.get("initial_states", []) else None)
        for nxt_s in steps[steps.index(status) + 1:]:
            n = avg.get(f"{nxt_s}_at")
            if n is not None and cur is not None and n > cur:
                return max(24.0, round(2 * (n - cur), 1)), "empiric: 2× durata medie observată a etapei"
    return DEFAULT_SLA_H, "implicit: 72h (fără suficiente date istorice)"


def _time_in_stage_h(doc: dict) -> float:
    ts = [t for t in (_parse_dt(v) for k, v in doc.items() if k.endswith("_at")) if t]
    last = max(ts) if ts else None
    if not last:
        return 0.0
    return round((datetime.now(timezone.utc) - last).total_seconds() / 3600, 1)


def _sla_level(ratio: float) -> str:
    if ratio > 3:
        return "abandoned"
    if ratio > 1:
        return "breached"
    if ratio > 0.7:
        return "at_risk"
    return "ok"


# ---------------------------------------------------------------------------
# 1+2 · COLLABORATION & RESPONSIBILITY ENGINE
# ---------------------------------------------------------------------------
def _stage_actors(proc: dict, state: str) -> list:
    """Actorii care pot avansa procesul DIN etapa dată (fără efecte de sistem GET);
    adminul e omis când există actori de business (poate oricum interveni)."""
    nxt = [t for t in _next_transitions(proc, state) if t["endpoint"]["method"] != "GET"]
    actors = {t["actor"] for t in nxt} - GENERIC_ACTORS
    return sorted(actors - ADMIN_ROLES or actors)


async def instance_collaboration(proc: dict, doc: dict) -> dict:
    status = str(doc.get("status") or "")
    terminal = status in proc.get("terminal_states", [])
    nxt = [] if terminal else [t for t in _next_transitions(proc, status)
                               if t["endpoint"]["method"] != "GET"]
    if not terminal and not nxt:
        terminal = True  # nicio acțiune umană posibilă → cvasi-terminală pentru colaborare
    non_admin = [t for t in nxt if t["actor"] not in ADMIN_ROLES]
    current = sorted({t["actor"] for t in (non_admin or nxt)} - GENERIC_ACTORS) \
        or (["system"] if not terminal and nxt else [])
    next_state = nxt[0]["to"] if nxt else None
    next_actors = _stage_actors(proc, next_state) if next_state else []
    present = sorted({f.removesuffix("_id") for f in OWNER_FIELDS if doc.get(f)})
    waiting = [a for a in present if a not in current]
    done_states = [s for s in proc.get("steps", []) if doc.get(f"{s}_at") and s != status]
    past_actors = sorted({t["actor"] for t in proc["transitions"]
                          if t["to"] in done_states} - GENERIC_ACTORS)
    released = [a for a in past_actors if a not in current and a not in next_actors]
    sla, sla_basis = sla_hours(proc, status)
    hours_in = _time_in_stage_h(doc)
    ratio = round(hours_in / sla, 2) if sla else 0
    level = "done" if terminal else _sla_level(ratio)
    delayed = current if level in ("breached", "abandoned") else []
    to_notify = list(dict.fromkeys(
        (delayed or current) + (waiting if level in ("breached", "abandoned") else [])))
    unassigned = [a for a in current if f"{a}_id" in OWNER_FIELDS and not doc.get(f"{a}_id")]
    eid = doc.get("id") or str(doc.get("_id"))
    return {
        "entity": {"id": eid, "label": str(doc.get("title") or doc.get("name") or eid)[:80]},
        "state": status, "terminal": terminal,
        "responsible_now": current, "next_actors": next_actors, "next_state": next_state,
        "waiting_actors": waiting, "released_actors": released,
        "delayed_actors": delayed, "unassigned_actors": unassigned,
        "blocking_actor": (delayed or unassigned or [None])[0],
        "to_notify": to_notify,
        "sla": {"hours_in_stage": hours_in, "sla_hours": sla, "ratio": ratio,
                "level": level, "basis": sla_basis},
        "handoff": _instance_handoff(proc, doc, status, current, nxt),
    }


# ---------------------------------------------------------------------------
# 3 · INTELLIGENT HANDOFF
# ---------------------------------------------------------------------------
def _instance_handoff(proc: dict, doc: dict, status: str, current: list, nxt: list) -> dict:
    into = sorted({t["actor"] for t in proc["transitions"]
                   if t["to"] == status} - GENERIC_ACTORS) or ["system"]
    return {
        "from_actor": into, "to_actor": current or ["—"],
        "why": f"Instanța a intrat în etapa «{status}» — responsabilitatea a trecut la "
               f"{', '.join(current) if current else 'nimeni (etapă finală sau nealocat)'}.",
        "transfers": {"entity": proc["entity"],
                      "label": str(doc.get("title") or doc.get("name") or "")[:60]},
        "next_step": (f"«{nxt[0]['to']}» prin {nxt[0]['endpoint']['method']} "
                      f"{nxt[0]['endpoint']['path']}" if nxt else "proces finalizat"),
    }


def handoff_map(proc: dict) -> list:
    out = []
    prev_actors, prev_state = None, None
    for s in proc.get("steps", []):
        acts = _stage_actors(proc, s)
        if prev_actors and acts and set(acts) != set(prev_actors):
            tr = next((t for t in proc["transitions"]
                       if t["from"] == prev_state and t["to"] == s), None)
            out.append({
                "from_actor": prev_actors, "to_actor": acts, "at_state": s,
                "why": f"După «{prev_state}», etapa «{s}» poate fi avansată doar de "
                       f"{', '.join(acts)}."
                       + (f" Transferul se face prin {tr['endpoint']['method']} "
                          f"{tr['endpoint']['path']}." if tr else ""),
                "transfers": proc["entity"],
            })
        if acts:
            prev_actors = acts
        prev_state = s
    return out


# ---------------------------------------------------------------------------
# 7 · ESCALATION ENGINE — propuneri argumentate, zero execuție
# ---------------------------------------------------------------------------
def escalation_options(collab: dict) -> list:
    ratio = collab["sla"]["ratio"]
    level = collab["sla"]["level"]
    if level in ("ok", "done"):
        return []
    opts = []
    who = ", ".join(collab["responsible_now"]) or "responsabilul"
    if level == "at_risk" or ratio <= 2:
        opts.append({"action": "reminder", "to": collab["responsible_now"],
                     "why": f"Etapa «{collab['state']}» e la {round(ratio * 100)}% din SLA — "
                            f"un reminder către {who} rezolvă de obicei fără escaladare."})
    if ratio > 2:
        opts.append({"action": "escalate", "to": ["operator", "admin"],
                     "why": f"Întârziere de {ratio}× SLA — {who} nu a reacționat la timp; "
                            "un nivel superior trebuie informat."})
    if collab["unassigned_actors"]:
        opts.append({"action": "reassign", "to": collab["unassigned_actors"],
                     "why": f"Niciun {', '.join(collab['unassigned_actors'])} alocat — "
                            "realocarea e singura cale de deblocare."})
    if ratio > 5:
        opts.append({"action": "close", "to": ["admin"],
                     "why": f"Inactivitate de {ratio}× SLA — abandon probabil; închiderea "
                            "eliberează resursele și curăță statisticile."})
    if any(a in ADMIN_ROLES for a in collab["responsible_now"]):
        opts.append({"action": "admin_intervention", "to": ["admin"],
                     "why": "Etapa curentă necesită explicit decizia unui administrator."})
    return opts[:3]


# ---------------------------------------------------------------------------
# 4 · NOTIFICATION INTELLIGENCE — intenții deduplicate + prioritizate
# ---------------------------------------------------------------------------
async def _notify_intent(kind: str, target: str, proc: dict, state: str, count: int,
                         priority: int, why: str, example: str) -> bool:
    """O singură notificare AGREGATĂ per (kind, target, proces, stare) — zero duplicate."""
    key = hashlib.sha1(f"{kind}|{target}|{proc['id']}|{state}".encode(), usedforsecurity=False).hexdigest()[:16]
    existing = await db.ai_brain_notifications.find_one({"key": key, "status": "active"})
    if existing:
        await db.ai_brain_notifications.update_one(
            {"key": key, "status": "active"},
            {"$set": {"last_seen_at": _now(), "priority": priority,
                      "instances": count, "why": why}})
        return False
    await db.ai_brain_notifications.insert_one({
        "key": key, "kind": kind, "target": target,
        "process_id": proc["id"], "process_name": proc["name"],
        "state": state, "instances": count, "example": example,
        "priority": priority, "why": why, "status": "active",
        "created_at": _now(), "last_seen_at": _now(),
    })
    return True


def _priority(collab: dict, proc: dict) -> int:
    ratio = collab["sla"]["ratio"]
    stats = (proc.get("stats") or {})
    stale_ratio = stats.get("stale_count", 0) / stats["total"] if stats.get("total") else 0
    p = min(50, round(ratio * 20)) + round(20 * stale_ratio)
    if collab["unassigned_actors"]:
        p += 15
    if collab["waiting_actors"]:
        p += 10
    return min(100, p)


# ---------------------------------------------------------------------------
# SLA SWEEP — scanare instanțe active + notificări + escaladări (persistate)
# ---------------------------------------------------------------------------
async def sla_sweep(run_id: str = "") -> dict:
    now = _now()
    sweep_start = now
    monitored, notif_new, all_escalations = 0, 0, 0
    results = []
    async for proc in db.ai_brain_processes.find(
            {"kind": "business", "entity": {"$ne": None}}, {"_id": 0}):
        terminal = proc.get("terminal_states") or []
        counts = {"ok": 0, "at_risk": 0, "breached": 0, "abandoned": 0}
        breaches = []
        agg: dict = {}
        cursor = db[proc["entity"]].find(
            {"status": {"$nin": terminal + [None, ""]}}).sort("created_at", 1).limit(40)
        async for doc in cursor:
            collab = await instance_collaboration(proc, doc)
            level = collab["sla"]["level"]
            if level == "done":
                continue
            counts[level] += 1
            if level in ("breached", "abandoned"):
                esc = escalation_options(collab)
                all_escalations += len(esc)
                prio = _priority(collab, proc)
                for target in collab["to_notify"][:2]:
                    a = agg.setdefault((target, collab["state"]),
                                       {"count": 0, "prio": 0, "max_h": 0.0,
                                        "responsible": set(), "example": ""})
                    a["count"] += 1
                    a["prio"] = max(a["prio"], prio)
                    a["max_h"] = max(a["max_h"], collab["sla"]["hours_in_stage"])
                    a["responsible"] |= set(collab["responsible_now"])
                    a["example"] = a["example"] or collab["entity"]["label"]
                if len(breaches) < 8:
                    breaches.append({**{k: collab[k] for k in
                                        ("entity", "state", "responsible_now", "waiting_actors",
                                         "blocking_actor", "sla", "handoff")},
                                     "escalations": esc, "priority": prio})
        for (target, state), a in agg.items():
            why = (f"{a['count']} instanțe «{proc['name']}» sunt blocate în etapa «{state}» "
                   f"peste SLA (cea mai veche: {round(a['max_h'] / 24)} zile). "
                   f"Responsabil: {', '.join(sorted(a['responsible'])) or '—'}. "
                   f"Ex: {a['example']}.")
            if await _notify_intent("sla_breach", target, proc, state,
                                    a["count"], a["prio"], why, a["example"]):
                notif_new += 1
        active = sum(counts.values())
        if active:
            monitored += 1
            results.append({"process_id": proc["id"], "process_name": proc["name"],
                            "actors": proc.get("actors") or [], "counts": counts,
                            "active": active, "breaches": breaches,
                            "run_id": run_id, "ts": now})
    await db.ai_brain_sla_status.delete_many({})
    if results:
        await db.ai_brain_sla_status.insert_many([dict(r) for r in results])
    # notificările nevalidate în acest sweep nu mai sunt de actualitate → expirate
    await db.ai_brain_notifications.update_many(
        {"status": "active", "last_seen_at": {"$lt": sweep_start}},
        {"$set": {"status": "expired", "expired_at": now}})
    return {"swept_at": now, "processes_monitored": monitored,
            "instances_checked": sum(r["active"] for r in results),
            "at_risk": sum(r["counts"]["at_risk"] for r in results),
            "breached": sum(r["counts"]["breached"] for r in results),
            "abandoned": sum(r["counts"]["abandoned"] for r in results),
            "notifications_created": notif_new, "escalations_proposed": all_escalations}


# ---------------------------------------------------------------------------
# 6 · COLLABORATION TIMELINE
# ---------------------------------------------------------------------------
async def collaboration_timeline(proc: dict, doc: dict) -> dict:
    events = await _timeline(proc, doc)
    contributors = sorted({e["actor"] for e in events if e.get("actor")})
    def _match(words):
        return [e for e in events if any(w in str(e.get("event", "")).lower() for w in words)]
    return {
        "events": events,
        "created_by": next((e.get("actor") for e in events if e.get("actor")), None)
                      or next((f.removesuffix("_id") for f in ("created_by", "client_id", "owner_id", "user_id")
                               if doc.get(f)), None),
        "contributors": contributors,
        "approvals": _match(("confirm", "approv", "accept"))[:5],
        "rejections": _match(("reject", "refuz", "disput", "cancel"))[:5],
    }


# ---------------------------------------------------------------------------
# STAREA COLABORĂRII per utilizator (Mentor + endpoint user)
# ---------------------------------------------------------------------------
async def collaboration_state(user: dict, process_id: str = None,
                               entity_id: str = None, path: str = "") -> dict:
    if process_id:
        proc = await get_process(process_id)
        if not proc or not proc.get("entity"):
            return {"found": False, "reason": "proces necunoscut sau fără entitate"}
        doc = await _find_entity(proc, user, entity_id)
    else:
        proc, doc = await _active_process(user, path)
    if not proc or not doc:
        return {"found": False, "reason": "nicio instanță activă de proces pentru acest utilizator"}
    collab = await instance_collaboration(proc, doc)
    return {"found": True,
            "process": {"id": proc["id"], "name": proc["name"]},
            **collab,
            "escalations": escalation_options(collab),
            "timeline": await collaboration_timeline(proc, doc),
            "resolved_at": _now()}


async def mentor_collab(user: dict, path: str = "") -> dict | None:
    st = await collaboration_state(user, path=path)
    if not st.get("found"):
        return None
    role = user.get("role") or ""
    you_act = role in st["responsible_now"]
    return {"process": st["process"]["name"],
            "responsible_now": st["responsible_now"], "you_act": you_act,
            "state": st["state"], "sla": st["sla"],
            "delayed": bool(st["delayed_actors"]),
            "message": (f"E rândul tău să acționezi în «{st['process']['name']}» "
                        f"(etapa «{st['state']}»)." if you_act else
                        f"Aștepți după: {', '.join(st['responsible_now']) or '—'} "
                        f"(etapa «{st['state']}»"
                        + (f", întârziere {st['sla']['ratio']}× SLA" if st["delayed_actors"] else "")
                        + ").")}


# ---------------------------------------------------------------------------
# 8 · OVERVIEW pentru Collaboration Explorer (admin)
# ---------------------------------------------------------------------------
async def collaboration_overview() -> dict:
    procs = [p async for p in db.ai_brain_sla_status.find({}, {"_id": 0})]
    notifications = [n async for n in db.ai_brain_notifications.find(
        {"status": "active"}, {"_id": 0}).sort("priority", -1).limit(20)]
    total_active = await db.ai_brain_notifications.count_documents({"status": "active"})
    return {
        "processes": sorted(procs, key=lambda p: -(p["counts"]["breached"] + p["counts"]["abandoned"])),
        "totals": {
            "monitored": len(procs),
            "instances": sum(p["active"] for p in procs),
            "at_risk": sum(p["counts"]["at_risk"] for p in procs),
            "breached": sum(p["counts"]["breached"] for p in procs),
            "abandoned": sum(p["counts"]["abandoned"] for p in procs),
            "notifications_active": total_active,
            "escalations": sum(len(b.get("escalations", [])) for p in procs for b in p.get("breaches", [])),
        },
        "notifications": notifications,
        "generated_at": _now(),
    }
