"""IT Collaborators Hub — internal/external dev-team manager (super-admin only).

Mounted at /api/admin/it-collaborators.

Endpoints:
  GET    /                          — list all collaborators
  POST   /                          — create a new collaborator
  GET    /{id}                      — fetch single collaborator
  PATCH  /{id}                      — update collaborator fields
  DELETE /{id}                      — soft-delete (status=archived)
  POST   /{id}/metrics              — update performance metrics (bugs/tasks/review)
  POST   /copilot/analyze           — AI Performance Copilot (Claude Sonnet 4.5)

Schema:
  it_collaborators = {
    _id: ObjectId,
    name, email, role (frontend|backend|qa|devops|ai|pm|design|fullstack),
    seniority (junior|mid|senior|principal),
    tech_stack: [str],
    status (active|paused|archived),
    started_at, hourly_rate, location, notes,
    metrics: { bugs_introduced, tasks_completed, review_score, last_sprint },
    created_at, updated_at
  }
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.it_collaborators")
router = APIRouter(prefix="/api/admin/it-collaborators", tags=["admin-it-collaborators"])

ALLOWED_ROLES = {"frontend", "backend", "fullstack", "qa", "devops", "ai", "pm", "design", "mobile", "other"}
ALLOWED_SENIORITY = {"junior", "mid", "senior", "principal"}
ALLOWED_STATUS = {"active", "paused", "archived"}


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin poate accesa IT Collaborators Hub.")


def _serialize(doc: dict) -> dict:
    if not doc:
        return doc
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "role": doc.get("role"),
        "seniority": doc.get("seniority"),
        "tech_stack": doc.get("tech_stack") or [],
        "status": doc.get("status") or "active",
        "started_at": doc.get("started_at"),
        "hourly_rate": doc.get("hourly_rate"),
        "location": doc.get("location"),
        "notes": doc.get("notes"),
        "metrics": doc.get("metrics") or {
            "bugs_introduced": 0,
            "tasks_completed": 0,
            "review_score": 0,
            "last_sprint": None,
        },
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class CollaboratorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: str
    seniority: str = "mid"
    tech_stack: Optional[List[str]] = []
    status: str = "active"
    hourly_rate: Optional[float] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    started_at: Optional[str] = None


class CollaboratorPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    seniority: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    status: Optional[str] = None
    hourly_rate: Optional[float] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    started_at: Optional[str] = None


class MetricsUpdate(BaseModel):
    bugs_introduced: Optional[int] = None
    tasks_completed: Optional[int] = None
    review_score: Optional[float] = None  # 0-10
    last_sprint: Optional[str] = None


class CopilotAnalyze(BaseModel):
    collaborator_ids: Optional[List[str]] = None  # if None → analyze all active
    question: Optional[str] = None  # optional free-text


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_collaborators(
    status: Optional[str] = None,
    role: Optional[str] = None,
    user=Depends(get_current_user),
):
    _require_super(user)
    q = {}
    if status and status != "all":
        q["status"] = status
    if role:
        q["role"] = role
    cur = db.it_collaborators.find(q).sort("created_at", -1)
    items = [_serialize(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("")
async def create_collaborator(payload: CollaboratorCreate, user=Depends(get_current_user)):
    _require_super(user)
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(400, f"role invalid; permis: {sorted(ALLOWED_ROLES)}")
    if payload.seniority not in ALLOWED_SENIORITY:
        raise HTTPException(400, f"seniority invalid; permis: {sorted(ALLOWED_SENIORITY)}")
    if payload.status not in ALLOWED_STATUS:
        raise HTTPException(400, f"status invalid; permis: {sorted(ALLOWED_STATUS)}")

    existing = await db.it_collaborators.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(409, f"Colaborator cu email {payload.email} există deja.")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "name": payload.name,
        "email": payload.email.lower(),
        "role": payload.role,
        "seniority": payload.seniority,
        "tech_stack": payload.tech_stack or [],
        "status": payload.status,
        "hourly_rate": payload.hourly_rate,
        "location": payload.location,
        "notes": payload.notes,
        "started_at": payload.started_at,
        "metrics": {
            "bugs_introduced": 0,
            "tasks_completed": 0,
            "review_score": 0,
            "last_sprint": None,
        },
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.it_collaborators.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize(doc)


@router.get("/{collab_id}")
async def get_collaborator(collab_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    doc = await db.it_collaborators.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Colaborator inexistent.")
    return _serialize(doc)


@router.patch("/{collab_id}")
async def patch_collaborator(collab_id: str, payload: CollaboratorPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")

    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "role" in update and update["role"] not in ALLOWED_ROLES:
        raise HTTPException(400, "role invalid")
    if "seniority" in update and update["seniority"] not in ALLOWED_SENIORITY:
        raise HTTPException(400, "seniority invalid")
    if "status" in update and update["status"] not in ALLOWED_STATUS:
        raise HTTPException(400, "status invalid")
    if "email" in update:
        update["email"] = str(update["email"]).lower()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.it_collaborators.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=True
    )
    if not res:
        raise HTTPException(404, "Colaborator inexistent.")
    return _serialize(res)


@router.delete("/{collab_id}")
async def delete_collaborator(collab_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.it_collaborators.update_one(
        {"_id": oid},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Colaborator inexistent.")
    return {"ok": True, "archived": True}


@router.post("/{collab_id}/metrics")
async def update_metrics(collab_id: str, payload: MetricsUpdate, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    upd = {}
    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            upd[f"metrics.{k}"] = v
    if not upd:
        raise HTTPException(400, "Nicio metrică furnizată.")
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.it_collaborators.find_one_and_update(
        {"_id": oid}, {"$set": upd}, return_document=True
    )
    if not res:
        raise HTTPException(404, "Colaborator inexistent.")
    return _serialize(res)


# ─────────────────────────────────────────────────────────────────────────────
# AI Performance Copilot (Claude Sonnet 4.5 via Emergent LLM key)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/copilot/analyze")
async def copilot_analyze(payload: CopilotAnalyze, user=Depends(get_current_user)):
    _require_super(user)
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY nu este configurat.")

    # Collect collaborator data
    q = {}
    if payload.collaborator_ids:
        try:
            oids = [ObjectId(c) for c in payload.collaborator_ids]
            q["_id"] = {"$in": oids}
        except Exception:
            raise HTTPException(400, "collaborator_ids conține ID invalid.")
    else:
        q["status"] = "active"
    docs = [_serialize(d) async for d in db.it_collaborators.find(q)]
    if not docs:
        raise HTTPException(404, "Nu există colaboratori activi de analizat.")

    # Build compact summary for the LLM
    team_summary = []
    for d in docs:
        m = d.get("metrics") or {}
        team_summary.append({
            "name": d["name"],
            "role": d["role"],
            "seniority": d["seniority"],
            "tech": d.get("tech_stack") or [],
            "bugs_introduced": m.get("bugs_introduced", 0),
            "tasks_completed": m.get("tasks_completed", 0),
            "review_score": m.get("review_score", 0),
            "last_sprint": m.get("last_sprint"),
            "status": d.get("status"),
        })

    system = (
        "Ești un Engineering Manager senior pentru PropManage (proptech). "
        "Analizezi metrici ale echipei IT și oferi un Performance Report obiectiv, "
        "în română. Răspunzi DOAR cu JSON valid, fără markdown wrapper. "
        "Schema cerută: {"
        "  summary: str (3-5 propoziții, sumar executiv),"
        "  risk_level: 'low' | 'medium' | 'high',"
        "  top_performers: [{name, reason}],"
        "  at_risk: [{name, reason, recommended_action}],"
        "  team_recommendations: [str],"
        "  sprint_risk_score: int (0-100)"
        "}"
    )
    import json
    prompt_parts = [
        "Echipa IT — metrici curente:",
        json.dumps(team_summary, ensure_ascii=False, indent=2),
    ]
    if payload.question:
        prompt_parts.append(f"\nÎntrebare suplimentară din partea Founder-ului: {payload.question}")
    prompt = "\n".join(prompt_parts)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=key,
            session_id=f"it_copilot_{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        raw = await chat.send_message(UserMessage(text=prompt))
        text = (raw or "").strip()
        if text.startswith("```"):
            text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
        i, j = text.find("{"), text.rfind("}")
        if i == -1 or j == -1 or j <= i:
            raise HTTPException(502, "AI nu a returnat JSON valid.")
        report = json.loads(text[i:j + 1])

        # Sanitize
        out = {
            "summary": str(report.get("summary") or "")[:1500],
            "risk_level": (report.get("risk_level") or "medium").lower(),
            "top_performers": [
                {"name": str(t.get("name") or "")[:80], "reason": str(t.get("reason") or "")[:300]}
                for t in (report.get("top_performers") or [])[:6]
            ],
            "at_risk": [
                {
                    "name": str(t.get("name") or "")[:80],
                    "reason": str(t.get("reason") or "")[:300],
                    "recommended_action": str(t.get("recommended_action") or "")[:300],
                }
                for t in (report.get("at_risk") or [])[:6]
            ],
            "team_recommendations": [str(r)[:400] for r in (report.get("team_recommendations") or [])[:8]],
            "sprint_risk_score": int(report.get("sprint_risk_score") or 0),
            "analyzed_count": len(team_summary),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        # Persist for history
        await db.it_copilot_reports.insert_one({
            **out,
            "question": payload.question,
            "generated_by": user.get("email"),
        })
        return out
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[it_copilot.analyze] failed: {e}")
        raise HTTPException(500, f"Eroare AI: {str(e)[:200]}")


@router.get("/copilot/history")
async def copilot_history(limit: int = 10, user=Depends(get_current_user)):
    _require_super(user)
    cur = db.it_copilot_reports.find({}).sort("generated_at", -1).limit(min(limit, 50))
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "count": len(items)}
