"""PropManage — AI Product Manager (P5)

Takes a raw product idea and decomposes it into a structured tree:
  Idea -> Epic -> Features[] -> UserStories[] (with acceptance criteria)

Uses Claude (via Emergent LLM Key) for the breakdown. Persists every
breakdown in `ai_pm_breakdowns` collection so you can replay/refine.

Goal: turn napkin ideas into actionable work items without manual translation.
"""
import logging
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from sub_admin_deps import require_admin_scope
from ai_core.provider import call_llm

logger = logging.getLogger("propmanage.ai_pm")
router = APIRouter(prefix="/api/admin/ai-pm", tags=["ai-product-manager"])

BREAKDOWNS_COLLECTION = "ai_pm_breakdowns"


class BreakdownIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    context: str = Field(default="", max_length=1500)  # optional persona/business context


def _build_system_prompt() -> str:
    return (
        "Ești AI Product Manager pentru platforma PropManage (Romania real estate + AI). "
        "Transformi o idee de produs într-o ierarhie structurată: Epic > Features > UserStories. "
        "Răspunde STRICT în JSON valid (fără markdown, fără text introductiv), schema: "
        '{"epic": {"title": string, "goal": string, "success_metric": string}, '
        '"features": [{"id": "F1", "title": string, "description": string, "priority": "P0"|"P1"|"P2"|"P3", '
        '"effort_estimate_days": int, '
        '"stories": [{"id": "F1-S1", "as_a": string, "i_want": string, "so_that": string, '
        '"acceptance_criteria": [string], "technical_notes": string}] }], '
        '"risks": [{"title": string, "mitigation": string, "severity": "low"|"medium"|"high"|"critical"}], '
        '"out_of_scope": [string]}. '
        "Reguli STRICTE: max 3 features, max 2 stories per feature, max 3 risks, max 3 out_of_scope. "
        "Acceptance criteria: max 3 per story, scurte (sub 80 caractere). "
        "Răspunde în română. Concis, fără text suplimentar."
    )


def _build_user_prompt(payload: BreakdownIn) -> str:
    ctx = f"\n# Context business\n{payload.context}\n" if payload.context.strip() else ""
    return (
        f"# Idee de descompus\n"
        f"**Titlu**: {payload.title}\n\n"
        f"**Descriere**: {payload.description}\n"
        f"{ctx}\n"
        f"Descompune în Epic > Features > UserStories conform schemei JSON."
    )


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                pass
    return None


@router.post("/breakdown")
async def breakdown(payload: BreakdownIn, user=Depends(require_admin_scope("ai"))):
    """Decompose an idea into Epic > Features > Stories tree."""
    system = _build_system_prompt()
    user_msg = _build_user_prompt(payload)

    llm_result = await call_llm(
        system_message=system,
        user_message=user_msg,
        session_id=f"ai-pm-{uuid.uuid4().hex[:8]}",
        override={"model": "claude-haiku-4-5", "max_tokens": 2500},
    )
    raw_text = llm_result.get("text", "")
    parsed = _extract_json(raw_text)
    error = None
    if not parsed:
        error = llm_result.get("error") or "LLM returned non-JSON output"
        parsed = {
            "epic": {"title": payload.title, "goal": "(fallback) Definește manual goal-ul.", "success_metric": "(fallback)"},
            "features": [],
            "risks": [{"title": "LLM nedisponibil", "mitigation": f"Reia după ce providerul revine ({error[:100]}).", "severity": "medium"}],
            "out_of_scope": ["LLM fallback — refă descompunerea manual sau retry."],
        }

    doc = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "context": payload.context,
        "submitted_by": user.get("email"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "llm_provider": llm_result.get("provider"),
        "llm_model": llm_result.get("model"),
        "llm_error": error,
        "result": parsed,
        "raw_response_preview": raw_text[:1500] if raw_text else None,
    }
    await db[BREAKDOWNS_COLLECTION].insert_one({**doc})
    doc.pop("_id", None)
    return doc


@router.get("/breakdowns")
async def list_breakdowns(limit: int = 30, user=Depends(require_admin_scope("ai"))):
    cursor = db[BREAKDOWNS_COLLECTION].find({}, {"_id": 0, "raw_response_preview": 0}).sort("submitted_at", -1).limit(limit)
    items = []
    async for d in cursor:
        items.append(d)
    return {"items": items, "count": len(items)}


@router.get("/breakdowns/{breakdown_id}")
async def get_breakdown(breakdown_id: str, user=Depends(require_admin_scope("ai"))):
    doc = await db[BREAKDOWNS_COLLECTION].find_one({"id": breakdown_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Breakdown not found")
    return doc


@router.post("/breakdowns/{breakdown_id}/inject-todos")
async def inject_todos(breakdown_id: str, user=Depends(require_admin_scope("ai"))):
    """Inject all features from a breakdown into the admin todo board as actionable items."""
    doc = await db[BREAKDOWNS_COLLECTION].find_one({"id": breakdown_id})
    if not doc:
        raise HTTPException(404, "Breakdown not found")
    features = (doc.get("result") or {}).get("features", []) or []
    if not features:
        return {"ok": True, "injected": 0, "skipped": "no_features"}

    now_iso = datetime.now(timezone.utc).isoformat()
    injected = 0
    for f in features:
        text = f"[AI-PM · {doc.get('title','idea')[:40]}] {f.get('title','(feature)')}"
        priority = {"P0": "high", "P1": "high", "P2": "medium", "P3": "low"}.get(f.get("priority", "P2"), "medium")
        # de-dupe by text (case-insensitive)
        existing = await db.admin_todos.find_one({"text": text})
        if existing:
            continue
        await db.admin_todos.insert_one({
            "id": str(uuid.uuid4()),
            "text": text[:500],
            "priority": priority,
            "done": False,
            "source": f"ai_pm:{breakdown_id}",
            "topic_title": doc.get("title", "")[:200],
            "created_at": now_iso,
        })
        injected += 1
    return {"ok": True, "injected": injected, "total_features": len(features)}


@router.delete("/breakdowns/{breakdown_id}")
async def delete_breakdown(breakdown_id: str, user=Depends(require_admin_scope("ai"))):
    res = await db[BREAKDOWNS_COLLECTION].delete_one({"id": breakdown_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Breakdown not found")
    return {"ok": True}
