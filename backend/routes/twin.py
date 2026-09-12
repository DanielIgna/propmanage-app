"""Twin Orchestrator AI Agent — natural-language Q&A about the platform itself.

Super-admin only. Gathers platform context (autonomy scores, recent autopilot
runs, audit log, alerts, KPIs) and feeds it as system prompt to Claude
Sonnet 4.5, which answers the admin's question.

Endpoint:
    POST /api/admin/twin/ask  { question: str, session_id?: str }

The Twin has read-only access to MongoDB collections via a curated context
bundle — no tool calling, no writes.
"""
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from sub_admin_deps import is_super_admin
from routes.autonomy import run_auto_tune_orchestration
from autonomy.snapshots import take_autonomy_snapshot, _CACHE

logger = logging.getLogger("propmanage.twin")

router = APIRouter(prefix="/api/admin/twin", tags=["twin-orchestrator"])

MODEL_NAME = "claude-sonnet-4-5-20250929"
MAX_CONTEXT_ITEMS = 8  # cap recent rows per collection to keep prompt sane


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=600)
    session_id: Optional[str] = None


# ============================================================================
# TWIN ACTION MODE — predefined safe actions executable by Twin via chat.
# Each action is read+write-confirmed via 2-step protocol:
#   1. POST /ask returns an action_proposal when Twin detects intent
#   2. POST /execute-action with confirmation_token executes it
# Tokens are single-use, 5-min TTL, super-admin only.
# ============================================================================
ALLOWED_ACTIONS = {
    "auto_tune": {
        "label": "Auto-Tune to Self-Driving",
        "description": "Rulează orchestrator complet (seed AI + repair + concierge + dismiss + snapshot)",
        "estimated_seconds": 8,
    },
    "send_founder_digest": {
        "label": "Trimite Founders' Digest acum",
        "description": "Trimite email-ul săptămânal de KPI-uri către toți super-adminii",
        "estimated_seconds": 4,
    },
    "boost_dev": {
        "label": "Boost DEV (Release Gate + dismiss findings)",
        "description": "Rulează Release Gate în background + dismiss findings vechi",
        "estimated_seconds": 6,
    },
    "take_snapshot": {
        "label": "Snapshot Autonomy acum",
        "description": "Forțează un snapshot nou + persistă în DB",
        "estimated_seconds": 2,
    },
}


def _detect_action_intent(question: str) -> Optional[str]:
    """Cheap keyword-based intent detector — runs BEFORE the LLM call.

    Returns the action key if a clear execution intent is detected, else None.
    Conservative: only triggers on imperative verbs + action keywords.
    """
    q = question.lower().strip()
    # Must contain an imperative verb (Romanian + English)
    has_imperative = any(v in q for v in [
        "rulează", "ruleaza", "execută", "executa", "fă", "fa ",
        "trimite", "lansează", "lanseaza", "porneste", "pornește",
        "run ", "execute", "send", "trigger", "do ",
    ])
    if not has_imperative:
        return None
    if any(k in q for k in ["auto-tune", "auto tune", "autotune", "self-heal", "self heal"]):
        return "auto_tune"
    if any(k in q for k in ["digest", "founders", "founder"]):
        return "send_founder_digest"
    if any(k in q for k in ["boost dev", "boost-dev"]):
        return "boost_dev"
    if any(k in q for k in ["snapshot", "snap "]):
        return "take_snapshot"
    return None


async def _execute_action(action_key: str, user: dict) -> dict:
    """Dispatcher — executes the action. Returns a dict with summary."""
    if action_key == "auto_tune":
        report = await run_auto_tune_orchestration(triggered_by=f"twin:{user['id']}")
        return {
            "ok": True,
            "tier_after": (report.get("after") or {}).get("tier"),
            "general_after": (report.get("after") or {}).get("scores", {}).get("general"),
            "ai_health": (report.get("ai_health") or {}).get("overall"),
            "delta": report.get("delta_general"),
        }
    if action_key == "send_founder_digest":
        from autonomy.founder_digest import weekly_founder_digest
        r = await weekly_founder_digest()
        return {"ok": r.get("ok"), "sent": r.get("sent"), "failed": r.get("failed")}
    if action_key == "boost_dev":
        # Use the existing boost-dev logic via internal HTTP-less call
        from autonomy.autopilot import daily_autopilot_sweep
        r = await daily_autopilot_sweep()
        return {"ok": True, "summary": r}
    if action_key == "take_snapshot":
        _CACHE["data"] = None
        snap = await take_autonomy_snapshot()
        return {
            "ok": True,
            "tier": snap.get("tier"),
            "general": (snap.get("scores") or {}).get("general"),
        }
    raise HTTPException(400, f"Acțiune necunoscută: {action_key}")


