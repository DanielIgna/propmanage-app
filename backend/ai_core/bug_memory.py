"""Bug Memory — unified, searchable view across all error sources.

Aggregates errors/findings from:
- qa_sessions.findings (manual QA Copilot)
- admin_ai_findings (AI Investigator auto-scans)
- audit_log entries flagged as errors

Provides a single search interface so when a new bug appears, the assistant
can answer "have we seen this before?" by similarity scoring.
"""
import logging
from collections import Counter

from db import db
from ai_core.memory import _tokenize, _score

logger = logging.getLogger("propmanage.ai_core.bug_memory")


async def _from_qa_sessions(query_tokens: set, limit: int) -> list[dict]:
    out = []
    cur = db.qa_sessions.find({}, {"id": 1, "title": 1, "findings": 1, "created_at": 1}).sort("created_at", -1).limit(50)
    async for s in cur:
        for f in (s.get("findings") or [])[-20:]:
            text = f.get("text", "") + " " + (f.get("ai_analysis", {}).get("summary") or "")
            toks = Counter(_tokenize(text))
            score = _score(query_tokens, toks)
            if score > 0:
                a = f.get("ai_analysis") or {}
                out.append({
                    "id": f.get("id"),
                    "source": "qa_copilot",
                    "session_id": s["id"],
                    "session_title": s.get("title"),
                    "text": f.get("text", "")[:400],
                    "summary": a.get("summary", ""),
                    "category": a.get("category", ""),
                    "severity": a.get("severity", "P2"),
                    "ts": f.get("ts"),
                    "score": round(score, 3),
                })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]


async def _from_ai_findings(query_tokens: set, limit: int) -> list[dict]:
    out = []
    cur = db.admin_ai_findings.find({}).sort("created_at", -1).limit(100)
    async for f in cur:
        text = (f.get("title", "") or "") + " " + (f.get("description", "") or "")
        toks = Counter(_tokenize(text))
        score = _score(query_tokens, toks)
        if score > 0:
            out.append({
                "id": str(f.get("_id", f.get("id", ""))),
                "source": "ai_investigator",
                "session_id": None,
                "session_title": None,
                "text": text[:400],
                "summary": f.get("title", ""),
                "category": f.get("category", ""),
                "severity": f.get("severity", "P2"),
                "ts": f.get("created_at"),
                "score": round(score, 3),
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]


async def search(query: str, limit: int = 10) -> dict:
    """Search bug memory across all sources. Returns {"items": [...], "total": int}."""
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return {"items": [], "total": 0}

    qa_results = await _from_qa_sessions(query_tokens, limit)
    ai_results = await _from_ai_findings(query_tokens, limit)

    merged = qa_results + ai_results
    merged.sort(key=lambda x: x["score"], reverse=True)
    items = merged[:limit]
    return {"items": items, "total": len(items)}


async def stats() -> dict:
    qa_total = 0
    cur = db.qa_sessions.aggregate([{"$project": {"n": {"$size": {"$ifNull": ["$findings", []]}}}}])
    async for d in cur:
        qa_total += d.get("n", 0)

    ai_total = await db.admin_ai_findings.count_documents({})
    return {
        "qa_findings": qa_total,
        "ai_investigator_findings": ai_total,
        "total": qa_total + ai_total,
    }
