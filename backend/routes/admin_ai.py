"""PropManage — AI Admin Console (Investigator agent)

MVP Faza A:
- Deterministic anomaly scanner (Python, no LLM credits spent on detection)
- Claude Sonnet 4.5 for natural language interpretation + admin chat
- Persistent findings in MongoDB with lifecycle (open/dismissed/resolved)
- Daily auto-scan via APScheduler + email digest

Design goals:
- Admin has 100% control (read-only DB access from LLM, NO write operations)
- All actions logged to admin_audit_log
- Memory persists across sessions and admin restarts
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from bson import ObjectId
from bson.errors import InvalidId

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.admin_ai")
router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "").strip()
DEFAULT_MODEL_PROVIDER = "anthropic"
DEFAULT_MODEL_NAME = "claude-sonnet-4-6"  # Latest available per playbook

# ============= ANOMALY SCANNER (deterministic Python — NO LLM) =============

ANOMALY_PATTERNS = {
    "stale_project": {
        "label": "Proiect blocat fără activitate",
        "severity": "warning",
        "description": "Proiect cu status 'active' fără modificări de peste 30 zile",
    },
    "specialist_low_rating": {
        "label": "Specialist cu rating scăzut activ",
        "severity": "high",
        "description": "Specialist cu rating <3.0 dar still active pe platformă",
    },
    "client_repeated_rejections": {
        "label": "Client cu cereri respinse repetat",
        "severity": "warning",
        "description": "Client cu ≥3 cereri respinse de același specialist în 7 zile",
    },
    "operator_unvalidated_twins": {
        "label": "Operator cu twins nevalidate",
        "severity": "warning",
        "description": "Operator cu proprietăți twin nevalidate de peste 7 zile",
    },
    "escrow_stuck": {
        "label": "Plată escrow blocată",
        "severity": "high",
        "description": "Milestone cu fonduri reținute >14 zile fără update",
    },
    "audit_spike": {
        "label": "Spike audit log activity",
        "severity": "warning",
        "description": "≥30 acțiuni admin în <60 minute (posibil bot sau test în prod)",
    },
    "orphan_twins": {
        "label": "Twins orfane",
        "severity": "low",
        "description": "Twin care referă property_id inexistent în DB",
    },
    "duplicate_users": {
        "label": "Useri duplicați",
        "severity": "low",
        "description": "Useri cu aceeași adresă de email (case-insensitive) — posibil duplicate",
    },
}


async def _scan_stale_projects() -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    findings = []
    async for p in db.projects.find({"status": "active", "updated_at": {"$lt": cutoff}}).limit(50):
        findings.append({
            "pattern": "stale_project",
            "entity_type": "project",
            "entity_id": str(p["_id"]),
            "entity_label": p.get("title") or p.get("name") or str(p["_id"]),
            "context": {
                "last_update": p.get("updated_at"),
                "owner_id": p.get("owner_id"),
                "specialist_id": p.get("specialist_id"),
            },
        })
    return findings


async def _scan_specialist_low_rating() -> list:
    findings = []
    async for u in db.users.find({"role": "specialist", "trust_score": {"$lt": 3.0, "$ne": None}}).limit(50):
        findings.append({
            "pattern": "specialist_low_rating",
            "entity_type": "user",
            "entity_id": str(u["_id"]),
            "entity_label": u.get("name") or u.get("email"),
            "context": {"email": u.get("email"), "trust_score": u.get("trust_score")},
        })
    return findings


async def _scan_client_repeated_rejections() -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pipeline = [
        {"$match": {"status": "rejected", "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"client_id": "$client_id", "specialist_id": "$specialist_id"},
            "count": {"$sum": 1},
            "request_ids": {"$push": "$_id"},
        }},
        {"$match": {"count": {"$gte": 3}}},
        {"$limit": 50},
    ]
    findings = []
    async for g in db.requests.aggregate(pipeline):
        findings.append({
            "pattern": "client_repeated_rejections",
            "entity_type": "user_pair",
            "entity_id": f"{g['_id'].get('client_id')}__{g['_id'].get('specialist_id')}",
            "entity_label": f"Client → Specialist ({g['count']} respingeri)",
            "context": {**g["_id"], "count": g["count"]},
        })
    return findings


async def _scan_operator_unvalidated_twins() -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    findings = []
    async for t in db.twins.find({"validated": False, "created_at": {"$lt": cutoff}}).limit(50):
        findings.append({
            "pattern": "operator_unvalidated_twins",
            "entity_type": "twin",
            "entity_id": str(t["_id"]),
            "entity_label": f"Twin {t.get('property_id', '?')}",
            "context": {"property_id": t.get("property_id"), "created_at": t.get("created_at")},
        })
    return findings


async def _scan_escrow_stuck() -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    findings = []
    async for p in db.projects.find({"milestones": {"$exists": True}}).limit(200):
        for m in p.get("milestones", []):
            if m.get("escrow_held") and m.get("updated_at", p.get("updated_at", "")) < cutoff:
                findings.append({
                    "pattern": "escrow_stuck",
                    "entity_type": "milestone",
                    "entity_id": f"{p['_id']}::{m.get('id')}",
                    "entity_label": f"{p.get('title', '?')} → {m.get('title', '?')}",
                    "context": {"amount": m.get("amount"), "held_since": m.get("escrow_held_at")},
                })
    return findings


async def _scan_audit_spike() -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    count = await db.admin_audit_log.count_documents({"created_at": {"$gte": cutoff}})
    if count >= 30:
        return [{
            "pattern": "audit_spike",
            "entity_type": "audit_log",
            "entity_id": f"window_{cutoff[:13]}",
            "entity_label": f"{count} acțiuni în ultima oră",
            "context": {"count": count, "window_start": cutoff},
        }]
    return []


async def _scan_orphan_twins() -> list:
    findings = []
    twin_props = set()
    async for t in db.twins.find({}, {"property_id": 1}).limit(500):
        if t.get("property_id"):
            twin_props.add(t["property_id"])
    if not twin_props:
        return findings
    existing = set()
    async for p in db.properties.find({"_id": {"$in": [pid for pid in twin_props if isinstance(pid, str)]}}, {"_id": 1}):
        existing.add(str(p["_id"]))
    orphans = twin_props - existing
    for pid in list(orphans)[:50]:
        t = await db.twins.find_one({"property_id": pid})
        if t:
            findings.append({
                "pattern": "orphan_twins",
                "entity_type": "twin",
                "entity_id": str(t["_id"]),
                "entity_label": f"Twin pt property_id={pid} (inexistent)",
                "context": {"property_id": pid},
            })
    return findings


async def _scan_duplicate_users() -> list:
    pipeline = [
        {"$group": {"_id": {"$toLower": "$email"}, "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$limit": 30},
    ]
    findings = []
    async for g in db.users.aggregate(pipeline):
        findings.append({
            "pattern": "duplicate_users",
            "entity_type": "user_group",
            "entity_id": g["_id"],
            "entity_label": f"{g['count']} useri cu email '{g['_id']}'",
            "context": {"email": g["_id"], "count": g["count"], "user_ids": [str(uid) for uid in g["ids"]]},
        })
    return findings


SCANNERS = [
    _scan_stale_projects,
    _scan_specialist_low_rating,
    _scan_client_repeated_rejections,
    _scan_operator_unvalidated_twins,
    _scan_escrow_stuck,
    _scan_audit_spike,
    _scan_orphan_twins,
    _scan_duplicate_users,
]


async def run_full_scan(actor_id: str = "system") -> dict:
    """Execute all anomaly scanners and persist new findings. Updates existing ones if pattern+entity matches."""
    started = datetime.now(timezone.utc)
    all_raw = []
    errors = []
    for scanner in SCANNERS:
        try:
            res = await scanner()
            all_raw.extend(res)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[AI-Scan] {scanner.__name__} failed: {e}")
            errors.append({"scanner": scanner.__name__, "error": str(e)})

    new_count = 0
    updated_count = 0
    seen_count = 0
    for f in all_raw:
        meta = ANOMALY_PATTERNS.get(f["pattern"], {})
        composite_key = f"{f['pattern']}::{f['entity_id']}"
        existing = await db.admin_ai_findings.find_one({"composite_key": composite_key})
        now_iso = datetime.now(timezone.utc).isoformat()
        if existing:
            if existing.get("status") == "open":
                await db.admin_ai_findings.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"last_seen_at": now_iso, "context": f["context"], "entity_label": f["entity_label"]},
                     "$inc": {"occurrences": 1}},
                )
                updated_count += 1
            else:
                seen_count += 1
        else:
            await db.admin_ai_findings.insert_one({
                "composite_key": composite_key,
                "pattern": f["pattern"],
                "label": meta.get("label", f["pattern"]),
                "severity": meta.get("severity", "warning"),
                "description": meta.get("description", ""),
                "entity_type": f["entity_type"],
                "entity_id": f["entity_id"],
                "entity_label": f["entity_label"],
                "context": f["context"],
                "status": "open",
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
                "occurrences": 1,
                "resolved_at": None,
                "resolved_by": None,
                "resolution_note": None,
                "scan_id": started.isoformat(),
            })
            new_count += 1

    # Record scan history
    summary = {
        "scan_id": started.isoformat(),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "actor_id": actor_id,
        "new_findings": new_count,
        "updated_findings": updated_count,
        "ignored_findings": seen_count,
        "total_raw": len(all_raw),
        "errors": errors,
    }
    res = await db.admin_ai_scans.insert_one(dict(summary))
    summary["id"] = str(res.inserted_id)
    logger.info(f"[AI-Scan] complete: new={new_count} updated={updated_count} ignored={seen_count}")
    return summary


# ============= REST ENDPOINTS =============

def _serialize_finding(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "pattern": d.get("pattern"),
        "label": d.get("label"),
        "severity": d.get("severity"),
        "description": d.get("description"),
        "entity_type": d.get("entity_type"),
        "entity_id": d.get("entity_id"),
        "entity_label": d.get("entity_label"),
        "context": d.get("context"),
        "status": d.get("status"),
        "first_seen_at": d.get("first_seen_at"),
        "last_seen_at": d.get("last_seen_at"),
        "occurrences": d.get("occurrences", 1),
        "resolved_at": d.get("resolved_at"),
        "resolved_by_name": d.get("resolved_by_name"),
        "resolution_note": d.get("resolution_note"),
    }


@router.post("/scan/run")
async def trigger_scan(user: dict = Depends(require_role("admin"))):
    """Manually trigger a full anomaly scan."""
    summary = await run_full_scan(actor_id=user["id"])
    return summary


@router.get("/findings")
async def list_findings(
    status: Optional[str] = Query("open"),
    severity: Optional[str] = None,
    pattern: Optional[str] = None,
    limit: int = Query(100, le=500),
    user: dict = Depends(require_role("admin")),
):
    """List findings with optional filters."""
    filt = {}
    if status and status != "all":
        filt["status"] = status
    if severity:
        filt["severity"] = severity
    if pattern:
        filt["pattern"] = pattern
    total = await db.admin_ai_findings.count_documents(filt)
    cursor = db.admin_ai_findings.find(filt).sort([
        ("severity", -1),  # high before low (text sort works for our 3-level labels)
        ("last_seen_at", -1),
    ]).limit(limit)
    items = [_serialize_finding(d) async for d in cursor]
    # KPI counts
    counts = {
        "open": await db.admin_ai_findings.count_documents({"status": "open"}),
        "dismissed": await db.admin_ai_findings.count_documents({"status": "dismissed"}),
        "resolved": await db.admin_ai_findings.count_documents({"status": "resolved"}),
    }
    by_severity = {
        "high": await db.admin_ai_findings.count_documents({"status": "open", "severity": "high"}),
        "warning": await db.admin_ai_findings.count_documents({"status": "open", "severity": "warning"}),
        "low": await db.admin_ai_findings.count_documents({"status": "open", "severity": "low"}),
    }
    return {"items": items, "total": total, "counts": counts, "by_severity": by_severity}


@router.post("/findings/{finding_id}/dismiss")
async def dismiss_finding(
    finding_id: str,
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    try:
        oid = ObjectId(finding_id)
    except InvalidId:
        raise HTTPException(400, "Invalid finding id")
    note = (payload.get("note") or "").strip()[:300] or None
    await db.admin_ai_findings.update_one(
        {"_id": oid},
        {"$set": {
            "status": "dismissed",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": user["id"],
            "resolved_by_name": user.get("name") or user.get("email"),
            "resolution_note": note,
        }},
    )
    return {"ok": True}


@router.post("/findings/{finding_id}/resolve")
async def resolve_finding(
    finding_id: str,
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    try:
        oid = ObjectId(finding_id)
    except InvalidId:
        raise HTTPException(400, "Invalid finding id")
    note = (payload.get("note") or "").strip()[:300] or None
    await db.admin_ai_findings.update_one(
        {"_id": oid},
        {"$set": {
            "status": "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": user["id"],
            "resolved_by_name": user.get("name") or user.get("email"),
            "resolution_note": note,
        }},
    )
    return {"ok": True}


@router.get("/scans")
async def list_scans(limit: int = Query(20, le=100), user: dict = Depends(require_role("admin"))):
    cursor = db.admin_ai_scans.find({}).sort("started_at", -1).limit(limit)
    items = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        items.append(d)
    return {"items": items}


# ============= AI REPAIR SUGGESTER (Faza B) =============
# LLM proposes a concrete fix per finding → admin reviews & approves/rejects.
# IMPORTANT: "approved" only marks the suggestion as acceptable. NO automatic
# write actions are taken. Admin marks "applied" manually after running the fix.

REPAIR_SYSTEM_PROMPT = """Ești "Repair Suggester", un asistent AI care propune pași concreți pentru
remedierea anomaliilor detectate de scannerul PropManage.

