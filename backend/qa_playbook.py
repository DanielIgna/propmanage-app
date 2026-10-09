"""QA Playbook — Interactive Test Run Engine.

Backend logic that:
1) Extracts a structured checklist (test cases) from the QA_DOC in docs_content.
2) Persists test runs in MongoDB so QA can pause/resume across sessions.
3) Exposes endpoints to flip a check (pass/fail/skip) with a note.
4) Calls Claude Sonnet 4.5 (via Emergent LLM Key) to suggest test cases for a feature.

Each test ID is parsed from the raw markdown — e.g. `**C-01** Înregistrare cu...`
The section heading provides category + priority (P0/P1/P2).
"""
from __future__ import annotations

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from db import db
from docs_content import QA_DOC

logger = logging.getLogger("propmanage.qa_playbook")


# ============================================================================
# Checklist extraction from QA_DOC
# ============================================================================

_TEST_ID_RE = re.compile(r"\*\*([A-Z]+-\d+)\*\*\s*(.+)", re.DOTALL)
_PRIORITY_RE = re.compile(r"\(P(\d)[^)]*\)")


def _strip_md(text: str) -> str:
    """Light-touch markdown stripper for descriptions (bold/italic/code)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_checklist_template() -> list[dict]:
    """Parse QA_DOC into a flat ordered list of test items.

    Each item: { id, code, category, priority, description, tags }
    Section structure: heading like "2. CLIENT — 30 scenarii test"
                       sub-heading h3 like "Onboarding (P0)" / "Lead Capture (P0)"
    """
    items: list[dict] = []
    for section in QA_DOC.get("sections", []):
        heading = section.get("heading", "")
        # Skip the intro section (which has no test IDs)
        if heading.startswith("1.") or "Cum folosești" in heading:
            continue
        # Derive category from heading: "2. CLIENT — 30 scenarii test" → "CLIENT"
        cat_match = re.match(r"^\d+\.\s*([A-ZĂÂÎȘȚa-zăâîșț\s\-/&\(\)]+?)(?:\s*[—–-]\s|\s*$)", heading)
        category = cat_match.group(1).strip().upper() if cat_match else heading.upper()
        current_subcat = None
        current_priority = "P1"
        for block in section.get("body", []):
            if isinstance(block, dict) and block.get("type") == "h3":
                sub = block.get("text", "")
                current_subcat = re.sub(r"\s*\(P\d[^)]*\)\s*$", "", sub).strip()
                pm = _PRIORITY_RE.search(sub)
                current_priority = f"P{pm.group(1)}" if pm else "P1"
            elif isinstance(block, dict) and block.get("type") == "list":
                for raw in block.get("items", []):
                    m = _TEST_ID_RE.match(raw)
                    if not m:
                        continue
                    code = m.group(1).strip()
                    desc = _strip_md(m.group(2))
                    items.append({
                        "id": code,            # public test id e.g. "C-01"
                        "code": code,
                        "category": category,
                        "subcategory": current_subcat or "",
                        "priority": current_priority,
                        "description": desc,
                    })
    return items


def checklist_stats(items: list[dict]) -> dict:
    by_cat: dict[str, int] = {}
    by_prio: dict[str, int] = {}
    for it in items:
        by_cat[it["category"]] = by_cat.get(it["category"], 0) + 1
        by_prio[it["priority"]] = by_prio.get(it["priority"], 0) + 1
    return {"total": len(items), "by_category": by_cat, "by_priority": by_prio}


# ============================================================================
# Test Run persistence
# ============================================================================

async def create_run(name: str, created_by: str, version: Optional[str] = None) -> dict:
    """Create a new QA run from the latest checklist template."""
    template = build_checklist_template()
    now = datetime.now(timezone.utc).isoformat()
    checks = []
    for t in template:
        checks.append({
            "id": str(uuid.uuid4()),
            "code": t["code"],
            "category": t["category"],
            "subcategory": t["subcategory"],
            "priority": t["priority"],
            "description": t["description"],
            "status": "pending",   # pending | pass | fail | skip
            "note": "",
            "updated_at": None,
            "updated_by": None,
        })
    doc = {
        "run_id": str(uuid.uuid4()),
        "name": name.strip() or f"QA Run · {now[:10]}",
        "version": version or "",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
        "checks": checks,
    }
    await db.qa_runs.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_runs(limit: int = 30) -> list[dict]:
    cursor = db.qa_runs.find({}, {"checks": 0}).sort("created_at", -1).limit(limit)
    out = []
    async for r in cursor:
        r.pop("_id", None)
        out.append(r)
    return out


async def add_adhoc_check(run_id: str, *, code: str, priority: str, category: str, description: str, subcategory: str = "ad-hoc / AI") -> Optional[dict]:
    """Append a new check (typically AI-suggested) to an existing run.

    Auto-de-dup: if a check with the same code already exists, returns the run unchanged.
    """
    run = await db.qa_runs.find_one({"run_id": run_id}, {"checks.code": 1, "closed_at": 1})
    if not run:
        return None
    if run.get("closed_at"):
        raise ValueError("Run is closed")
    existing = {c.get("code") for c in run.get("checks", [])}
    if code in existing:
        # Idempotent: silently return the current run
        return await get_run(run_id)
    if priority not in ("P0", "P1", "P2"):
        priority = "P1"
    new_check = {
        "id": str(uuid.uuid4()),
        "code": code.strip()[:20],
        "category": (category or "AD-HOC").strip().upper()[:40],
        "subcategory": subcategory,
        "priority": priority,
        "description": (description or "").strip()[:600],
        "status": "pending",
        "note": "",
        "updated_at": None,
        "updated_by": None,
        "ai_added": True,
    }
    now = datetime.now(timezone.utc).isoformat()
    await db.qa_runs.update_one(
        {"run_id": run_id},
        {"$push": {"checks": new_check}, "$set": {"updated_at": now}},
    )
    return await get_run(run_id)


async def get_run(run_id: str) -> Optional[dict]:
    r = await db.qa_runs.find_one({"run_id": run_id})
    if not r:
        return None
    r.pop("_id", None)
    return r


async def update_check(run_id: str, check_id: str, *, status: str, note: str, actor: str) -> Optional[dict]:
    if status not in ("pending", "pass", "fail", "skip"):
        raise ValueError("invalid status")
    now = datetime.now(timezone.utc).isoformat()
    res = await db.qa_runs.update_one(
        {"run_id": run_id, "checks.id": check_id},
        {"$set": {
            "checks.$.status": status,
            "checks.$.note": (note or "").strip()[:2000],
            "checks.$.updated_at": now,
            "checks.$.updated_by": actor,
            "updated_at": now,
        }},
    )
    if res.matched_count == 0:
        return None
    return await get_run(run_id)


async def close_run(run_id: str) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    res = await db.qa_runs.update_one(
        {"run_id": run_id},
        {"$set": {"closed_at": now, "updated_at": now}},
    )
    if res.matched_count == 0:
        return None
    return await get_run(run_id)


def run_summary(run: dict) -> dict:
    """Aggregate counts + pass rate for a run."""
    counts = {"pending": 0, "pass": 0, "fail": 0, "skip": 0}
    p0_fail = 0
    p1_fail = 0
    for c in run.get("checks", []):
        counts[c.get("status", "pending")] = counts.get(c.get("status", "pending"), 0) + 1
        if c.get("status") == "fail":
            if c.get("priority") == "P0":
                p0_fail += 1
            elif c.get("priority") == "P1":
                p1_fail += 1
    total = sum(counts.values())
    closed = total - counts["pending"]
    return {
        "total": total,
        "closed": closed,
        "progress_pct": round(closed / total * 100, 1) if total else 0.0,
        "by_status": counts,
        "p0_fail": p0_fail,
        "p1_fail": p1_fail,
        "release_blocked": p0_fail > 0,
    }


# ============================================================================
# AI Test Suggester (Claude Sonnet 4.5 via Emergent LLM Key)
# ============================================================================

async def ai_suggest_tests(feature: str, context: Optional[str] = None) -> dict:
    """Ask Claude to draft 8-12 fresh manual test cases for a given feature.

    Returns: { "items": [ {code, priority, category, description}, ...], "raw": "...", "provider": "..." }
    Never raises — on failure returns {"items": [], "error": "..."}.
    """
    feature = (feature or "").strip()
    if not feature:
        return {"items": [], "error": "Empty feature description"}
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"items": [], "error": "ANTHROPIC_API_KEY not configured"}
    prompt = _build_prompt(feature, context)
    try:
        from llm_chat import LlmChat, UserMessage
        chat = (LlmChat(
            api_key=key,
            session_id=f"qa-suggest-{uuid.uuid4().hex[:8]}",
            system_message=_SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929"))
        msg = UserMessage(text=prompt)
        resp_text = await chat.send_message(msg)
        items = _parse_ai_response(resp_text)
        return {"items": items, "raw": resp_text[:8000], "provider": "claude-sonnet-4-5"}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[QA AI suggest] failed: {e}")
        return {"items": [], "error": f"{type(e).__name__}: {str(e)[:200]}"}


_SYSTEM_PROMPT = """You are a senior QA engineer for PropManage — a Romanian SaaS platform for property management
(marketplace of verified specialists + escrow payments + 3D Digital Twin + admin tools).

