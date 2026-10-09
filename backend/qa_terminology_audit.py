"""QA Terminology Audit — detects inconsistent vocabulary across docs.

Example concept clusters where the same idea is referred to by different words:
- canonical "escrow" vs variants ["cont blocat", "depozit garanție", "fonduri blocate"]
- canonical "specialist" vs variants ["meseriaș", "profesionist", "executant"]
- canonical "comision platformă" vs variants ["taxă platformă", "fee platformă"]

The audit:
1. Loads cluster definitions from db.term_clusters (seeded on first scan).
2. Walks every doc block; for each cluster, if BOTH canonical AND variant terms
   appear (or 2+ variants), records an inconsistency.
3. AI fix rewrites the offending block to use the canonical term throughout.
4. Apply stores the rewrite in db.doc_overrides — same override mechanism as
   the content-audit module — so the change shows up immediately in PDF + UI.

Optional: AI cluster discovery scans all docs and proposes NEW clusters that
should be added to db.term_clusters.
"""
from __future__ import annotations

import os
import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from db import db
from docs_content import DOCS_CONTENT

logger = logging.getLogger("propmanage.term_audit")


# ----------------------------------------------------------------------------
# Default seed clusters (loaded once on first scan)
# ----------------------------------------------------------------------------

DEFAULT_CLUSTERS = [
    {
        "key": "escrow",
        "canonical": "escrow",
        "variants": ["cont blocat", "depozit garanție", "fonduri blocate", "depozit blocat", "cont segregat"],
        "description": "Mecanismul de protecție a plății — bani blocați până la confirmare.",
    },
    {
        "key": "specialist",
        "canonical": "specialist",
        "variants": ["meseriaș", "profesionist", "executant", "prestator", "tehnician"],
        "description": "Persoana care execută lucrarea pentru client.",
    },
    {
        "key": "client",
        "canonical": "client",
        "variants": ["proprietar", "beneficiar", "deținător proprietate"],
        "description": "Persoana care plătește pentru lucrare (deține proprietatea).",
    },
    {
        "key": "comision",
        "canonical": "comision platformă",
        "variants": ["taxă platformă", "fee platformă", "comision PropManage"],
        "description": "Procentul de 5% reținut de PropManage din suma escrow.",
    },
    {
        "key": "trust_score",
        "canonical": "Trust Score",
        "variants": ["scor încredere", "punctaj încredere", "rating intern"],
        "description": "Scorul intern care prioritizează specialiștii în marketplace.",
    },
]


async def seed_clusters_if_empty() -> int:
    n = await db.term_clusters.count_documents({})
    if n > 0:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    docs = [{**c, "created_at": now, "updated_at": now, "is_seed": True} for c in DEFAULT_CLUSTERS]
    await db.term_clusters.insert_many(docs)
    return len(docs)


async def list_clusters() -> list[dict]:
    out = []
    async for c in db.term_clusters.find({}).sort("key", 1):
        c.pop("_id", None)
        out.append(c)
    return out


# ----------------------------------------------------------------------------
# Scanner
# ----------------------------------------------------------------------------

def _block_text(block) -> str:
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


def _word_present(text: str, term: str) -> bool:
    """Case-insensitive whole-word/phrase match (allows Romanian diacritics)."""
    t = text.lower()
    needle = term.lower()
    # Word boundary on each side using simple lookaround on punctuation/whitespace
    pattern = r"(?<![\w])" + re.escape(needle) + r"(?![\w])"
    return re.search(pattern, t) is not None


