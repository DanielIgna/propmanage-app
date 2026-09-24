"""Sprint C — Multi-Offer Flow + Hybrid Ranking + Fairness Rotation + Sponsorizat badge.

D2: submit_offer is public Marketplace participation (45 Lead Credits or 45 RON).
Client selection is accept_offer (D6). Public /accept is residual (D13).
Legacy fee_ron / priority_fee_ron are stored for compatibility and ranking, not charged.

Collections:
  - marketplace_offers (NEW): {request_id, specialist_id, fee_paid, message, status, created_at, ranking_score, sponsored}

Ranking formula (admin-tunable but defaults shown):
  score = fee_norm × 0.35 + rating × 0.30 + tier × 0.20 + recency × 0.10 + fairness × 0.05

Fairness Rotation (24h slot):
  - Day 1 from request creation: top 3 by base_score
  - Day 2: shift cohort — specialists who weren't in top 3 get +15% boost
  - Day 3+: revert to plain base_score

Sponsorizat badge: top 1-2 offers with priority_fee_ron > 0 get `sponsored=True` flag.
"""
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from db import db
from deps import get_current_user, require_role
from fulfillment_commit import (
    CLIENT_SELECTION,
    MULTI_OFFER,
    commit_assignment,
    stored_assignment_version,
)
from lead_credits import (
    debit_participation,
    paid_with_label,
    refund_participation,
    write_participation_ledger,
)
from services import notify, log_event

logger = logging.getLogger("propmanage.marketplace_offers")

router = APIRouter(prefix="/api", tags=["marketplace-offers"])

TIER_SCORE = {"ENTRY": 1, "VERIFIED": 2, "PREMIUM": 3}


# ============================================================================
# Models
# ============================================================================
class OfferIn(BaseModel):
    # LEGACY fields — accepted for backward compatibility, not charged (D2: 45 credits OR 45 RON).
    fee_ron: float = Field(0.0, ge=0.0, le=50.0, description="Legacy apply fee. Not charged as D2 participation.")
    priority_fee_ron: float = Field(0.0, ge=0.0, le=50.0, description="Legacy sponsored extra. Not charged as D2 participation.")
    message: Optional[str] = Field(None, max_length=1000)
    proposed_start_date: Optional[str] = None
    proposed_end_date: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0, le=500)


# ============================================================================
# Helpers — config + ranking
# ============================================================================
async def _get_fee_config():
    return await db.fee_configs.find_one({"_singleton": True}) or {}


async def _multi_offer_enabled() -> bool:
    cfg = await _get_fee_config()
    return bool(cfg.get("multi_offer_enabled"))


def _assignment_http(reason: str) -> HTTPException:
    if reason in ("already_assigned", "not_open", "version_mismatch", "conflict"):
        return HTTPException(409, "Cererea a fost deja atribuită")
    if reason == "strategy_mismatch":
        return HTTPException(400, "Strategia cererii nu permite această atribuire")
    return HTTPException(400, "Atribuirea nu a putut fi confirmată")


