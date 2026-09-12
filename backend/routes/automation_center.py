"""Automation Center — reguli Dacă → Atunci create de admin, cu executor real.

3 template-uri de reguli cu parametri editabili:
  request_reminder      — cerere fără specialist >X ore → notificare in-app adminilor
  fast_response_badge   — specialist acceptă în <X minute → badge Fast Response
  client_reactivation   — client inactiv >X zile → email reactivare (queued)
Fiecare execuție e logată în automation_executions.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/automation", tags=["automation"])
logger = logging.getLogger("propmanage.automation")

RULE_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "request_reminder",
        "if_label": "Cerere fără specialist de peste {param} ore",
        "then_label": "Notifică adminii in-app cu lista cererilor blocate",
        "param_label": "ore", "param_default": 24, "param_min": 1, "param_max": 168,
        "run_interval_hours": 24,
    },
    {
        "key": "fast_response_badge",
        "if_label": "Specialist a acceptat o cerere în sub {param} minute",
        "then_label": "Acordă badge ⚡ Fast Response pe profil",
        "param_label": "minute", "param_default": 5, "param_min": 1, "param_max": 60,
        "run_interval_hours": 24,
    },
    {
        "key": "client_reactivation",
        "if_label": "Client inactiv de peste {param} zile",
        "then_label": "Programează email de reactivare (coadă)",
        "param_label": "zile", "param_default": 30, "param_min": 7, "param_max": 180,
        "run_interval_hours": 24,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _seed_rules() -> None:
    for t in RULE_TEMPLATES:
        existing = await db.automation_rules.find_one({"key": t["key"]})
        if not existing:
            await db.automation_rules.insert_one({
                **t, "enabled": False, "param": t["param_default"],
                "runs_count": 0, "last_run_at": None, "created_at": _now(),
            })


# ── Executors ─────────────────────────────────────────────────────────────────
async def _run_request_reminder(hours: int) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    stuck = []
    async for r in db.requests.find({"status": {"$in": ["open", "pending"]}, "created_at": {"$lt": cutoff}}, {"title": 1, "category": 1}).limit(50):
        stuck.append(r)
    if stuck:
        admins = await db.users.find({"role": "admin"}, {"_id": 1}).to_list(10)
        titles = ", ".join((s.get("title") or "cerere")[:40] for s in stuck[:5])
        for a in admins:
            await db.notifications.insert_one({
                "user_id": str(a["_id"]),
                "title": f"⏰ {len(stuck)} cereri blocate peste {hours}h",
                "message": f"Fără specialist asignat: {titles}{'…' if len(stuck) > 5 else ''}",
                "type": "automation", "link": "/admin/command-center",
                "read": False, "created_at": _now(),
            })
    return {"matched": len(stuck), "actions": f"{len(stuck)} cereri semnalate adminilor" if stuck else "Nicio cerere blocată"}


async def _run_fast_response_badge(minutes: int) -> dict[str, Any]:
    fast_specialists: set[str] = set()
    async for r in db.requests.find({"assigned_at": {"$nin": [None, ""]}, "specialist_id": {"$nin": [None, ""]}}, {"created_at": 1, "assigned_at": 1, "specialist_id": 1}):
        try:
            created = datetime.fromisoformat(r["created_at"])
            assigned = datetime.fromisoformat(r["assigned_at"])
            if (assigned - created).total_seconds() <= minutes * 60:
                fast_specialists.add(str(r["specialist_id"]))
        except (ValueError, TypeError, KeyError):
            continue
    awarded = 0
    from bson import ObjectId
    for sid in fast_specialists:
        try:
            res = await db.users.update_one(
                {"_id": ObjectId(sid), "fast_response_badge": {"$ne": True}},
                {"$set": {"fast_response_badge": True, "fast_response_awarded_at": _now()}},
            )
            awarded += res.modified_count
        except Exception:  # noqa: BLE001
            continue
    return {"matched": len(fast_specialists), "actions": f"{awarded} badge-uri noi acordate ({len(fast_specialists)} specialiști eligibili)"}


async def _run_client_reactivation(days: int) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    queued = 0
    async for u in db.users.find({"role": "client", "$or": [{"last_seen": {"$lt": cutoff}}, {"last_seen": None}], "created_at": {"$lt": cutoff}}, {"email": 1, "name": 1}).limit(100):
        existing = await db.automation_emails.find_one({"email": u.get("email"), "kind": "reactivation", "status": "queued"})
        if not existing:
            await db.automation_emails.insert_one({
                "email": u.get("email"), "name": u.get("name"), "kind": "reactivation",
                "status": "queued", "queued_at": _now(),
            })
            queued += 1
    return {"matched": queued, "actions": f"{queued} emailuri de reactivare adăugate în coadă"}


EXECUTORS = {
    "request_reminder": _run_request_reminder,
    "fast_response_badge": _run_fast_response_badge,
    "client_reactivation": _run_client_reactivation,
}


async def run_due_rules() -> dict[str, Any]:
    """APScheduler callable (hourly) — rulează regulile active al căror interval a expirat.
    Acesta este pasul care face Automation Center autonom (Autonomy Level 3)."""
    await _seed_rules()
    ran = []
    now = datetime.now(timezone.utc)
    async for rule in db.automation_rules.find({"enabled": True}):
        interval = rule.get("run_interval_hours", 24)
        last = rule.get("last_run_at")
        if last:
            try:
                if (now - datetime.fromisoformat(last)).total_seconds() < interval * 3600:
                    continue
            except (ValueError, TypeError):
                pass
        try:
            result = await EXECUTORS[rule["key"]](rule["param"])
        except Exception as e:  # noqa: BLE001
            logger.error(f"[automation-scheduler] {rule['key']} failed: {e}")
            continue
        await db.automation_rules.update_one({"key": rule["key"]}, {"$set": {"last_run_at": _now()}, "$inc": {"runs_count": 1}})
        await db.automation_executions.insert_one({
            "id": uuid.uuid4().hex[:12], "rule_key": rule["key"], "param": rule["param"],
            "matched": result["matched"], "actions": result["actions"],
            "run_by": "scheduler", "ran_at": _now(),
        })
        ran.append({"rule": rule["key"], **result})
    if ran:
        logger.info(f"[automation-scheduler] ran {len(ran)} rules: {[r['rule'] for r in ran]}")
    return {"ran": ran, "count": len(ran)}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/rules")
async def list_rules(_admin=Depends(require_role("admin"))):
    await _seed_rules()
    out = []
    async for r in db.automation_rules.find({}, {"_id": 0}):
        out.append(r)
    return {"rules": out}


@router.patch("/rules/{key}")
async def patch_rule(key: str, enabled: bool | None = Body(None, embed=True), param: int | None = Body(None, embed=True),
                     _admin=Depends(require_role("admin"))):
    rule = await db.automation_rules.find_one({"key": key})
    if not rule:
        raise HTTPException(404, f"Regulă necunoscută: {key}")
    patch: dict[str, Any] = {}
    if enabled is not None:
        patch["enabled"] = enabled
    if param is not None:
        patch["param"] = max(rule["param_min"], min(rule["param_max"], int(param)))
    if not patch:
        raise HTTPException(400, "Nimic de actualizat.")
    await db.automation_rules.update_one({"key": key}, {"$set": patch})
    doc = await db.automation_rules.find_one({"key": key}, {"_id": 0})
    return doc


@router.post("/rules/{key}/run")
async def run_rule(key: str, admin=Depends(require_role("admin"))):
    rule = await db.automation_rules.find_one({"key": key})
    if not rule:
        raise HTTPException(404, f"Regulă necunoscută: {key}")
    executor = EXECUTORS[key]
    result = await executor(rule["param"])
    await db.automation_rules.update_one({"key": key}, {"$set": {"last_run_at": _now()}, "$inc": {"runs_count": 1}})
    await db.automation_executions.insert_one({
        "id": uuid.uuid4().hex[:12], "rule_key": key, "param": rule["param"],
        "matched": result["matched"], "actions": result["actions"],
        "run_by": admin.get("email"), "ran_at": _now(),
    })
    return {"rule_key": key, **result}


@router.get("/executions")
async def list_executions(limit: int = 30, _admin=Depends(require_role("admin"))):
    out = []
    async for e in db.automation_executions.find({}, {"_id": 0}).sort("ran_at", -1).limit(max(1, min(limit, 100))):
        out.append(e)
    return {"executions": out}