def scan_doc_for_clusters(slug: str, clusters: list[dict], resolved_doc: Optional[dict] = None) -> list[dict]:
    """Return inconsistencies in a doc.

    An inconsistency = within the same DOC, two or more terms of the same
    cluster appear (e.g. one section uses 'escrow' and another uses 'cont blocat').

    If `resolved_doc` is provided (with overrides already applied), it is used
    instead of the raw `DOCS_CONTENT[slug]` — so we don't re-flag fixed conflicts.
    """
    doc = resolved_doc or DOCS_CONTENT.get(slug)
    if not doc:
        return []
    out = []
    for cluster in clusters:
        all_terms = [cluster["canonical"]] + list(cluster["variants"])
        hits_per_block = []  # list of (sec_idx, blk_idx, found_terms, excerpt)
        for sec_idx, section in enumerate(doc.get("sections", [])):
            for blk_idx, block in enumerate(section.get("body", []) or []):
                text = _block_text(block)
                if not text:
                    continue
                found = [t for t in all_terms if _word_present(text, t)]
                if found:
                    hits_per_block.append((sec_idx, blk_idx, found, text[:280], section.get("heading", "")))

        # Build full set of distinct terms in this doc for this cluster
        all_found = set()
        for h in hits_per_block:
            all_found.update(h[2])
        # Inconsistency: more than 1 distinct term used
        if len(all_found) >= 2:
            out.append({
                "doc_slug": slug,
                "cluster_key": cluster["key"],
                "canonical": cluster["canonical"],
                "variants_used": sorted(all_found),
                "occurrences": [
                    {"section_index": s, "block_index": b, "section_heading": h, "terms": fs, "excerpt": ex}
                    for (s, b, fs, ex, h) in hits_per_block
                ],
            })
    return out


async def scan_all_docs() -> dict:
    """Run the full audit across every doc; returns aggregated report."""
    from docs_service import resolve_doc_with_overrides
    await seed_clusters_if_empty()
    clusters = await list_clusters()
    by_doc = {}
    total = 0
    for slug in DOCS_CONTENT.keys():
        # Use the resolved doc (with overrides applied) so fixes are reflected immediately
        try:
            resolved = await resolve_doc_with_overrides(slug)
        except Exception:  # noqa: BLE001
            resolved = None
        inc = scan_doc_for_clusters(slug, clusters, resolved_doc=resolved)
        if inc:
            by_doc[slug] = inc
            total += len(inc)
    return {"clusters_checked": len(clusters), "total_inconsistencies": total, "by_doc": by_doc}


# ----------------------------------------------------------------------------
# Persist inconsistencies as actionable rows (for the admin UI)
# ----------------------------------------------------------------------------

async def persist_inconsistencies(report: dict) -> dict:
    """Insert one row per (doc, cluster) inconsistency, idempotent by `key`."""
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    existing = 0
    for slug, lst in report.get("by_doc", {}).items():
        for inc in lst:
            key = f"{slug}::{inc['cluster_key']}"
            already = await db.term_inconsistencies.find_one({"key": key, "status": {"$in": ["open", "approved"]}})
            if already:
                existing += 1
                continue
            await db.term_inconsistencies.insert_one({
                "id": uuid.uuid4().hex[:12],
                "key": key,
                "doc_slug": slug,
                "cluster_key": inc["cluster_key"],
                "canonical": inc["canonical"],
                "variants_used": inc["variants_used"],
                "occurrences": inc["occurrences"],
                "status": "open",
                "ai_suggested_fix": None,
                "created_at": now,
                "updated_at": now,
                "applied_at": None,
            })
            added += 1
    return {"added": added, "already_existing": existing, "total": report.get("total_inconsistencies", 0)}


async def list_inconsistencies(status: Optional[str] = None) -> list[dict]:
    q = {}
    if status:
        q["status"] = status
    out = []
    async for r in db.term_inconsistencies.find(q).sort("created_at", -1).limit(200):
        r.pop("_id", None)
        out.append(r)
    return out


async def update_status(inc_id: str, status: str, actor: str) -> Optional[dict]:
    if status not in ("open", "approved", "dismissed", "fixed"):
        raise ValueError("invalid status")
    now = datetime.now(timezone.utc).isoformat()
    res = await db.term_inconsistencies.find_one_and_update(
        {"id": inc_id},
        {"$set": {"status": status, "updated_at": now, "updated_by": actor}},
        return_document=True,
    )
    if res is None:
        return None
    res.pop("_id", None)
    return res


