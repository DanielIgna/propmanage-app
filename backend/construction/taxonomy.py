"""CIP-A — Construction Taxonomy service layer.

Collection: construction_taxonomy
  {id, name, slug, parent_id, depth_level (0-2), legacy_category, is_active,
   is_publicly_visible (computed by gate), specialist_count, order, source,
   created_at, updated_at}

Visibility gate (Etapa 5): un nod e vizibil public DOAR dacă e activ, toți
strămoșii sunt activi și categoria lui legacy are ≥1 specialist verificat.
"""
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.construction")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or uuid.uuid4().hex[:8]


def _node(name: str, parent_id, depth: int, legacy: str, order: int) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "slug": slugify(name),
        "parent_id": parent_id,
        "depth_level": depth,
        "legacy_category": legacy,
        "is_active": True,
        "is_publicly_visible": False,
        "specialist_count": 0,
        "order": order,
        "source": "seed",
        "created_at": _now(),
        "updated_at": _now(),
    }


async def seed_construction_taxonomy() -> dict:
    """Idempotent: seed only when the collection is empty."""
    existing = await db.construction_taxonomy.count_documents({})
    if existing > 0:
        return {"seeded": False, "nodes": existing}
    from construction.taxonomy_data import TAXONOMY
    docs = []
    for r_i, (legacy, root_name, subs) in enumerate(TAXONOMY):
        root = _node(root_name, None, 0, legacy, r_i)
        root["slug"] = legacy
        docs.append(root)
        for s_i, (sub_name, services) in enumerate(subs):
            sub = _node(sub_name, root["id"], 1, legacy, s_i)
            docs.append(sub)
            for v_i, svc in enumerate(services):
                docs.append(_node(svc, sub["id"], 2, legacy, v_i))
    await db.construction_taxonomy.insert_many([{**d} for d in docs])
    logger.info(f"[construction] taxonomy seeded: {len(docs)} nodes")
    return {"seeded": True, "nodes": len(docs)}


async def get_specialist_counts() -> dict:
    """Verified specialists count per flat category (specialty ∪ service_categories)."""
    counts: dict = {}
    async for u in db.users.find(
        {"role": "specialist", "verified": True},
        {"specialty": 1, "service_categories": 1},
    ):
        cats = set(u.get("service_categories") or [])
        if u.get("specialty"):
            cats.add(u["specialty"])
        for c in cats:
            if c:
                counts[c] = counts.get(c, 0) + 1
    return counts


async def _requests_per_category(days: int = 90) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    out = {}
    async for row in db.requests.aggregate([
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    ]):
        if row.get("_id"):
            out[row["_id"]] = row["n"]
    return out


async def refresh_category_visibility() -> dict:
    """The visibility gate. Returns summary incl. hidden-with-potential roots."""
    counts = await get_specialist_counts()
    nodes = [d async for d in db.construction_taxonomy.find({})]
    by_id = {n["id"]: n for n in nodes}

    def chain_active(n: dict) -> bool:
        cur = n
        while cur:
            if not cur.get("is_active", True):
                return False
            cur = by_id.get(cur.get("parent_id"))
        return True

    visibility_changes = 0
    visible_count = 0
    for n in nodes:
        cnt = counts.get(n.get("legacy_category") or "", 0)
        visible = chain_active(n) and cnt > 0
        if visible:
            visible_count += 1
        if visible != bool(n.get("is_publicly_visible")) or cnt != n.get("specialist_count"):
            if visible != bool(n.get("is_publicly_visible")):
                visibility_changes += 1
            await db.construction_taxonomy.update_one(
                {"id": n["id"]},
                {"$set": {"is_publicly_visible": visible, "specialist_count": cnt, "updated_at": _now()}},
            )

    # Hidden with potential: roots with 0 verified specialists but client demand (90d)
    demand = await _requests_per_category()
    hidden_with_potential = [
        {"legacy_category": n["legacy_category"], "name": n["name"],
         "requests_90d": demand.get(n["legacy_category"], 0)}
        for n in nodes
        if n.get("depth_level") == 0
        and counts.get(n.get("legacy_category") or "", 0) == 0
        and demand.get(n.get("legacy_category") or "", 0) > 0
    ]
    hidden_with_potential.sort(key=lambda x: -x["requests_90d"])

    result = {
        "total_nodes": len(nodes),
        "visible_count": visible_count,
        "hidden_count": len(nodes) - visible_count,
        "visibility_changes": visibility_changes,
        "specialist_counts": counts,
        "hidden_with_potential": hidden_with_potential,
        "ran_at": _now(),
    }
    logger.info(
        f"[construction] visibility gate: {visible_count}/{len(nodes)} vizibile, "
        f"{visibility_changes} schimbări, {len(hidden_with_potential)} ascunse cu potențial"
    )
    return result


def build_tree(nodes: list) -> list:
    """Flat nodes → nested tree (children arrays), sorted by order."""
    by_id = {n["id"]: {**n, "children": []} for n in nodes}
    roots = []
    for n in by_id.values():
        pid = n.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(n)
        else:
            roots.append(n)

    def _sort(items):
        items.sort(key=lambda x: (x.get("order", 0), x.get("name", "")))
        for it in items:
            _sort(it["children"])
    _sort(roots)
    return roots


async def construction_visibility_cron() -> None:
    """Daily 04:30 — routes the refresh through the Autonomy Orchestrator."""
    from orchestrator.engine import emit_signal
    await emit_signal("category_visibility_refresh", {"trigger": "cron_0430"})
