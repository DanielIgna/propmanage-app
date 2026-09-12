"""Beta War Room — Issue Prioritization Board (bug-uri + cereri de features din beta).

Workflow: new -> triaged -> in_progress -> fixed -> shipped | wont_fix.
Severitate: P0 (blocant beta) / P1 (major) / P2 (minor) / P3 (nice-to-have).
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

router = APIRouter(prefix="/api", tags=["beta_issues"])

TYPES = {"bug", "feature", "feedback"}
SEVERITIES = {"P0", "P1", "P2", "P3"}
STATUSES = {"new", "triaged", "in_progress", "fixed", "shipped", "wont_fix"}
SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/admin/beta/issues")
async def create_issue(body: dict = Body(...), admin: dict = Depends(require_role("admin"))):
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "Titlul este obligatoriu")
    itype = body.get("type") or "bug"
    severity = body.get("severity") or "P2"
    if itype not in TYPES:
        raise HTTPException(400, f"Tip invalid (permise: {sorted(TYPES)})")
    if severity not in SEVERITIES:
        raise HTTPException(400, f"Severitate invalidă (permise: {sorted(SEVERITIES)})")
    doc = {
        "id": uuid4().hex[:12],
        "title": title[:200],
        "description": (body.get("description") or "").strip()[:2000],
        "type": itype,
        "severity": severity,
        "status": "new",
        "source": (body.get("source") or "manual").strip()[:100],
        "reporter_email": (body.get("reporter_email") or "").strip()[:120],
        "notes": "",
        "created_by": admin.get("email"),
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.beta_issues.insert_one(dict(doc))
    return {"ok": True, "issue": doc}


@router.get("/admin/beta/issues")
async def list_issues(status: str = "", type: str = "", admin: dict = Depends(require_role("admin"))):
    q = {}
    if status and status in STATUSES:
        q["status"] = status
    if type and type in TYPES:
        q["type"] = type
    items = await db.beta_issues.find(q, {"_id": 0}).to_list(1000)
    items.sort(key=lambda i: (SEV_ORDER.get(i.get("severity"), 9), i.get("created_at", "")), reverse=False)
    all_items = items if not q else await db.beta_issues.find({}, {"_id": 0, "status": 1, "severity": 1}).to_list(2000)
    open_statuses = {"new", "triaged", "in_progress"}
    counts = {
        "total": len(all_items),
        "open": sum(1 for i in all_items if i.get("status") in open_statuses),
        "open_p0": sum(1 for i in all_items if i.get("status") in open_statuses and i.get("severity") == "P0"),
        "open_p1": sum(1 for i in all_items if i.get("status") in open_statuses and i.get("severity") == "P1"),
        "fixed": sum(1 for i in all_items if i.get("status") in {"fixed", "shipped"}),
    }
    return {"items": items, "counts": counts}


@router.patch("/admin/beta/issues/{issue_id}")
async def update_issue(issue_id: str, body: dict = Body(...), admin: dict = Depends(require_role("admin"))):
    updates = {}
    if "status" in body:
        if body["status"] not in STATUSES:
            raise HTTPException(400, f"Status invalid (permise: {sorted(STATUSES)})")
        updates["status"] = body["status"]
    if "severity" in body:
        if body["severity"] not in SEVERITIES:
            raise HTTPException(400, f"Severitate invalidă (permise: {sorted(SEVERITIES)})")
        updates["severity"] = body["severity"]
    if "notes" in body:
        updates["notes"] = str(body["notes"]).strip()[:2000]
    if "title" in body and str(body["title"]).strip():
        updates["title"] = str(body["title"]).strip()[:200]
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    updates["updated_at"] = _now()
    updates["updated_by"] = admin.get("email")
    res = await db.beta_issues.update_one({"id": issue_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(404, "Issue inexistent")
    doc = await db.beta_issues.find_one({"id": issue_id}, {"_id": 0})
    return {"ok": True, "issue": doc}
