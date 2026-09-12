"""Strategic Partners Dashboard + Cross-Reference Engine.

Unifică City Partners + Marketplace Partners într-o singură vedere admin.
Cross-Reference Engine: dat fiind un lead al unui City Partner (de ex.
administrator de bloc), găsește marketplace partners relevanți din același oraș
și sugerează conexiuni comerciale folosind Claude Sonnet 4.5.

Endpoints (super-admin only):
  GET  /api/admin/strategic-partners/dashboard          ecosystem overview
  POST /api/admin/strategic-partners/cross-ref/{lead_id}  AI cross-program match
  GET  /api/admin/strategic-partners/opportunities      precomputed cross matches
"""
import logging
import os
import uuid as _uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.strategic_partners")
router = APIRouter(prefix="/api/admin/strategic-partners", tags=["admin-strategic-partners"])


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin.")


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    """Aggregate view: side-by-side health of City + Marketplace ecosystems."""
    _require_super(user)

    # CITY
    city_total = await db.city_partners.count_documents({})
    city_active = await db.city_partners.count_documents({"status": "active"})
    city_onboarding = await db.city_partners.count_documents({"status": "onboarding"})
    city_leads = await db.city_partner_leads.count_documents({})
    city_conv = await db.city_partner_leads.count_documents({"stage": "converted"})
    city_rev = 0
    async for r in db.city_partner_leads.aggregate([{"$group": {"_id": None, "t": {"$sum": "$revenue_generated"}}}]):
        city_rev = r.get("t") or 0

    # MARKETPLACE
    mkt_total = await db.marketplace_partners.count_documents({})
    mkt_active = await db.marketplace_partners.count_documents({"status": "active"})
    mkt_onboarding = await db.marketplace_partners.count_documents({"status": "onboarding"})
    mkt_leads = await db.marketplace_leads.count_documents({})
    mkt_conv = await db.marketplace_leads.count_documents({"stage": "converted"})
    mkt_rev = 0
    async for r in db.marketplace_leads.aggregate([{"$group": {"_id": None, "t": {"$sum": "$revenue_generated"}}}]):
        mkt_rev = r.get("t") or 0

    # City coverage by city
    city_geo = {}
    async for p in db.city_partners.find({"status": {"$ne": "terminated"}}):
        c = p.get("city") or "—"
        city_geo[c] = city_geo.get(c, 0) + 1
    # Marketplace coverage by city
    mkt_geo = {}
    async for p in db.marketplace_partners.find({"status": {"$ne": "terminated"}}):
        c = p.get("city") or "—"
        mkt_geo[c] = mkt_geo.get(c, 0) + 1
    coverage = []
    for c in set(list(city_geo.keys()) + list(mkt_geo.keys())):
        coverage.append({
            "city": c,
            "city_partners": city_geo.get(c, 0),
            "marketplace_partners": mkt_geo.get(c, 0),
            "covered": city_geo.get(c, 0) > 0 and mkt_geo.get(c, 0) > 0,
        })
    coverage.sort(key=lambda x: -(x["city_partners"] + x["marketplace_partners"]))

    # Pending cross-reference opportunities (count of unmatched city leads)
    unmatched = await db.city_partner_leads.count_documents({
        "stage": {"$in": ["introduced", "contacted"]},
        "cross_ref_done": {"$ne": True},
    })

    return {
        "city": {
            "total": city_total,
            "active": city_active,
            "onboarding": city_onboarding,
            "leads": city_leads,
            "converted": city_conv,
            "revenue": city_rev,
            "conversion_rate": round((city_conv / city_leads * 100), 1) if city_leads else 0,
        },
        "marketplace": {
            "total": mkt_total,
            "active": mkt_active,
            "onboarding": mkt_onboarding,
            "leads": mkt_leads,
            "converted": mkt_conv,
            "revenue": mkt_rev,
            "conversion_rate": round((mkt_conv / mkt_leads * 100), 1) if mkt_leads else 0,
        },
        "totals": {
            "partners": city_total + mkt_total,
            "leads": city_leads + mkt_leads,
            "converted": city_conv + mkt_conv,
            "revenue": city_rev + mkt_rev,
        },
        "coverage": coverage[:20],
        "cross_ref_unmatched": unmatched,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/cross-ref/{lead_id}")
async def cross_reference(lead_id: str, user=Depends(get_current_user)):
    """Given a city_partner lead, find relevant marketplace partners (same city)
    and rank top 3 with Claude Sonnet 4.5.
    """
    _require_super(user)
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(400, "lead_id invalid.")

    lead = await db.city_partner_leads.find_one({"_id": oid})
    if not lead:
        raise HTTPException(404, "Lead inexistent.")
    city_partner = await db.city_partners.find_one({"_id": lead.get("partner_id")})
    if not city_partner:
        raise HTTPException(404, "City partner inexistent pentru lead.")

    target_city = city_partner.get("city")
    # Fetch marketplace partners — same city first, fallback to all active
    candidates = []
    async for p in db.marketplace_partners.find({"status": "active", "city": target_city}):
        candidates.append(p)
    if not candidates:
        async for p in db.marketplace_partners.find({"status": "active"}).limit(20):
            candidates.append(p)
    if not candidates:
        raise HTTPException(404, "Niciun marketplace partner activ pentru cross-reference.")

    # Build context
    import json
    ctx = {
        "lead": {
            "name": lead.get("lead_name"),
            "email": lead.get("lead_email"),
            "stage": lead.get("stage"),
            "notes": lead.get("notes"),
            "source": lead.get("source"),
        },
        "city_partner": {
            "company": city_partner.get("company"),
            "city": city_partner.get("city"),
            "portfolio_type": city_partner.get("portfolio_type"),
            "units_managed": city_partner.get("units_managed"),
        },
        "marketplace_candidates": [{
            "id": str(p["_id"]),
            "company": p.get("company"),
            "tier": p.get("tier"),
            "categories": p.get("categories") or [],
            "city": p.get("city"),
        } for p in candidates[:15]],
    }

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")

    system = (
        "Ești un Ecosystem Connector pentru PropManage. Primești un LEAD adus de un "
        "City Partner (administrator de bloc / dezvoltator) și o listă de Marketplace "
        "Partners activi. Sarcina ta: identifici TOP 3 marketplace partners cei mai "
        "relevanți pentru acest lead, bazat pe context (administratorul administrează "
        "blocuri = nevoie probabilă de sanitare/instalații/vopsele/HVAC etc.). "
        "Răspunzi DOAR cu JSON valid în română: "
        "{matches: [{marketplace_partner_id, company, relevance_score(0-100), "
        "reason (max 200c, propunere concretă de colaborare)}], "
        "introduction_email_subject, introduction_email_body (max 600c, ton prietenos profesional)}."
    )
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=key,
        session_id=f"xref_{_uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=json.dumps(ctx, ensure_ascii=False, indent=2)))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise HTTPException(502, "AI nu a returnat JSON valid.")
    report = json.loads(text[i:j + 1])

    out = {
        "lead_id": lead_id,
        "lead_name": lead.get("lead_name"),
        "city_partner_company": city_partner.get("company"),
        "city": target_city,
        "matches": [
            {
                "marketplace_partner_id": str(m.get("marketplace_partner_id") or "")[:30],
                "company": str(m.get("company") or "")[:120],
                "relevance_score": int(m.get("relevance_score") or 0),
                "reason": str(m.get("reason") or "")[:250],
            }
            for m in (report.get("matches") or [])[:3]
        ],
        "introduction_email_subject": str(report.get("introduction_email_subject") or "")[:200],
        "introduction_email_body": str(report.get("introduction_email_body") or "")[:800],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mark lead as cross-ref done
    await db.city_partner_leads.update_one(
        {"_id": oid},
        {"$set": {"cross_ref_done": True, "cross_ref_at": out["generated_at"]}},
    )
    _synced = await db.city_partner_leads.find_one({"_id": oid})
    if _synced:
        from leads_store import sync_lead
        await sync_lead("city_partner", _synced)
    await db.strategic_cross_refs.insert_one({**out, "generated_by": user.get("email")})
    return out


@router.get("/opportunities")
async def opportunities(limit: int = 10, user=Depends(get_current_user)):
    """Returns the latest cross-reference results for the admin to review."""
    _require_super(user)
    cur = db.strategic_cross_refs.find({}).sort("generated_at", -1).limit(min(limit, 50))
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "count": len(items)}


@router.get("/unmatched-leads")
async def unmatched_leads(user=Depends(get_current_user)):
    """Returns city_partner leads not yet processed via cross-reference."""
    _require_super(user)
    cur = db.city_partner_leads.find({
        "stage": {"$in": ["introduced", "contacted"]},
        "cross_ref_done": {"$ne": True},
    }).sort("created_at", -1).limit(50)
    items = []
    async for l in cur:
        cp = await db.city_partners.find_one({"_id": l.get("partner_id")})
        items.append({
            "id": str(l["_id"]),
            "lead_name": l.get("lead_name"),
            "stage": l.get("stage"),
            "city_partner_company": cp.get("company") if cp else None,
            "city": cp.get("city") if cp else None,
            "created_at": l.get("created_at"),
        })
    return {"items": items, "count": len(items)}