async def close_open_offers_after_assignment(
    request_id: str,
    winner_offer_id: Optional[str] = None,
) -> None:
    """Mark the winning offer won and any remaining open offers lost.

    Called only after commit_assignment succeeds. The winner update matches
    status=open, so a second accept cannot create a second winner.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    if winner_offer_id:
        await db.marketplace_offers.update_one(
            {
                "_id": ObjectId(winner_offer_id),
                "request_id": request_id,
                "status": "open",
            },
            {"$set": {"status": "won", "won_at": now_iso}},
        )
        await db.marketplace_offers.update_many(
            {
                "request_id": request_id,
                "status": "open",
                "_id": {"$ne": ObjectId(winner_offer_id)},
            },
            {"$set": {"status": "lost", "lost_at": now_iso}},
        )
        return
    await db.marketplace_offers.update_many(
        {"request_id": request_id, "status": "open"},
        {"$set": {"status": "lost", "lost_at": now_iso}},
    )


async def _ensure_active_offer_unique_index() -> None:
    """One non-withdrawn offer per specialist per request (D2 concurrency)."""
    try:
        await db.marketplace_offers.create_index(
            [("request_id", 1), ("specialist_id", 1)],
            unique=True,
            partialFilterExpression={"status": {"$in": ["open", "won", "lost"]}},
            name="uniq_active_offer_per_specialist",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("marketplace_offers unique index: %s", e)


def _fee_norm(fee: float, min_f: float, max_f: float) -> float:
    if max_f <= min_f:
        return 0.5
    return max(0.0, min(1.0, (fee - min_f) / (max_f - min_f)))


def _recency_score(created_at_iso: str) -> float:
    """Newer offers get higher recency (decays over 7 days)."""
    try:
        created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    except Exception:
        return 0.5
    age_h = max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 3600.0)
    # Half-life 72h → exp decay
    return math.exp(-age_h / 72.0)


def _fairness_boost(req_created_iso: str, offer_created_iso: str) -> float:
    """Time-window fairness — day 2-3 since request creation, recently-applied specialists get a small boost.

    Returns 0..1 (0=no boost, 1=full +15% bump). After day 3, returns 0.
    """
    try:
        req_age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(req_created_iso.replace("Z", "+00:00"))).total_seconds() / 3600.0
    except Exception:
        return 0.0
    if req_age_h < 24:
        return 0.0
    if req_age_h > 72:
        return 0.0
    # Linear ramp during day 2 (24-48h), full boost during day 3 (48-72h)
    if req_age_h < 48:
        return (req_age_h - 24) / 24.0
    return 1.0


async def _compute_score(offer: dict, request_doc: dict, spec_doc: dict, cfg: dict) -> dict:
    min_f = cfg.get("min_fee_ron", 5.0)
    max_f = cfg.get("max_fee_ron", 50.0)
    total_fee = (offer.get("fee_ron") or 0.0) + (offer.get("priority_fee_ron") or 0.0)
    fee_norm = _fee_norm(total_fee, min_f, max_f)
    rating_norm = max(0.0, min(1.0, (spec_doc.get("rating") or 0.0) / 5.0))
    tier_norm = TIER_SCORE.get(spec_doc.get("tier") or "ENTRY", 1) / 3.0
    rec = _recency_score(offer.get("created_at", ""))
    fair = _fairness_boost(request_doc.get("created_at", ""), offer.get("created_at", ""))
    score = fee_norm * 0.35 + rating_norm * 0.30 + tier_norm * 0.20 + rec * 0.10 + fair * 0.05
    return {
        "score": round(score, 4),
        "components": {"fee_norm": round(fee_norm, 3), "rating_norm": round(rating_norm, 3), "tier_norm": round(tier_norm, 3), "recency": round(rec, 3), "fairness": round(fair, 3)},
        "total_fee_ron": total_fee,
    }


# ============================================================================
# 1. SPECIALIST APPLIES (submits offer + pays fee)
# ============================================================================
@router.post("/requests/{req_id}/offers")
async def submit_offer(req_id: str, data: OfferIn, user: dict = Depends(require_role("specialist"))):
    """D2: participate with 45 Lead Credits or 45 RON. Does not assign the request."""
    req = await db.requests.find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    if req.get("fulfillment_strategy") != MULTI_OFFER:
        raise HTTPException(400, "Această cerere nu acceptă oferte publice")
    if req.get("status") != "open":
        raise HTTPException(400, "Această cerere nu mai acceptă oferte")
    if req.get("client_id") == user["id"]:
        raise HTTPException(400, "Nu poți aplica la propria ta cerere")
    existing = await db.marketplace_offers.find_one(
        {"request_id": req_id, "specialist_id": user["id"], "status": {"$ne": "withdrawn"}}
    )
    if existing:
        raise HTTPException(409, "Ai deja o ofertă activă la această cerere")
    open_count = await db.marketplace_offers.count_documents({"request_id": req_id, "status": "open"})
    if open_count >= 5:
        raise HTTPException(400, "S-au înregistrat deja 5 oferte la această cerere — așteaptă următoarea")
    spec = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not spec:
        raise HTTPException(404, "User not found")

    uid = ObjectId(user["id"])
    await _ensure_active_offer_unique_index()
    debit = await debit_participation(uid)

    raced = await db.marketplace_offers.find_one(
        {"request_id": req_id, "specialist_id": user["id"], "status": {"$ne": "withdrawn"}}
    )
    if raced:
        await refund_participation(uid, debit["payment"])
        raise HTTPException(409, "Ai deja o ofertă activă la această cerere")
    open_again = await db.marketplace_offers.count_documents({"request_id": req_id, "status": "open"})
    if open_again >= 5:
        await refund_participation(uid, debit["payment"])
        raise HTTPException(400, "S-au înregistrat deja 5 oferte la această cerere — așteaptă următoarea")

    now_iso = datetime.now(timezone.utc).isoformat()
    offer_doc = {
        "request_id": req_id,
        "specialist_id": user["id"],
        "specialist_name": spec.get("name", ""),
        "fee_ron": data.fee_ron,
        "priority_fee_ron": data.priority_fee_ron,
        "fee_paid_total": debit["monetary_fee"],
        "paid_with": paid_with_label(debit),
        "message": (data.message or "").strip()[:1000],
        "proposed_start_date": data.proposed_start_date,
        "proposed_end_date": data.proposed_end_date,
        "estimated_hours": data.estimated_hours,
        "status": "open",
        "created_at": now_iso,
        "sponsored": False,
    }
    try:
        result = await db.marketplace_offers.insert_one(offer_doc)
    except DuplicateKeyError:
        await refund_participation(uid, debit["payment"])
        raise HTTPException(409, "Ai deja o ofertă activă la această cerere")
    except Exception:
        await refund_participation(uid, debit["payment"])
        raise
    offer_id = str(result.inserted_id)
    await write_participation_ledger(user["id"], req_id, debit, offer_id=offer_id)
    await notify(
        req["client_id"],
        "Ofertă nouă primită",
        f"{spec.get('name', 'Specialist')} a aplicat la cererea ta. Verifică oferta.",
        type_="offer",
        link=f"/client/requests/{req_id}/offers",
    )
    await log_event(
        req_id,
        "offer.submitted",
        actor=user,
        payload={"offer_id": offer_id, "paid_with": paid_with_label(debit), "fee": debit["monetary_fee"]},
    )
    return {
        "ok": True,
        "offer_id": offer_id,
        "paid_with": paid_with_label(debit),
        "lead_credits_after": debit["remaining_credits"],
        "balance_after": debit["wallet_after"],
        "fee_paid": debit["monetary_fee"],
    }


# ============================================================================
# 2. CLIENT BROWSES OFFERS (ranked)
# ============================================================================
@router.get("/requests/{req_id}/offers")
async def list_offers(req_id: str, sort: str = Query("hybrid", regex="^(hybrid|rating|fee|newest)$"), user: dict = Depends(get_current_user)):
    """List offers for a request. Ranking-aware. Sort options: hybrid (default), rating, fee, newest."""
    req = await db.requests.find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    # RBAC: client (owner), admin, or any specialist who has an offer
    is_owner = req.get("client_id") == user["id"]
    is_admin = user.get("role") == "admin"
    if not (is_owner or is_admin):
        own_offer = await db.marketplace_offers.find_one({"request_id": req_id, "specialist_id": user["id"]})
        if not own_offer:
            raise HTTPException(403, "Doar clientul care a publicat cererea sau specialiștii care au aplicat pot vedea ofertele")
    cfg = await _get_fee_config()
    top_visible = cfg.get("top_visible_count", 3)
    offers_cursor = db.marketplace_offers.find({"request_id": req_id, "status": "open"})
    items = []
    async for o in offers_cursor:
        oid = str(o.pop("_id"))
        o["id"] = oid
        spec = await db.users.find_one({"_id": ObjectId(o["specialist_id"])}, {"name": 1, "rating": 1, "reviews_count": 1, "tier": 1, "tier_warning_low_rating": 1})
        o["specialist"] = {
            "id": o["specialist_id"], "name": spec.get("name", ""),
            "rating": spec.get("rating"), "reviews_count": spec.get("reviews_count", 0),
            "tier": spec.get("tier", "ENTRY"), "low_rating_warning": bool(spec.get("tier_warning_low_rating")),
        }
        ranking = await _compute_score(o, req, spec or {}, cfg)
        o.update(ranking)
        items.append(o)
    # Sort
    if sort == "hybrid":
        items.sort(key=lambda x: x["score"], reverse=True)
    elif sort == "rating":
        items.sort(key=lambda x: (x["specialist"].get("rating") or 0), reverse=True)
    elif sort == "fee":
        items.sort(key=lambda x: x["total_fee_ron"], reverse=True)
    elif sort == "newest":
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    # Mark visible cohort + sponsored badge (only on hybrid sort)
    if sort == "hybrid":
        sponsored_count = 0
        for idx, o in enumerate(items):
            o["visible_in_top"] = idx < top_visible
            if o.get("sponsored") and sponsored_count < 2 and idx < top_visible:
                o["badge"] = "sponsored"
                sponsored_count += 1
    return {"items": items, "total": len(items), "sort": sort, "ranking_policy": "fee×0.35 + rating×0.30 + tier×0.20 + recency×0.10 + fairness×0.05"}


# ============================================================================
# 3. CLIENT ACCEPTS AN OFFER
# ============================================================================
@router.post("/requests/{req_id}/offers/{offer_id}/accept")
async def accept_offer(req_id: str, offer_id: str, user: dict = Depends(require_role("client"))):
    req = await db.requests.find_one({"_id": ObjectId(req_id), "client_id": user["id"]})
    if not req:
        raise HTTPException(404, "Request not found")
    if req.get("fulfillment_strategy") != MULTI_OFFER:
        raise HTTPException(400, "Strategia cererii nu permite acceptarea unei oferte")
    if req.get("status") != "open":
        raise HTTPException(400, "Cererea nu mai e disponibilă")
    offer = await db.marketplace_offers.find_one({"_id": ObjectId(offer_id), "request_id": req_id, "status": "open"})
    if not offer:
        raise HTTPException(404, "Ofertă invalidă")
    spec = await db.users.find_one({"_id": ObjectId(offer["specialist_id"])}) or {}
    committed = await commit_assignment(
        request_id=req_id,
        expected_strategy=MULTI_OFFER,
        expected_assignment_version=stored_assignment_version(req),
        specialist_id=offer["specialist_id"],
        assignment_authority=CLIENT_SELECTION,
        assignment_trigger="client_accept_offer",
        assignment_reason="client accepted an offer",
        actor=user,
        offer_id=offer_id,
        specialist_snapshot={
            "specialist_name": offer.get("specialist_name", ""),
            "specialist_specialty": spec.get("specialty") or spec.get("category") or "",
            "specialist_city": spec.get("city") or spec.get("location") or "",
            "specialist_verified": bool(spec.get("verified")),
        },
    )
    if not committed["ok"]:
        raise _assignment_http(committed["reason"])
    extra = {"selected_offer_fee": offer.get("fee_paid_total", 0)}
    if offer.get("proposed_start_date"):
        extra["schedule_proposal"] = {
            "start_date": offer.get("proposed_start_date"),
            "end_date": offer.get("proposed_end_date"),
            "estimated_hours": offer.get("estimated_hours"),
            "proposed_at": offer.get("created_at"),
            "proposed_by": offer["specialist_id"],
        }
    await db.requests.update_one(
        {
            "_id": ObjectId(req_id),
            "specialist_id": offer["specialist_id"],
            "selected_offer_id": offer_id,
        },
        {"$set": extra},
    )
    await close_open_offers_after_assignment(req_id, offer_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    # Notify the winner + losers
    await notify(offer["specialist_id"], "Felicitări — oferta acceptată!", f"Clientul a ales oferta ta pentru '{req.get('title','')}'. Poți începe lucrarea.", type_="offer_won", link="/specialist")
    losers_cur = db.marketplace_offers.find({"request_id": req_id, "status": "lost"}, {"specialist_id": 1})
    async for ld in losers_cur:
        await notify(ld["specialist_id"], "Ofertă necâștigătoare", f"Clientul a ales un alt specialist pentru '{req.get('title','')}'. Fee-ul rămâne consumat ca cost de lead.", type_="offer_lost", link="/specialist")
    await log_event(req_id, "offer.accepted", actor=user, payload={"offer_id": offer_id, "specialist_id": offer["specialist_id"]})

    # House Health attribution — if this request came from a HH recommendation,
    # capture commission for later reconciliation. Non-blocking.
    try:
        hh_src = req.get("house_health_source")
        if hh_src and hh_src.get("commission_status") == "pending":
            offer_fee = float(offer.get("fee_paid_total", 0) or 0)
            commission_pct = float(hh_src.get("commission_pct", 10.0))
            commission_amount = round(offer_fee * (commission_pct / 100.0), 2)
            await db.requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {
                    "house_health_source.commission_status": "captured",
                    "house_health_source.commission_amount": commission_amount,
                    "house_health_source.commission_captured_at": now_iso,
                    "house_health_source.specialist_id": offer["specialist_id"],
                }},
            )
            await db.hh_audit_log.insert_one({
                "user_id": user["id"],
                "action": "commission_captured",
                "resource_id": hh_src.get("recommendation_id"),
                "request_id": req_id,
                "specialist_id": offer["specialist_id"],
                "amount": commission_amount,
                "commission_pct": commission_pct,
                "timestamp": now_iso,
            })
    except Exception as e:  # noqa: BLE001
        logger.warning("[house_health] commission capture failed for req=%s: %s", req_id, e)

    return {"ok": True, "specialist_id": offer["specialist_id"], "specialist_name": offer.get("specialist_name", "")}


# ============================================================================
# 4. SPECIALIST WITHDRAWS THEIR OFFER (no refund per platform policy)
# ============================================================================
@router.post("/requests/{req_id}/offers/{offer_id}/withdraw")
async def withdraw_offer(req_id: str, offer_id: str, user: dict = Depends(require_role("specialist"))):
    offer = await db.marketplace_offers.find_one({"_id": ObjectId(offer_id), "specialist_id": user["id"], "request_id": req_id})
    if not offer:
        raise HTTPException(404, "Oferta ta nu există")
    if offer.get("status") != "open":
        raise HTTPException(400, "Oferta nu mai este activă")
    await db.marketplace_offers.update_one({"_id": ObjectId(offer_id)}, {"$set": {"status": "withdrawn", "withdrawn_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "refund": False, "note": "Fee-ul plătit rămâne consumat ca cost de lead (politica platformei)"}


# ============================================================================
# 5. SPECIALIST WELCOME VOUCHER (bonus — auto-issued on specialist registration)
# ============================================================================
async def issue_welcome_voucher_for_specialist(user_id: str, user_email: str):
    """Best-effort — issues a 50% welcome voucher (valid 30 days) when a specialist registers.

    Idempotent: only issues if user has no `welcome_voucher_issued` flag.
    """
    try:
        u = await db.users.find_one({"_id": ObjectId(user_id)}, {"welcome_voucher_issued": 1, "role": 1, "name": 1})
        if not u or u.get("role") != "specialist" or u.get("welcome_voucher_issued"):
            return None
        import secrets
        code = "WELCOME-" + secrets.token_hex(4).upper()
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        await db.vouchers.insert_one({
            "code": code, "percent": 50, "client_id": user_id,
            "reason": "Welcome voucher — primul venit pe PropManage ca specialist",
            "status": "active", "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires, "source": "auto_welcome_specialist",
        })
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"welcome_voucher_issued": True, "welcome_voucher_code": code}})
        # Send email (best-effort)
        try:
            from email_service import send_email, _layout
            html = _layout(
                "Bun venit, specialist!",
                "Voucher 50% așteaptă",
                f"<p>Salut {u.get('name','')},</p><p>Felicitări că te-ai înscris pe PropManage ca specialist!</p>"
                f"<p>Te recompensăm cu un voucher de <strong>50% reducere</strong> la primul fee de aplicare la o cerere:</p>"
                f"<div style='background:#d4ff3a15; border-left:3px solid #d4ff3a; padding:16px; border-radius:12px; margin:16px 0;'>"
                f"<div style='font-family:monospace;font-size:18px;color:#d4ff3a;letter-spacing:2px;'>{code}</div></div>"
                f"<p>Valabil 30 de zile. Folosește-l la următoarea aplicare.</p>",
                "https://propmanage.ro/specialist", "Mergi la dashboard"
            )
            await send_email(to=user_email, subject="🎁 Bun venit pe PropManage — voucher 50%", html=html)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[welcome_voucher] email send failed: {e}")
        # NEW: Auto-create a "Hello" community post with MEMBER_OF_THE_WEEK badge
        try:
            from routes.community import auto_create_welcome_topic
            await auto_create_welcome_topic(user_id=user_id, user_name=u.get("name") or "Specialist nou", role="specialist")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[welcome_voucher] community post failed: {e}")
        return code
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[welcome_voucher] failed: {e}")
        return None
