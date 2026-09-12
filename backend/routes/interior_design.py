"""Design Interior — serviciu independent, acces liber (fără Twin/abonament).

Public: content (editabil din admin), lead-uri, AI Assistant (Claude).
Admin: editare completă conținut + SEO + vizibilitate + gestionare lead-uri.
SEO: conținutul lung (2500+ cuvinte) e servit din DB și randat cu H2/H3.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from db import db
from deps import require_role

router = APIRouter(prefix="/api", tags=["interior-design"])
logger = logging.getLogger("propmanage.interior_design")

from service_content_design import DEFAULT_CONTENT



async def _get_content() -> dict[str, Any]:
    # 2.4: service_pages e master; fallback + dual-write cu legacy interior_design_content
    # BUGFIX: verificarea content_version rulează pe AMBELE ramuri (master + legacy),
    # altfel pe medii unde service_pages nu are doc, legacy întorcea conținut stale.
    doc = await db.service_pages.find_one({"slug": "design-interior"})
    if not doc:
        doc = await db.interior_design_content.find_one({"_id": "main"})

    current_version = DEFAULT_CONTENT["content_version"]
    doc_version = (doc or {}).get("content_version") or 1

    if not doc or doc_version < current_version:
        # First-time seed OR upgrade — păstrează flagurile admin, restul e conținut nou
        upgraded = {**DEFAULT_CONTENT,
                    "active": (doc or {}).get("active", True),
                    "show_on_homepage": (doc or {}).get("show_on_homepage", True),
                    "slug": "design-interior",
                    "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.service_pages.update_one({"slug": "design-interior"}, {"$set": upgraded}, upsert=True)
        await db.interior_design_content.update_one({"_id": "main"}, {"$set": upgraded}, upsert=True)
        logger.info(f"[interior_design] content upgraded {doc_version} → {current_version}")
        doc = await db.service_pages.find_one({"slug": "design-interior"})

    doc.pop("_id", None)
    return doc


# ── PUBLIC ────────────────────────────────────────────────────────────────────
@router.get("/interior-design/content")
async def public_content():
    content = await _get_content()
    if not content.get("active", True):
        raise HTTPException(404, "Serviciul este momentan dezactivat.")
    return content


class LeadIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    style: str | None = None
    budget: str | None = None
    surface_mp: int | None = None
    rooms: str | None = None
    city: str | None = None
    message: str | None = None
    consult_date: str | None = None
    photo_urls: list[str] = []
    lead_type: str = "proiect"  # proiect | oferta | consultanta
    # Attribution (optional, filled by SEO CTA modal — measures organic→SEO page→CTA→lead)
    landing_page: str | None = None
    di_slug: str | None = None
    seo_cluster: str | None = None
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    referrer: str | None = None


def _triage_lead(p: "LeadIn") -> tuple[int, str]:
    """Scoring determinist 0-100 → segment hot/warm/nurture (Self-Driving lead triage)."""
    score = 20
    if p.phone: score += 20
    if p.budget:
        b = p.budget.lower()
        score += 25 if any(x in b for x in ("10000", "15000", "20000", "peste", ">")) else 15
    if p.surface_mp and p.surface_mp >= 60: score += 10
    if p.message and len(p.message) > 60: score += 10
    if p.photo_urls: score += 10
    if p.lead_type == "proiect": score += 5
    score = min(100, score)
    segment = "hot" if score >= 70 else "warm" if score >= 45 else "nurture"
    return score, segment


@router.post("/interior-design/leads")
async def create_lead(payload: LeadIn):
    score, segment = _triage_lead(payload)
    lead = {
        "id": uuid.uuid4().hex[:12],
        **payload.model_dump(),
        "photo_urls": payload.photo_urls[:10],
        "status": "new",
        "score": score,
        "segment": segment,
        "triaged_by": "autonomy:lead_triage",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.interior_design_leads.insert_one({**lead})
    try:
        from leads_store import sync_lead
        await sync_lead("interior_design", lead)
    except Exception:  # noqa: BLE001
        pass
    try:
        from orchestrator.engine import notify_admins
        if segment == "hot":
            await notify_admins(
                f"🔥 Lead HOT Design Interior ({score}/100): {payload.name}",
                f"{payload.lead_type} · {payload.style or 'stil nespecificat'} · {payload.budget or 'buget nespecificat'} · {payload.city or ''} — contactează în max 1h!",
                link="/admin/interior-design", send_emails=True,
            )
        else:
            await notify_admins(
                f"🎨 Lead nou Design Interior ({segment}, {score}/100): {payload.name}",
                f"{payload.lead_type} · {payload.style or 'stil nespecificat'} · {payload.budget or 'buget nespecificat'} · {payload.city or ''}",
                link="/admin/interior-design",
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[interior-design] notify fail: {e}")
    return {"ok": True, "lead_id": lead["id"], "message": "Mulțumim! Un designer te va contacta în 24-48h."}


# Rate limit per IP: max 10 întrebări / 10 minute (protecție quota LLM)
_ai_hits: dict[str, list[float]] = {}
AI_RL_MAX = 10
AI_RL_WINDOW = 600


def _check_ai_rate_limit(ip: str):
    now = time.time()
    hits = [t for t in _ai_hits.get(ip, []) if now - t < AI_RL_WINDOW]
    if len(hits) >= AI_RL_MAX:
        raise HTTPException(429, "Ai atins limita de întrebări. Reîncearcă peste câteva minute sau completează formularul.")
    hits.append(now)
    _ai_hits[ip] = hits


@router.post("/interior-design/assistant")
async def design_assistant(request: Request, question: str = Body(..., embed=True), session_id: str = Body(None, embed=True)):
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    _check_ai_rate_limit(ip)
    question = question.strip()[:500]
    if not question:
        raise HTTPException(400, "Întrebarea este goală.")
    session_id = session_id or uuid.uuid4().hex[:12]

    history = []
    sess = await db.interior_assistant_sessions.find_one({"session_id": session_id})
    if sess:
        history = (sess.get("messages") or [])[-6:]

    try:
        from orchestrator.llm import claude_json
        hist_text = "\n".join(f"{m['role']}: {m['text']}" for m in history)
        system = (
            "Ești consultantul AI de design interior al PropManage (România). Răspunzi în română, cald și profesionist, "
            "la întrebări despre: stiluri de amenajare, bugete realiste în lei (piața RO 2026), materiale, mobilier, "
            "culori, iluminat, compartimentare, ergonomie și recomandări per cameră (living/bucătărie/baie/dormitor/birou). "
            "Răspuns concis (max 150 cuvinte), concret, cu cifre unde e cazul. La final, când e natural, sugerează "
            "completarea formularului pentru oferte de la designeri reali. "
            "Răspunde STRICT JSON: {\"answer\": str RO}."
        )
        prompt = (f"Istoric conversație:\n{hist_text}\n\n" if hist_text else "") + f"Întrebare: {question}"
        result = await claude_json(system=system, prompt=prompt, session_prefix=f"interior-ai-{session_id}")
        answer = str(result.get("answer") or "").strip()[:1200]
        if not answer:
            raise ValueError("empty")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[interior-design] assistant LLM fail: {e}")
        answer = ("Momentan nu pot răspunde — te rog reîncearcă în câteva secunde. Între timp, poți completa formularul "
                  "de mai jos și un designer real îți va răspunde la toate întrebările în 24-48h.")

    new_messages = history + [{"role": "user", "text": question}, {"role": "assistant", "text": answer}]
    await db.interior_assistant_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"messages": new_messages[-12:], "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"answer": answer, "session_id": session_id}


# ── ADMIN ─────────────────────────────────────────────────────────────────────
@router.get("/admin/interior-design/content")
async def admin_get_content(_admin=Depends(require_role("admin"))):
    return await _get_content()


@router.put("/admin/interior-design/content")
async def admin_update_content(patch: dict = Body(...), _admin=Depends(require_role("admin"))):
    allowed = {"active", "show_on_homepage", "menu_order", "seo", "hero", "benefits",
               "portfolio", "reviews", "faq", "styles", "budgets", "local_cities", "seo_article",
               "brand", "positioning", "journey", "process_phases", "digital_twin", "audit",
               "implementation", "styles_showcase", "ecosystem",
               "canonical_flow", "audit_full", "twin_full"}
    clean = {k: v for k, v in patch.items() if k in allowed}
    if not clean:
        raise HTTPException(400, "Nimic valid de actualizat.")
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.interior_design_content.update_one({"_id": "main"}, {"$set": clean}, upsert=True)
    await db.service_pages.update_one(
        {"slug": "design-interior"},
        {"$set": {**clean, "slug": "design-interior", "tenant_id": "main"}},
        upsert=True,
    )
    return await _get_content()


@router.get("/admin/interior-design/leads")
async def admin_leads(status: str | None = None, limit: int = 100, _admin=Depends(require_role("admin"))):
    q: dict[str, Any] = {}
    if status:
        q["status"] = status
    out = []
    async for lead in db.interior_design_leads.find(q, {"_id": 0}).sort("created_at", -1).limit(max(1, min(limit, 300))):
        out.append(lead)
    counts: dict[str, int] = {}
    async for lead in db.interior_design_leads.find({}, {"status": 1}):
        counts[lead.get("status", "new")] = counts.get(lead.get("status", "new"), 0) + 1
    return {"leads": out, "total": len(out), "counts": counts}


@router.patch("/admin/interior-design/leads/{lead_id}")
async def admin_patch_lead(lead_id: str, status: str = Body(..., embed=True), _admin=Depends(require_role("admin"))):
    if status not in ("new", "contacted", "offered", "won", "lost"):
        raise HTTPException(400, "Status invalid.")
    res = await db.interior_design_leads.update_one({"id": lead_id}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(404, "Lead inexistent.")
    return {"ok": True}
