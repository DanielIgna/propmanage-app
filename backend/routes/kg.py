"""KG REST API (admin) — entity_links (KG-0) + Entity Registry & Governance (KG-1, Sprint 4)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_role
from kg.links import backfill_entity_links, kg_stats, links_of
from kg.registry import governance_report, list_registry, registered_types, seed_registry

router = APIRouter(prefix="/api/admin/kg", tags=["knowledge-graph"])


@router.get("/stats")
async def get_kg_stats(user=Depends(require_role("admin"))):
    return await kg_stats()


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_links(entity_type: str, entity_id: str, rel: str = None, user=Depends(require_role("admin"))):
    if entity_type not in await registered_types():
        raise HTTPException(400, f"Tip de nod neînregistrat: {entity_type} — declară-l în kg_entity_registry (regula G1)")
    return await links_of(entity_type, entity_id, rel)


@router.post("/backfill")
async def run_backfill(user=Depends(require_role("admin"))):
    return await backfill_entity_links()


# ── KG-1: Entity Registry & Governance (Sprint 4) ────────────────────────────
class EntityPatch(BaseModel):
    label_ro: str | None = None
    status: str | None = None
    rels_out: list[str] | None = None


@router.get("/registry")
async def get_registry(counts: bool = True, user=Depends(require_role("admin"))):
    items = await list_registry(with_counts=counts)
    return {"items": items, "total": len(items)}


@router.post("/registry/seed")
async def reseed_registry(user=Depends(require_role("admin"))):
    return await seed_registry()


@router.patch("/registry/{entity_type}")
async def patch_entity(entity_type: str, body: EntityPatch, user=Depends(require_role("admin"))):
    updates = body.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in ("active", "deprecated"):
        raise HTTPException(400, "Status permis: active | deprecated")
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    from datetime import datetime, timezone
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await db.kg_entity_registry.update_one({"entity_type": entity_type}, {"$set": updates})
    if not r.matched_count:
        raise HTTPException(404, "Entitate neînregistrată")
    return await db.kg_entity_registry.find_one({"entity_type": entity_type}, {"_id": 0})


@router.get("/governance")
async def get_governance(user=Depends(require_role("admin"))):
    return await governance_report()