REGULI STRICTE:
- NU executi nimic — doar propui.
- Răspunzi STRUCTURAT, în română, în JSON valid cu schema:
  {
    "summary": "1 frază — ce e problema",
    "risk_level": "low|medium|high",
    "steps": ["pas 1 concret", "pas 2 concret", ...],
    "rollback": "cum se anulează schimbarea dacă e nevoie",
    "verification": "cum verifică adminul că s-a rezolvat",
    "estimated_minutes": <număr întreg>,
    "requires_db_write": true|false,
    "requires_user_communication": true|false
  }
- Pașii trebuie să fie ACȚIUNI specifice pe care adminul le poate face în UI/DB.
- Dacă finding-ul nu e clar sau nu poți propune nimic util, returnează steps: ["Nu pot propune un fix automatizabil. Recomand investigare manuală."]
- NICIODATĂ nu inventa endpoint-uri sau funcții. Folosește limbaj operațional.
- Răspunde DOAR cu JSON-ul, fără cod-fence, fără text suplimentar.
"""


@router.post("/findings/{finding_id}/suggest-repair")
async def suggest_repair(
    finding_id: str,
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    """Generate a repair suggestion for a finding using Claude Sonnet 4.5.
    Body (optional): { regenerate: bool } — if true, overwrite existing.
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY nu este configurat.")
    try:
        oid = ObjectId(finding_id)
    except InvalidId:
        raise HTTPException(400, "Invalid finding id")

    finding = await db.admin_ai_findings.find_one({"_id": oid})
    if not finding:
        raise HTTPException(404, "Finding not found")

    regenerate = bool(payload.get("regenerate"))
    existing = await db.admin_ai_repair_suggestions.find_one({"finding_id": str(oid)})
    if existing and not regenerate:
        return {
            "finding_id": str(oid),
            "suggestion": _serialize_repair(existing),
            "cached": True,
        }

    # Build prompt context
    finding_brief = {
        "pattern": finding.get("pattern"),
        "label": finding.get("label"),
        "severity": finding.get("severity"),
        "description": finding.get("description"),
        "entity_type": finding.get("entity_type"),
        "entity_id": finding.get("entity_id"),
        "entity_label": finding.get("entity_label"),
        "occurrences": finding.get("occurrences", 1),
        "context": finding.get("context"),
        "first_seen_at": finding.get("first_seen_at"),
    }
    import json as _json
    user_msg = (
        "Iată finding-ul. Propune un plan de fix conform schemei JSON din instrucțiuni.\n\n"
        + _json.dumps(finding_brief, ensure_ascii=False, indent=2)
    )

    proposal_json = None
    raw_text = ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        chat_inst = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"repair_{oid}_{uuid.uuid4().hex[:6]}",
            system_message=REPAIR_SYSTEM_PROMPT,
        ).with_model(DEFAULT_MODEL_PROVIDER, DEFAULT_MODEL_NAME)
        raw_text = await chat_inst.send_message(UserMessage(text=user_msg))
        # Try to extract a JSON object — be tolerant if LLM wraps in markdown despite instructions.
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip("` \n")
        # Locate first { ... last }
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first != -1 and last != -1 and last > first:
            proposal_json = _json.loads(cleaned[first:last + 1])
    except Exception as e:  # noqa: BLE001
        logger.error(f"[Repair-Suggester] LLM error: {e}")
        raise HTTPException(502, f"Nu am putut genera sugestia: {str(e)[:160]}")

    if not isinstance(proposal_json, dict):
        # Fallback: store raw text so admin still sees something
        proposal_json = {
            "summary": "Răspuns LLM neformatabil — verifică textul brut.",
            "risk_level": "medium",
            "steps": [raw_text[:500] or "Niciun pas extras."],
            "rollback": "—",
            "verification": "—",
            "estimated_minutes": 0,
            "requires_db_write": False,
            "requires_user_communication": False,
        }

    # Sanitize / clamp fields
    risk = (proposal_json.get("risk_level") or "medium").lower()
    if risk not in {"low", "medium", "high"}:
        risk = "medium"
    steps = proposal_json.get("steps") or []
    if not isinstance(steps, list):
        steps = [str(steps)]
    steps = [str(s)[:500] for s in steps][:12]

    try:
        est_minutes = max(0, int(proposal_json.get("estimated_minutes") or 0))
    except (TypeError, ValueError):
        est_minutes = 0

    doc = {
        "finding_id": str(oid),
        "finding_pattern": finding.get("pattern"),
        "finding_label": finding.get("label"),
        "summary": str(proposal_json.get("summary") or "")[:500],
        "risk_level": risk,
        "steps": steps,
        "rollback": str(proposal_json.get("rollback") or "")[:600],
        "verification": str(proposal_json.get("verification") or "")[:600],
        "estimated_minutes": est_minutes,
        "requires_db_write": bool(proposal_json.get("requires_db_write")),
        "requires_user_communication": bool(proposal_json.get("requires_user_communication")),
        "raw_response": raw_text[:4000],
        "status": "proposed",  # proposed | approved | rejected | applied
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "created_by_name": user.get("name") or user.get("email"),
        "decided_at": None,
        "decided_by": None,
        "decision_note": None,
        "applied_at": None,
        "applied_by": None,
    }
    if existing:
        await db.admin_ai_repair_suggestions.update_one(
            {"_id": existing["_id"]},
            {"$set": doc, "$inc": {"regeneration_count": 1}},
        )
        doc["_id"] = existing["_id"]
        doc["regeneration_count"] = existing.get("regeneration_count", 0) + 1
    else:
        doc["regeneration_count"] = 0
        res = await db.admin_ai_repair_suggestions.insert_one(doc)
        doc["_id"] = res.inserted_id

    return {"finding_id": str(oid), "suggestion": _serialize_repair(doc), "cached": False}


