"""PropManage — Architecture Review Board (P3)

A lightweight pre-build gate. Before writing code for a new feature/module, you
submit the idea here. The board:
  1. Indexes ALL existing modules (admin pages, backend routers, future ideas
     proposals) into a compact catalog.
  2. Sends the idea + catalog to Claude with a strict overlap detection prompt.
  3. Returns: overlap_score (0-100), overlapping_modules (with reasons),
     verdict (build_new | extend_existing | merge_proposal | reject_duplicate),
     suggested_actions.
  4. Persists every review in `architecture_reviews` collection.

Goal: prevent module proliferation / dead code accumulation. Aligned with the
deprecation strategy — instead of building V2 from scratch, extend or merge.
"""
import logging
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from ai_core.provider import call_llm
from ai_governance.agent_registry import get_agents

logger = logging.getLogger("propmanage.architecture_board")
router = APIRouter(prefix="/api/admin/architecture-board", tags=["architecture-board"])

REVIEWS_COLLECTION = "architecture_reviews"

# Curated catalog of major existing modules (kept short on purpose — too much
# context dilutes the LLM's overlap detection).
MODULES_CATALOG = [
    {"slug": "verified_estate", "name": "Imobile Verificate", "kind": "module", "summary": "Marketplace listings with audit + Digital Twin certification, Stripe checkout, Kanban moderation."},
    {"slug": "marketplace_requests", "name": "Marketplace Specialists", "kind": "module", "summary": "Client requests + specialist matching + lead fee + chat."},
    {"slug": "digital_twin", "name": "Digital Twin (3D Viewer)", "kind": "module", "summary": "Three.js + Blender + Matterport/Sketchfab embeds; Q&A AI on twin context."},
    {"slug": "qa_copilot", "name": "QA Copilot", "kind": "ai_agent", "summary": "Claude-powered manual QA session structuring + prompt generator."},
    {"slug": "ai_dev_team", "name": "AI Dev Team", "kind": "ai_agent", "summary": "4 specialized Claude agents (FE/BE/QA/Security) analyzing code files."},
    {"slug": "ai_security_center", "name": "AI Security Center", "kind": "ai_agent", "summary": "Threat scoring + Claude-powered recommendations."},
    {"slug": "ai_control_center", "name": "AI Control Center", "kind": "ai_agent", "summary": "Provider switching, memory browser, bug search, knowledge graph."},
    {"slug": "ai_governance", "name": "AI Governance Center", "kind": "ai_agent", "summary": "Read-only observability + deprecation plan + permissions matrix + health monitoring."},
    {"slug": "founder_gate", "name": "Founder Approval Gate", "kind": "governance", "summary": "Foundation registry of 13 critical actions (FG-0 done). Twilio SMS DEFERRED."},
    {"slug": "future_ideas", "name": "Future Ideas Vault", "kind": "governance", "summary": "Strategic R&D proposals catalog with status tracking + decision log + weekly digest."},
    {"slug": "deprecation_pulse", "name": "Deprecation Pulse", "kind": "governance", "summary": "Weekly email digest of upcoming agent retirements + provider risk."},
    {"slug": "bug_memory", "name": "Bug Memory Aggregator", "kind": "module", "summary": "Unified view across QA findings + AI investigator findings."},
    {"slug": "autonomy_engine", "name": "Autonomy Engine", "kind": "ai_agent", "summary": "Daily scoring + recommendations (operational/technical/security/dev/ai)."},
    {"slug": "auto_match", "name": "Auto-Match Engine", "kind": "module", "summary": "Hourly cron: matches specialists with client requests."},
    {"slug": "weekly_briefing", "name": "Weekly AI Briefing", "kind": "module", "summary": "Mondays 09:00 — executive email summary of AI activity."},
    {"slug": "verified_estate_emails", "name": "Email Sequences (drip + newsletter)", "kind": "module", "summary": "Drip reminder + weekly newsletter for verified estate."},
    {"slug": "documentation", "name": "Admin Documentation", "kind": "module", "summary": "In-app manual with RAG AI assistant."},
    {"slug": "service_contracts", "name": "Service Contracts", "kind": "module", "summary": "Romanian template contract + e-sign + operator mediation."},
    {"slug": "settings_snapshots", "name": "Settings Snapshots", "kind": "module", "summary": "Daily snapshot + restore (with pre_restore safety snapshot)."},
    {"slug": "gdpr_pack", "name": "GDPR Pack", "kind": "module", "summary": "Data export + consent log + deletion request workflow."},
]


class ReviewIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    proposed_scope: str = Field(default="", max_length=1000)