# ----------------------------------------------------------------------------
# AI Fix — rewrite a single occurrence block to use canonical term
# ----------------------------------------------------------------------------

async def ai_suggest_fix(inc_id: str, occurrence_index: int = 0) -> dict:
    """Ask Claude to rewrite the occurrence's block, replacing variants with canonical."""
    inc = await db.term_inconsistencies.find_one({"id": inc_id})
    if not inc:
        return {"error": "not found"}
    occurrences = inc.get("occurrences", [])
    if occurrence_index >= len(occurrences):
        return {"error": "occurrence index out of range"}
    occ = occurrences[occurrence_index]
    variants_used = inc["variants_used"]
    canonical = inc["canonical"]
    other_variants = [v for v in variants_used if v.lower() != canonical.lower()]

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"error": "ANTHROPIC_API_KEY missing"}
    prompt = f"""Document: `{inc['doc_slug']}` · Secțiune: `{occ['section_heading']}`

Termenul canonic stabilit: **{canonical}**
Variante folosite alternativ în document (greșit, lipsă consistență): {other_variants}

Paragraf actual:
\"\"\"
{occ['excerpt']}
\"\"\"

Rescrie paragraful înlocuind variantele cu termenul canonic, păstrând complet sensul și informațiile.
Nu schimba structura, nu adăuga informații noi. Doar înlocuiește.
Răspuns STRICT JSON: {{"title": "păstrează sau adaptează", "body": "paragraful rescris"}}. Fără fences, fără proză."""
    try:
        from llm_chat import LlmChat, UserMessage
        chat = (LlmChat(
            api_key=key,
            session_id=f"term-fix-{inc_id[:8]}-{occurrence_index}",
            system_message="Ești editor de documentație. Standardizezi terminologia înlocuind sinonime cu termenul canonic, fără a pierde sens.",
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
        await db.term_inconsistencies.update_one(
            {"id": inc_id},
            {"$set": {
                "ai_suggested_fix": {
                    "occurrence_index": occurrence_index,
                    "section_index": occ["section_index"],
                    "block_index": occ["block_index"],
                    "title": title,
                    "body": body,
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {"title": title, "body": body, "occurrence_index": occurrence_index}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[term-audit] AI fix failed for {inc_id}: {e}")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def apply_fix(inc_id: str, actor: str, custom_body: Optional[str] = None, custom_title: Optional[str] = None) -> dict:
    inc = await db.term_inconsistencies.find_one({"id": inc_id})
    if not inc:
        return {"error": "not found"}
    fix = inc.get("ai_suggested_fix") or {}
    body = custom_body or fix.get("body")
    title = custom_title or fix.get("title") or ""
    sec_idx = fix.get("section_index")
    blk_idx = fix.get("block_index")
    if not body or sec_idx is None or blk_idx is None:
        return {"error": "no fix to apply — run ai-suggest first"}
    now = datetime.now(timezone.utc).isoformat()
    override = {
        "doc_slug": inc["doc_slug"],
        "section_index": sec_idx,
        "block_index": blk_idx,
        "patch": {"type": "callout", "variant": "info", "title": title, "body": body},
        "source_term_inconsistency_id": inc_id,
        "applied_by": actor,
        "applied_at": now,
    }
    await db.doc_overrides.replace_one(
        {"doc_slug": override["doc_slug"], "section_index": sec_idx, "block_index": blk_idx},
        override,
        upsert=True,
    )
    await db.term_inconsistencies.update_one(
        {"id": inc_id},
        {"$set": {"status": "fixed", "applied_at": now, "updated_at": now, "updated_by": actor}},
    )
    return {"ok": True, "override": override}


# ----------------------------------------------------------------------------
# AI Cluster Discovery — find NEW concept clusters not yet in db.term_clusters
# ----------------------------------------------------------------------------

async def ai_discover_clusters(sample_slugs: Optional[list[str]] = None) -> dict:
    """Run Claude on a doc sample and propose new term clusters worth tracking."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"error": "ANTHROPIC_API_KEY missing"}
    slugs = sample_slugs or list(DOCS_CONTENT.keys())
    samples = []
    for s in slugs[:4]:
        d = DOCS_CONTENT.get(s, {})
        for sec in (d.get("sections") or [])[:3]:
            for blk in (sec.get("body") or [])[:3]:
                t = _block_text(blk)
                if t and len(t) > 50:
                    samples.append(f"[{s} · {sec.get('heading','')[:50]}] {t[:300]}")
                    if len(samples) >= 30:
                        break
            if len(samples) >= 30:
                break
        if len(samples) >= 30:
            break
    existing = await list_clusters()
    existing_keys = [c["key"] for c in existing]
    prompt = (
        "Analizează aceste extrase din documentația PropManage și identifică termeni distincți "
        "care se referă la ACELAȘI concept (sinonime sau aproximații).\n\n"
        f"Cluster-uri DEJA existente (ignoră-le): {existing_keys}\n\n"
        "Extrase:\n"
        + "\n---\n".join(samples)
        + "\n\nRăspuns STRICT JSON: {\"new_clusters\": [{\"key\": \"snake_case\", \"canonical\": \"termen preferat\", \"variants\": [\"sinonim1\",...], \"description\": \"...\"}, ...]}"
    )
    try:
        from llm_chat import LlmChat, UserMessage
        chat = (LlmChat(
            api_key=key,
            session_id=f"term-discover-{uuid.uuid4().hex[:8]}",
            system_message="Ești editor de documentație și identifici inconsistențe de terminologie.",
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
        proposed = data.get("new_clusters", [])
        if not isinstance(proposed, list):
            return {"error": "bad shape", "raw": resp[:400]}
        # Sanitize, do NOT insert yet — return to admin for review
        clean = []
        for c in proposed[:10]:
            if not isinstance(c, dict):
                continue
            key_s = (c.get("key") or "").strip()[:60]
            canonical = (c.get("canonical") or "").strip()[:80]
            variants = [v.strip()[:80] for v in (c.get("variants") or []) if isinstance(v, str)][:8]
            desc = (c.get("description") or "").strip()[:300]
            if key_s and canonical and variants:
                clean.append({"key": key_s, "canonical": canonical, "variants": variants, "description": desc})
        return {"proposed": clean, "raw_count": len(proposed)}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[term-audit] AI discover failed: {e}")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def add_cluster(key: str, canonical: str, variants: list[str], description: str = "") -> dict:
    if not key or not canonical or not variants:
        return {"error": "key/canonical/variants required"}
    existing = await db.term_clusters.find_one({"key": key})
    if existing:
        return {"error": "cluster key already exists"}
    now = datetime.now(timezone.utc).isoformat()
    await db.term_clusters.insert_one({
        "key": key, "canonical": canonical, "variants": variants,
        "description": description, "created_at": now, "updated_at": now, "is_seed": False,
    })
    return {"ok": True}


# ----------------------------------------------------------------------------
# Bulk: AI-fix + apply on every open inconsistency in one shot
# ----------------------------------------------------------------------------

async def _ai_rewrite_block(doc_slug: str, section_heading: str, canonical: str, other_variants: list[str], excerpt: str) -> dict:
    """Pure AI call: rewrite block to use canonical term. Doesn't touch DB."""
    import asyncio as _aio
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"error": "ANTHROPIC_API_KEY missing"}
    prompt = f"""Document: `{doc_slug}` · Secțiune: `{section_heading}`

Termen canonic: **{canonical}**
Variante de înlocuit: {other_variants}

Paragraf:
\"\"\"
{excerpt}
\"\"\"

Rescrie înlocuind variantele cu termenul canonic. Răspuns STRICT JSON: {{"title":"","body":""}}. Fără fences."""
    try:
        from llm_chat import LlmChat, UserMessage
        chat = (LlmChat(
            api_key=key,
            session_id=f"term-bulk-{uuid.uuid4().hex[:8]}",
            system_message="Editor de documentație. Standardizezi terminologia.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929"))
        resp = await _aio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=25)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", resp.strip())
        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            data = json.loads(m.group(0)) if m else None
        if not data or not data.get("body"):
            return {"error": "AI returned empty/non-JSON", "raw": resp[:200]}
        return {"title": (data.get("title") or "").strip()[:200], "body": data["body"].strip()[:2000]}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def apply_all_open(actor: str, max_items: int = 50, max_occurrences_per_inc: int = 5, concurrency: int = 8, inc_id: Optional[str] = None) -> dict:
    """Bulk fix. If `inc_id` is provided, processes only that one inconsistency.

    Frontend can call this in a loop per-inconsistency to stay under the 60s
    ingress timeout while showing live progress.
    """
    import asyncio
    if inc_id:
        row = await db.term_inconsistencies.find_one({"id": inc_id, "status": "open"})
        inconsistencies = [row] if row else []
    else:
        cursor = db.term_inconsistencies.find({"status": "open"}).limit(max_items)
        inconsistencies = []
        async for row in cursor:
            inconsistencies.append(row)

    # Build list of (inc_row, occurrence_index, occurrence_obj)
    jobs = []
    for row in inconsistencies:
        canonical = row["canonical"]
        others = [v for v in row.get("variants_used", []) if v.lower() != canonical.lower()]
        for i, occ in enumerate(row.get("occurrences", [])[:max_occurrences_per_inc]):
            jobs.append((row, i, occ, canonical, others))

    sem = asyncio.Semaphore(concurrency)
    now = datetime.now(timezone.utc).isoformat()
    success_per_inc: dict[str, int] = {}
    fail_per_inc: dict[str, int] = {}

    async def _run(row, idx, occ, canonical, others):
        async with sem:
            res = await _ai_rewrite_block(row["doc_slug"], occ.get("section_heading", ""), canonical, others, occ.get("excerpt", ""))
            inc_id = row["id"]
            if res.get("error"):
                fail_per_inc[inc_id] = fail_per_inc.get(inc_id, 0) + 1
                return
            # Apply override directly
            override = {
                "doc_slug": row["doc_slug"],
                "section_index": occ["section_index"],
                "block_index": occ["block_index"],
                "patch": {"type": "callout", "variant": "info", "title": res.get("title", ""), "body": res["body"]},
                "source_term_inconsistency_id": inc_id,
                "applied_by": actor,
                "applied_at": now,
            }
            try:
                await db.doc_overrides.replace_one(
                    {"doc_slug": override["doc_slug"], "section_index": occ["section_index"], "block_index": occ["block_index"]},
                    override,
                    upsert=True,
                )
                success_per_inc[inc_id] = success_per_inc.get(inc_id, 0) + 1
            except Exception:  # noqa: BLE001
                fail_per_inc[inc_id] = fail_per_inc.get(inc_id, 0) + 1

    await asyncio.gather(*[_run(*j) for j in jobs])

    # Mark inconsistencies as fixed if at least 1 occurrence patched, partial if mixed
    details = []
    fixed = 0
    failed = 0
    for row in inconsistencies:
        inc_id = row["id"]
        s = success_per_inc.get(inc_id, 0)
        f = fail_per_inc.get(inc_id, 0)
        status = "fixed" if (s > 0 and f == 0) else ("partial" if s > 0 else "fail")
        if status in ("fixed", "partial"):
            await db.term_inconsistencies.update_one(
                {"id": inc_id},
                {"$set": {"status": "fixed", "applied_at": now, "updated_at": now, "updated_by": actor}},
            )
            fixed += 1
        else:
            failed += 1
        details.append({
            "id": inc_id, "doc_slug": row["doc_slug"], "cluster": row["cluster_key"],
            "status": status, "occurrences_patched": s, "occurrences_failed": f,
        })
    return {
        "processed": len(inconsistencies), "fixed": fixed, "failed": failed,
        "total_occurrences": len(jobs), "details": details,
    }