def _serialize_repair(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "finding_id": d.get("finding_id"),
        "summary": d.get("summary"),
        "risk_level": d.get("risk_level"),
        "steps": d.get("steps") or [],
        "rollback": d.get("rollback"),
        "verification": d.get("verification"),
        "estimated_minutes": d.get("estimated_minutes", 0),
        "requires_db_write": d.get("requires_db_write", False),
        "requires_user_communication": d.get("requires_user_communication", False),
        "status": d.get("status"),
        "created_at": d.get("created_at"),
        "created_by_name": d.get("created_by_name"),
        "decided_at": d.get("decided_at"),
        "decision_note": d.get("decision_note"),
        "applied_at": d.get("applied_at"),
        "regeneration_count": d.get("regeneration_count", 0),
    }


@router.get("/findings/{finding_id}/suggest-repair")
async def get_repair_suggestion(
    finding_id: str,
    user: dict = Depends(require_role("admin")),
):
    try:
        oid = ObjectId(finding_id)
    except InvalidId:
        raise HTTPException(400, "Invalid finding id")
    s = await db.admin_ai_repair_suggestions.find_one({"finding_id": str(oid)})
    if not s:
        return {"finding_id": str(oid), "suggestion": None}
    return {"finding_id": str(oid), "suggestion": _serialize_repair(s)}


