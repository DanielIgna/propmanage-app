"""AI Brain · Process Intelligence Engine (AIB-006).

Descoperă AUTOMAT procesele de business din codul real (zero liste hardcodate):
mașini de stări per colecție (insert/update cu «status» în routes/*.py), actori din
guard-urile endpoint-urilor, playbook-uri orchestrator (procese automate).
Componente: Process Discovery, Process Registry (db.ai_brain_processes),
Process State Engine (starea reală per utilizator/entitate), Blocker Detection,
Process Timeline (câmpuri *_at + activity_events), Business Flow Mapping
(relații references/co_writes) + sincronizare în Knowledge Graph (AIB-005).
"""
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from db import db

BACKEND_DIR = Path("/app/backend")

ROUTER_RE = re.compile(r"(\w+)\s*=\s*APIRouter\(([^)]*)\)")
DECOR_RE = re.compile(r"@(\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")
DB_WRITE_RE = re.compile(r"db\.([a-z_][a-z0-9_]*)\.(insert_one|update_one|update_many|find_one_and_update)\s*\(")
STATUS_RE = re.compile(r"[\"']status[\"']\s*:\s*[\"']([a-z_]+)[\"']")
PRECOND_RE = re.compile(r"(?<![a-z_])status[\"'\]\)]*\s*(?:!=|==)\s*[\"']([a-z_]+)[\"']")
GUARD_RE = re.compile(r"require_role\(\s*[\"'](\w+)[\"']")

