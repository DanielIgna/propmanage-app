"""KG-0 — Property Knowledge Graph, etapa 0 (Blueprint §12).

Graf LOGIC peste Mongo — nu se schimbă baza de date.
Colecție: entity_links {id, from_type, from_id, rel, to_type, to_id, metadata, created_at}
Convenție (Blueprint, regulă imediată): orice feature nou scrie legăturile pe care le creează via kg.links.link().

Tipuri de noduri: property, user (client/specialist/operator), request (work), dispute,
transaction (invoice), phase, conversation, notification.
Relații standard: owned_by, requested_by, on_property, assigned_to, disputes, pays_for, for_work.
"""
import logging
import uuid
from datetime import datetime, timezone

from db import db

logger = logging.getLogger("propmanage.kg")

RELS = ["owned_by", "requested_by", "on_property", "assigned_to", "disputes", "pays_for", "for_work",
        "has_twin_project", "has_twin_model"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id_of(doc: dict) -> str:
    return str(doc.get("id") or doc.get("_id"))


async def ensure_kg_indexes():
    await db.entity_links.create_index(
        [("from_type", 1), ("from_id", 1), ("rel", 1), ("to_type", 1), ("to_id", 1)],
        unique=True, name="uniq_link",
    )
    await db.entity_links.create_index([("from_type", 1), ("from_id", 1)], name="from_lookup")
    await db.entity_links.create_index([("to_type", 1), ("to_id", 1)], name="to_lookup")
    await db.entity_links.create_index([("rel", 1)], name="rel_lookup")


async def link(from_type: str, from_id: str, rel: str, to_type: str, to_id: str, metadata: dict = None) -> bool:
    """Upsert idempotent al unei muchii. Returnează True dacă e nouă."""
    if not (from_id and to_id):
        return False
    res = await db.entity_links.update_one(
        {"from_type": from_type, "from_id": str(from_id), "rel": rel, "to_type": to_type, "to_id": str(to_id)},
        {"$setOnInsert": {"id": uuid.uuid4().hex, "metadata": metadata or {}, "created_at": _now()}},
        upsert=True,
    )
    return res.upserted_id is not None


async def unlink(from_type: str, from_id: str, rel: str, to_type: str, to_id: str) -> int:
    res = await db.entity_links.delete_one(
        {"from_type": from_type, "from_id": str(from_id), "rel": rel, "to_type": to_type, "to_id": str(to_id)}
    )
    return res.deleted_count


async def links_of(entity_type: str, entity_id: str, rel: str = None, limit: int = 200) -> dict:
    """Toate muchiile unui nod (1-hop walk, ambele direcții)."""
    q_out = {"from_type": entity_type, "from_id": str(entity_id)}
    q_in = {"to_type": entity_type, "to_id": str(entity_id)}
    if rel:
        q_out["rel"] = rel
        q_in["rel"] = rel
    outgoing = await db.entity_links.find(q_out, {"_id": 0}).limit(limit).to_list(limit)
    incoming = await db.entity_links.find(q_in, {"_id": 0}).limit(limit).to_list(limit)
    return {"entity": {"type": entity_type, "id": str(entity_id)}, "outgoing": outgoing, "incoming": incoming}


async def kg_stats() -> dict:
    total = await db.entity_links.count_documents({})
    by_rel = []
    async for row in db.entity_links.aggregate([
        {"$group": {"_id": "$rel", "count": {"$sum": 1}}}, {"$sort": {"count": -1}},
    ]):
        by_rel.append({"rel": row["_id"], "count": row["count"]})
    node_types = set()
    async for row in db.entity_links.aggregate([
        {"$group": {"_id": {"f": "$from_type", "t": "$to_type"}}},
    ]):
        node_types.add(row["_id"]["f"])
        node_types.add(row["_id"]["t"])
    return {"total_links": total, "by_rel": by_rel, "node_types": sorted(node_types)}


async def backfill_entity_links() -> dict:
    """Idempotent — populează graful din colecțiile existente (lanțul core al ciclului de viață)."""
    await ensure_kg_indexes()
    created = {"owned_by": 0, "requested_by": 0, "on_property": 0, "assigned_to": 0, "disputes": 0, "pays_for": 0, "for_work": 0}

    async for p in db.properties.find({}, {"id": 1, "owner_id": 1}):
        if p.get("owner_id") and await link("property", _id_of(p), "owned_by", "user", p["owner_id"]):
            created["owned_by"] += 1

    async for r in db.requests.find({}, {"id": 1, "client_id": 1, "property_id": 1, "specialist_id": 1}):
        rid = _id_of(r)
        if r.get("client_id") and await link("request", rid, "requested_by", "user", r["client_id"]):
            created["requested_by"] += 1
        if r.get("property_id") and await link("request", rid, "on_property", "property", r["property_id"]):
            created["on_property"] += 1
        if r.get("specialist_id") and await link("request", rid, "assigned_to", "user", r["specialist_id"]):
            created["assigned_to"] += 1

    async for d in db.disputes.find({}, {"id": 1, "request_id": 1}):
        if d.get("request_id") and await link("dispute", _id_of(d), "disputes", "request", d["request_id"]):
            created["disputes"] += 1

    async for t in db.transactions.find({}, {"id": 1, "user_id": 1, "request_id": 1, "type": 1}):
        tid = _id_of(t)
        if t.get("user_id") and await link("transaction", tid, "pays_for", "user", t["user_id"], {"type": t.get("type")}):
            created["pays_for"] += 1
        if t.get("request_id") and await link("transaction", tid, "for_work", "request", t["request_id"]):
            created["for_work"] += 1

    total_new = sum(created.values())
    logger.info(f"[kg] backfill: {total_new} muchii noi — {created}")
    return {"created": created, "total_new": total_new, "total_links": await db.entity_links.count_documents({})}