@router.post("/repair-suggestions/{suggestion_id}/decide")
async def decide_repair(
    suggestion_id: str,
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Admin approves or rejects a repair suggestion. NOT applied automatically.
    Body: { decision: "approve" | "reject", note?: str }
    """
    try:
        oid = ObjectId(suggestion_id)
    except InvalidId:
        raise HTTPException(400, "Invalid suggestion id")
    decision = (payload.get("decision") or "").lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(400, "decision must be 'approve' or 'reject'")
    note = (payload.get("note") or "").strip()[:400] or None
    new_status = "approved" if decision == "approve" else "rejected"
    res = await db.admin_ai_repair_suggestions.update_one(
        {"_id": oid},
        {"$set": {
            "status": new_status,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "decided_by": user["id"],
            "decision_note": note,
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Suggestion not found")
    return {"ok": True, "status": new_status}


@router.post("/repair-suggestions/{suggestion_id}/mark-applied")
async def mark_applied(
    suggestion_id: str,
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    """Admin manually marks a previously-approved suggestion as applied (after they ran it).
    Optionally auto-resolves the linked finding.
    """
    try:
        oid = ObjectId(suggestion_id)
    except InvalidId:
        raise HTTPException(400, "Invalid suggestion id")
    sug = await db.admin_ai_repair_suggestions.find_one({"_id": oid})
    if not sug:
        raise HTTPException(404, "Suggestion not found")
    if sug.get("status") != "approved":
        raise HTTPException(400, "Doar sugestiile aprobate pot fi marcate ca aplicate.")
    note = (payload.get("note") or "").strip()[:400] or None
    auto_resolve = bool(payload.get("resolve_finding", True))
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.admin_ai_repair_suggestions.update_one(
        {"_id": oid},
        {"$set": {
            "status": "applied",
            "applied_at": now_iso,
            "applied_by": user["id"],
            "apply_note": note,
        }},
    )
    if auto_resolve and sug.get("finding_id"):
        try:
            fobj = ObjectId(sug["finding_id"])
            await db.admin_ai_findings.update_one(
                {"_id": fobj, "status": "open"},
                {"$set": {
                    "status": "resolved",
                    "resolved_at": now_iso,
                    "resolved_by": user["id"],
                    "resolved_by_name": user.get("name") or user.get("email"),
                    "resolution_note": f"Auto-rezolvat după aplicare repair: {note or '—'}",
                }},
            )
        except InvalidId:
            pass
    return {"ok": True}


@router.get("/repair-suggestions")
async def list_repair_suggestions(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    user: dict = Depends(require_role("admin")),
):
    filt = {}
    if status and status != "all":
        filt["status"] = status
    cursor = db.admin_ai_repair_suggestions.find(filt).sort("created_at", -1).limit(limit)
    items = [_serialize_repair(d) async for d in cursor]
    counts = {
        "proposed": await db.admin_ai_repair_suggestions.count_documents({"status": "proposed"}),
        "approved": await db.admin_ai_repair_suggestions.count_documents({"status": "approved"}),
        "rejected": await db.admin_ai_repair_suggestions.count_documents({"status": "rejected"}),
        "applied": await db.admin_ai_repair_suggestions.count_documents({"status": "applied"}),
    }
    return {"items": items, "counts": counts}


@router.get("/repair-suggestions/audit")
async def repair_audit_log(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_role("admin")),
):
    """Aggregate repair-suggestion effectiveness per finding pattern over the last N days.
    Returns rows so admin can see which AI suggestions actually work (high apply rate)
    and which patterns the LLM struggles with (high reject rate or low apply rate).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Per-pattern aggregation
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$finding_pattern",
            "total": {"$sum": 1},
            "proposed": {"$sum": {"$cond": [{"$eq": ["$status", "proposed"]}, 1, 0]}},
            "approved": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}},
            "applied": {"$sum": {"$cond": [{"$eq": ["$status", "applied"]}, 1, 0]}},
            "avg_minutes": {"$avg": "$estimated_minutes"},
            "avg_regenerations": {"$avg": "$regeneration_count"},
            "high_risk": {"$sum": {"$cond": [{"$eq": ["$risk_level", "high"]}, 1, 0]}},
            "last_label": {"$last": "$finding_label"},
            "last_created_at": {"$max": "$created_at"},
        }},
        {"$sort": {"total": -1}},
    ]

    rows = []
    async for r in db.admin_ai_repair_suggestions.aggregate(pipeline):
        total = r["total"] or 1
        applied = r["applied"]
        rejected = r["rejected"]
        approved_total = r["approved"] + applied  # approved (not yet applied) + applied
        # Effectiveness = applied / (decided)  where decided = approved+rejected+applied
        decided = approved_total + rejected
        effectiveness = round((applied / decided) * 100, 1) if decided else None
        rows.append({
            "pattern": r["_id"] or "unknown",
            "pattern_label": r.get("last_label") or r["_id"],
            "total": r["total"],
            "proposed": r["proposed"],
            "approved": r["approved"],
            "applied": r["applied"],
            "rejected": r["rejected"],
            "approve_rate_pct": round((approved_total / total) * 100, 1),
            "reject_rate_pct": round((rejected / total) * 100, 1),
            "apply_rate_pct": round((applied / total) * 100, 1),
            "effectiveness_pct": effectiveness,  # apply / decided (excludes proposed)
            "avg_minutes": round(r.get("avg_minutes") or 0, 1),
            "avg_regenerations": round(r.get("avg_regenerations") or 0, 2),
            "high_risk": r["high_risk"],
            "last_created_at": r["last_created_at"],
        })

    # Global totals
    totals = {
        "total": sum(r["total"] for r in rows),
        "applied": sum(r["applied"] for r in rows),
        "approved": sum(r["approved"] for r in rows),
        "rejected": sum(r["rejected"] for r in rows),
        "proposed": sum(r["proposed"] for r in rows),
    }
    decided_global = totals["applied"] + totals["approved"] + totals["rejected"]
    totals["global_effectiveness_pct"] = round((totals["applied"] / decided_global) * 100, 1) if decided_global else None
    totals["global_apply_rate_pct"] = round((totals["applied"] / totals["total"]) * 100, 1) if totals["total"] else 0
    totals["window_days"] = days

    # Highlight best & worst (only if pattern has ≥3 decided)
    best = None
    worst = None
    for r in rows:
        decided = r["approved"] + r["applied"] + r["rejected"]
        if decided < 3:
            continue
        eff = r["effectiveness_pct"]
        if eff is None:
            continue
        if best is None or eff > best["effectiveness_pct"]:
            best = r
        if worst is None or eff < worst["effectiveness_pct"]:
            worst = r

    return {
        "rows": rows,
        "totals": totals,
        "best_pattern": best,
        "worst_pattern": worst,
    }


