"""PropManage router: PropBenefits (PB-001) — motorul economic și de retenție."""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import get_current_user, require_role
from propbenefits import ledger, campaigns, opportunities, membership, eligibility
from propbenefits.config import get_config, update_config, ensure_seed, CAMPAIGN_KINDS, CAMPAIGN_STATUSES
from propbenefits.health import subscription_health, ecosystem_health, subscription_impact_scores, health_snapshot_tick
from propbenefits.ai_agents import success_manager, growth_advisor
from propbenefits.referral_ext import referral_activation_tick

logger = logging.getLogger("propmanage.propbenefits")

user_router = APIRouter(prefix="/api/benefits", tags=["prop-benefits"])
admin_router = APIRouter(prefix="/api/admin/prop-benefits", tags=["prop-benefits-admin"])


# ============================================================================
# USER — oportunități, portofel, nivel, success manager
# ============================================================================
@user_router.get("/opportunities")
async def my_opportunities(user: dict = Depends(get_current_user)):
    await ensure_seed()
    return await opportunities.feed(user)


@user_router.get("/wallet")
async def my_wallet(user: dict = Depends(get_current_user)):
    return await ledger.wallet_summary(user["id"])


@user_router.get("/membership")
async def my_membership(user: dict = Depends(get_current_user)):
    ctx = await eligibility.user_context(user)
    return await membership.compute_membership(ctx)


@user_router.post("/claim/{campaign_id}")
async def claim_benefit(campaign_id: str, user: dict = Depends(get_current_user)):
    result = await campaigns.claim(user, campaign_id)
    if result.get("error"):
        raise HTTPException(result.get("code", 400), result["error"])
    return result


@user_router.post("/use/{benefit_id}")
async def use_benefit(benefit_id: str, user: dict = Depends(get_current_user)):
    result = await ledger.use_benefit(user["id"], benefit_id)
    if result.get("error"):
        raise HTTPException(409 if result["error"].startswith("status_") else 404,
                            {"not_found": "Beneficiu inexistent.",
                             "status_used": "Beneficiul a fost deja folosit.",
                             "status_expired": "Beneficiul a expirat.",
                             "status_pending_activation": "Beneficiul nu este încă activ."}.get(result["error"], result["error"]))
    return result


@user_router.get("/success-manager")
async def my_success_manager(user: dict = Depends(get_current_user)):
    return await success_manager(user)


# ============================================================================
# PB-002 · PropBenefits Everywhere — sumarele contextuale per rol
# ============================================================================
@user_router.get("/pulse")
async def my_pulse(user: dict = Depends(get_current_user)):
    from propbenefits.summaries import client_pulse
    await ensure_seed()
    return await client_pulse(user)


@user_router.get("/specialist-summary")
async def my_specialist_summary(user: dict = Depends(get_current_user)):
    from propbenefits.summaries import specialist_summary
    return await specialist_summary(user)


