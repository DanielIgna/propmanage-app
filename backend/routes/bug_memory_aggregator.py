"""Bug Memory Aggregator — read-only unified view over QA + AI findings.

Phase 1.3 (P3 Quick Win). Reuses ai_core.bug_memory.search() + stats() — no
new collection, no new logic, just an HTTP wrapper + a "recent unified" feed.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from db import db
from deps import require_role
from ai_core import bug_memory as engine

logger = logging.getLogger("propmanage.bug_memory_aggregator")
router = APIRouter(prefix="/api/admin/bug-memory", tags=["bug-memory"])


@router.get("/stats")
async def get_stats(user=Depends(require_role("admin"))):
    """Lightweight stats card for admin dashboard."""
    return await engine.stats()


@router.get("/search")
async def search(q: str = Query(..., min_length=2), limit: int = 20,
                 user=Depends(require_role("admin"))):
    """Full text-style search across all bug sources."""
    return await engine.search(q, limit=limit)


def _normalize_ts(v) -> Optional[str]:
    if not v:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


@router.get("/recent")
async def recent_unified(limit: int = 30, severity: Optional[str] = None,
                         source: Optional[str] = None,
                         user=Depends(require_role("admin"))):
    """Return most recent findings from BOTH sources, sorted by date.

    No query needed — useful for "what bugs have we seen lately?" overview.
    Filters: severity (P0/P1/P2/P3), source (qa_copilot/ai_investigator).
    """
    items = []

    # QA sessions findings
    if source in (None, "qa_copilot"):
        cur = db.qa_sessions.find({}, {
            "id": 1, "title": 1, "findings": 1, "created_at": 1,
        }).sort("created_at", -1).limit(40)
        async for s in cur:
            for f in (s.get("findings") or []):
                a = f.get("ai_analysis") or {}
                sev = a.get("severity", "P2")
                if severity and sev != severity:
                    continue
                items.append({
                    "id": f.get("id"),
                    "source": "qa_copilot",
                    "session_id": s["id"],
                    "session_title": s.get("title"),
                    "text": (f.get("text") or "")[:300],
                    "summary": a.get("summary", ""),
                    "category": a.get("category", ""),
                    "severity": sev,
                    "ts": _normalize_ts(f.get("ts") or s.get("created_at")),
                })

    # AI investigator findings
    if source in (None, "ai_investigator"):
        cur = db.admin_ai_findings.find({}).sort("created_at", -1).limit(80)
        async for f in cur:
            sev = f.get("severity", "P2")
            if severity and sev != severity:
                continue
            items.append({
                "id": str(f.get("_id", f.get("id", ""))),
                "source": "ai_investigator",
                "session_id": None,
                "session_title": None,
                "text": (f.get("description") or "")[:300],
                "summary": f.get("title", ""),
                "category": f.get("category", ""),
                "severity": sev,
                "ts": _normalize_ts(f.get("created_at")),
            })

    items.sort(key=lambda x: x["ts"] or "", reverse=True)
    items = items[:limit]

    # Aggregate stats for this view
    by_severity: dict = {}
    by_source: dict = {}
    for i in items:
        by_severity[i["severity"]] = by_severity.get(i["severity"], 0) + 1
        by_source[i["source"]] = by_source.get(i["source"], 0) + 1

    return {
        "items": items,
        "count": len(items),
        "by_severity": by_severity,
        "by_source": by_source,
    }
