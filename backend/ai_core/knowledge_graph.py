"""Knowledge Graph — read-only entity relationship view.

Builds nodes + edges from existing collections WITHOUT mutating data.
Used by the Admin AI Control Center to visualize who-knows-whom.
"""
from db import db


async def for_user(user_id: str, depth: int = 1) -> dict:
    """Return a small graph centered on a user.

    Nodes: User, Properties they own, Requests they made, Specialists assigned, Listings.
    Edges: owns, requested, assigned_to, related_to.
    """
    if not user_id:
        return {"nodes": [], "edges": []}

    from bson import ObjectId
    or_clauses = [{"id": user_id}, {"email": user_id}]
    try:
        or_clauses.insert(0, {"_id": ObjectId(user_id)})
    except Exception:
        pass
    uid_query = {"$or": or_clauses}

    user = await db.users.find_one(uid_query)
    if not user:
        return {"nodes": [], "edges": []}

    uid_str = str(user.get("_id") or user.get("id"))
    nodes = [{
        "id": f"user:{uid_str}",
        "type": "user",
        "label": user.get("name") or user.get("email", "?"),
        "meta": {"role": user.get("role"), "email": user.get("email")},
    }]
    edges = []

    # Properties owned
    async for p in db.properties.find({"owner_id": uid_str}).limit(20):
        pid = str(p.get("_id") or p.get("id"))
        nodes.append({"id": f"property:{pid}", "type": "property", "label": p.get("name") or p.get("address", "Imobil"), "meta": {"city": p.get("city")}})
        edges.append({"from": f"user:{uid_str}", "to": f"property:{pid}", "label": "owns"})

    # Requests created by user
    async for r in db.requests.find({"client_id": uid_str}).sort("created_at", -1).limit(20):
        rid = str(r.get("_id") or r.get("id"))
        nodes.append({"id": f"request:{rid}", "type": "request", "label": (r.get("title") or "Solicitare")[:60], "meta": {"status": r.get("status"), "category": r.get("category")}})
        edges.append({"from": f"user:{uid_str}", "to": f"request:{rid}", "label": "requested"})
        # Specialist assigned to this request
        if r.get("specialist_id"):
            sid = r["specialist_id"]
            nodes.append({"id": f"specialist:{sid}", "type": "specialist", "label": r.get("specialist_name") or "Specialist", "meta": {"specialty": r.get("specialist_specialty"), "city": r.get("specialist_city")}})
            edges.append({"from": f"request:{rid}", "to": f"specialist:{sid}", "label": "assigned_to"})

    # Verified Estate listings linked to user (if seller)
    async for lst in db.verified_estate_listings.find({"owner_email": user.get("email")}).limit(10):
        lid = str(lst.get("_id") or lst.get("id"))
        nodes.append({"id": f"listing:{lid}", "type": "listing", "label": (lst.get("title") or "Listing")[:60], "meta": {"status": lst.get("status"), "price": lst.get("price")}})
        edges.append({"from": f"user:{uid_str}", "to": f"listing:{lid}", "label": "owns_listing"})

    # Deduplicate nodes (defensive)
    seen = set()
    unique_nodes = []
    for n in nodes:
        if n["id"] in seen:
            continue
        seen.add(n["id"])
        unique_nodes.append(n)

    return {"nodes": unique_nodes, "edges": edges, "center_user_id": uid_str}


async def overview() -> dict:
    """High-level platform graph stats (counts of nodes/edges by type)."""
    users = await db.users.count_documents({})
    properties = await db.properties.count_documents({})
    requests = await db.requests.count_documents({})
    listings = await db.verified_estate_listings.count_documents({})
    twins = await db.digital_twin_models.count_documents({})
    memories = await db.ai_memories.count_documents({})
    return {
        "nodes": {
            "users": users,
            "properties": properties,
            "requests": requests,
            "listings": listings,
            "digital_twins": twins,
            "ai_memories": memories,
        },
    }