OWNER_FIELDS = ("owner_id", "client_id", "user_id", "specialist_id", "created_by", "partner_id", "buyer_id")
ADMIN_ROLES = {"admin", "super_admin"}
DATE_BLOCK_WORDS = ("deadline", "expires", "expiry", "valid_until")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _parse_dt(v) -> datetime | None:
    if not isinstance(v, str) or len(v) < 8:
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# 1 · PROCESS DISCOVERY — mașini de stări extrase din codul endpoint-urilor
# ---------------------------------------------------------------------------
def _endpoints_with_bodies(text: str) -> list:
    prefixes = {}
    for var, args in ROUTER_RE.findall(text):
        pm = re.search(r"prefix\s*=\s*[\"']([^\"']+)[\"']", args)
        prefixes[var] = pm.group(1) if pm else ""
    matches = list(DECOR_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        var, meth, path = m.groups()
        body = text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        gm = GUARD_RE.search(body[:600])
        guard = gm.group(1) if gm else ("authenticated" if "get_current_user" in body[:600] else "public")
        out.append((meth.upper(), f"{prefixes.get(var, '')}{path}", guard, body))
    return out


def discover_transitions() -> tuple:
    """Returnează (found_per_coll, endpoint_colls) — descoperit exclusiv din cod."""
    found: dict = {}
    endpoint_colls: list = []
    for f in sorted((BACKEND_DIR / "routes").glob("*.py")):
        text = _read(f)
        for meth, path, guard, body in _endpoints_with_bodies(text):
            precond = PRECOND_RE.findall(body)
            colls_here = set()
            for m in DB_WRITE_RE.finditer(body):
                coll, op = m.groups()
                window = body[m.end():m.end() + 700]
                if op == "insert_one":
                    froms, tos = [], STATUS_RE.findall(window[:500])
                    if not tos:
                        pre = body[max(0, m.start() - 900):m.start()]
                        tos = STATUS_RE.findall(pre)[-1:]
                else:
                    set_idx = window.find("$set")
                    if set_idx < 0:
                        continue
                    froms = STATUS_RE.findall(window[:set_idx])
                    tos = STATUS_RE.findall(window[set_idx:set_idx + 400])
                    if not tos:
                        pre = body[max(0, m.start() - 900):m.start()]
                        last = None
                        for sm in STATUS_RE.finditer(pre):
                            last = sm
                        if last and not DB_WRITE_RE.search(pre, last.end()):
                            wlast = None
                            for wm in DB_WRITE_RE.finditer(pre):
                                if wm.start() < last.start():
                                    wlast = wm
                            seg = pre[wlast.end():last.start()] if wlast else ")"
                            # valid doar dacă apelul DB anterior s-a închis înaintea statusului
                            if seg.count(")") > seg.count("("):
                                tos = [last.group(1)]
                if not tos:
                    continue
                to, frm = tos[0], (froms or precond or [None])[0]
                p = found.setdefault(coll, {"transitions": [], "states": set(), "initial": set(),
                                            "actors": set(), "files": set(), "modules": set(), "has_update": False})
                key = (frm, to, meth, path)
                if key in {(t["from"], t["to"], t["endpoint"]["method"], t["endpoint"]["path"]) for t in p["transitions"]}:
                    continue
                p["transitions"].append({"from": frm, "to": to, "actor": guard,
                                         "op": "insert" if op == "insert_one" else "update",
                                         "endpoint": {"method": meth, "path": path}, "file": f.name})
                p["states"].add(to)
                if frm:
                    p["states"].add(frm)
                if op == "insert_one":
                    p["initial"].add(to)
                else:
                    p["has_update"] = True
                p["actors"].add(guard)
                p["files"].add(f.name)
                p["modules"].add((path.split("/") + ["", ""])[2] or "root")
                colls_here.add(coll)
            if len(colls_here) > 1:
                endpoint_colls.append(colls_here)
    return found, endpoint_colls


def _order_states(states: set, initial: set, transitions: list) -> tuple:
    """Sortare topologică (Kahn) pe muchiile explicite from→to; stările neancorate separat."""
    edges = {(t["from"], t["to"]) for t in transitions if t["from"] and t["to"] and t["from"] != t["to"]}
    insert_weight: dict = {}
    for t in transitions:
        if t.get("op") == "insert":
            insert_weight[t["to"]] = insert_weight.get(t["to"], 0) + 1
    anchored = {s for e in edges for s in e}
    indeg = {s: 0 for s in anchored}
    for _, b in edges:
        indeg[b] += 1
    order = []
    ready = sorted((s for s in anchored if indeg[s] == 0),
                   key=lambda s: (-insert_weight.get(s, 0), s))
    while ready:
        s = ready.pop(0)
        order.append(s)
        for a, b in sorted(edges):
            if a == s:
                indeg[b] -= 1
                if indeg[b] == 0:
                    ready.append(b)
        ready.sort(key=lambda x: (-insert_weight.get(x, 0), x))
    order.extend(sorted(anchored - set(order)))  # cicluri
    return order, sorted(states - anchored)


async def _sort_by_data(coll: str, rest: list) -> list:
    """Ordonează empiric stările neancorate: offset-ul mediu al «{stare}_at» față de created_at."""
    if len(rest) < 2:
        return rest
    offs: dict = {}
    async for doc in db[coll].find({"created_at": {"$exists": True}}).limit(300):
        c = _parse_dt(doc.get("created_at"))
        if not c:
            continue
        for s in rest:
            dt = _parse_dt(doc.get(f"{s}_at"))
            if dt and dt >= c:
                offs.setdefault(s, []).append((dt - c).total_seconds())
    avg = {s: sum(v) / len(v) for s, v in offs.items() if v}
    return sorted(rest, key=lambda s: (0, avg[s]) if s in avg else (1, s))


def _terminal_states(anchored: list, rest: list, transitions: list) -> list:
    """Terminal = fără tranziții explicite de ieșire și fără tranziții update non-admin
    «din orice stare» către o etapă ulterioară ancorată (excludem simulările admin)."""
    pos = {s: i for i, s in enumerate(anchored)}
    explicit_from = {t["from"] for t in transitions if t["from"]}
    open_updates = [t for t in transitions
                    if t["from"] is None and t.get("op") == "update" and t["actor"] not in ADMIN_ROLES]
    out = []
    for s in anchored:
        if s not in explicit_from and not any(pos.get(t["to"], -1) > pos[s] for t in open_updates):
            out.append(s)
    for s in rest:
        if s not in explicit_from and not any(t["to"] != s for t in open_updates):
            out.append(s)
    return out


def _file_purpose(files: set) -> str:
    for fn in sorted(files):
        first = _read(BACKEND_DIR / "routes" / fn).lstrip()[:300]
        if first.startswith('"""'):
            return first[3:first.find("\n")].strip().strip('"')[:200]
    return ""


PLURAL_SUFFIXES = ("s", "es", "_projects")


def _plural_candidates(base: str) -> list:
    out = [base + s for s in PLURAL_SUFFIXES] + [base]
    if base.endswith("y"):
        out.append(base[:-1] + "ies")
    return out


async def _relations(proc_colls: set, endpoint_colls: list) -> dict:
    rels: dict = {c: [] for c in proc_colls}
    for coll in proc_colls:
        seen = set()
        async for doc in db[coll].find({}).limit(3):
            for k in doc:
                if not k.endswith("_id") or k == "_id":
                    continue
                for cand in _plural_candidates(k[:-3]):
                    if cand in proc_colls and cand != coll and cand not in seen:
                        seen.add(cand)
                        rels[coll].append({"to": f"proc_{cand}", "rel": "references"})
    for group in endpoint_colls:
        procs = sorted(group & proc_colls)
        for i, a in enumerate(procs):
            for b in procs[i + 1:]:
                if not any(r["to"] == f"proc_{b}" for r in rels[a]):
                    rels[a].append({"to": f"proc_{b}", "rel": "co_writes"})
    return rels


# ---------------------------------------------------------------------------
# 2 · STATISTICI DE EXECUȚIE — din datele reale ale colecției
# ---------------------------------------------------------------------------
async def _stats(coll: str, terminal: list) -> dict:
    total = await db[coll].count_documents({})
    by_status: dict = {}
    async for d in db[coll].aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        by_status[str(d["_id"])] = d["n"]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    abandon: dict = {}
    async for d in db[coll].aggregate([
            {"$match": {"created_at": {"$lt": cutoff, "$type": "string"}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        if str(d["_id"]) not in terminal:
            abandon[str(d["_id"])] = d["n"]
    durations: dict = {}
    async for doc in db[coll].find({"created_at": {"$exists": True}}).limit(120):
        c = _parse_dt(doc.get("created_at"))
        if not c:
            continue
        for k, v in doc.items():
            if k.endswith("_at") and k != "created_at":
                dt = _parse_dt(v)
                if dt and dt >= c:
                    durations.setdefault(k, []).append((dt - c).total_seconds() / 3600)
    return {
        "total": total,
        "by_status": by_status,
        "active": total - sum(by_status.get(t, 0) for t in terminal),
        "stale_count": sum(abandon.values()),
        "abandon_points": sorted(({"state": k, "stuck": v} for k, v in abandon.items()),
                                 key=lambda x: -x["stuck"])[:5],
        "avg_hours_from_start": {k: round(sum(v) / len(v), 1) for k, v in durations.items() if len(v) >= 2},
    }


# ---------------------------------------------------------------------------
# 3 · PROCESS REGISTRY — construire + stocare + sincronizare graf
# ---------------------------------------------------------------------------
async def build_processes(run_id: str = "") -> dict:
    found, endpoint_colls = discover_transitions()
    proc_colls = set()
    for coll, p in found.items():
        if len(p["states"]) < 2 or not p["has_update"]:
            continue
        sample = await db[coll].find_one({})
        if sample is not None and "status" not in sample:
            continue
        proc_colls.add(coll)
    rels = await _relations(proc_colls, endpoint_colls)

    now = _now()
    procs = []
    for coll in sorted(proc_colls):
        p = found[coll]
        anchored, rest = _order_states(p["states"], p["initial"], p["transitions"])
        init_rest = [s for s in sorted(p["initial"]) if s in rest]
        other_rest = [s for s in rest if s not in init_rest]
        steps = init_rest + anchored + await _sort_by_data(coll, other_rest)
        terminal = _terminal_states(anchored, rest, p["transitions"])
        kind = "business" if (p["actors"] - ADMIN_ROLES) else "internal"
        procs.append({
            "id": f"proc_{coll}", "name": coll.replace("_", " ").title(), "kind": kind,
            "entity": coll, "purpose": _file_purpose(p["files"]),
            "actors": sorted(p["actors"]), "states": sorted(p["states"]),
            "initial_states": sorted(p["initial"]), "terminal_states": terminal,
            "steps": steps, "transitions": p["transitions"],
            "files": sorted(p["files"]), "modules": sorted(p["modules"]),
            "relations": rels.get(coll, []),
            "stats": await _stats(coll, terminal),
            "updated_at": now, "run_id": run_id,
        })

    try:
        from orchestrator.playbooks import PLAYBOOKS
        for signal, pb in PLAYBOOKS.items():
            procs.append({
                "id": f"auto_{pb['id']}", "name": pb["name"], "kind": "automated",
                "entity": None, "purpose": (pb.get("description") or "")[:300],
                "actors": ["system"], "trigger_signal": signal, "states": [], "steps": [],
                "initial_states": [], "terminal_states": [], "transitions": [],
                "files": [], "modules": ["orchestrator"], "relations": [], "stats": None,
                "updated_at": now, "run_id": run_id,
            })
    except Exception:  # noqa: BLE001
        pass

    await db.ai_brain_processes.delete_many({})
    if procs:
        await db.ai_brain_processes.insert_many([dict(pr) for pr in procs])
    await _sync_graph(procs)
    # AIB-008: istoric statistici pentru detectarea degradării (Guardian Feedback)
    try:
        from ai_brain.adaptive import snapshot_process_stats
        await snapshot_process_stats(run_id)
    except Exception:  # noqa: BLE001
        pass

    by_kind: dict = {}
    for pr in procs:
        by_kind[pr["kind"]] = by_kind.get(pr["kind"], 0) + 1
    return {"built_at": now, "total": len(procs), "by_kind": by_kind,
            "states": sum(len(pr["states"]) for pr in procs),
            "transitions": sum(len(pr["transitions"]) for pr in procs),
            "actors": sorted({a for pr in procs for a in pr["actors"]}),
            "relations": sum(len(pr["relations"]) for pr in procs)}


async def _sync_graph(procs: list):
    await db.ai_brain_graph_edges.delete_many({"$or": [
        {"source": {"$regex": "^process:proc_"}}, {"target": {"$regex": "^process:proc_"}}]})
    await db.ai_brain_graph_nodes.delete_many({"id": {"$regex": "^process:proc_"}})
    nodes, edges = [], []
    for pr in procs:
        if not pr["id"].startswith("proc_"):
            continue
        nid = f"process:{pr['id']}"
        nodes.append({"id": nid, "kind": "process", "label": pr["name"]})
        edges.append({"source": nid, "target": f"entity:{pr['entity']}", "rel": "manages", "weight": 1})
        for a in pr["actors"]:
            edges.append({"source": nid, "target": f"role:{a}", "rel": "involves", "weight": 1})
        for m in pr["modules"]:
            edges.append({"source": nid, "target": f"module:{m}", "rel": "in_module", "weight": 1})
        for r in pr["relations"]:
            if r["rel"] == "references":
                edges.append({"source": f"process:{r['to']}", "target": nid, "rel": "flows_to", "weight": 1})
            else:
                edges.append({"source": nid, "target": f"process:{r['to']}", "rel": r["rel"], "weight": 1})
    if nodes:
        await db.ai_brain_graph_nodes.insert_many(nodes)
    if edges:
        await db.ai_brain_graph_edges.insert_many(edges)


async def list_processes(kind: str = "") -> list:
    q = {"kind": kind} if kind else {}
    items = [p async for p in db.ai_brain_processes.find(q, {"_id": 0})]
    order = {"business": 0, "internal": 1, "automated": 2}
    items.sort(key=lambda p: (order.get(p["kind"], 3), -((p.get("stats") or {}).get("total", 0))))
    return items


async def get_process(pid: str) -> dict | None:
    return await db.ai_brain_processes.find_one({"id": pid}, {"_id": 0})


# ---------------------------------------------------------------------------
# 4 · PROCESS STATE ENGINE — starea reală per utilizator/entitate
# ---------------------------------------------------------------------------
def _uid(user: dict) -> str:
    return user.get("id") or str(user.get("_id", ""))


async def _find_entity(proc: dict, user: dict, entity_id: str = None):
    coll = db[proc["entity"]]
    if entity_id:
        from bson import ObjectId
        queries = [{"id": entity_id}]
        if ObjectId.is_valid(entity_id):
            queries.insert(0, {"_id": ObjectId(entity_id)})
        for q in queries:
            doc = await coll.find_one(q)
            if doc:
                return doc
        return None
    uid = _uid(user)
    if not uid:
        return None
    return await coll.find_one({"$or": [{f: uid} for f in OWNER_FIELDS]}, sort=[("created_at", -1)])


async def _active_process(user: dict, path: str = ""):
    module = ([s for s in (path or "").split("?")[0].split("/") if s] + ["root"])[0]
    mkey = module.replace("-", "_")
    procs = [p async for p in db.ai_brain_processes.find({"kind": "business"}, {"_id": 0})]
    scored = [p for p in procs
              if mkey in (p.get("entity") or "") or module in p.get("modules", []) or mkey in p.get("modules", [])]
    best, best_doc, best_ts = None, None, ""
    for p in (scored or procs):
        doc = await _find_entity(p, user)
        if doc:
            ts = str(doc.get("updated_at") or doc.get("created_at") or "")
            if ts >= best_ts:
                best, best_doc, best_ts = p, doc, ts
    if best:
        return best, best_doc
    return (scored[0], None) if scored else (None, None)


def _next_transitions(proc: dict, status: str) -> list:
    nxt = [t for t in proc["transitions"] if t["from"] == status and t["to"] != status]
    if not nxt and status in proc["steps"]:
        later = set(proc["steps"][proc["steps"].index(status) + 1:]) - {status}
        nxt = [t for t in proc["transitions"]
               if t["from"] is None and t.get("op") == "update" and t["to"] in later]
    return nxt


def _brief(proc: dict) -> dict:
    return {"id": proc["id"], "name": proc["name"], "entity": proc["entity"],
            "actors": proc["actors"], "steps": proc["steps"]}


async def process_state(user: dict, process_id: str = None, entity_id: str = None, path: str = "") -> dict:
    if process_id:
        proc = await get_process(process_id)
        if not proc:
            return {"found": False, "reason": "proces necunoscut"}
        if not proc.get("entity"):
            return {"found": True, "process": _brief(proc), "status": "automated",
                    "reason": "proces automat (orchestrator) — fără stare per utilizator"}
        doc = await _find_entity(proc, user, entity_id)
    else:
        proc, doc = await _active_process(user, path)
        if not proc:
            return {"found": False, "reason": "niciun proces activ detectat pentru acest utilizator"}

    if not doc:
        starters = [t for t in proc["transitions"] if t["from"] is None and t["to"] in proc["initial_states"]]
        return {"found": True, "process": _brief(proc), "entity": None, "status": "not_started",
                "current_state": None, "step_index": -1, "total_steps": len(proc["steps"]),
                "steps": [{"state": s, "phase": "pending"} for s in proc["steps"]],
                "completed_steps": [], "remaining_steps": proc["steps"],
                "next_actions": starters[:3], "who_acts": sorted({t["actor"] for t in starters}),
                "blockers": await _upstream_blockers(proc, user), "timeline": [], "resolved_at": _now()}

    status = str(doc.get("status") or "")
    steps = proc["steps"]
    idx = steps.index(status) if status in steps else -1
    step_list = []
    for i, s in enumerate(steps):
        if i == idx:
            phase = "current"
        elif doc.get(f"{s}_at"):
            phase = "done"  # dovadă reală: timestamp-ul etapei există pe document
        elif 0 <= i < idx and s in proc["initial_states"]:
            phase = "done"
        else:
            phase = "pending"
        step_list.append({"state": s, "phase": phase})
    terminal = status in proc["terminal_states"]
    nxt_all = [] if terminal else _next_transitions(proc, status)
    non_admin = [t for t in nxt_all if t["actor"] not in ADMIN_ROLES]
    nxt = non_admin or nxt_all
    eid = doc.get("id") or str(doc.get("_id"))
    return {"found": True, "process": _brief(proc),
            "entity": {"id": eid, "label": str(doc.get("title") or doc.get("name") or eid)[:80],
                       "collection": proc["entity"]},
            "status": "completed" if terminal else "in_progress",
            "current_state": status, "step_index": idx, "total_steps": len(steps),
            "steps": step_list,
            "completed_steps": [s["state"] for s in step_list if s["phase"] == "done"],
            "remaining_steps": [s["state"] for s in step_list if s["phase"] == "pending"],
            "next_actions": nxt[:5], "who_acts": sorted({t["actor"] for t in nxt}),
            "blockers": [] if terminal else await _blockers(proc, doc, user, nxt),
            "timeline": await _timeline(proc, doc), "resolved_at": _now()}


# ---------------------------------------------------------------------------
# 5 · BLOCKER DETECTION — cauze reale + cine trebuie să acționeze
# ---------------------------------------------------------------------------
async def _upstream_blockers(proc: dict, user: dict) -> list:
    out, uid = [], _uid(user)
    for r in proc.get("relations", []):
        if r["rel"] != "references":
            continue
        up = await get_process(r["to"])
        if not up or not up.get("entity"):
            continue
        has = await db[up["entity"]].find_one({"$or": [{f: uid} for f in OWNER_FIELDS]})
        if not has:
            out.append({"kind": "upstream_missing", "process": up["id"],
                        "text": f"Pornește mai întâi procesul «{up['name']}» — acest proces depinde de el."})
    return out[:3]


async def _blockers(proc: dict, doc: dict, user: dict, nxt: list) -> list:
    out = []
    role = user.get("role") or ""
    now = datetime.now(timezone.utc)
    actors = {t["actor"] for t in nxt}
    open_actors = actors - {"authenticated", "public"}
    if open_actors and role not in actors and "authenticated" not in actors and "public" not in actors:
        out.append({"kind": "waiting_on_actor", "who": sorted(open_actors),
                    "text": f"Pasul următor trebuie făcut de: {', '.join(sorted(open_actors))} — nu de tine ({role})."})
    for a in open_actors:
        f = f"{a}_id"
        if f in OWNER_FIELDS and not doc.get(f):
            out.append({"kind": "actor_unassigned",
                        "text": f"Niciun {a} alocat încă — procesul așteaptă alocarea unui {a}."})
    for k, v in doc.items():
        if isinstance(v, str) and any(w in k for w in DATE_BLOCK_WORDS):
            dt = _parse_dt(v)
            if dt and dt < now:
                out.append({"kind": "expired", "field": k,
                            "text": f"Termenul «{k}» a expirat la {v[:10]} — procesul nu poate continua fără reînnoire."})
    ts = [t for t in (_parse_dt(v) for k, v in doc.items() if k.endswith("_at")) if t]
    last = max(ts) if ts else None
    if last and (now - last) > timedelta(days=7):
        out.append({"kind": "stalled", "days": (now - last).days,
                    "text": f"Nicio activitate de {(now - last).days} zile — procesul pare blocat în etapa "
                            f"«{doc.get('status')}»."})
    if nxt and all(t["actor"] in ADMIN_ROLES for t in nxt) and role not in ADMIN_ROLES:
        out.append({"kind": "needs_approval",
                    "text": "Etapa următoare necesită aprobare din partea unui administrator."})
    return out[:4]


# ---------------------------------------------------------------------------
# 6 · PROCESS TIMELINE — cronologie reală din entitate + event bus
# ---------------------------------------------------------------------------
async def _timeline(proc: dict, doc: dict) -> list:
    events = []
    for k, v in doc.items():
        if (k.endswith("_at") or k.endswith("_date")) and isinstance(v, str):
            dt = _parse_dt(v)
            if dt:
                events.append({"event": k.removesuffix("_at").removesuffix("_date").replace("_", " "),
                               "ts": dt.isoformat(), "source": "entity"})
    eid = doc.get("id") or str(doc.get("_id"))
    async for e in db.activity_events.find({"request_id": eid}, {"_id": 0}).sort("created_at", 1).limit(15):
        actor = e.get("actor")
        events.append({"event": e.get("type") or e.get("event_type"), "ts": e.get("created_at"),
                       "actor": (actor.get("name") if isinstance(actor, dict) else None) or e.get("actor_name"),
                       "source": "events"})
    events = [e for e in events if e.get("ts") and e.get("event")]
    events.sort(key=lambda e: str(e["ts"]))
    return events[-15:]


# ---------------------------------------------------------------------------
# 7 · MENTOR SUMMARY — integrare AIB-004 (compact, determinist)
# ---------------------------------------------------------------------------
async def mentor_summary(user: dict, path: str) -> dict | None:
    st = await process_state(user, path=path)
    if not st.get("found") or st.get("status") == "automated":
        return None
    return {"process_id": st["process"]["id"], "name": st["process"]["name"],
            "entity": (st.get("entity") or {}).get("label"),
            "status": st["status"], "current_state": st.get("current_state"),
            "step_index": st.get("step_index"), "total_steps": st.get("total_steps"),
            "next": [t["to"] for t in st.get("next_actions") or []][:2],
            "who_acts": st.get("who_acts") or [], "blockers": (st.get("blockers") or [])[:2]}
