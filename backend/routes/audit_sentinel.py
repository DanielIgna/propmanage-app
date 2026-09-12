"""Audit Sentinel — anomaly detector pe loguri (CAO Roadmap 2.4, PRD P0).

Detectori deterministe pe demo_activity_logs + admin_actions_log:
  rate_spike   — >200 request-uri/oră per utilizator
  error_burst  — ≥10 răspunsuri 4xx/5xx în 5 minute per utilizator
  scope_probe  — ≥5 acțiuni admin refuzate (out-of-scope)/oră per utilizator
Anomaliile sunt deduplicate per (email, tip, zi), notifică adminii in-app și
alimentează Notification Center + axa HDI din Autonomy Engine.
"""
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/audit-sentinel", tags=["audit-sentinel"])
logger = logging.getLogger("propmanage.audit_sentinel")

RATE_SPIKE_PER_HOUR = 200
ERROR_BURST_5MIN = 10
SCOPE_PROBE_PER_HOUR = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _record_anomaly(a_type: str, email: str, count: int, detail: str) -> bool:
    """Dedupe per (email, type, day). Returns True if newly created."""
    today = _now().strftime("%Y-%m-%d")
    existing = await db.audit_anomalies.find_one({"type": a_type, "email": email, "date": today})
    if existing:
        await db.audit_anomalies.update_one({"_id": existing["_id"]}, {"$set": {"count": count, "detail": detail, "updated_at": _now().isoformat()}})
        return False
    await db.audit_anomalies.insert_one({
        "id": uuid.uuid4().hex[:12], "type": a_type, "email": email, "count": count,
        "detail": detail, "severity": "high", "date": today, "resolved": False,
        "ts": _now().isoformat(),
    })
    return True


async def run_sentinel_scan() -> dict[str, Any]:
    """Scanează ultima oră de loguri. APScheduler callable + endpoint manual."""
    now = _now()
    h1 = (now - timedelta(hours=1)).isoformat()
    new_anomalies = []

    per_user: Counter = Counter()
    errors_5min: dict[str, Counter] = defaultdict(Counter)
    async for log in db.demo_activity_logs.find({"ts": {"$gte": h1}}, {"email": 1, "status_code": 1, "ts": 1}):
        email = log.get("email") or "unknown"
        per_user[email] += 1
        sc = log.get("status_code") or 0
        if sc >= 400:
            bucket = (log.get("ts") or "")[:15]  # granularitate ~10 min ISO prefix
            errors_5min[email][bucket] += 1

    for email, cnt in per_user.items():
        if cnt > RATE_SPIKE_PER_HOUR:
            if await _record_anomaly("rate_spike", email, cnt, f"{cnt} request-uri în ultima oră (prag {RATE_SPIKE_PER_HOUR})"):
                new_anomalies.append(("rate_spike", email, cnt))

    for email, buckets in errors_5min.items():
        worst = max(buckets.values()) if buckets else 0
        if worst >= ERROR_BURST_5MIN:
            if await _record_anomaly("error_burst", email, worst, f"{worst} erori 4xx/5xx în fereastră scurtă (prag {ERROR_BURST_5MIN})"):
                new_anomalies.append(("error_burst", email, worst))

    denied: Counter = Counter()
    async for log in db.admin_actions_log.find({"ts": {"$gte": h1}, "outcome": {"$in": ["denied", "blocked", "forbidden"]}}, {"user_email": 1}):
        denied[log.get("user_email") or "unknown"] += 1
    for email, cnt in denied.items():
        if cnt >= SCOPE_PROBE_PER_HOUR:
            if await _record_anomaly("scope_probe", email, cnt, f"{cnt} acțiuni admin refuzate/oră — posibilă tentativă out-of-scope"):
                new_anomalies.append(("scope_probe", email, cnt))

    if new_anomalies:
        try:
            from orchestrator.engine import notify_admins
            lines = "\n".join(f"• {t} — {e} ({c})" for t, e, c in new_anomalies[:6])
            await notify_admins(f"🛡 Audit Sentinel: {len(new_anomalies)} anomalii noi", lines, link="/admin/notification-center")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[audit-sentinel] notify fail: {e}")
        logger.warning(f"[audit-sentinel] {len(new_anomalies)} anomalii noi: {new_anomalies}")

    return {"scanned_users": len(per_user), "new_anomalies": len(new_anomalies), "ran_at": now.isoformat()}


@router.post("/scan")
async def manual_scan(_admin=Depends(require_role("admin"))):
    return await run_sentinel_scan()


@router.get("/anomalies")
async def list_anomalies(resolved: bool | None = None, limit: int = 50, _admin=Depends(require_role("admin"))):
    q: dict[str, Any] = {}
    if resolved is not None:
        q["resolved"] = resolved
    out = []
    async for a in db.audit_anomalies.find(q, {"_id": 0}).sort("ts", -1).limit(max(1, min(limit, 200))):
        out.append(a)
    return {"anomalies": out, "total": len(out)}


@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(anomaly_id: str, admin=Depends(require_role("admin"))):
    res = await db.audit_anomalies.update_one(
        {"id": anomaly_id},
        {"$set": {"resolved": True, "resolved_by": admin.get("email"), "resolved_at": _now().isoformat()}},
    )
    return {"ok": res.matched_count == 1}