def _build_system_prompt() -> str:
    return (
        "Ești Architecture Review Board, un agent care evaluează propuneri de feature-uri noi pe platforma "
        "PropManage și detectează suprapuneri cu module existente. "
        "Răspunde STRICT în JSON valid (fără markdown, fără text introductiv) cu schema: "
        '{"overlap_score": int 0-100, "verdict": "build_new"|"extend_existing"|"merge_proposal"|"reject_duplicate", '
        '"overlapping_modules": [{"slug": string, "name": string, "reason": string, "weight": int 0-100}], '
        '"suggested_actions": [string], "rationale": string, "risk_of_redundancy": "low"|"medium"|"high"}. '
        "Reguli: overlap_score 0 = idee complet nouă, 100 = duplicat complet. "
        "verdict 'extend_existing' = recomandat când >50% suprapunere. "
        "Răspunde în română. Maxim 3 module overlapping. Maxim 4 suggested_actions concrete."
    )


def _build_user_prompt(payload: ReviewIn, catalog: list) -> str:
    catalog_block = "\n".join([
        f"- {m['slug']} ({m['kind']}) :: {m['name']} :: {m['summary']}"
        for m in catalog
    ])
    return (
        f"# Propunere de evaluat\n"
        f"**Titlu**: {payload.title}\n\n"
        f"**Descriere**: {payload.description}\n\n"
        f"**Scope propus**: {payload.proposed_scope or '(nedefinit)'}\n\n"
        f"# Catalog module existente PropManage ({len(catalog)})\n"
        f"{catalog_block}\n\n"
        f"Analizează propunerea și detectează SUPRAPUNERI. Returnează JSON conform schemei."
    )


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from LLM output."""
    if not text:
        return None
    # Strip markdown code fence
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        # Try to find first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                pass
    return None


async def _augmented_catalog() -> list:
    """Combine static catalog with AI agents from registry (auto-discovery)."""
    cat = list(MODULES_CATALOG)
    static_slugs = {m["slug"] for m in cat}
    for agent in get_agents():
        if agent["slug"] in static_slugs:
            continue
        cat.append({
            "slug": agent["slug"],
            "name": agent["name"],
            "kind": "ai_agent",
            "summary": agent.get("purpose", "")[:140],
        })
    return cat


@router.get("/catalog")
async def get_catalog(user=Depends(require_role("admin"))):
    """Return the combined module catalog used for overlap detection."""
    cat = await _augmented_catalog()
    return {"items": cat, "count": len(cat)}


@router.post("/review")
async def submit_review(payload: ReviewIn, user=Depends(require_role("admin"))):
    """Submit a new feature/idea for overlap review."""
    catalog = await _augmented_catalog()
    system = _build_system_prompt()
    user_msg = _build_user_prompt(payload, catalog)

    llm_result = await call_llm(
        system_message=system,
        user_message=user_msg,
        session_id=f"arch-board-{uuid.uuid4().hex[:8]}",
        override={"model": "claude-haiku-4-5", "max_tokens": 1500},
    )
    raw_text = llm_result.get("text", "")
    parsed = _extract_json(raw_text)
    error = None
    if not parsed:
        # Deterministic fallback so the UI never breaks completely
        error = llm_result.get("error") or "LLM returned non-JSON output"
        parsed = {
            "overlap_score": 0,
            "verdict": "build_new",
            "overlapping_modules": [],
            "suggested_actions": ["LLM nedisponibil — review manual recomandat."],
            "rationale": f"Fallback determinist (motiv: {error[:120]}). Verifică manual catalog-ul.",
            "risk_of_redundancy": "medium",
        }

    review_doc = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "proposed_scope": payload.proposed_scope,
        "submitted_by": user.get("email"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "llm_provider": llm_result.get("provider"),
        "llm_model": llm_result.get("model"),
        "llm_error": error,
        "result": parsed,
        "raw_response_preview": raw_text[:1000] if raw_text else None,
    }
    await db[REVIEWS_COLLECTION].insert_one({**review_doc})
    review_doc.pop("_id", None)
    return review_doc


@router.get("/reviews")
async def list_reviews(limit: int = 30, user=Depends(require_role("admin"))):
    cursor = db[REVIEWS_COLLECTION].find({}, {"_id": 0, "raw_response_preview": 0}).sort("submitted_at", -1).limit(limit)
    items = []
    async for d in cursor:
        items.append(d)
    return {"items": items, "count": len(items)}


@router.get("/reviews/{review_id}")
async def get_review(review_id: str, user=Depends(require_role("admin"))):
    doc = await db[REVIEWS_COLLECTION].find_one({"id": review_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Review not found")
    return doc


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, user=Depends(require_role("admin"))):
    res = await db[REVIEWS_COLLECTION].delete_one({"id": review_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Review not found")
    return {"ok": True}
