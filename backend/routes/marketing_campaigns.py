"""AI Marketing Campaigns + Auto-Campaign Trigger + Image Studio (Nano Banana).

Faza 2 modul: generator manual campanii + detector automat oportunități +
generare imagini ad/social cu Gemini Nano Banana.

Endpoints (super_admin sau marketing_manager):
  POST   /api/admin/marketing/campaigns/generate           — generator manual
  GET    /api/admin/marketing/campaigns                    — listă (fără base64)
  GET    /api/admin/marketing/campaigns/{id}               — detail cu imagini
  POST   /api/admin/marketing/campaigns/{id}/approve
  POST   /api/admin/marketing/campaigns/{id}/reject
  POST   /api/admin/marketing/campaigns/{id}/regenerate-image
  POST   /api/admin/marketing/auto-triggers/scan           — rulează detectorul acum
  GET    /api/admin/marketing/auto-triggers/recent

Collection: marketing_campaigns
  { objective, service_category, county, budget_ron, status (draft|approved|rejected|auto_draft),
    avatar, audience, ad_texts[], cta, kpis, images[base64], generated_at,
    generated_by, source ('manual'|'auto_trigger'), trigger_reason, approved_at }
"""
import json
import logging
import os
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from routes.marketing_growth import _require_marketing, _iso_days_ago

logger = logging.getLogger("propmanage.marketing_campaigns")
router = APIRouter(prefix="/api/admin/marketing", tags=["admin-marketing-campaigns"])

VALID_OBJECTIVES = {"awareness", "leads", "conversions", "retention", "engagement"}
GROWTH_THRESHOLD_PCT = 30  # auto-trigger when category grows >= 30% MoM
MIN_PREV_REQUESTS = 5      # min volume to avoid noise


# ---------- Helpers ----------

def _serialize_campaign(d: dict, include_images: bool = False) -> dict:
    if not d:
        return d
    out = {
        "id": str(d.get("_id")),
        "objective": d.get("objective"),
        "service_category": d.get("service_category"),
        "county": d.get("county"),
        "budget_ron": d.get("budget_ron"),
        "status": d.get("status") or "draft",
        "source": d.get("source") or "manual",
        "trigger_reason": d.get("trigger_reason"),
        "avatar": d.get("avatar"),
        "audience": d.get("audience"),
        "ad_texts": d.get("ad_texts") or [],
        "cta": d.get("cta"),
        "kpis": d.get("kpis") or {},
        "image_prompts": d.get("image_prompts") or [],
        "image_count": d.get("image_count") if d.get("image_count") is not None else len(d.get("images") or []),
        "generated_at": d.get("generated_at"),
        "generated_by": d.get("generated_by"),
        "calibration_applied": d.get("calibration_applied", False),
        "last_performance": d.get("last_performance"),
        "approved_at": d.get("approved_at"),
        "approved_by": d.get("approved_by"),
        "rejected_at": d.get("rejected_at"),
    }
    if include_images:
        # base64 data URIs — never log this
        out["images"] = [
            {"idx": i, "data_uri": f"data:{img.get('mime_type', 'image/png')};base64,{img.get('data')}"}
            for i, img in enumerate(d.get("images") or [])
        ]
    return out


async def _claude_generate_campaign(objective: str, service: str, county: str,
                                    budget: int, trigger_reason: str | None = None) -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    # Inject performance-based calibration learnings if any
    try:
        from routes.marketing_performance import get_active_calibration_hint
        calibration = await get_active_calibration_hint()
    except Exception as e:
        logger.warning(f"[generator] calibration fetch failed: {e}")
        calibration = None
    system = (
        "Ești un AI Campaign Generator pentru PropManage (platformă property management România). "
        "Primești un brief: obiectiv + serviciu + județ + buget RON. Generezi un draft de campanie "
        "complet, în română, exclusiv ca JSON: {"
        "avatar: {age_range, occupation, pain_points (max 3), motivations (max 3)}, "
        "audience: {targeting (max 200c), interests (array max 6), exclusions (array max 3)}, "
        "ad_texts: [{primary_text (max 180c), headline (max 40c), description (max 30c)}] (3 variante), "
        "cta: string scurt (ex: 'Cere ofertă'), "
        "image_prompts: [string1, string2] (2 prompts în engleză pentru generare imagini AI ad-creative photo-realistic, "
        "fără text suprapus pe imagine; descriu scenă, lumină, atmosferă; relevant pentru serviciu+județ), "
        "kpis: {expected_impressions, expected_clicks, expected_leads, expected_cpc_ron, daily_budget_ron, duration_days}, "
        "rationale: string max 250c — de ce această strategie}"
    )
    if calibration:
        system += "\n\n" + calibration
    brief = {
        "obiectiv": objective,
        "serviciu": service,
        "județ": county,
        "buget_total_ron": budget,
    }
    if trigger_reason:
        brief["context_trigger_automat"] = trigger_reason
    chat = LlmChat(api_key=key, session_id=f"camp_{_uuid.uuid4().hex[:8]}", system_message=system)\
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=json.dumps(brief, ensure_ascii=False)))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise HTTPException(502, "AI nu a returnat JSON valid pentru campanie.")
    return json.loads(text[i:j + 1])