@router.get("/repair-suggestions/by-pattern/{pattern}")
async def list_by_pattern(
    pattern: str,
    days: int = Query(90, ge=1, le=365),
    user: dict = Depends(require_role("admin")),
):
    """Drill-down: all suggestions for a given pattern in the window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor = db.admin_ai_repair_suggestions.find({
        "finding_pattern": pattern,
        "created_at": {"$gte": cutoff},
    }).sort("created_at", -1).limit(200)
    items = [_serialize_repair(d) async for d in cursor]
    return {"pattern": pattern, "items": items, "count": len(items)}


@router.get("/repair-suggestions/trend")
async def repair_trend(
    weeks: int = Query(4, ge=1, le=12),
    user: dict = Depends(require_role("admin")),
):
    """7×N heatmap of AI Repair Suggester effectiveness over time.
    Returns one cell per day for the last `weeks*7` days. Each cell has:
    - date (YYYY-MM-DD), weekday (0=Mon … 6=Sun), is_future (false here, but kept for symmetry)
    - count, applied, approved, rejected, decided
    - effectiveness_pct = applied / decided (null when decided==0)
    """
    days = weeks * 7
    # Anchor on Monday so heatmap aligns into clean week-columns
    today = datetime.now(timezone.utc).date()
    today_weekday = today.weekday()  # 0=Mon
    # Last cell is today; total days back = days-1
    start = today - timedelta(days=days - 1)
    cutoff_iso = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).isoformat()

    # Aggregate per day
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff_iso}}},
        {"$project": {
            "day": {"$substr": ["$created_at", 0, 10]},
            "status": 1,
        }},
        {"$group": {
            "_id": "$day",
            "count": {"$sum": 1},
            "applied": {"$sum": {"$cond": [{"$eq": ["$status", "applied"]}, 1, 0]}},
            "approved": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}},
        }},
    ]
    by_day = {}
    async for row in db.admin_ai_repair_suggestions.aggregate(pipeline):
        by_day[row["_id"]] = row

    cells = []
    for i in range(days):
        d = start + timedelta(days=i)
        key = d.isoformat()
        row = by_day.get(key, {})
        applied = row.get("applied", 0)
        approved = row.get("approved", 0)
        rejected = row.get("rejected", 0)
        decided = applied + approved + rejected
        cells.append({
            "date": key,
            "weekday": d.weekday(),
            "count": row.get("count", 0),
            "applied": applied,
            "approved": approved,
            "rejected": rejected,
            "decided": decided,
            "effectiveness_pct": round((applied / decided) * 100, 1) if decided else None,
        })

    # Rolling totals
    total_count = sum(c["count"] for c in cells)
    total_applied = sum(c["applied"] for c in cells)
    total_decided = sum(c["decided"] for c in cells)
    rolling_effectiveness = round((total_applied / total_decided) * 100, 1) if total_decided else None

    # Trend: compare last half vs first half effectiveness
    half = len(cells) // 2
    fst_applied = sum(c["applied"] for c in cells[:half])
    fst_decided = sum(c["decided"] for c in cells[:half])
    snd_applied = sum(c["applied"] for c in cells[half:])
    snd_decided = sum(c["decided"] for c in cells[half:])
    fst_eff = (fst_applied / fst_decided) * 100 if fst_decided else None
    snd_eff = (snd_applied / snd_decided) * 100 if snd_decided else None
    trend_delta = round(snd_eff - fst_eff, 1) if (fst_eff is not None and snd_eff is not None) else None

    return {
        "weeks": weeks,
        "days": days,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "cells": cells,
        "today_weekday": today_weekday,
        "totals": {
            "count": total_count,
            "applied": total_applied,
            "decided": total_decided,
            "rolling_effectiveness_pct": rolling_effectiveness,
            "trend_delta_pct": trend_delta,
            "first_half_effectiveness_pct": round(fst_eff, 1) if fst_eff is not None else None,
            "second_half_effectiveness_pct": round(snd_eff, 1) if snd_eff is not None else None,
        },
    }


# ============= CHAT WITH AI INVESTIGATOR =============

def _build_system_prompt() -> str:
    return """Ești "Investigator", un agent AI specializat în consilierea administratorilor platformei PropManage (o platformă de property management cu 4 roluri: Client, Specialist, Operator, Admin).

ROLUL TĂU:
- Răspunzi în română (utilizatorul preferă RO)
- Analizezi findings/anomalii detectate de scannerul determinist
- Răspunzi la întrebări despre starea platformei
- Sugerezi acțiuni — DAR NU EXECUȚI nimic. Adminul are control 100%.
- Ești concis, factual, fără floricele. Folosește bullet points și tabele când e util.

CONSTRÂNGERI CRITICE:
- NU inventa date. Dacă nu știi, spune "nu am această informație în contextul curent".
- NU promite acțiuni autonome — orice schimbare necesită aprobarea adminului.
- Pentru întrebări care necesită query în DB, sugerează ce filtru să folosească adminul în UI sau cere clarificări.

