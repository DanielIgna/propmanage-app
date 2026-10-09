"""QA Content Audit — detects audience-mismatch in docs and persists conflicts.

When the AI is uncertain a doc paragraph fits its target role (client/specialist/
operator/admin), it flags a `doc_conflict`. Admins review and either approve a
suggested rewrite or dismiss the false-positive — all from the QA Playbook UI.

Approved fixes are stored as `db.doc_overrides` keyed by (doc_slug, section_heading,
block_index). The doc renderer (PDF, MD, HTML) prefers the override when present,
so we can patch documentation WITHOUT modifying source code.
"""
from __future__ import annotations

import os
import re
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from db import db
from docs_content import DOCS_CONTENT

logger = logging.getLogger("propmanage.content_audit")


# ----------------------------------------------------------------------------
# Heuristic audience-mismatch detectors (deterministic, fast — no AI required)
# ----------------------------------------------------------------------------

# Phrases that strongly suggest a client/payer perspective
_CLIENT_PERSPECTIVE_HINTS = [
    r"banii pe care îi plătești",
    r"plătești specialistului",
    r"NU ajung la specialist",
    r"banii se rambursează",
    r"protecția ta",  # used in client context
    r"cum aleg specialistul",
    r"găsești cel mai bun specialist",
    r"găsesc specialistul",
]

# Phrases that strongly suggest a specialist/payee perspective
_SPECIALIST_PERSPECTIVE_HINTS = [
    r"comisionul tău",
    r"95% din sumă ajunge",
    r"lead fee",
    r"badge VERIFIED",
    r"ești plătit",
    r"primești plata",
    r"cum câștigi",
    r"trust score-ul tău",
    r"completează-ți profilul",
]

# Phrases that strongly suggest admin/internal
_ADMIN_PERSPECTIVE_HINTS = [
    r"backend/",
    r"emergent llm key",
    r"supervisor",
    r"mongoDB",
    r"apscheduler",
    r"audit log",
    r"impersonare",
]


def _scan_text_for_audience(text: str) -> dict:
    """Return counts of hits per audience category in a text fragment."""
    t = text.lower() if isinstance(text, str) else ""
    counts = {
        "client": sum(1 for p in _CLIENT_PERSPECTIVE_HINTS if re.search(p.lower(), t)),
        "specialist": sum(1 for p in _SPECIALIST_PERSPECTIVE_HINTS if re.search(p.lower(), t)),
        "admin": sum(1 for p in _ADMIN_PERSPECTIVE_HINTS if re.search(p.lower(), t)),
    }
    return counts


def _block_text(block) -> str:
    """Flatten any block (str / dict) into a searchable string."""
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return ""
    parts = [block.get("title", ""), block.get("body", ""), block.get("text", ""), block.get("caption", "")]
    items = block.get("items") or []
    for it in items:
        if isinstance(it, str):
            parts.append(it)
        elif isinstance(it, dict):
            parts.append(it.get("title", ""))
            parts.append(it.get("body", ""))
    return " ".join(p for p in parts if p)


# ----------------------------------------------------------------------------
# Audit one doc
# ----------------------------------------------------------------------------

def audit_doc(slug: str) -> list[dict]:
    """Audit one doc; return list of conflict dicts (NOT persisted yet)."""
    doc = DOCS_CONTENT.get(slug)
    if not doc:
        return []
    role = doc.get("role", "")
    conflicts = []
    for sec_idx, section in enumerate(doc.get("sections", [])):
        heading = section.get("heading", "")
        for blk_idx, block in enumerate(section.get("body", []) or []):
            text = _block_text(block)
            if len(text) < 30:
                continue
            counts = _scan_text_for_audience(text)
            wrong_audience = None
            severity = None
            # Specialist doc with client-perspective hints → wrong audience
            if role == "specialist" and counts["client"] >= 1 and counts["specialist"] == 0:
                wrong_audience = "client"
                severity = "high" if counts["client"] >= 2 else "medium"
            elif role == "client" and counts["specialist"] >= 2 and counts["client"] == 0:
                wrong_audience = "specialist"
                severity = "medium"
            elif role in ("client", "specialist") and counts["admin"] >= 2 and (counts["client"] + counts["specialist"]) == 0:
                wrong_audience = "admin"
                severity = "low"
            if wrong_audience:
                conflicts.append({
                    "doc_slug": slug,
                    "doc_role": role,
                    "section_index": sec_idx,
                    "section_heading": heading,
                    "block_index": blk_idx,
                    "block_excerpt": text[:300],
                    "wrong_audience": wrong_audience,
                    "severity": severity,
                    "hint_counts": counts,
                })
    return conflicts


def audit_all_docs() -> list[dict]:
    """Audit every doc in the registry."""
    out = []
    for slug in DOCS_CONTENT.keys():
        out.extend(audit_doc(slug))
    return out


# ----------------------------------------------------------------------------
# Conflict persistence
# ----------------------------------------------------------------------------

CONFLICT_STATUSES = ("open", "approved", "dismissed", "fixed")


def _conflict_key(c: dict) -> str:
    return f"{c['doc_slug']}::{c['section_index']}::{c['block_index']}"


