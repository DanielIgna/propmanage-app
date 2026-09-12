"""leads_store — motorul unic de lead-uri (Sprint 2 · 2.1, strangler pattern).

Colecția unificată: `leads`. Legacy-ul rămâne intact (read-only pentru module vechi);
scrierile fac dual-write prin sync_lead() — idempotent pe (source, meta.legacy_id).
Triage AI universal: score 0-100 + segment hot/warm/nurture pe toate sursele.
"""
import logging
from datetime import datetime, timezone

from db import db
from tenancy import DEFAULT_TENANT as TENANT

logger = logging.getLogger("propmanage.leads_store")

STAGE_MAP = {
    "new": "new", "contacted": "contacted", "introduced": "contacted", "scheduled": "contacted",
    "qualified": "qualified", "negotiation": "qualified",
    "converted": "won", "won": "won", "closed_won": "won",
    "lost": "lost", "closed_lost": "lost", "closed": "lost",
}
_CORE_KEYS = {"_id", "id", "name", "lead_name", "email", "lead_email", "phone", "lead_phone",
              "stage", "status", "score", "segment", "created_at", "updated_at", "created_by",
              "partner_id", "revenue_generated", "notes", "tenant_id"}


def _triage(root: dict, meta: dict) -> tuple[int, str]:
    score = 20
    if root.get("phone"):
        score += 20
    value = meta.get("estimated_value") or meta.get("budget") or root.get("revenue_generated") or 0
    try:
        if isinstance(value, str):
            value = 10000 if any(x in value.lower() for x in ("10000", "15000", "peste", ">")) else 5000
        if float(value) >= 5000:
            score += 25
        elif float(value) > 0:
            score += 15
    except (TypeError, ValueError):
        pass
    text = str(root.get("notes") or meta.get("message") or "")
    if len(text) > 60:
        score += 10
    if meta.get("company") or root.get("partner_id"):
        score += 10
    if meta.get("surface_mp") and float(meta["surface_mp"] or 0) >= 60:
        score += 10
    score = min(100, score)
    segment = "hot" if score >= 70 else "warm" if score >= 45 else "nurture"
    return score, segment


async def sync_lead(source: str, legacy_doc: dict) -> None:
    """Upsert idempotent în `leads` din orice document legacy. Nu aruncă niciodată (fire-safe)."""
    try:
        legacy_id = str(legacy_doc.get("id") or legacy_doc.get("_id") or "")
        if not legacy_id:
            return
        root = {
            "name": legacy_doc.get("lead_name") or legacy_doc.get("name") or "",
            "email": (legacy_doc.get("lead_email") or legacy_doc.get("email") or "").lower(),
            "phone": legacy_doc.get("lead_phone") or legacy_doc.get("phone") or "",
            "partner_id": str(legacy_doc["partner_id"]) if legacy_doc.get("partner_id") else None,
            "revenue_generated": legacy_doc.get("revenue_generated") or 0,
            "notes": legacy_doc.get("notes") or "",
            "created_by": legacy_doc.get("created_by"),
        }
        raw_stage = str(legacy_doc.get("stage") or legacy_doc.get("status") or "new")
        meta = {k: (str(v) if k.endswith("_id") else v) for k, v in legacy_doc.items() if k not in _CORE_KEYS}
        meta["legacy_id"] = legacy_id
        if legacy_doc.get("score") is not None:
            score, segment = legacy_doc["score"], legacy_doc.get("segment", "warm")
        else:
            score, segment = _triage(root, meta)
        existing = await db.leads.find_one({"source": source, "meta.legacy_id": legacy_id}, {"ops_stage": 1})
        stage = existing.get("ops_stage") if existing and existing.get("ops_stage") else STAGE_MAP.get(raw_stage, "new")
        await db.leads.update_one(
            {"source": source, "meta.legacy_id": legacy_id},
            {"$set": {
                **root, "source": source, "stage": stage, "stage_raw": raw_stage,
                "score": score, "segment": segment, "meta": meta,
                "tenant_id": legacy_doc.get("tenant_id") or TENANT,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, "$setOnInsert": {"created_at": legacy_doc.get("created_at") or datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[leads_store] sync fail ({source}): {e}")


LEGACY_SOURCES = {
    "city_partner": "city_partner_leads",
    "marketplace_partner": "marketplace_leads",
    "interior_design": "interior_design_leads",
    "demo": "demo_leads",
    "partner": "partner_leads",
    "franchise_application": "franchise_applications",
    "client_junior": "client_junior_requests",
    "specialist_entry": "specialist_entry_applications",
    "lead_magnet": "lead_magnet_leads",
}


async def migrate_all() -> dict:
    """Migrare idempotentă a tuturor colecțiilor legacy în `leads`."""
    out = {}
    for source, col in LEGACY_SOURCES.items():
        docs = await db[col].find({}).to_list(2000)
        for d in docs:
            await sync_lead(source, d)
        out[source] = len(docs)
    return out


async def list_leads(source: str = None, stage: str = None, segment: str = None, limit: int = 200,
                     tenant: str = None) -> list:
    q = {}
    if source:
        q["source"] = source
    if stage:
        q["stage"] = stage
    if segment:
        q["segment"] = segment
    if tenant:
        q["tenant_id"] = tenant
    return await db.leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def summary(days: int = 7, tenant: str = None) -> dict:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    match = {"created_at": {"$gte": cutoff}}
    if tenant:
        match["tenant_id"] = tenant
    pipeline = [
        {"$match": match},
        {"$group": {"_id": {"source": "$source", "segment": "$segment"}, "n": {"$sum": 1}}},
    ]
    rows = await db.leads.aggregate(pipeline).to_list(100)
    total = await db.leads.count_documents(match)
    hot = sum(r["n"] for r in rows if r["_id"]["segment"] == "hot")
    by_source = {}
    for r in rows:
        by_source[r["_id"]["source"]] = by_source.get(r["_id"]["source"], 0) + r["n"]
    return {"days": days, "total": total, "hot": hot, "by_source": by_source}