async def _nano_banana_generate(prompt: str) -> Optional[dict]:
    """Generate single ad image via Gemini Nano Banana. Returns {mime_type, data} base64."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=f"img_{_uuid.uuid4().hex[:8]}",
                       system_message="You are a professional ad-creative photo generator. "
                                      "Generate photo-realistic marketing images. No text overlays.")\
            .with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        msg = UserMessage(text=prompt)
        _, images = await chat.send_message_multimodal_response(msg)
        if images and len(images) > 0:
            first = images[0]
            return {"mime_type": first.get("mime_type", "image/png"), "data": first.get("data")}
    except Exception as e:
        logger.warning(f"[nano-banana] generation failed: {e}")
    return None


# ---------- Models ----------

class GenerateReq(BaseModel):
    objective: str
    service_category: str
    county: str
    budget_ron: int = Field(ge=50, le=100000)
    skip_images: bool = False


# ---------- 1. Manual generator ----------

@router.post("/campaigns/generate")
async def generate_campaign(req: GenerateReq, user=Depends(get_current_user)):
    _require_marketing(user)
    if req.objective not in VALID_OBJECTIVES:
        raise HTTPException(400, f"Obiectiv invalid. Permise: {sorted(VALID_OBJECTIVES)}")

    draft = await _claude_generate_campaign(req.objective, req.service_category, req.county, req.budget_ron)
    images = []
    if not req.skip_images:
        for p in (draft.get("image_prompts") or [])[:2]:
            img = await _nano_banana_generate(p)
            if img:
                images.append(img)

    doc = {
        "objective": req.objective,
        "service_category": req.service_category,
        "county": req.county,
        "budget_ron": req.budget_ron,
        "status": "draft",
        "source": "manual",
        "avatar": draft.get("avatar"),
        "audience": draft.get("audience"),
        "ad_texts": (draft.get("ad_texts") or [])[:3],
        "cta": str(draft.get("cta") or "")[:50],
        "image_prompts": (draft.get("image_prompts") or [])[:2],
        "images": images,
        "image_count": len(images),
        "kpis": draft.get("kpis") or {},
        "rationale": str(draft.get("rationale") or "")[:300],
        "calibration_applied": bool(await db.marketing_performance_learnings.find_one({"active": True})),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("email"),
    }
    res = await db.marketing_campaigns.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_campaign(doc, include_images=True)


# ---------- 2. List + detail ----------

@router.get("/campaigns")
async def list_campaigns(status: Optional[str] = None, limit: int = 30,
                         user=Depends(get_current_user)):
    _require_marketing(user)
    q = {}
    if status:
        q["status"] = status
    cur = db.marketing_campaigns.find(q, {"images": 0}).sort("generated_at", -1).limit(min(limit, 100))
    items = []
    async for d in cur:
        items.append(_serialize_campaign(d, include_images=False))
    return {"items": items, "count": len(items)}


@router.get("/campaigns/{cid}")
async def get_campaign(cid: str, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    d = await db.marketing_campaigns.find_one({"_id": oid})
    if not d:
        raise HTTPException(404, "Campanie inexistentă.")
    return _serialize_campaign(d, include_images=True)


# ---------- 3. Approve / Reject ----------

@router.post("/campaigns/{cid}/approve")
async def approve_campaign(cid: str, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.marketing_campaigns.update_one(
        {"_id": oid},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat(),
                  "approved_by": user.get("email")}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Campanie inexistentă.")
    return {"ok": True, "status": "approved"}


@router.post("/campaigns/{cid}/reject")
async def reject_campaign(cid: str, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.marketing_campaigns.update_one(
        {"_id": oid},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc).isoformat(),
                  "rejected_by": user.get("email")}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Campanie inexistentă.")
    return {"ok": True, "status": "rejected"}


# ---------- 4. Regenerate single image ----------

class RegenImg(BaseModel):
    prompt: Optional[str] = None
    image_index: int = 0


@router.post("/campaigns/{cid}/regenerate-image")
async def regenerate_image(cid: str, req: RegenImg, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    d = await db.marketing_campaigns.find_one({"_id": oid})
    if not d:
        raise HTTPException(404, "Campanie inexistentă.")
    prompts = d.get("image_prompts") or []
    prompt = req.prompt or (prompts[req.image_index] if req.image_index < len(prompts) else None)
    if not prompt:
        raise HTTPException(400, "Prompt indisponibil.")
    img = await _nano_banana_generate(prompt)
    if not img:
        raise HTTPException(502, "Generare imagine eșuată.")
    images = d.get("images") or []
    if req.image_index < len(images):
        images[req.image_index] = img
    else:
        images.append(img)
    await db.marketing_campaigns.update_one({"_id": oid}, {"$set": {"images": images, "image_count": len(images)}})
    return {
        "ok": True,
        "image_index": req.image_index,
        "data_uri": f"data:{img['mime_type']};base64,{img['data']}",
    }


# ---------- 5. AUTO-TRIGGER scan ----------

async def _detect_growth_triggers() -> list[dict]:
    """Detect (category × county) pairs growing >=30% MoM with min volume."""
    iso_30 = _iso_days_ago(30)
    iso_60 = _iso_days_ago(60)

    async def _count(start, end):
        pipe = [
            {"$match": {"created_at": {"$gte": start, "$lt": end} if end else {"$gte": start},
                        "category": {"$ne": None}, "county": {"$ne": None}}},
            {"$group": {"_id": {"cat": "$category", "county": "$county"}, "n": {"$sum": 1}}},
        ]
        out = {}
        async for r in db.requests.aggregate(pipe):
            out[(r["_id"]["cat"], r["_id"]["county"])] = r["n"]
        return out

    cur = await _count(iso_30, None)
    prev = await _count(iso_60, iso_30)

    triggers = []
    for (cat, county), n in cur.items():
        if not cat or not county:
            continue
        p = prev.get((cat, county), 0)
        if p < MIN_PREV_REQUESTS:
            continue
        growth = round((n - p) / p * 100, 1)
        if growth >= GROWTH_THRESHOLD_PCT:
            triggers.append({
                "category": cat, "county": county,
                "current": n, "previous": p,
                "growth_pct": growth,
                "reason": f"Creștere {growth}% MoM ({p}→{n} cereri) pentru '{cat}' în {county}.",
            })
    return triggers


@router.post("/auto-triggers/scan")
async def auto_trigger_scan(user=Depends(get_current_user)):
    """Run growth detector. For each trigger that doesn't already have a recent
    auto_draft (last 7d), generate a Claude draft campaign (no images to save tokens).
    """
    _require_marketing(user)
    triggers = await _detect_growth_triggers()
    iso_7 = _iso_days_ago(7)
    created = []
    skipped = []
    for t in triggers:
        # skip if recent auto_draft exists
        existing = await db.marketing_campaigns.find_one({
            "source": "auto_trigger",
            "service_category": t["category"],
            "county": t["county"],
            "generated_at": {"$gte": iso_7},
        })
        if existing:
            skipped.append({**t, "skipped_reason": "auto_draft existent în ultimele 7 zile"})
            continue
        # generate draft via Claude (text only — no images for batch)
        try:
            draft = await _claude_generate_campaign(
                "leads", t["category"], t["county"],
                budget=max(300, t["current"] * 25),  # heuristic
                trigger_reason=t["reason"],
            )
        except HTTPException as e:
            logger.warning(f"[auto-trigger] Claude failed for {t}: {e.detail}")
            continue
        doc = {
            "objective": "leads",
            "service_category": t["category"],
            "county": t["county"],
            "budget_ron": max(300, t["current"] * 25),
            "status": "auto_draft",
            "source": "auto_trigger",
            "trigger_reason": t["reason"],
            "trigger_metrics": {"current": t["current"], "previous": t["previous"], "growth_pct": t["growth_pct"]},
            "avatar": draft.get("avatar"),
            "audience": draft.get("audience"),
            "ad_texts": (draft.get("ad_texts") or [])[:3],
            "cta": str(draft.get("cta") or "")[:50],
            "image_prompts": (draft.get("image_prompts") or [])[:2],
            "images": [],  # generated on-demand at approval
            "kpis": draft.get("kpis") or {},
            "rationale": str(draft.get("rationale") or "")[:300],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "auto_trigger_engine",
        }
        res = await db.marketing_campaigns.insert_one(doc)
        doc["_id"] = res.inserted_id
        created.append(_serialize_campaign(doc, include_images=False))
    return {
        "triggers_detected": len(triggers),
        "drafts_created": len(created),
        "skipped_recent_duplicate": len(skipped),
        "created": created,
        "skipped": skipped,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/auto-triggers/recent")
async def auto_triggers_recent(limit: int = 10, user=Depends(get_current_user)):
    _require_marketing(user)
    cur = db.marketing_campaigns.find(
        {"source": "auto_trigger"}, {"images": 0}
    ).sort("generated_at", -1).limit(min(limit, 50))
    items = [_serialize_campaign(d, include_images=False) async for d in cur]
    return {"items": items, "count": len(items)}