async def persist_conflicts(conflicts: list[dict]) -> dict:
    """Insert NEW conflicts; skip existing ones. Returns counts."""
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    existing = 0
    for c in conflicts:
        key = _conflict_key(c)
        already = await db.doc_conflicts.find_one({"key": key, "status": {"$in": ["open", "approved"]}})
        if already:
            existing += 1
            continue
        await db.doc_conflicts.insert_one({
            **c,
            "key": key,
            "id": uuid.uuid4().hex[:12],
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "ai_suggested_fix": None,
            "applied_at": None,
        })
        added += 1
    return {"added": added, "already_existing": existing, "total_scanned": len(conflicts)}


async def list_conflicts(status: Optional[str] = None) -> list[dict]:
    q = {}
    if status:
        q["status"] = status
    cur = db.doc_conflicts.find(q).sort("created_at", -1).limit(200)
    out = []
    async for r in cur:
        r.pop("_id", None)
        out.append(r)
    return out


async def update_conflict_status(conflict_id: str, status: str, actor: str) -> Optional[dict]:
    if status not in CONFLICT_STATUSES:
        raise ValueError("invalid status")
    now = datetime.now(timezone.utc).isoformat()
    res = await db.doc_conflicts.find_one_and_update(
        {"id": conflict_id},
        {"$set": {"status": status, "updated_at": now, "updated_by": actor}},
        return_document=True,
    )
    if res is None:
        return None
    res.pop("_id", None)
    return res


# ----------------------------------------------------------------------------
# AI-generated fix (Claude Sonnet 4.5 via Emergent LLM Key)
# ----------------------------------------------------------------------------

async def ai_suggest_fix(conflict_id: str) -> dict:
    conflict = await db.doc_conflicts.find_one({"id": conflict_id})
    if not conflict:
        return {"error": "not found"}
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"error": "ANTHROPIC_API_KEY missing"}
    prompt = f"""Manualul `{conflict['doc_slug']}` are rolul `{conflict['doc_role']}`.
Acest paragraf pare scris din perspectiva audienței greșite (`{conflict['wrong_audience']}`).
Secțiune: {conflict['section_heading']}
Paragraf actual:
\"\"\"
{conflict['block_excerpt']}
\"\"\"

Rescrie paragraful din perspectiva audienței CORECTE (rolul docului = `{conflict['doc_role']}`).
Păstrează aceleași informații (escrow, comisioane, garanții), dar schimbă pronumele și unghiul.
Răspunde STRICT cu un JSON: {{"title": "...", "body": "..."}}. Fără markdown, fără fences."""
    try:
        from llm_chat import LlmChat, UserMessage
        chat = (LlmChat(
            api_key=key,
            session_id=f"doc-fix-{conflict_id}",
            system_message="Ești un editor senior de documentație. Rescrii pasaje pentru a se potrivi audienței corecte, fără a pierde informații utile.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929"))
        resp = await chat.send_message(UserMessage(text=prompt))
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", resp.strip())
        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if not m:
                return {"error": "AI returned non-JSON", "raw": resp[:400]}
            data = json.loads(m.group(0))
        title = (data.get("title") or "").strip()[:200]
        body = (data.get("body") or "").strip()[:2000]
        if not body:
            return {"error": "AI returned empty body", "raw": resp[:400]}
        await db.doc_conflicts.update_one(
            {"id": conflict_id},
            {"$set": {"ai_suggested_fix": {"title": title, "body": body}, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"title": title, "body": body}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[content-audit] AI fix failed for {conflict_id}: {e}")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


# ----------------------------------------------------------------------------
# Apply fix — store override in db.doc_overrides (no source-code mutation)
# ----------------------------------------------------------------------------

async def apply_fix(conflict_id: str, actor: str, custom_body: Optional[str] = None, custom_title: Optional[str] = None) -> dict:
    conflict = await db.doc_conflicts.find_one({"id": conflict_id})
    if not conflict:
        return {"error": "not found"}
    fix = conflict.get("ai_suggested_fix") or {}
    body = custom_body or fix.get("body")
    title = custom_title or fix.get("title")
    if not body:
        return {"error": "no fix body — run ai-suggest first or provide custom_body"}
    now = datetime.now(timezone.utc).isoformat()
    override_doc = {
        "doc_slug": conflict["doc_slug"],
        "section_index": conflict["section_index"],
        "block_index": conflict["block_index"],
        "patch": {"type": "callout", "variant": "info", "title": title or "", "body": body},
        "source_conflict_id": conflict_id,
        "applied_by": actor,
        "applied_at": now,
    }
    # Upsert by (doc_slug, section_index, block_index)
    await db.doc_overrides.replace_one(
        {"doc_slug": override_doc["doc_slug"], "section_index": override_doc["section_index"], "block_index": override_doc["block_index"]},
        override_doc,
        upsert=True,
    )
    await db.doc_conflicts.update_one(
        {"id": conflict_id},
        {"$set": {"status": "fixed", "applied_at": now, "updated_at": now, "updated_by": actor}},
    )
    return {"ok": True, "override": override_doc}


async def get_overrides_for_doc(doc_slug: str) -> dict:
    """Returns dict keyed (sec_idx, blk_idx) → patch."""
    out = {}
    async for r in db.doc_overrides.find({"doc_slug": doc_slug}):
        out[(r["section_index"], r["block_index"])] = r["patch"]
    return out