Your job: when given a feature or area, output a structured list of 8-12 manual test cases that a human QA
will execute step-by-step. Every test case must:
- Have a short uppercase code like "AI-01", "AI-02"... (use the feature initials as prefix)
- Have a priority: P0 (must-pass / release blocker), P1 (should-pass), or P2 (nice-to-have)
- Have a category that fits PropManage's domain (e.g. CLIENT, SPECIALIST, OPERATOR, ADMIN, INTEGRATION, SECURITY, PERFORMANCE)
- Have a single-line action+expected-outcome description in Romanian (max 220 chars)
- Cover happy path + at least 2 edge cases + at least 1 security/permissions test
- Use diacritice românești corectly (ă, â, î, ș, ț)

Output STRICT JSON only, no prose, no markdown fences. Schema:
{"items":[{"code":"AI-01","priority":"P0","category":"CLIENT","description":"..."}, ...]}"""


def _build_prompt(feature: str, context: Optional[str]) -> str:
    parts = [f"Feature/area to test: {feature}"]
    if context:
        parts.append(f"Context extra: {context}")
    parts.append("Generate 8-12 test cases following the system rules. Output JSON only.")
    return "\n\n".join(parts)


def _parse_ai_response(text: str) -> list[dict]:
    import json
    # Strip code fences if present
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except Exception:
        # Try to find the first {...} JSON block
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except Exception:
            return []
    raw_items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw_items, list):
        return []
    out = []
    for it in raw_items[:20]:
        if not isinstance(it, dict):
            continue
        code = str(it.get("code", "")).strip()[:20]
        prio = str(it.get("priority", "P1")).strip().upper()
        if prio not in ("P0", "P1", "P2"):
            prio = "P1"
        cat = str(it.get("category", "GENERAL")).strip().upper()[:40]
        desc = str(it.get("description", "")).strip()[:400]
        if not code or not desc:
            continue
        out.append({"code": code, "priority": prio, "category": cat, "description": desc})
    return out


# ============================================================================
# Markdown export for a run (for sharing reports)
# ============================================================================

def render_run_markdown(run: dict) -> str:
    summary = run_summary(run)
    lines = []
    lines.append(f"# QA Run · {run.get('name','-')}")
    lines.append("")
    lines.append(f"- Created at: `{run.get('created_at','')}`")
    lines.append(f"- Version: `{run.get('version') or '-'}`")
    lines.append(f"- Progress: **{summary['closed']}/{summary['total']}** ({summary['progress_pct']}%)")
    lines.append(f"- Pass / Fail / Skip / Pending: **{summary['by_status']['pass']} / {summary['by_status']['fail']} / {summary['by_status']['skip']} / {summary['by_status']['pending']}**")
    lines.append(f"- **P0 fails: {summary['p0_fail']}** — Release blocked: {'YES' if summary['release_blocked'] else 'no'}")
    lines.append(f"- P1 fails: {summary['p1_fail']}")
    lines.append("")
    # Group by category
    by_cat: dict[str, list] = {}
    for c in run.get("checks", []):
        by_cat.setdefault(c["category"], []).append(c)
    for cat, checks in by_cat.items():
        lines.append(f"## {cat}")
        lines.append("")
        for c in checks:
            status = c.get("status", "pending")
            icon = {"pass": "✅", "fail": "❌", "skip": "⏭", "pending": "⬜"}.get(status, "⬜")
            lines.append(f"- {icon} **{c['code']}** [{c['priority']}] — {c['description']}")
            if c.get("note"):
                lines.append(f"   - _Notă_: {c['note']}")
        lines.append("")
    return "\n".join(lines)