class ExecuteActionRequest(BaseModel):
    action_key: str = Field(..., min_length=2, max_length=50)
    confirmation_token: str = Field(..., min_length=8, max_length=128)
    session_id: Optional[str] = None


async def _gather_platform_context() -> dict:
    """Snapshot of the platform state for the AI prompt."""
    ctx = {"now": datetime.now(timezone.utc).isoformat()}

    # Latest autonomy snapshot
    snap = await db.autonomy_snapshots.find_one({}, sort=[("timestamp", -1)])
    if snap:
        ctx["latest_autonomy"] = {
            "timestamp": snap.get("timestamp"),
            "tier": snap.get("tier"),
            "scores": snap.get("scores"),
            "breakdown_summary": snap.get("breakdown_summary"),
            "recommendations_count": snap.get("recommendations_count"),
        }

    # Last 5 autonomy snapshots (trend)
    trend = []
    async for s in db.autonomy_snapshots.find({}, {"_id": 0, "timestamp": 1, "tier": 1, "scores": 1}).sort("timestamp", -1).limit(5):
        trend.append(s)
    ctx["autonomy_trend_5d"] = list(reversed(trend))

    # Recent autopilot runs
    runs = []
    async for r in db.autopilot_runs.find({}, {"_id": 0}).sort("ran_at", -1).limit(MAX_CONTEXT_ITEMS):
        runs.append(r)
    ctx["recent_autopilot_runs"] = runs

    # Recent tier alerts
    alerts = []
    async for a in db.autonomy_alerts.find({}, {"_id": 0}).sort("sent_at", -1).limit(5):
        alerts.append(a)
    ctx["recent_tier_alerts"] = alerts

    # Admin actions today (counts by outcome)
    today_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    allowed = await db.admin_actions_log.count_documents({"ts": {"$gte": today_iso}, "outcome": "allowed"})
    denied = await db.admin_actions_log.count_documents({"ts": {"$gte": today_iso}, "outcome": "denied"})
    ctx["admin_actions_24h"] = {"allowed": allowed, "denied": denied}

    # Top admins by activity (last 24h)
    top_actors = []
    pipeline = [
        {"$match": {"ts": {"$gte": today_iso}}},
        {"$group": {"_id": "$user_email", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    async for d in db.admin_actions_log.aggregate(pipeline):
        if d.get("_id"):
            top_actors.append({"email": d["_id"], "actions_24h": d["count"]})
    ctx["top_admins_24h"] = top_actors

    # AI Health latest
    today = datetime.now(timezone.utc).date().isoformat()
    h = await db.admin_ai_health_history.find_one({"day": today}, {"_id": 0})
    if h:
        ctx["ai_health_today"] = h

    # Counts overview
    try:
        ctx["counts"] = {
            "users_total": await db.users.count_documents({}),
            "requests_total": await db.requests.count_documents({}),
            "kyc_pending": await db.kyc_documents.count_documents({"status": "pending"}),
            "open_ai_findings": await db.admin_ai_findings.count_documents({"status": "open"}),
        }
    except Exception:  # noqa: BLE001
        ctx["counts"] = {}

    return ctx


def _build_system_prompt(ctx: dict, proposed_action: Optional[str] = None) -> str:
    import json as _json
    ctx_str = _json.dumps(ctx, default=str, indent=2)[:9000]
    action_hint = ""
    if proposed_action and proposed_action in ALLOWED_ACTIONS:
        meta = ALLOWED_ACTIONS[proposed_action]
        action_hint = (
            f"\n\nACTION INTENT DETECTED: utilizatorul vrea să execute '{meta['label']}'.\n"
            f"Spune ce face acțiunea pe scurt (2-3 fraze) + cere confirmare explicită "
            f"('confirmă cu butonul de mai jos'). Nu spune că ai executat — UI-ul va afișa "
            f"butonul de confirmare. NU executa nimic, doar explică."
        )
    return (
        "You are Twin, the AI orchestrator for PropManage — an AI-assisted "
        "property management platform for Romania. You answer admin questions "
        "about the platform's state, scores, recent actions, and trends.\n\n"
        "RULES:\n"
        "- Respond in ROMANIAN (the user is Romanian).\n"
        "- Be concise — 2-5 sentences typical. Use bullets only when listing.\n"
        "- Use specific numbers from the context (tier, scores, counts).\n"
        "- If the answer requires data NOT in the context, say so honestly and suggest where to look (which admin page).\n"
        "- Never make up numbers. If the context shows ai_health.overall=91, say 91 — not 'around 90'.\n"
        "- For 'why' questions, look at autonomy_trend_5d and recent_autopilot_runs to explain causes.\n"
        "- For 'what should I do' questions, suggest concrete actions (Auto-Tune, Boost DEV, etc.).\n"
        "- You have READ-ONLY context. You cannot execute actions DIRECTLY — but when "
        "user intent is to execute, a confirmation button appears in UI.\n"
        f"{action_hint}\n\n"
        f"CURRENT PLATFORM CONTEXT (JSON snapshot):\n{ctx_str}\n"
    )


@router.post("/ask")
async def twin_ask(payload: AskRequest, user=Depends(require_role("admin"))):
    """Ask the Twin Orchestrator a question about the platform.

    Super-admin only. The Twin reads the live platform state and answers in
    natural Romanian using Claude Sonnet 4.5.
    """
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate folosi Twin Orchestrator.")

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(500, "EMERGENT_LLM_KEY lipsește din environment.")

    session_id = payload.session_id or f"twin-{user['id']}-{uuid.uuid4().hex[:8]}"

    # ACTION MODE — detect execution intent BEFORE calling LLM
    proposed_action = _detect_action_intent(payload.question)
    action_proposal = None
    if proposed_action and proposed_action in ALLOWED_ACTIONS:
        # Check if question also contains scheduling info
        from twin_schedule import _detect_schedule_intent
        sched_info = _detect_schedule_intent(payload.question)

        meta = ALLOWED_ACTIONS[proposed_action]
        token = secrets.token_urlsafe(24)
        await db.twin_action_tokens.insert_one({
            "token": token,
            "action_key": proposed_action,
            "user_id": user["id"],
            "session_id": session_id,
            "question": payload.question,
            "schedule_info": sched_info,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "used": False,
        })
        action_proposal = {
            "action_key": proposed_action,
            "label": meta["label"],
            "description": meta["description"],
            "estimated_seconds": meta["estimated_seconds"],
            "confirmation_token": token,
            "expires_in_minutes": 5,
            "schedule_info": sched_info,  # None or {kind, when, label}
        }

    try:
        ctx = await _gather_platform_context()
        system_prompt = _build_system_prompt(ctx, proposed_action=proposed_action)

        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=key,
            session_id=session_id,
            system_message=system_prompt,
        ).with_model("anthropic", MODEL_NAME)
        answer = await chat.send_message(UserMessage(text=payload.question))

        # Persist Q&A for audit + future analysis
        await db.twin_conversations.insert_one({
            "id": uuid.uuid4().hex,
            "session_id": session_id,
            "user_id": user["id"],
            "user_email": user.get("email"),
            "question": payload.question,
            "answer": (answer or "")[:4000],
            "model": MODEL_NAME,
            "asked_at": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "ok": True,
            "session_id": session_id,
            "answer": answer or "(Răspuns gol — încearcă o reformulare a întrebării.)",
            "context_keys": list(ctx.keys()),
            "action_proposal": action_proposal,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[twin.ask] failed: {e}")
        raise HTTPException(500, f"Eroare Twin: {str(e)[:200]}")


@router.post("/execute-action")
async def twin_execute_action(payload: ExecuteActionRequest, user=Depends(require_role("admin"))):
    """Execute a Twin-proposed action with confirmation token.

    Tokens are single-use, 5-min TTL, scoped to user_id. Returns the action's
    result summary so Twin can post it in the chat.
    """
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate executa acțiuni Twin.")

    # Validate token
    tok = await db.twin_action_tokens.find_one({
        "token": payload.confirmation_token,
        "user_id": user["id"],
        "action_key": payload.action_key,
        "used": False,
    })
    if not tok:
        raise HTTPException(404, "Token de confirmare invalid sau deja folosit.")

    expires_at = tok.get("expires_at", "")
    if expires_at and datetime.now(timezone.utc).isoformat() > expires_at:
        raise HTTPException(410, "Token de confirmare expirat (TTL 5min). Reformulează cererea.")

    # Burn token (single-use)
    await db.twin_action_tokens.update_one(
        {"_id": tok["_id"]},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
    )

    # Execute + audit
    try:
        # If the token has schedule_info → register a scheduled job (don't execute now)
        sched_info = tok.get("schedule_info")
        if sched_info and isinstance(sched_info, dict) and sched_info.get("kind"):
            from twin_schedule import register_schedule
            from server import scheduler
            schedule_id = uuid.uuid4().hex
            try:
                doc = await register_schedule(
                    scheduler=scheduler,
                    schedule_id=schedule_id,
                    user_id=user["id"],
                    user_email=user.get("email"),
                    action_key=payload.action_key,
                    schedule_info=sched_info,
                    question=tok.get("question", ""),
                )
            except ValueError as ve:
                raise HTTPException(400, str(ve))
            return {
                "ok": True,
                "scheduled": True,
                "action_key": payload.action_key,
                "label": ALLOWED_ACTIONS.get(payload.action_key, {}).get("label", payload.action_key),
                "result": {
                    "schedule_id": schedule_id,
                    "kind": doc["kind"],
                    "label": doc["label"],
                    "status": "active",
                },
            }

        # Otherwise execute immediately
        result = await _execute_action(payload.action_key, user)
        await db.twin_actions_log.insert_one({
            "id": uuid.uuid4().hex,
            "action_key": payload.action_key,
            "user_id": user["id"],
            "user_email": user.get("email"),
            "session_id": payload.session_id or tok.get("session_id"),
            "result": result,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "source_question": tok.get("question"),
        })
        return {
            "ok": True,
            "scheduled": False,
            "action_key": payload.action_key,
            "label": ALLOWED_ACTIONS.get(payload.action_key, {}).get("label", payload.action_key),
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[twin.execute] action={payload.action_key} failed: {e}")
        raise HTTPException(500, f"Eroare execuție: {str(e)[:200]}")


@router.get("/history")
async def twin_history(
    session_id: Optional[str] = None,
    limit: int = 30,
    user=Depends(require_role("admin")),
):
    """Recent Q&A pairs. Optionally filter by session_id."""
    q = {"user_id": user["id"]}
    if session_id:
        q["session_id"] = session_id
    cursor = db.twin_conversations.find(q, {"_id": 0}).sort("asked_at", -1).limit(min(limit, 100))
    items = [d async for d in cursor]
    return {"items": list(reversed(items)), "count": len(items)}


@router.get("/scheduled")
async def list_schedules(user=Depends(require_role("admin"))):
    """List active + recent scheduled actions for the current user."""
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin.")
    cursor = db.twin_scheduled_actions.find(
        {"user_id": user["id"]},
        {"_id": 0},
    ).sort("created_at", -1).limit(50)
    items = [d async for d in cursor]
    return {"items": items, "count": len(items)}


@router.delete("/scheduled/{schedule_id}")
async def delete_schedule(schedule_id: str, user=Depends(require_role("admin"))):
    """Cancel a scheduled action (idempotent)."""
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin.")
    from twin_schedule import cancel_schedule
    from server import scheduler
    ok = await cancel_schedule(scheduler, schedule_id, user["id"])
    if not ok:
        raise HTTPException(404, "Schedule not found")
    return {"ok": True, "schedule_id": schedule_id}
