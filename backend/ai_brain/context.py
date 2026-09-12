"""AI Brain · Context Awareness Engine (AIB-002).

Determină automat contextul utilizatorului (rol, permisiuni efective, modul, pagină,
entitate selectată, acțiuni disponibile) pe baza Knowledge Registry din Sprint 1 —
zero liste hardcodate de rute/API-uri.

Navigation Context: db.ai_brain_navigation (evenimente per utilizator autentificat,
cu durată calculată server-side). Conversation Context: REUTILIZEAZĂ db.ai_sessions
(memoria AI unificată existentă), agent="ai_brain" — fără infrastructură paralelă.
Fără LLM în acest sprint — doar mecanica de context și continuitate.
"""
import re
import uuid
from datetime import datetime, timezone

from db import db
from ai_brain import registry

ID_RE = re.compile(r"^([0-9a-f]{24}|[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.I)

ENTITY_KEYWORDS = {
    "property": ("properties", "title"), "properties": ("properties", "title"),
    "imobil": ("properties", "title"), "imobile-verificate": ("verified_estate_listings", "title"),
    "twin": ("digital_twin_projects", "name"), "digital-twin": ("digital_twin_projects", "name"),
    "request": ("requests", "title"), "requests": ("requests", "title"),
    "cerere": ("requests", "title"), "jobs": ("requests", "title"),
    "specialist": ("users", "name"), "specialists": ("users", "name"),
    "house-health": ("twins", "property_id"), "contracts": ("service_contracts", "title"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _effective_guards(user: dict) -> set:
    role = user.get("role") or ""
    guards = {"public", "authenticated", role}
    if role in ("admin", "super_admin"):
        guards |= {"admin", "super_admin"}
    return guards


async def _match_route(path: str) -> dict | None:
    reg = await registry.get("routes", limit=1000)
    clean = (path.split("?")[0].rstrip("/") or "/")
    for r in reg["data"]:
        rp = r["path"]
        if rp == clean:
            return r
        if ":" in rp and re.match("^" + re.sub(r":[^/]+", "[^/]+", rp) + "$", clean):
            return r
    return None


async def _resolve_entity(path: str, entity_id: str | None) -> dict | None:
    from bson import ObjectId
    segs = [s for s in (path or "").split("?")[0].split("/") if s]
    candidates = []
    if entity_id:
        candidates.append((segs[0] if segs else "", entity_id))
    for i, s in enumerate(segs[1:], 1):
        if ID_RE.match(s):
            candidates.append((segs[i - 1], s))
    for keyword, eid in candidates:
        coll_name, label_field = ENTITY_KEYWORDS.get(keyword, (None, None))
        colls = [(coll_name, label_field)] if coll_name else list({v for v in ENTITY_KEYWORDS.values()})
        for cname, lfield in colls:
            queries = [{"id": eid}]
            try:
                queries.insert(0, {"_id": ObjectId(eid)})
            except Exception:  # noqa: BLE001
                pass
            for q in queries:
                doc = await db[cname].find_one(q, {lfield: 1, "title": 1, "name": 1})
                if doc:
                    label = doc.get(lfield) or doc.get("title") or doc.get("name") or eid
                    return {"type": cname, "id": eid, "label": str(label)[:80]}
    return None


async def _available_actions(user: dict, module: str) -> list:
    guards = _effective_guards(user)
    reg = await registry.get("apis", limit=1000)
    out = []
    for a in reg["data"]:
        if a["guard"] not in guards:
            continue
        seg = (a["path"].split("/") + ["", ""])[2]
        if module and seg != module and not (module == "admin" and seg == "admin"):
            continue
        out.append({"method": a["method"], "path": a["path"], "guard": a["guard"]})
        if len(out) >= 30:
            break
    return out


async def resolve_context(user: dict, path: str = "", entity_id: str = None, action: str = None) -> dict:
    role = user.get("role") or ""
    guards = _effective_guards(user)
    reg_apis = await registry.get("apis", limit=1000)
    accessible = sum(1 for a in reg_apis["data"] if a["guard"] in guards)

    segs = [s for s in (path or "").split("?")[0].split("/") if s]
    module = segs[0] if segs else "root"
    route = await _match_route(path) if path else None
    entity = await _resolve_entity(path, entity_id)

    active_property = None
    if entity and entity["type"] == "properties":
        active_property = entity
    else:
        uid = user.get("id") or str(user.get("_id", ""))
        p = await db.properties.find_one({"owner_id": uid}, {"title": 1, "id": 1}, sort=[("created_at", -1)])
        if p:
            active_property = {"type": "properties", "id": p.get("id") or str(p["_id"]), "label": str(p.get("title", ""))[:80]}

    nav = await navigation_history(user.get("id") or str(user.get("_id", "")), limit=5)
    return {
        "user": {"id": user.get("id") or str(user.get("_id", "")), "email": user.get("email"),
                 "name": user.get("name"), "role": role, "tier": user.get("tier"),
                 "experience_tier": user.get("experience_tier"), "verified": bool(user.get("verified")),
                 "zone": user.get("zone"), "active_view": user.get("active_view")},
        "organization": {"tenant_id": user.get("tenant_id")},
        "permissions": {"effective_guards": sorted(guards), "accessible_endpoints": accessible,
                        "total_endpoints": reg_apis["count"]},
        "location": {"path": path or None, "module": module,
                     "route": route, "known_route": route is not None},
        "entity": entity,
        "active_property": active_property,
        "intended_action": action,
        "available_actions": await _available_actions(user, module),
        "workflow": {"trail": [e["path"] for e in nav["events"]],
                     "current_module": module,
                     "previous_module": nav["events"][1]["module"] if len(nav["events"]) > 1 else None},
        "resolved_at": _now(),
    }


# ---------------------------------------------------------------------------
# Navigation Context
# ---------------------------------------------------------------------------
async def record_navigation(user_id: str, path: str, role: str = None) -> dict:
    now = datetime.now(timezone.utc)
    prev = await db.ai_brain_navigation.find_one({"user_id": user_id}, sort=[("ts", -1)])
    if prev and not prev.get("duration_ms"):
        try:
            delta = (now - datetime.fromisoformat(prev["ts"])).total_seconds() * 1000
            if 0 < delta < 30 * 60 * 1000:
                await db.ai_brain_navigation.update_one({"_id": prev["_id"]}, {"$set": {"duration_ms": round(delta)}})
        except Exception:  # noqa: BLE001
            pass
    segs = [s for s in path.split("?")[0].split("/") if s]
    await db.ai_brain_navigation.insert_one({
        "id": uuid.uuid4().hex, "user_id": user_id, "path": path.split("?")[0],
        "module": segs[0] if segs else "root", "role": role, "ts": now.isoformat(),
    })
    return {"recorded": True}


async def navigation_history(user_id: str, limit: int = 20) -> dict:
    events = [e async for e in db.ai_brain_navigation.find(
        {"user_id": user_id}, {"_id": 0}).sort("ts", -1).limit(limit)]
    modules: dict = {}
    for e in events:
        m = modules.setdefault(e["module"], {"module": e["module"], "visits": 0, "time_ms": 0})
        m["visits"] += 1
        m["time_ms"] += e.get("duration_ms") or 0
    return {"events": events,
            "top_modules": sorted(modules.values(), key=lambda m: -m["visits"])[:5],
            "total_events": await db.ai_brain_navigation.count_documents({"user_id": user_id})}


# ---------------------------------------------------------------------------
# Conversation Context — reutilizează db.ai_sessions (agent="ai_brain")
# ---------------------------------------------------------------------------
AGENT = "ai_brain"


async def conversation_append(user_id: str, session_id: str, role: str, content: str,
                              entities: list = None, topic: str = None) -> dict:
    now = _now()
    update = {
        "$push": {"messages": {"role": role, "content": content[:4000], "ts": now}},
        "$set": {"user_id": user_id, "updated_at": now,
                 "context.last_message": content[:200], "context.last_role": role},
        "$setOnInsert": {"created_at": now, "agent": AGENT, "session_id": session_id},
    }
    if role == "user":
        update["$set"]["context.last_question"] = content[:300]
        update["$set"]["context.topic"] = topic or content[:120]
    if entities:
        update["$addToSet"] = {"context.entities": {"$each": entities[:10]}}
    await db.ai_sessions.update_one({"agent": AGENT, "session_id": session_id, "user_id": user_id},
                                    update, upsert=True)
    return await conversation_get(user_id, session_id)


async def conversation_get(user_id: str, session_id: str) -> dict | None:
    doc = await db.ai_sessions.find_one(
        {"agent": AGENT, "session_id": session_id, "user_id": user_id}, {"_id": 0})
    if doc:
        doc["messages"] = (doc.get("messages") or [])[-50:]
    return doc


async def conversation_list(user_id: str, limit: int = 10) -> list:
    return [d async for d in db.ai_sessions.find(
        {"agent": AGENT, "user_id": user_id},
        {"_id": 0, "messages": 0}).sort("updated_at", -1).limit(limit)]
