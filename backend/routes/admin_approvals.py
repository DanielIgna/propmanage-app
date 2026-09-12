"""Admin Approval Workflow (Milestone 3 — Feb 22 2026).

A senior admin can directly perform any action allowed by their scope.
A junior admin's destructive/major actions are converted to a pending
``admin_approval`` row that a senior (within the same scope) or the super
admin can approve or reject.

Collection: ``admin_approvals``
  {
    id, action, payload, scope, requested_by, requested_by_email,
    status: "pending"|"approved"|"rejected"|"executed"|"failed",
    review_required_from: ["senior", "super"],
    created_at, decided_at, decided_by, decided_by_email,
    decision_note, execution_result,
  }

Helper API:
  - ``maybe_require_approval(user, action, payload, scope, executor)`` —
    if user is junior in a non-general scope, persist a pending approval row
    and return ``{"approval_required": True, "approval_id": ...}``.
    Otherwise (senior / super) invoke ``executor(payload, user)`` directly.

Endpoints (super admin OR senior in same scope):
  GET    /api/admin/approvals?status=pending
  POST   /api/admin/approvals/{id}/approve
  POST   /api/admin/approvals/{id}/reject
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Any

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.approvals")
router = APIRouter(prefix="/api/admin/approvals", tags=["admin-approvals"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def maybe_require_approval(
    user: dict,
    action: str,
    payload: dict,
    scope: str,
    executor: Callable[[dict, dict], Awaitable[Any]],
) -> dict:
    """Gate a major action through approval if the caller is a junior.

    - Super-admin (scope=general) → execute immediately.
    - Senior in matching scope or "general" → execute immediately.
    - Junior in matching scope → persist pending approval, return placeholder.
    """
    user_scope = (user.get("admin_scope") or "general").lower()
    seniority = (user.get("admin_seniority") or "senior").lower()
    # Super admin or anyone marked senior → run directly
    if user_scope == "general" or seniority == "senior":
        result = await executor(payload, user)
        return {"approval_required": False, "result": result}

    # Junior → require approval
    approval_id = str(uuid.uuid4())
    doc = {
        "id": approval_id,
        "action": action,
        "payload": payload,
        "scope": scope,
        "requested_by": user.get("id"),
        "requested_by_email": user.get("email"),
        "requested_by_seniority": seniority,
        "status": "pending",
        "created_at": _now_iso(),
    }
    await db.admin_approvals.insert_one(doc)
    # Best-effort notify reviewers (seniors in the scope + super admins)
    try:
        from services import notify
        async for reviewer in db.users.find({
            "role": "admin",
            "$or": [
                {"admin_scope": "general"},
                {"admin_scope": scope, "admin_seniority": "senior"},
            ],
            "is_active": {"$ne": False},
        }):
            rid = str(reviewer.get("_id"))
            if rid == user.get("id"):
                continue
            try:
                await notify(
                    rid,
                    f"⚠️ Cerere aprobare: {action}",
                    f"{user.get('email')} ({seniority} {scope}) așteaptă aprobare pentru {action}.",
                    type_="admin_approval",
                    link="/admin/approvals",
                )
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[approvals] notify reviewers failed: {e}")
    return {"approval_required": True, "approval_id": approval_id, "status": "pending"}


# ---- Internal executors registry ----
# action_name -> async (payload, decider_user) -> result
_EXECUTORS: dict[str, Callable[[dict, dict], Awaitable[Any]]] = {}


def register_action(name: str):
    def deco(fn):
        _EXECUTORS[name] = fn
        return fn
    return deco


# Default executor for actions whose handler is registered elsewhere.
async def _exec_registered(action: str, payload: dict, decider: dict) -> dict:
    fn = _EXECUTORS.get(action)
    if fn is None:
        raise HTTPException(500, f"No executor registered for action '{action}'")
    return await fn(payload, decider)


# ---- ENDPOINTS ----
def _can_review(user: dict, approval: dict) -> bool:
    if is_super_admin(user):
        return True
    seniority = (user.get("admin_seniority") or "junior").lower()
    user_scope = (user.get("admin_scope") or "general").lower()
    if seniority == "senior" and user_scope == approval.get("scope"):
        return True
    return False


@router.get("")
async def list_approvals(
    status: str = "pending",
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """List approvals visible to the caller.

    Super-admin → all. Senior in scope → only their scope. Junior → only their
    own requests.
    """
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    q: dict = {}
    if status and status != "all":
        q["status"] = status
    if not is_super_admin(user):
        seniority = (user.get("admin_seniority") or "junior").lower()
        scope = (user.get("admin_scope") or "general").lower()
        if seniority == "senior":
            q["$or"] = [{"scope": scope}, {"requested_by": user["id"]}]
        else:
            q["requested_by"] = user["id"]
    limit = max(1, min(int(limit), 500))
    cursor = db.admin_approvals.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = [d async for d in cursor]
    return {"items": items, "count": len(items)}


@router.post("/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    approval = await db.admin_approvals.find_one({"id": approval_id})
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval.get("status") != "pending":
        raise HTTPException(400, f"Approval is already {approval.get('status')}")
    if not _can_review(user, approval):
        raise HTTPException(403, "Nu ai dreptul să aprobi această cerere.")

    # Execute the action
    exec_result: Any = None
    exec_status = "executed"
    exec_error: Optional[str] = None
    try:
        exec_result = await _exec_registered(approval["action"], approval.get("payload") or {}, user)
    except HTTPException as e:
        exec_status = "failed"
        exec_error = f"HTTP {e.status_code}: {e.detail}"
    except Exception as e:  # noqa: BLE001
        exec_status = "failed"
        exec_error = str(e)[:300]

    update = {
        "status": "approved" if exec_status == "executed" else "failed",
        "decided_at": _now_iso(),
        "decided_by": user["id"],
        "decided_by_email": user.get("email"),
        "decision_note": (body or {}).get("note", "")[:500],
        "execution_status": exec_status,
        "execution_error": exec_error,
        "execution_result": exec_result if isinstance(exec_result, (dict, list, str, int, float, bool, type(None))) else str(exec_result)[:400],
    }
    await db.admin_approvals.update_one({"id": approval_id}, {"$set": update})
    # Notify requester
    try:
        from services import notify
        await notify(
            approval["requested_by"],
            f"✅ Cerere aprobată: {approval['action']}",
            f"{user.get('email')} ți-a aprobat cererea. Status execuție: {exec_status}.",
            type_="admin_approval_result",
            link="/admin/approvals",
        )
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": approval_id, "execution_status": exec_status, "execution_error": exec_error, "result": exec_result}


@router.post("/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    body: dict = Body(default={}),
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    approval = await db.admin_approvals.find_one({"id": approval_id})
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval.get("status") != "pending":
        raise HTTPException(400, f"Approval is already {approval.get('status')}")
    if not _can_review(user, approval):
        raise HTTPException(403, "Nu ai dreptul să respingi această cerere.")
    await db.admin_approvals.update_one(
        {"id": approval_id},
        {"$set": {
            "status": "rejected",
            "decided_at": _now_iso(),
            "decided_by": user["id"],
            "decided_by_email": user.get("email"),
            "decision_note": (body or {}).get("note", "")[:500],
        }},
    )
    try:
        from services import notify
        await notify(
            approval["requested_by"],
            f"❌ Cerere respinsă: {approval['action']}",
            f"{user.get('email')} ți-a respins cererea. Motiv: {(body or {}).get('note', '—')}",
            type_="admin_approval_result",
            link="/admin/approvals",
        )
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": approval_id, "status": "rejected"}


# ============================================================================
# REGISTERED ACTIONS — invokable via approve_action
# ============================================================================
@register_action("create_sub_admin")
async def _exec_create_sub_admin(payload: dict, decider: dict) -> dict:
    """Replay the create-sub-admin flow with super-admin privileges."""
    # Lazily import to avoid circular deps
    from routes.sub_admins import create_sub_admin, SubAdminCreate
    spec = SubAdminCreate(**payload)
    return await create_sub_admin(spec, user=decider)


@register_action("deactivate_sub_admin")
async def _exec_deactivate_sub_admin(payload: dict, decider: dict) -> dict:
    from routes.sub_admins import deactivate_sub_admin
    admin_id = payload.get("admin_id")
    if not admin_id:
        raise HTTPException(400, "Missing admin_id")
    return await deactivate_sub_admin(admin_id=admin_id, user=decider)


@register_action("update_autonomy_targets")
async def _exec_update_autonomy_targets(payload: dict, decider: dict) -> dict:
    """Apply autonomy targets/weights changes (mirror of PUT /api/admin/autonomy/targets)."""
    from routes.autonomy import update_targets
    return await update_targets(payload=payload, user=decider)

@register_action("analytics_loop_remediation")
async def _exec_analytics_loop_remediation(payload: dict, decider: dict) -> dict:
    """Executor pentru propunerile MEDIUM ale Operational Autonomy Loop.
    Aprobat de om → creează task-ul de remediere (reversibil) + rezolvă finding-ul."""
    key = payload.get("finding_key")
    todo_id = str(uuid.uuid4())
    await db.admin_todos.insert_one({
        "id": todo_id,
        "text": f"[Autonomy·Aprobat] {payload.get('recommended_action', 'Remediere fricțiune')}",
        "priority": "medium",
        "done": False,
        "created_at": _now_iso(),
        "created_by": decider.get("email", "admin"),
        "source": "analytics_loop",
        "finding_key": key,
    })
    if key:
        await db.admin_ai_findings.update_one(
            {"composite_key": key},
            {"$set": {"status": "resolved", "resolved_at": _now_iso(),
                      "resolved_by": decider.get("email", "admin"),
                      "resolution_note": "analytics_loop: propunere aprobată de om → task de remediere creat."}},
        )
    return {"ok": True, "todo_id": todo_id, "finding_key": key}



@register_action("project_lifecycle_transition")
async def _exec_project_lifecycle_transition(payload: dict, decider: dict) -> dict:
    """Executor pentru tranziții de lifecycle MEDIUM (ex: on_hold→archived) aprobate de om.
    Deleagă către API-ul îngust `transition_project` cu `human_approved=True`. NU ocolește
    validările (stare/blocante/read-back/audit)."""
    from autonomy.lifecycle import transition_project
    res = await transition_project(
        payload.get("project_id"),
        payload.get("transition"),
        actor=decider,
        autoexec_allowed=True,
        reason=payload.get("reason", "Aprobat de admin"),
        human_approved=True,
    )
    if not res.get("ok"):
        raise Exception(f"Lifecycle transition failed: {res.get('status')} — {res.get('reason') or res.get('error')}")
    return res
