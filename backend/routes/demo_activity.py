"""Demo Activity Log — track everything demo sub-admins do on the platform.

Middleware logs every authenticated API request made by users with
`is_demo_sub_admin=True`, capturing:
  - timestamp, email, name, scope
  - method, path, status_code, response_time_ms
  - friendly action label (e.g., "Listă campanii marketing")

Async fire-and-forget to avoid impacting response latency.

Endpoints (super_admin only):
  GET /api/admin/demo-activity                  — recent logs (filters: email, days, q)
  GET /api/admin/demo-activity/summary          — per-user aggregate (totals, top pages)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.demo_activity")
router = APIRouter(prefix="/api/admin/demo-activity", tags=["admin-demo-activity"])

# Map common URL patterns → friendly Romanian labels for the activity feed.
ACTION_LABELS = [
    (r"/api/admin/marketing/dashboard", "Vizualizat Marketing Dashboard"),
    (r"/api/admin/marketing/insights", "Generat AI Insights"),
    (r"/api/admin/marketing/recommendations", "Generat AI Recommendations"),
    (r"/api/admin/marketing/copilot", "Conversație Marketing Copilot"),
    (r"/api/admin/marketing/segments", "Vizualizat Segments"),
    (r"/api/admin/marketing/forecast", "Vizualizat Forecast"),
    (r"/api/admin/marketing/growth", "Vizualizat Growth"),
    (r"/api/admin/marketing/future-ideas", "Vizualizat Idei viitoare"),
    (r"/api/admin/marketing/campaigns/generate", "Generat Campanie AI"),
    (r"/api/admin/marketing/campaigns/", "Acces Detaliu Campanie"),
    (r"/api/admin/marketing/campaigns", "Listă Campanii"),
    (r"/api/admin/marketing/auto-triggers/scan", "Rulare Auto-Trigger Scan"),
    (r"/api/admin/marketing/performance/summary", "Vizualizat Performance Summary"),
    (r"/api/admin/marketing/performance/learnings", "Acces Learnings"),
    (r"/api/admin/strategic-partners/dashboard", "Strategic Partners Dashboard"),
    (r"/api/admin/strategic-partners/cross-ref", "Cross-Reference AI"),
    (r"/api/admin/city-partners", "City Partners"),
    (r"/api/admin/marketplace-partners", "Marketplace Partners"),
    (r"/api/admin/it-collaborators", "IT Hub"),
    (r"/api/admin/legal", "Legal Audit"),
    (r"/api/admin/demo-accounts", "Demo Accounts (admin)"),
    (r"/api/admin/admin-accounts", "Admin Accounts (admin)"),
    (r"/api/admin/users", "Listă utilizatori"),
    (r"/api/admin/properties", "Listă proprietăți"),
    (r"/api/admin/requests", "Listă cereri"),
    (r"/api/auth/login", "Autentificare"),
    (r"/api/auth/logout", "Delogare"),
]


def _friendly_label(path: str) -> str:
    for pattern, label in ACTION_LABELS:
        if path.startswith(pattern):
            return label
    if path.startswith("/api/admin/"):
        return "Admin · " + path.replace("/api/admin/", "")[:60]
    return "API · " + path[:60]


async def _log_demo_activity(user: dict, request: Request, status_code: int, duration_ms: int) -> None:
    """Insert one log row. Best-effort; failures swallowed."""
    try:
        await db.demo_activity_logs.insert_one({
            "email": user.get("email"),
            "name": user.get("name") or "—",
            "scope": user.get("admin_scope") or "—",
            "role": user.get("role") or "—",
            "method": request.method,
            "path": request.url.path,
            "label": _friendly_label(request.url.path),
            "status_code": status_code,
            "duration_ms": duration_ms,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "")[:200],
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[demo_activity] log failed: {e}")


def schedule_log(user: dict, request: Request, status_code: int, duration_ms: int) -> None:
    """Fire-and-forget. Used by middleware."""
    if not user or not user.get("is_demo_sub_admin"):
        return
    # Skip noisy endpoints
    p = request.url.path
    if p in {"/api/auth/me", "/api/health", "/api/_health"} or p.startswith("/api/admin/demo-activity"):
        return
    try:
        asyncio.create_task(_log_demo_activity(user, request, status_code, duration_ms))
    except RuntimeError:
        # No running loop — skip silently
        pass


# ---------- Endpoints ----------

@router.get("")
async def list_activity(
    email: Optional[str] = None,
    days: int = 7,
    q: Optional[str] = None,
    limit: int = 200,
    user=Depends(get_current_user),
):
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin.")
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))).isoformat()
    query = {"ts": {"$gte": since}}
    if email:
        query["email"] = email
    if q:
        query["$or"] = [
            {"label": {"$regex": q, "$options": "i"}},
            {"path": {"$regex": q, "$options": "i"}},
        ]
    cur = db.demo_activity_logs.find(query).sort("ts", -1).limit(min(limit, 500))
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "count": len(items), "since": since}


@router.get("/summary")
async def activity_summary(days: int = 7, user=Depends(get_current_user)):
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin.")
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))).isoformat()

    # Per-user aggregate
    pipe = [
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {
            "_id": "$email",
            "name": {"$first": "$name"},
            "scope": {"$first": "$scope"},
            "total_actions": {"$sum": 1},
            "errors": {"$sum": {"$cond": [{"$gte": ["$status_code", 400]}, 1, 0]}},
            "last_seen": {"$max": "$ts"},
            "labels": {"$push": "$label"},
        }},
        {"$sort": {"total_actions": -1}},
    ]
    users = []
    async for r in db.demo_activity_logs.aggregate(pipe):
        # Top 5 labels for this user
        from collections import Counter
        top_labels = Counter(r.get("labels") or []).most_common(5)
        users.append({
            "email": r["_id"],
            "name": r.get("name"),
            "scope": r.get("scope"),
            "total_actions": r["total_actions"],
            "errors": r["errors"],
            "last_seen": r.get("last_seen"),
            "top_pages": [{"label": l, "count": c} for l, c in top_labels],
        })

    # Global top pages
    pipe2 = [
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {"_id": "$label", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 12},
    ]
    global_top = [{"label": r["_id"], "count": r["n"]} async for r in db.demo_activity_logs.aggregate(pipe2)]

    total_logs = await db.demo_activity_logs.count_documents({"ts": {"$gte": since}})

    return {
        "since": since,
        "days": days,
        "total_actions": total_logs,
        "users": users,
        "global_top_pages": global_top,
    }
