"""Sprint A — Dynamic Fee System + Tier Rules + Auto-Promotion + Policy Docs.

Admin-configurable. Extends existing infrastructure without replacing it.

Collections introduced:
  - fee_configs: per-category/zone/season fee rules (singleton-ish, history kept)
  - tier_rules: thresholds for ENTRY → VERIFIED → PREMIUM promotion
  - policy_documents: versioned T&C / Privacy / Reviews / Suspensions policies
  - marketplace_offers: multi-specialist applications per request (optional, feature-flagged)

Endpoints (admin only):
  GET/PUT  /api/admin/fee-config
  GET/PUT  /api/admin/tier-rules
  GET/POST /api/admin/policy-docs
  POST     /api/admin/run-auto-promotion       (manual trigger; also runs daily 03:30)

Public endpoints:
  GET  /api/policy-docs/{slug}                 (latest published version of a policy)
  GET  /api/fee-config/effective?category=&zone=  (compute fee a specialist would pay)
  POST /api/auth/become-client                 (inverse of become-specialist; same dual_role)
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role

logger = logging.getLogger("propmanage.specialist_progression")

router_admin = APIRouter(prefix="/api/admin", tags=["sprint-a-admin"])
router_public = APIRouter(prefix="/api", tags=["sprint-a-public"])


# ============================================================================
# 1. FEE CONFIG
# ============================================================================
class FeeRuleItem(BaseModel):
    """A single fee rule scoped to category/zone/season. The most-specific rule wins."""
    category: Optional[str] = None       # e.g. "hvac" — None = applies to all categories
    zone: Optional[str] = None           # e.g. "Bucuresti-Sector1" — None = all zones
    season: Optional[str] = None         # e.g. "summer" — None = year-round
    base_fee_ron: float = Field(5.0, ge=5.0, le=50.0)      # min 5, max 50 (anti-abuse cap)
    priority_fee_ron: float = Field(0.0, ge=0.0, le=50.0)  # optional extra paid for top rank
    active: bool = True


class FeeConfigUpdate(BaseModel):
    rules: List[FeeRuleItem]
    min_fee_ron: float = Field(5.0, ge=1.0)
    max_fee_ron: float = Field(50.0, ge=5.0)
    top_visible_count: int = Field(3, ge=1, le=10)
    rotation_window_hours: int = Field(24, ge=1, le=168)
    multi_offer_enabled: bool = False   # FEATURE FLAG — legacy "accept" still works when off


@router_admin.get("/fee-config")
async def get_fee_config(_: dict = Depends(require_role("admin"))):
    doc = await db.fee_configs.find_one({"_singleton": True}) or {}
    return {
        "rules": doc.get("rules", []),
        "min_fee_ron": doc.get("min_fee_ron", 5.0),
        "max_fee_ron": doc.get("max_fee_ron", 50.0),
        "top_visible_count": doc.get("top_visible_count", 3),
        "rotation_window_hours": doc.get("rotation_window_hours", 24),
        "multi_offer_enabled": doc.get("multi_offer_enabled", False),
        "updated_at": doc.get("updated_at"),
    }


@router_admin.put("/fee-config")
async def update_fee_config(data: FeeConfigUpdate, user: dict = Depends(require_role("admin"))):
    payload = data.model_dump()
    payload["_singleton"] = True
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = user["id"]
    # Snapshot history (audit trail)
    await db.fee_configs_history.insert_one({k: v for k, v in payload.items() if k != "_singleton"})
    await db.fee_configs.update_one({"_singleton": True}, {"$set": payload}, upsert=True)
    return {"ok": True}


@router_public.get("/fee-config/effective")
async def effective_fee(category: Optional[str] = None, zone: Optional[str] = None):
    """Compute the fee a specialist would pay for applying to a request in this category+zone.

    Resolution order (most-specific first):
      1) category + zone match
      2) category only
      3) zone only
      4) global (no scope)
      5) min_fee_ron fallback
    """
    cfg = await db.fee_configs.find_one({"_singleton": True}) or {}
    rules = [r for r in (cfg.get("rules") or []) if r.get("active", True)]
    min_f = cfg.get("min_fee_ron", 5.0)
    # Try most specific first
    def match(r, cat_match, zone_match):
        return (r.get("category") == category if cat_match else r.get("category") is None) and \
               (r.get("zone") == zone if zone_match else r.get("zone") is None)
    for cm, zm in [(True, True), (True, False), (False, True), (False, False)]:
        for r in rules:
            if match(r, cm, zm):
                return {"base_fee_ron": max(r.get("base_fee_ron", min_f), min_f), "priority_fee_ron": r.get("priority_fee_ron", 0.0)}
    return {"base_fee_ron": min_f, "priority_fee_ron": 0.0}


# ============================================================================
# 2. TIER RULES
# ============================================================================
class TierRulesUpdate(BaseModel):
    """Admin-configurable thresholds for auto-promotion. NO hardcoded values."""
    nivel_2_min_completed_jobs: int = Field(10, ge=1)
    nivel_2_min_rating: float = Field(4.2, ge=1.0, le=5.0)
    nivel_2_min_reviews: int = Field(5, ge=1)
    nivel_3_min_completed_jobs: int = Field(50, ge=1)
    nivel_3_min_rating: float = Field(4.7, ge=1.0, le=5.0)
    nivel_3_min_reviews: int = Field(25, ge=1)
    soft_demote_below_rating: float = Field(4.0, ge=1.0, le=5.0)   # soft only — visual warning, not ban
    cron_enabled: bool = True


@router_admin.get("/tier-rules")
async def get_tier_rules(_: dict = Depends(require_role("admin"))):
    doc = await db.tier_rules.find_one({"_singleton": True}) or {}
    defaults = TierRulesUpdate().model_dump()
    return {**defaults, **{k: v for k, v in doc.items() if k != "_id" and k != "_singleton"}}


@router_admin.put("/tier-rules")
async def update_tier_rules(data: TierRulesUpdate, user: dict = Depends(require_role("admin"))):
    payload = data.model_dump()
    payload["_singleton"] = True
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = user["id"]
    await db.tier_rules.update_one({"_singleton": True}, {"$set": payload}, upsert=True)
    return {"ok": True}


# ============================================================================
# 3. AUTO-PROMOTION ENGINE
# ============================================================================
TIER_ORDER = {"ENTRY": 1, "VERIFIED": 2, "PREMIUM": 3}


async def _compute_user_metrics(user_id: str) -> dict:
    """Return completed jobs count + reviews count + average rating for a specialist."""
    completed = await db.requests.count_documents({
        "$or": [{"specialist_id": user_id}, {"accepted_by": user_id}],
        "status": {"$in": ["completed", "closed"]},
    })
    reviews_cur = db.reviews.find({"specialist_id": user_id}, {"rating": 1})
    ratings = [r.get("rating") async for r in reviews_cur if isinstance(r.get("rating"), (int, float))]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    return {"completed_jobs": completed, "reviews_count": len(ratings), "avg_rating": avg_rating}


async def run_auto_promotion(triggered_by: str = "cron") -> dict:
    """Iterate active specialists, evaluate, promote/soft-flag.

    Idempotent. NEVER demotes/suspends a user (per platform-neutral policy).
    Only promotes upward. Sets `tier_warning_low_rating=True` if avg<soft_demote threshold.
    """
    rules_doc = await db.tier_rules.find_one({"_singleton": True}) or {}
    rules = TierRulesUpdate(**{k: v for k, v in rules_doc.items() if k not in ("_id", "_singleton")}).model_dump()
    if not rules.get("cron_enabled", True):
        return {"ok": True, "skipped": "cron_disabled"}

    promoted = 0
    flagged_low = 0
    cleared_low = 0
    scanned = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor = db.users.find({"role": "specialist", "deleted": {"$ne": True}}, {"_id": 1, "tier": 1, "tier_warning_low_rating": 1, "email": 1})
    async for u in cursor:
        scanned += 1
        uid = str(u["_id"])
        m = await _compute_user_metrics(uid)
        current_tier = u.get("tier") or "ENTRY"
        new_tier = current_tier
        # Promotion checks (only upward)
        if (m["completed_jobs"] >= rules["nivel_3_min_completed_jobs"]
            and m["avg_rating"] >= rules["nivel_3_min_rating"]
            and m["reviews_count"] >= rules["nivel_3_min_reviews"]):
            new_tier = "PREMIUM"
        elif (m["completed_jobs"] >= rules["nivel_2_min_completed_jobs"]
              and m["avg_rating"] >= rules["nivel_2_min_rating"]
              and m["reviews_count"] >= rules["nivel_2_min_reviews"]):
            if TIER_ORDER.get(current_tier, 1) < TIER_ORDER["VERIFIED"]:
                new_tier = "VERIFIED"
        # Only update if strictly upward
        update = {}
        if TIER_ORDER.get(new_tier, 1) > TIER_ORDER.get(current_tier, 1):
            update["tier"] = new_tier
            update["tier_promoted_at"] = now_iso
            promoted += 1
        # Soft warning flag (visual only — does not affect ranking, never bans)
        warn_now = bool(m["reviews_count"] >= 3 and m["avg_rating"] > 0 and m["avg_rating"] < rules["soft_demote_below_rating"])
        prev_warn = bool(u.get("tier_warning_low_rating"))
        if warn_now and not prev_warn:
            update["tier_warning_low_rating"] = True
            update["tier_warning_at"] = now_iso
            flagged_low += 1
        elif not warn_now and prev_warn:
            update["tier_warning_low_rating"] = False
            cleared_low += 1
        if update:
            await db.users.update_one({"_id": u["_id"]}, {"$set": update})

    summary = {"ok": True, "scanned": scanned, "promoted": promoted, "flagged_low": flagged_low, "cleared_low": cleared_low, "triggered_by": triggered_by, "at": now_iso}
    insert_doc = dict(summary)
    await db.tier_promotion_runs.insert_one(insert_doc)
    logger.info(f"[auto-promotion] {summary}")
    return summary


@router_admin.post("/run-auto-promotion")
async def trigger_auto_promotion(user: dict = Depends(require_role("admin"))):
    """Manual trigger — runs the same engine the cron job uses."""
    return await run_auto_promotion(triggered_by=f"manual:{user['id']}")


@router_admin.get("/tier-promotion-runs")
async def list_promotion_runs(_: dict = Depends(require_role("admin")), limit: int = Query(20, le=100)):
    cur = db.tier_promotion_runs.find({}, sort=[("at", -1)]).limit(limit)
    items = []
    async for d in cur:
        d.pop("_id", None)
        items.append(d)
    return {"items": items}


# ============================================================================
# 4. POLICY DOCUMENTS (versioned, public)
# ============================================================================
POLICY_SLUGS = ("terms", "privacy", "reviews_policy", "suspensions_policy", "ranking_policy")


class PolicyDocCreate(BaseModel):
    slug: str
    title: str
    content_html: str
    version: str = Field(..., min_length=1)
    effective_from: Optional[str] = None    # ISO date; defaults to now
    requires_reacceptance: bool = False     # if True, all users see banner on next login


@router_admin.get("/policy-docs")
async def admin_list_policies(_: dict = Depends(require_role("admin"))):
    """List ALL versions of all policies, latest first."""
    cur = db.policy_documents.find({}, sort=[("created_at", -1)])
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items}


@router_admin.post("/policy-docs")
async def admin_create_policy(data: PolicyDocCreate, user: dict = Depends(require_role("admin"))):
    if data.slug not in POLICY_SLUGS:
        raise HTTPException(400, f"Slug must be one of: {', '.join(POLICY_SLUGS)}")
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "slug": data.slug, "title": data.title, "content_html": data.content_html,
        "version": data.version, "effective_from": data.effective_from or now_iso,
        "requires_reacceptance": data.requires_reacceptance,
        "created_at": now_iso, "created_by": user["id"], "published": True,
    }
    result = await db.policy_documents.insert_one(doc)
    return {"id": str(result.inserted_id), "ok": True}


@router_public.get("/policy-docs/{slug}")
async def public_get_policy(slug: str):
    """Get latest published version of a policy. Public endpoint."""
    if slug not in POLICY_SLUGS:
        raise HTTPException(404, "Unknown policy slug")
    doc = await db.policy_documents.find_one({"slug": slug, "published": True}, sort=[("effective_from", -1)])
    if not doc:
        return {"slug": slug, "title": slug.replace("_", " ").title(), "content_html": "<p><em>Politică în pregătire.</em></p>", "version": "0.0.0", "missing": True}
    doc["id"] = str(doc.pop("_id"))
    return doc


# ============================================================================
# 5. DUAL ROLE — become-client (inverse of existing become-specialist)
# ============================================================================
@router_public.post("/auth/become-client")
async def become_client(user: dict = Depends(get_current_user)):
    """A specialist enables the client view too (dual_role). Same email/phone/wallet — just unlocks client UI."""
    if user.get("role") not in ("specialist", "client"):
        raise HTTPException(403, "Only specialists or clients can use dual-role")
    if user.get("dual_role_enabled"):
        return {"ok": True, "already_dual": True}
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"dual_role_enabled": True, "active_view": "client", "became_client_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "dual_role_enabled": True, "active_view": "client"}