@user_router.get("/building-summary/{building_id}")
async def my_building_summary(building_id: str, user: dict = Depends(get_current_user)):
    from propbenefits.summaries import building_summary
    result = await building_summary(user, building_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


@user_router.get("/marketplace-flags")
async def my_marketplace_flags(user: dict = Depends(get_current_user)):
    from propbenefits.summaries import marketplace_flags
    await ensure_seed()
    return await marketplace_flags(user)


@user_router.get("/context-banner/{surface}")
async def my_context_banner(surface: str, user: dict = Depends(get_current_user)):
    from propbenefits.summaries import context_banner
    if surface not in ("house_health", "digital_twin"):
        raise HTTPException(400, "surface invalid — permise: house_health, digital_twin")
    return await context_banner(user, surface)


@user_router.get("/community-deals")
async def my_community_deals(user: dict = Depends(get_current_user)):
    from propbenefits.community_deals import list_deals, DISCLAIMER
    return {"items": await list_deals(user_id=user["id"]), "disclaimer": DISCLAIMER}


@user_router.post("/community-deals/{deal_id}/support")
async def support_community_deal(deal_id: str, user: dict = Depends(get_current_user)):
    from propbenefits.community_deals import support_deal
    result = await support_deal(deal_id, user["id"])
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


# ============================================================================
# PB-003 · Community Trust & Recommendation Engine
# ============================================================================
@user_router.post("/recommendations")
async def submit_rec(body: dict = Body(...), user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import submit_recommendation
    result = await submit_recommendation(user, body)
    if result.get("error"):
        raise HTTPException(result.get("code", 400), result["error"])
    return result


@user_router.get("/recommendations/mine")
async def my_recs(user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import my_recommendations
    return await my_recommendations(user["id"])


@user_router.get("/ambassador")
async def my_ambassador(user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import ambassador_status
    return await ambassador_status(user["id"])


@user_router.post("/community-deals/{deal_id}/signal")
async def signal_community_deal(deal_id: str, body: dict = Body(...), user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import signal_deal
    result = await signal_deal(deal_id, user["id"], str(body.get("signal", "")))
    if result.get("error"):
        raise HTTPException(result.get("code", 400), result["error"])
    return result


@user_router.get("/community-deals/{deal_id}/why")
async def why_community_deal(deal_id: str, user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import explain_deal
    from propbenefits.eligibility import user_context
    result = await explain_deal(deal_id, await user_context(user))
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


@user_router.get("/trust/{specialist_id}")
async def specialist_trust(specialist_id: str, user: dict = Depends(get_current_user)):
    from propbenefits.trust_engine import explain_specialist
    return await explain_specialist(specialist_id)


# ============================================================================
# ADMIN — control complet FĂRĂ cod
# ============================================================================
@admin_router.get("/overview")
async def pb_overview(user=Depends(require_role("admin"))):
    await ensure_seed()
    eco = await ecosystem_health()
    return {
        "ecosystem": eco,
        "campaigns": {
            "active": await db.pb_campaigns.count_documents({"status": "active"}),
            "total": await db.pb_campaigns.count_documents({}),
        },
        "benefits": {
            "available": await db.pb_ledger.count_documents({"status": "available"}),
            "used": await db.pb_ledger.count_documents({"status": "used"}),
            "expired": await db.pb_ledger.count_documents({"status": "expired"}),
        },
        "referrals": {
            "pending": await db.pb_referral_pending.count_documents({"status": "pending_activation"}),
            "activated": await db.pb_referral_pending.count_documents({"status": "activated"}),
        },
        "health": {
            "at_risk": await db.pb_subscription_health.count_documents({"status": "at_risk"}),
            "watch": await db.pb_subscription_health.count_documents({"status": "watch"}),
            "healthy": await db.pb_subscription_health.count_documents({"status": "healthy"}),
        },
        "meta": {"kinds": CAMPAIGN_KINDS, "statuses": CAMPAIGN_STATUSES},
    }


@admin_router.get("/campaigns")
async def pb_campaigns_list(status: str = None, kind: str = None, user=Depends(require_role("admin"))):
    await ensure_seed()
    return {"items": await campaigns.list_campaigns(status, kind)}


@admin_router.post("/campaigns")
async def pb_campaign_create(body: dict = Body(...), user=Depends(require_role("admin"))):
    try:
        return await campaigns.create_campaign(body, user.get("email", "admin"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@admin_router.patch("/campaigns/{cid}")
async def pb_campaign_update(cid: str, body: dict = Body(...), user=Depends(require_role("admin"))):
    try:
        return await campaigns.update_campaign(cid, body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))


@admin_router.get("/config")
async def pb_config_get(user=Depends(require_role("admin"))):
    cfg = await get_config()
    cfg.pop("_id", None)
    return cfg


@admin_router.patch("/config")
async def pb_config_patch(body: dict = Body(...), user=Depends(require_role("admin"))):
    try:
        cfg = await update_config(body, user.get("email", "admin"))
        cfg.pop("_id", None)
        return cfg
    except ValueError as e:
        raise HTTPException(400, str(e))


@admin_router.get("/subscription-health")
async def pb_sub_health(status: str = None, user=Depends(require_role("admin"))):
    q = {"status": status} if status else {}
    items = await db.pb_subscription_health.find(q, {"_id": 0}).sort("score", 1).to_list(200)
    return {"items": items}


@admin_router.get("/subscription-health/{email}")
async def pb_sub_health_user(email: str, user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    return await subscription_health(target)


@admin_router.get("/ecosystem-health")
async def pb_eco_health(user=Depends(require_role("admin"))):
    return await ecosystem_health()


@admin_router.get("/impact-scores")
async def pb_impact_scores(user=Depends(require_role("admin"))):
    return await subscription_impact_scores()


@admin_router.get("/growth-advisor")
async def pb_growth_advisor(refresh: bool = False, user=Depends(require_role("admin"))):
    return await growth_advisor(refresh=refresh)


@admin_router.get("/north-star")
async def pb_north_star(user=Depends(require_role("admin"))):
    from propbenefits.health import north_star
    return await north_star()


@admin_router.get("/community-growth")
async def pb_community_growth(user=Depends(require_role("admin"))):
    from propbenefits.trust_engine import community_growth
    return await community_growth()


@admin_router.get("/community-deals")
async def pb_deals_admin(user=Depends(require_role("admin"))):
    from propbenefits.community_deals import list_deals, DEAL_STATUSES
    return {"items": await list_deals(include_archived=True), "statuses": DEAL_STATUSES}


@admin_router.post("/community-deals")
async def pb_deal_create(body: dict = Body(...), user=Depends(require_role("admin"))):
    from propbenefits.community_deals import upsert_deal
    try:
        return await upsert_deal(body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@admin_router.patch("/community-deals/{deal_id}")
async def pb_deal_update(deal_id: str, body: dict = Body(...), user=Depends(require_role("admin"))):
    from propbenefits.community_deals import upsert_deal
    try:
        return await upsert_deal(body, deal_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))


@admin_router.post("/run-tick")
async def pb_run_tick(user=Depends(require_role("admin"))):
    return await pb_daily_tick()


# ============================================================================
# Tick zilnic — expirări, activări referral, snapshot Subscription Health
# ============================================================================
async def pb_daily_tick() -> dict:
    from propbenefits.trust_engine import validate_recommendations_tick, trust_scores_tick, sync_trust_graph
    expired = await ledger.expire_tick()
    activated = await referral_activation_tick()
    snap = await health_snapshot_tick()
    recs = await validate_recommendations_tick()
    trust_n = await trust_scores_tick()
    graph = await sync_trust_graph()
    result = {"benefits_expired": expired, "referrals_activated": activated, **snap,
              "recommendations_validated": recs["validated"], "trust_scores": trust_n,
              "trust_graph": graph}
    logger.info(f"[propbenefits] daily tick: {result}")
    return result