FORMAT RĂSPUNS:
- Începe cu un rezumat de 1 frază
- Apoi detalii structurate (bullets/numbered)
- Termină cu "Acțiuni sugerate:" doar dacă e relevant — fiecare prefixată cu severitate (🔴 urgent, 🟠 important, 🟡 monitorizare)"""


async def _get_findings_summary_for_context(limit: int = 30) -> str:
    """Build a compact text snapshot of current open findings to inject into LLM context."""
    cursor = db.admin_ai_findings.find({"status": "open"}).sort([
        ("severity", -1), ("occurrences", -1), ("last_seen_at", -1),
    ]).limit(limit)
    lines = []
    async for f in cursor:
        sev_icon = {"high": "🔴", "warning": "🟠", "low": "🟡"}.get(f.get("severity"), "·")
        lines.append(f"- {sev_icon} [{f.get('pattern')}] {f.get('entity_label')} (occurrences: {f.get('occurrences', 1)}, first seen: {f.get('first_seen_at', '?')[:10]})")
    if not lines:
        return "Niciun finding deschis în acest moment."
    return "FINDINGS DESCHISE CURENTE:\n" + "\n".join(lines)


@router.post("/chat/send")
async def chat_send(
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Send a chat message to the Investigator agent.
    Body: { session_id: str (optional, creates new if missing), message: str }
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY nu este configurat în /app/backend/.env")

    session_id = payload.get("session_id") or f"admin_ai_{user['id']}_{uuid.uuid4().hex[:8]}"
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        raise HTTPException(400, "Mesajul este gol.")

    # Load or create session
    sess = await db.admin_ai_sessions.find_one({"session_id": session_id})
    now_iso = datetime.now(timezone.utc).isoformat()
    if not sess:
        await db.admin_ai_sessions.insert_one({
            "session_id": session_id,
            "admin_id": user["id"],
            "admin_name": user.get("name") or user.get("email"),
            "created_at": now_iso,
            "last_message_at": now_iso,
            "message_count": 0,
            "title": user_message[:60],
        })

    # Save user message
    await db.admin_ai_messages.insert_one({
        "session_id": session_id,
        "role": "user",
        "content": user_message,
        "created_at": now_iso,
    })

    # Build context: findings snapshot + recent message history
    findings_snapshot = await _get_findings_summary_for_context()
    history_cursor = db.admin_ai_messages.find({"session_id": session_id}).sort("created_at", 1).limit(20)
    history = []
    async for m in history_cursor:
        history.append({"role": m["role"], "content": m["content"]})

    # Compose system message with live context
    system_msg = _build_system_prompt() + f"\n\n--- CONTEXT LIVE (snapshot la {now_iso}) ---\n{findings_snapshot}"

    # Call LLM
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_msg,
        ).with_model(DEFAULT_MODEL_PROVIDER, DEFAULT_MODEL_NAME)

        # Replay history except the latest user message (which we'll send fresh)
        # NOTE: emergentintegrations LlmChat keeps internal history per session_id.
        # We don't want to double up. So we just send the latest user message.
        response_text = await chat.send_message(UserMessage(text=user_message))
        provider_used = DEFAULT_MODEL_PROVIDER
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AI-Chat] LLM call failed: {e}")
        response_text = f"❌ Nu am putut contacta modelul AI. Eroare: {str(e)[:200]}\n\nPoți încerca din nou peste câteva secunde sau verifică EMERGENT_LLM_KEY în logs."
        provider_used = "error"

    # Save assistant message
    await db.admin_ai_messages.insert_one({
        "session_id": session_id,
        "role": "assistant",
        "content": response_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider_used,
    })
    await db.admin_ai_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"last_message_at": datetime.now(timezone.utc).isoformat()},
         "$inc": {"message_count": 2}},
    )

    return {
        "session_id": session_id,
        "message": response_text,
        "history": history + [{"role": "assistant", "content": response_text}],
    }


@router.get("/chat/sessions")
async def list_chat_sessions(user: dict = Depends(require_role("admin"))):
    cursor = db.admin_ai_sessions.find({"admin_id": user["id"]}).sort("last_message_at", -1).limit(30)
    items = []
    async for s in cursor:
        items.append({
            "session_id": s["session_id"],
            "title": s.get("title"),
            "created_at": s.get("created_at"),
            "last_message_at": s.get("last_message_at"),
            "message_count": s.get("message_count", 0),
        })
    return {"items": items}


@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: str,
    user: dict = Depends(require_role("admin")),
):
    sess = await db.admin_ai_sessions.find_one({"session_id": session_id})
    if not sess or sess.get("admin_id") != user["id"]:
        raise HTTPException(404, "Session not found")
    cursor = db.admin_ai_messages.find({"session_id": session_id}).sort("created_at", 1)
    msgs = []
    async for m in cursor:
        msgs.append({
            "role": m["role"],
            "content": m["content"],
            "created_at": m.get("created_at"),
        })
    return {"session_id": session_id, "messages": msgs, "title": sess.get("title")}


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    user: dict = Depends(require_role("admin")),
):
    sess = await db.admin_ai_sessions.find_one({"session_id": session_id})
    if not sess or sess.get("admin_id") != user["id"]:
        raise HTTPException(404, "Session not found")
    await db.admin_ai_sessions.delete_one({"session_id": session_id})
    await db.admin_ai_messages.delete_many({"session_id": session_id})
    return {"ok": True}


# ============= DAILY AUTO-SCAN + EMAIL DIGEST =============

async def run_daily_ai_digest():
    """Cron job: runs daily at 03:00 Europe/Bucharest. Auto-scans + emails digest to admin at 08:00.
    Split into 2 cron jobs in server.py: scan at 03:00, digest at 08:00.
    """
    try:
        summary = await run_full_scan(actor_id="system_cron")
        logger.info(f"[AI-DailyDigest] scan complete: {summary['new_findings']} new")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AI-DailyDigest] scan error: {e}")


async def send_daily_ai_digest_email():
    """Send digest email summarizing open findings to all admins (or ADMIN_EMAIL if no admin users)."""
    try:
        # Pick top 20 open findings ordered by severity then occurrences
        cursor = db.admin_ai_findings.find({"status": "open"}).sort([
            ("severity", -1), ("occurrences", -1), ("last_seen_at", -1),
        ]).limit(20)
        items = []
        async for f in cursor:
            items.append(f)
        if not items:
            logger.info("[AI-Digest] no open findings — skipping email")
            return

        # Get admin emails
        admin_emails = []
        async for u in db.users.find({"role": "admin"}, {"email": 1}):
            if u.get("email"):
                admin_emails.append(u["email"])
        if not admin_emails:
            admin_emails = [os.environ.get("ADMIN_EMAIL", "admin@propmanage.io")]

        # Build HTML body
        rows_html = ""
        for f in items:
            sev = f.get("severity")
            color = {"high": "#dc2626", "warning": "#fbbf24", "low": "#94a3b8"}.get(sev, "#94a3b8")
            sev_label = {"high": "URGENT", "warning": "ATENȚIE", "low": "INFO"}.get(sev, sev)
            rows_html += f"""
              <tr>
                <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; vertical-align:top;">
                  <span style="display:inline-block; padding:2px 8px; border-radius:999px; background:{color}22; color:{color}; font-size:10px; font-weight:bold;">{sev_label}</span>
                </td>
                <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; vertical-align:top;">
                  <div style="color:#fff; font-size:13px;">{f.get('label')}</div>
                  <div style="color:#a8a8b0; font-size:12px; margin-top:2px;">{f.get('entity_label')}</div>
                </td>
                <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; text-align:right; vertical-align:top; color:#888893; font-size:11px;">
                  {f.get('occurrences', 1)}x
                </td>
              </tr>
            """

        from email_service import _layout, send_email as _send_email  # type: ignore
        body_html = f"""
          <p>Bună,</p>
          <p>Investigatorul AI a scanat platforma și a detectat <strong>{len(items)} anomalii deschise</strong>. Sumar:</p>
          <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:14px; margin:18px 0;">
            <tr style="background:#0f0f12;">
              <th style="padding:10px 12px; text-align:left; font-size:11px; color:#888893; letter-spacing:0.5px;">SEVERITATE</th>
              <th style="padding:10px 12px; text-align:left; font-size:11px; color:#888893; letter-spacing:0.5px;">FINDING</th>
              <th style="padding:10px 12px; text-align:right; font-size:11px; color:#888893; letter-spacing:0.5px;">OCURENȚE</th>
            </tr>
            {rows_html}
          </table>
          <p style="color:#a8a8b0; font-size:13px;">Deschide consola admin pentru a vedea detalii complete, a aproba acțiuni sau a marca finding-uri ca rezolvate:</p>
          <p><a href="https://propmanage.ro/admin" style="display:inline-block; padding:12px 24px; background:#d4ff3a; color:#000; text-decoration:none; border-radius:8px; font-weight:bold;">Deschide AI Console</a></p>
        """
        html = _layout(
            title="🤖 Daily AI Investigator Digest",
            preheader=f"{len(items)} anomalii deschise pe platformă",
            body_html=body_html,
        )
        subject = f"[PropManage AI] {len(items)} anomalii deschise · digest zilnic"
        result = await _send_email(admin_emails, subject, html)
        logger.info(f"[AI-Digest] email sent to {len(admin_emails)} admin(s) via {result.get('provider')}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AI-Digest] error: {e}")


# ============= REPAIR EFFECTIVENESS LOW ALERT (Phase 47D) =============
# Cron-driven email alert when rolling AI effectiveness drops below a threshold.
# Reuses the same window logic as /repair-suggestions/trend.

DEFAULT_ALERT_CONFIG = {
    "enabled": False,
    "threshold_pct": 50,           # alert if rolling effectiveness < this
    "window_days": 7,              # rolling window
    "min_decided": 3,              # require at least this many decided suggestions
    "recipients": [],              # email list; falls back to admin users when empty
    "last_sent_at": None,
    "last_state": None,            # {effectiveness_pct, applied, decided, alert_triggered, ...}
    "last_check_at": None,
}


async def _get_alert_config() -> dict:
    doc = await db.admin_ai_alert_config.find_one({"_id": "global"})
    if not doc:
        return dict(DEFAULT_ALERT_CONFIG)
    merged = dict(DEFAULT_ALERT_CONFIG)
    merged.update({k: v for k, v in doc.items() if k != "_id"})
    return merged


async def _save_alert_config(updates: dict, actor_id: str):
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = actor_id
    await db.admin_ai_alert_config.update_one({"_id": "global"}, {"$set": updates}, upsert=True)


async def _compute_rolling_effectiveness(days: int) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        # Decontamination: exclude synthetic seed rows (fabricated by auto-tune
        # to inflate effectiveness). Real decisions only.
        {"$match": {"created_at": {"$gte": cutoff}, "synthetic_for_score_seed": {"$ne": True}}},
        {"$group": {
            "_id": None,
            "applied": {"$sum": {"$cond": [{"$eq": ["$status", "applied"]}, 1, 0]}},
            "approved": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}},
            "total": {"$sum": 1},
        }},
    ]
    res = None
    async for r in db.admin_ai_repair_suggestions.aggregate(pipeline):
        res = r
    if not res:
        return {"applied": 0, "approved": 0, "rejected": 0, "total": 0, "decided": 0, "effectiveness_pct": None}
    decided = res["applied"] + res["approved"] + res["rejected"]
    eff = round((res["applied"] / decided) * 100, 1) if decided else None
    return {
        "applied": res["applied"], "approved": res["approved"], "rejected": res["rejected"],
        "total": res["total"], "decided": decided, "effectiveness_pct": eff,
    }


async def _resolve_alert_recipients(cfg: dict) -> list:
    recipients = list(cfg.get("recipients") or [])
    if recipients:
        return recipients
    # Fallback: admin users
    async for u in db.users.find({"role": "admin"}, {"email": 1}):
        if u.get("email"):
            recipients.append(u["email"])
    if not recipients:
        recipients = [os.environ.get("ADMIN_EMAIL", "admin@propmanage.io")]
    return recipients


def _build_alert_email_html(state: dict, cfg: dict) -> str:
    eff = state.get("effectiveness_pct")
    eff_str = f"{eff}%" if eff is not None else "—"
    color = "#dc2626" if (eff is not None and eff < cfg["threshold_pct"]) else "#fbbf24"
    body_html = f"""
      <p>Bună,</p>
      <p>Sistemul AI Repair Suggester are <strong>eficacitate scăzută</strong> în ultimele {cfg['window_days']} zile.</p>
      <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:14px; margin:18px 0;">
        <tr>
          <td style="padding:18px 22px;">
            <div style="color:#888893; font-size:11px; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:6px;">Eficacitate rolling ({cfg['window_days']}z)</div>
            <div style="color:{color}; font-size:42px; font-weight:bold; line-height:1;">{eff_str}</div>
            <div style="color:#a8a8b0; font-size:12px; margin-top:6px;">Prag configurat: <b>{cfg['threshold_pct']}%</b></div>
          </td>
          <td style="padding:18px 22px; border-left:1px solid #2a2a30;">
            <div style="color:#888893; font-size:11px; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:6px;">Detalii sugestii</div>
            <div style="color:#fff; font-size:13px; line-height:1.8;">
              Total: <b>{state.get('total', 0)}</b><br>
              Aplicate: <b style="color:#60a5fa;">{state.get('applied', 0)}</b><br>
              Aprobate: <b style="color:#34d399;">{state.get('approved', 0)}</b><br>
              Respinse: <b style="color:#f87171;">{state.get('rejected', 0)}</b>
            </div>
          </td>
        </tr>
      </table>
      <p style="color:#a8a8b0; font-size:13px;">Recomandări:</p>
      <ul style="color:#a8a8b0; font-size:13px;">
        <li>Verifică în Repair Audit Log care pattern-uri au eficacitate < 30% și ajustează prompt-ul.</li>
        <li>Marchează manual sugestiile vechi care nu au fost aplicate (cleanup).</li>
        <li>Regenerează sugestiile pentru finding-urile critice cu risc mare.</li>
      </ul>
      <p><a href="{os.environ.get('APP_PUBLIC_URL', 'https://propmanage.io')}/admin" style="display:inline-block; padding:12px 24px; background:#d4ff3a; color:#000; text-decoration:none; border-radius:8px; font-weight:bold;">Deschide AI Console</a></p>
    """
    return body_html


async def _send_effectiveness_alert_email(state: dict, cfg: dict, dry_run: bool = False) -> dict:
    from email_service import _layout, send_email as _send_email  # type: ignore
    recipients = await _resolve_alert_recipients(cfg)
    eff = state.get("effectiveness_pct")
    subject = f"[PropManage AI] Eficacitate AI scăzută: {eff}% (prag {cfg['threshold_pct']}%)"
    html = _layout(
        title="⚠️ Eficacitate AI sub prag",
        preheader=f"Eficacitate {eff}% în ultimele {cfg['window_days']}z (prag {cfg['threshold_pct']}%)",
        body_html=_build_alert_email_html(state, cfg),
    )
    if dry_run:
        return {"dry_run": True, "recipients": recipients, "subject": subject, "preview_chars": len(html)}
    result = await _send_email(recipients, subject, html)
    return {"dry_run": False, "recipients": recipients, "subject": subject, "provider": result.get("provider")}


async def run_ai_effectiveness_alert_check(force: bool = False, dry_run: bool = False) -> dict:
    cfg = await _get_alert_config()
    if not cfg.get("enabled") and not force:
        return {"skipped": True, "reason": "disabled"}
    state = await _compute_rolling_effectiveness(cfg["window_days"])
    state["alert_triggered"] = False
    state["checked_at"] = datetime.now(timezone.utc).isoformat()
    decided = state.get("decided", 0)
    eff = state.get("effectiveness_pct")
    if decided < cfg["min_decided"]:
        state["skip_reason"] = f"only {decided} decisions (need ≥{cfg['min_decided']})"
        await _save_alert_config({"last_state": state, "last_check_at": state["checked_at"]}, actor_id="system_cron")
        return {"skipped": True, **state}
    if eff is None or eff >= cfg["threshold_pct"]:
        state["skip_reason"] = "above threshold"
        await _save_alert_config({"last_state": state, "last_check_at": state["checked_at"]}, actor_id="system_cron")
        return {"skipped": True, **state}

    # Dedupe per ISO week unless force=true
    iso_week = datetime.now(timezone.utc).strftime("%G-W%V")
    if not force and cfg.get("last_sent_week") == iso_week:
        state["skip_reason"] = f"already sent this week ({iso_week})"
        await _save_alert_config({"last_state": state, "last_check_at": state["checked_at"]}, actor_id="system_cron")
        return {"skipped": True, **state}

    send_result = await _send_effectiveness_alert_email(state, cfg, dry_run=dry_run)
    state["alert_triggered"] = True
    state["last_sent_at"] = datetime.now(timezone.utc).isoformat() if not dry_run else None
    state["last_sent_to"] = send_result.get("recipients")
    updates = {
        "last_state": state,
        "last_check_at": state["checked_at"],
    }
    if not dry_run:
        updates["last_sent_at"] = state["last_sent_at"]
        updates["last_sent_week"] = iso_week
        # Append to history
        await db.admin_ai_alert_history.insert_one({
            "sent_at": state["last_sent_at"],
            "state": state,
            "cfg_snapshot": {k: cfg.get(k) for k in ("threshold_pct", "window_days", "min_decided", "recipients")},
            "iso_week": iso_week,
        })
    await _save_alert_config(updates, actor_id="system_cron")
    return {"sent": not dry_run, **state, "send_result": send_result}


# ----- REST endpoints -----

@router.get("/effectiveness-alert/config")
async def get_alert_cfg(user: dict = Depends(require_role("admin"))):
    return await _get_alert_config()


@router.put("/effectiveness-alert/config")
async def put_alert_cfg(payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    allowed = {"enabled", "threshold_pct", "window_days", "min_decided", "recipients"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    # Validate
    if "threshold_pct" in updates:
        try: updates["threshold_pct"] = max(0, min(100, int(updates["threshold_pct"])))
        except (TypeError, ValueError): raise HTTPException(400, "threshold_pct must be int 0..100")
    if "window_days" in updates:
        try: updates["window_days"] = max(1, min(60, int(updates["window_days"])))
        except (TypeError, ValueError): raise HTTPException(400, "window_days must be int 1..60")
    if "min_decided" in updates:
        try: updates["min_decided"] = max(1, int(updates["min_decided"]))
        except (TypeError, ValueError): raise HTTPException(400, "min_decided must be positive int")
    if "recipients" in updates:
        if not isinstance(updates["recipients"], list):
            raise HTTPException(400, "recipients must be a list")
        emails = []
        for e in updates["recipients"]:
            s = str(e or "").strip().lower()
            if s and "@" in s and "." in s:
                emails.append(s)
        updates["recipients"] = emails[:25]
    await _save_alert_config(updates, user["id"])
    return await _get_alert_config()


@router.post("/effectiveness-alert/test")
async def test_alert(payload: dict = Body(default={}), user: dict = Depends(require_role("admin"))):
    """Body: {dry_run: bool=true, force: bool=true}"""
    dry_run = payload.get("dry_run", True)
    force = payload.get("force", True)
    return await run_ai_effectiveness_alert_check(force=force, dry_run=dry_run)


@router.get("/effectiveness-alert/history")
async def alert_history(limit: int = Query(20, le=100), user: dict = Depends(require_role("admin"))):
    cursor = db.admin_ai_alert_history.find({}).sort("sent_at", -1).limit(limit)
    items = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        items.append(d)
    return {"items": items}


# ============= AI HEALTH SCORE (Phase 47E) =============
# Combines 3 sub-scores into single 0-100 platform-AI fitness score.
# All computed on-the-fly from existing collections. No new storage required.

SEVERITY_WEIGHTS = {"critical": 25, "high": 10, "warning": 3, "medium": 3, "info": 1, "low": 1}


async def _compute_findings_score(days: int = 7) -> dict:
    """Lower open weighted-severity = higher score. 0 findings = 100, ≥100 weight pts = 0."""
    cursor = db.admin_ai_findings.find({"status": "open"}, {"severity": 1})
    weight = 0
    by_severity = {"critical": 0, "high": 0, "warning": 0, "medium": 0, "info": 0, "low": 0}
    async for f in cursor:
        sev = (f.get("severity") or "info").lower()
        by_severity[sev] = by_severity.get(sev, 0) + 1
        weight += SEVERITY_WEIGHTS.get(sev, 1)
    score = max(0, min(100, round(100 - weight)))
    return {
        "score": score,
        "weight_total": weight,
        "by_severity": by_severity,
        "total_open": sum(by_severity.values()),
    }


async def _compute_effectiveness_score(days: int = 7) -> dict:
    """Rolling effectiveness = applied / decided. Score = pct directly. If no decisions → neutral 70."""
    res = await _compute_rolling_effectiveness(days)
    eff = res.get("effectiveness_pct")
    if eff is None:
        return {"score": 70, "effectiveness_pct": None, "neutral": True, **res}
    return {"score": round(eff), "effectiveness_pct": eff, "neutral": False, **res}


async def _compute_concierge_score(days: int = 7) -> dict:
    """Higher block_rate = lower score. Score = 100 - block_rate_pct, floored at 30."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    # Decontamination: exclude synthetic seed messages (fabricated by auto-tune
    # to force block_rate=0 → concierge score 100). Real traffic only.
    total = await db.concierge_messages.count_documents({
        "created_at": {"$gte": cutoff}, "role": "assistant",
        "synthetic_for_score_seed": {"$ne": True},
    })
    if total == 0:
        return {"score": 80, "total": 0, "blocked": 0, "block_rate_pct": None, "neutral": True}
    blocked = await db.concierge_messages.count_documents({
        "created_at": {"$gte": cutoff},
        "role": "assistant",
        "blocked": True,
        "synthetic_for_score_seed": {"$ne": True},
    })
    block_rate = round((blocked / total) * 100, 1)
    score = max(30, min(100, round(100 - block_rate * 2)))  # 2x weight on block rate
    return {"score": score, "total": total, "blocked": blocked, "block_rate_pct": block_rate, "neutral": False}


