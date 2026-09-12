"""AI Brain · Knowledge Intelligence Engine (AIB-005).

Construiește AUTOMAT graful de cunoaștere al ecosistemului din Discovery/Registry —
zero relații hardcodate. Noduri: module, route, component, api, service, role, entity
(colecții Mongo), process (playbook-uri orchestrator). Muchii derivate din codul real:
  route→component (registry), route→module, route→route (linkuri de ieșire din sursă),
  component→api (apeluri /api/... din sursă), api→module, api→role (guard),
  api→service (fișierul care-l definește), service→entity (db.X din sursă),
  signal→process (orchestrator PLAYBOOKS).
Motoare: Dependency (cine folosește/de cine depinde), Impact (BFS pe muchii inverse),
Cross Navigation (module conexe ponderate), Explain Relationships (LLM ancorat pe graf).
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from db import db
from ai_brain import registry

FRONTEND_SRC = Path("/app/frontend/src")
BACKEND_DIR = Path("/app/backend")

API_CALL_RE = re.compile(r"[\"'`](/api/[a-zA-Z0-9\-_/]+)")
LINK_RE = re.compile(r'\bto="(/[^"]+)"')
DB_USE_RE = re.compile(r"\bdb\.([a-z_][a-z0-9_]*)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _nid(kind: str, key: str) -> str:
    return f"{kind}:{key}"


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
async def build_graph() -> dict:
    routes = (await registry.get("routes", limit=1000))["data"]
    apis = (await registry.get("apis", limit=3000))["data"]
    pages = (await registry.get("pages", limit=1000))["data"]
    page_file = {p["name"]: p["file"] for p in pages}

    nodes: dict = {}
    edges: dict = {}

    def add_node(kind, key, label=None, **meta):
        nid = _nid(kind, key)
        if nid not in nodes:
            nodes[nid] = {"id": nid, "kind": kind, "label": label or key, **({"meta": meta} if meta else {})}
        return nid

    def add_edge(src, dst, rel):
        k = (src, dst, rel)
        edges[k] = edges.get(k, 0) + 1

    # Route → component/module + cross-links + component → api
    route_patterns = []
    for r in routes:
        rid = add_node("route", r["path"])
        seg = (r["path"].split("/") + [""])[1] or "root"
        add_edge(rid, add_node("module", seg), "in_module")
        cid = add_node("component", r["component"])
        add_edge(rid, cid, "renders")
        route_patterns.append((r["path"], re.compile("^" + re.sub(r":[^/]+", "[^/]+", r["path"]) + "/?$") if ":" in r["path"] else None, rid))

    def match_route(path):
        clean = path.split("?")[0].rstrip("/") or "/"
        for rp, rx, rid in route_patterns:
            if rp == clean or (rx and rx.match(clean)):
                return rid
        return None

    api_paths = [(a, a["path"]) for a in apis]
    for r in routes:
        f = page_file.get(r["component"])
        if not f:
            continue
        src = _read(FRONTEND_SRC / f)
        cid = _nid("component", r["component"])
        for link in set(LINK_RE.findall(src)):
            if "${" in link:
                continue
            tid = match_route(link)
            if tid and tid != _nid("route", r["path"]):
                add_edge(_nid("route", r["path"]), tid, "links_to")
        called = set(API_CALL_RE.findall(src))
        for cp in called:
            for a, ap in api_paths:
                base = ap.split("{")[0].rstrip("/")
                if base and (cp == base or cp.startswith(base + "/") or base.startswith(cp)):
                    add_edge(cid, add_node("api", f"{a['method']} {ap}", meta_skip=True), "calls")
                    break

    # API → module/role/service; service → entity
    for a in apis:
        aid = add_node("api", f"{a['method']} {a['path']}")
        seg = (a["path"].split("/") + ["", ""])[2] or "root"
        add_edge(aid, add_node("module", seg), "in_module")
        add_edge(aid, add_node("role", a["guard"]), "requires_role")
        sid = add_node("service", a["file"].replace(".py", ""))
        add_edge(aid, sid, "defined_in")

    for f in (BACKEND_DIR / "routes").glob("*.py"):
        sid = _nid("service", f.stem)
        if sid not in nodes:
            continue
        for coll in set(DB_USE_RE.findall(_read(f))):
            add_edge(sid, add_node("entity", coll), "touches")

    # Orchestrator processes (playbooks reale)
    pb_src = _read(BACKEND_DIR / "orchestrator" / "playbooks.py")
    for m in re.finditer(r'"(\w+)":\s*\{\s*"id":\s*"(\w+)",\s*"name":\s*"([^"]+)"', pb_src):
        signal, pid, name = m.groups()
        prid = add_node("process", pid, label=name)
        add_edge(add_node("signal", signal), prid, "triggers")
    for coll in set(DB_USE_RE.findall(_read(BACKEND_DIR / "orchestrator" / "engine.py"))):
        add_edge(add_node("service", "orchestrator/engine"), add_node("entity", coll), "touches")

    await db.ai_brain_graph_nodes.delete_many({})
    await db.ai_brain_graph_edges.delete_many({})
    if nodes:
        await db.ai_brain_graph_nodes.insert_many([dict(n) for n in nodes.values()])
        await db.ai_brain_graph_nodes.create_index("id")
    if edges:
        await db.ai_brain_graph_edges.insert_many(
            [{"source": s, "target": t, "rel": rel, "weight": w} for (s, t, rel), w in edges.items()])
        await db.ai_brain_graph_edges.create_index("source")
        await db.ai_brain_graph_edges.create_index("target")

    by_kind = {}
    for n in nodes.values():
        by_kind[n["kind"]] = by_kind.get(n["kind"], 0) + 1
    result = {"built_at": _now(), "nodes": len(nodes), "edges": len(edges), "by_kind": by_kind}
    await db.ai_brain_graph_meta.update_one({"_id": "meta"}, {"$set": result}, upsert=True)
    return result


# ---------------------------------------------------------------------------
# QUERIES — Dependency / Impact / Cross Navigation
# ---------------------------------------------------------------------------
async def overview() -> dict:
    meta = await db.ai_brain_graph_meta.find_one({"_id": "meta"}, {"_id": 0}) or {}
    rels = {}
    async for d in db.ai_brain_graph_edges.aggregate([{"$group": {"_id": "$rel", "n": {"$sum": 1}}}]):
        rels[d["_id"]] = d["n"]
    return {**meta, "by_rel": rels}


async def search_nodes(q: str = "", kind: str = "", limit: int = 30) -> list:
    query = {}
    if kind:
        query["kind"] = kind
    if q:
        query["$or"] = [{"id": {"$regex": re.escape(q), "$options": "i"}},
                        {"label": {"$regex": re.escape(q), "$options": "i"}}]
    return [n async for n in db.ai_brain_graph_nodes.find(query, {"_id": 0}).limit(limit)]


async def node_detail(node_id: str) -> dict:
    node = await db.ai_brain_graph_nodes.find_one({"id": node_id}, {"_id": 0})
    if not node:
        return {"node": None}
    outgoing = [e async for e in db.ai_brain_graph_edges.find({"source": node_id}, {"_id": 0}).limit(80)]
    incoming = [e async for e in db.ai_brain_graph_edges.find({"target": node_id}, {"_id": 0}).limit(80)]
    return {"node": node,
            "depends_on": outgoing,      # Dependency Engine: de cine depinde
            "used_by": incoming,          # cine îl folosește
            "degree": {"out": len(outgoing), "in": len(incoming)}}


async def impact(node_id: str, depth: int = 2) -> dict:
    """Impact Engine: dacă modifici acest nod, ce e afectat (BFS pe muchii inverse)."""
    affected, frontier, seen = [], {node_id}, {node_id}
    for level in range(1, depth + 1):
        nxt = set()
        async for e in db.ai_brain_graph_edges.find({"target": {"$in": list(frontier)}}, {"_id": 0}):
            if e["source"] not in seen:
                seen.add(e["source"])
                nxt.add(e["source"])
                affected.append({"id": e["source"], "via": e["rel"], "level": level})
        frontier = nxt
        if not frontier or len(affected) > 120:
            break
    by_kind = {}
    for a in affected:
        k = a["id"].split(":")[0]
        by_kind.setdefault(k, []).append(a["id"])
    return {"node": node_id, "total_affected": len(affected),
            "by_kind": {k: v[:20] for k, v in by_kind.items()}, "affected": affected[:120]}


async def related_modules(module: str, limit: int = 6, exclude_hubs: bool = True) -> list:
    """Cross Navigation: module conexe, ponderate după numărul de legături reale."""
    HUBS = {"module:admin", "module:auth", "module:public", "module:me", "module:root"}
    mid = _nid("module", module)
    scores: dict = {}
    # 1) rute din modul care leagă spre rute din alte module
    route_ids = [e["source"] async for e in db.ai_brain_graph_edges.find(
        {"target": mid, "rel": "in_module", "source": {"$regex": "^route:"}}, {"source": 1})]
    async for e in db.ai_brain_graph_edges.find({"source": {"$in": route_ids}, "rel": "links_to"}, {"_id": 0}):
        async for m in db.ai_brain_graph_edges.find({"source": e["target"], "rel": "in_module"}, {"target": 1}):
            if m["target"] != mid:
                scores[m["target"]] = scores.get(m["target"], 0) + 2
    # 2) entități partajate: servicii din modul ating aceleași colecții ca alte module
    api_ids = [e["source"] async for e in db.ai_brain_graph_edges.find(
        {"target": mid, "rel": "in_module", "source": {"$regex": "^api:"}}, {"source": 1}).limit(200)]
    svc_ids = {e["target"] async for e in db.ai_brain_graph_edges.find(
        {"source": {"$in": api_ids}, "rel": "defined_in"}, {"target": 1})}
    ent_ids = {e["target"] async for e in db.ai_brain_graph_edges.find(
        {"source": {"$in": list(svc_ids)}, "rel": "touches"}, {"target": 1})}
    other_svcs = {e["source"] async for e in db.ai_brain_graph_edges.find(
        {"target": {"$in": list(ent_ids)}, "rel": "touches"}, {"source": 1})} - svc_ids
    async for e in db.ai_brain_graph_edges.find(
            {"target": {"$in": list(other_svcs)}, "rel": "defined_in"}, {"source": 1}).limit(400):
        async for m in db.ai_brain_graph_edges.find({"source": e["source"], "rel": "in_module"}, {"target": 1}):
            if m["target"] != mid:
                scores[m["target"]] = scores.get(m["target"], 0) + 1
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if exclude_hubs:
        ranked = [(k, v) for k, v in ranked if k not in HUBS]
    return [{"module": k.split(":", 1)[1], "strength": v} for k, v in ranked[:limit]]


# ---------------------------------------------------------------------------
# Explain Relationships — LLM ancorat EXCLUSIV pe graf
# ---------------------------------------------------------------------------
async def explain_relationship(user: dict, question: str) -> dict:
    ql = question.lower()
    matched = [n async for n in db.ai_brain_graph_nodes.find(
        {"kind": {"$in": ["module", "entity", "service", "process"]}}, {"_id": 0})]
    hits = [n for n in matched if n["label"].lower().replace("_", " ") in ql
            or n["label"].lower().replace("-", " ") in ql
            or n["label"].lower() in ql.replace(" ", "-") or n["label"].lower() in ql.replace(" ", "_")]
    hits = hits[:4] or [n for n in matched if n["kind"] == "module"][:2]

    grounding = []
    for n in hits:
        d = await node_detail(n["id"])
        rel = await related_modules(n["label"], limit=4) if n["kind"] == "module" else []
        grounding.append({"node": n, "used_by": d["used_by"][:12], "depends_on": d["depends_on"][:12],
                          "related_modules": rel})
    role = user.get("role") or ""
    key = hashlib.sha1(f"rel|{role}|{question.strip().lower()[:120]}".encode(), usedforsecurity=False).hexdigest()
    cached = await db.ai_brain_explanations.find_one({"key": key}, {"_id": 0})
    if cached:
        await db.ai_brain_explanations.update_one({"key": key}, {"$inc": {"hits": 1}})
        return {"explanation": cached["text"], "cached": True, "matched_nodes": [n["id"] for n in hits]}

    from ai_core.provider import call_llm
    from ai_brain.explain import SYSTEM_PROMPT
    user_msg = (
        f"Întrebarea utilizatorului (rol: {role}): «{question}»\n"
        "Explică RELAȚIILE dintre elementele ecosistemului PropManage, folosind EXCLUSIV muchiile "
        "din graful de mai jos (used_by = cine îl folosește, depends_on = de cine depinde, "
        "related_modules = module conexe cu pondere). Structură (Markdown, română):\n"
        "## De ce există\n## Cu ce e conectat (relații concrete din graf)\n## Ce s-ar strica fără el\n"
        "## Unde mergi mai departe\n\n"
        f"GRAF REAL:\n{grounding}"
    )
    res = await call_llm(SYSTEM_PROMPT, user_msg, session_id=f"rel-{key[:12]}")
    if res.get("error") or not res.get("text"):
        lines = [f"## Conexiuni pentru {n['label']}" + "\n" + "\n".join(
            f"- {e['rel']}: {e['source'] if e['target'] == n['id'] else e['target']}"
            for e in (grounding[i]["used_by"] + grounding[i]["depends_on"])[:8])
            for i, n in enumerate(hits)]
        return {"explanation": "\n\n".join(lines), "cached": False, "model": "fallback",
                "matched_nodes": [n["id"] for n in hits]}
    await db.ai_brain_explanations.update_one(
        {"key": key},
        {"$set": {"key": key, "kind": "relationship", "role": role, "text": res["text"],
                  "model": res.get("model", ""), "created_at": _now()}, "$setOnInsert": {"hits": 0}},
        upsert=True)
    return {"explanation": res["text"], "cached": False, "model": res.get("model"),
            "matched_nodes": [n["id"] for n in hits]}