def _grade(score: int) -> str:
    if score >= 90: return "Excelent"
    if score >= 75: return "Bună"
    if score >= 60: return "Acceptabilă"
    if score >= 40: return "Atenție"
    return "Critică"


def _grade_color(score: int) -> str:
    if score >= 75: return "emerald"
    if score >= 60: return "amber"
    return "red"


@router.get("/health-score")
async def health_score(
    days: int = Query(7, ge=1, le=30),
    user: dict = Depends(require_role("admin")),
):
    f = await _compute_findings_score(days)
    e = await _compute_effectiveness_score(days)
    c = await _compute_concierge_score(days)
    # Weighted overall: findings 40%, effectiveness 35%, concierge 25%.
    overall = round(0.40 * f["score"] + 0.35 * e["score"] + 0.25 * c["score"])

    # Trend: snapshot per day for the last 14 days (lightweight — uses same counts).
    trend = []
    today = datetime.now(timezone.utc).date()
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_iso = day.isoformat()
        # Use simplified per-day: open findings as of *end of day* is expensive; instead, store today's snapshot.
        # For trend, we read from db.admin_ai_health_history if present; else only today's data point.
        snap = await db.admin_ai_health_history.find_one({"day": day_iso})
        if snap:
            trend.append({"day": day_iso, "overall": snap["overall"], "f": snap.get("findings_score"), "e": snap.get("effectiveness_score"), "c": snap.get("concierge_score")})

    # Persist today's snapshot (idempotent upsert per day)
    today_iso = today.isoformat()
    await db.admin_ai_health_history.update_one(
        {"day": today_iso},
        {"$set": {
            "day": today_iso,
            "overall": overall,
            "findings_score": f["score"],
            "effectiveness_score": e["score"],
            "concierge_score": c["score"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    # Re-fetch trend to include today (after upsert)
    trend = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_iso = day.isoformat()
        snap = await db.admin_ai_health_history.find_one({"day": day_iso})
        if snap:
            trend.append({"day": day_iso, "overall": snap["overall"], "f": snap.get("findings_score"), "e": snap.get("effectiveness_score"), "c": snap.get("concierge_score")})

    delta_7d = None
    if len(trend) >= 2:
        # Compare today's overall vs ~7 days ago (or earliest available)
        oldest = trend[max(0, len(trend) - 8)]["overall"] if len(trend) > 7 else trend[0]["overall"]
        delta_7d = overall - oldest

    return {
        "overall": overall,
        "grade": _grade(overall),
        "color": _grade_color(overall),
        "delta_7d": delta_7d,
        "window_days": days,
        "metrics": {
            "findings": {**f, "weight": 0.40, "label": "Findings deschise"},
            "effectiveness": {**e, "weight": 0.35, "label": "Eficacitate Repair AI"},
            "concierge": {**c, "weight": 0.25, "label": "Concierge — block rate"},
        },
        "trend": trend,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
