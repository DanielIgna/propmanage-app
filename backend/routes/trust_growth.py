"""GBOS P0 — Trust Growth Engine: Rebook/Recommend rollups, invitații + recomandări (referral).

Colecții noi (aditive): referral_invites, recommendations.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role
from services import notify, log_event

logger = logging.getLogger("propmanage.trust_growth")
router = APIRouter(prefix="/api", tags=["trust-growth"])

REBOOK_MIN_SHOW = 5  # PM-200: nu afișăm procente pe eșantioane nesemnificative


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def rebook_rollup(specialist_id: str) -> dict:
    """Agregă răspunsurile 'ai angaja din nou?' din recenziile client→specialist (v1+v2)."""
    counts = {"yes": 0, "no": 0, "not_sure": 0}
    async for row in db.reviews.aggregate([
        {"$match": {"specialist_id": specialist_id,
                    "direction": {"$ne": "specialist_to_client"},
                    "would_hire_again": {"$in": ["yes", "no", "not_sure"]}}},
        {"$group": {"_id": "$would_hire_again", "n": {"$sum": 1}}},
    ]):
        counts[row["_id"]] = row["n"]
    total = sum(counts.values())
    pct = round(counts["yes"] * 100 / total) if total else None
    return {"yes": counts["yes"], "no": counts["no"], "not_sure": counts["not_sure"],
            "total": total, "pct": pct, "show": total >= REBOOK_MIN_SHOW}


async def recommend_rollup(specialist_id: str) -> dict:
    """% 'l-ai recomanda altui proprietar?' din recenzii verificate."""
    yes = no = 0
    async for row in db.reviews.aggregate([
        {"$match": {"specialist_id": specialist_id,
                    "direction": {"$ne": "specialist_to_client"},
                    "would_recommend": {"$in": [True, False]}}},
        {"$group": {"_id": "$would_recommend", "n": {"$sum": 1}}},
    ]):
        if row["_id"] is True:
            yes = row["n"]
        else:
            no = row["n"]
    total = yes + no
    return {"yes": yes, "no": no, "total": total,
            "pct": round(yes * 100 / total) if total else None,
            "show": total >= REBOOK_MIN_SHOW}


async def recommenders_rollup(specialist_id: str) -> int:
    """Proprietari DISTINCȚI care recomandă: din recenzii (would_recommend) + recomandări directe."""
    ids = set()
    async for r in db.reviews.find({"specialist_id": specialist_id,
                                    "direction": {"$ne": "specialist_to_client"},
                                    "would_recommend": True}, {"client_id": 1}):
        if r.get("client_id"):
            ids.add(r["client_id"])
    async for r in db.recommendations.find({"specialist_id": specialist_id}, {"owner_id": 1}):
        if r.get("owner_id"):
            ids.add(r["owner_id"])
    return len(ids)


@router.get("/marketplace/specialists/{specialist_id}/trust")
async def specialist_trust(specialist_id: str):
    """Public: rollup-ul de încredere al unui specialist (Rebook > stele, PM-200)."""
    try:
        spec = await db.users.find_one({"_id": ObjectId(specialist_id), "role": "specialist"})
    except Exception:
        spec = None
    if not spec:
        raise HTTPException(404, "Specialist inexistent")
    rebook = await rebook_rollup(specialist_id)
    recommend = await recommend_rollup(specialist_id)
    recommenders = await recommenders_rollup(specialist_id)
    completed = await db.requests.count_documents({"specialist_id": specialist_id, "status": "confirmed"})
    return {
        "specialist_id": specialist_id,
        "rebook": rebook,
        "recommend": recommend,
        "recommenders": recommenders,
        "completed_jobs": completed,
        "rating": spec.get("rating"),
        "reviews_count": spec.get("reviews_count", 0),
        "verified": bool(spec.get("verified")),
        "explain": "Rebook = % proprietari care, după o lucrare reală finalizată, au spus că l-ar angaja din nou. Se afișează de la 5 răspunsuri.",
    }


@router.get("/marketplace/specialists/{specialist_id}/recommendations")
async def specialist_recommendations(specialist_id: str, limit: int = 20):
    """Public: recomandări directe de la proprietari (doar prenume — privacy PM-200)."""
    out = []
    docs = await db.recommendations.find({"specialist_id": specialist_id}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 50))
    for r in docs:
        first_name = (r.get("owner_name") or "Proprietar").split(" ")[0]
        out.append({
            "owner": first_name,
            "category": r.get("category"),
            "note": r.get("note"),
            "source": r.get("source"),
            "created_at": r.get("created_at"),
        })
    return {"items": out, "total": len(out)}


# ============================================================================
# REFERRAL / INVITE ENGINE (P0.1 + P0.2)
# ============================================================================
class InviteIn(BaseModel):
    invited_role: Literal["client", "specialist"] = "client"
    name: str = Field(min_length=2, max_length=120)
    email: Optional[str] = Field(None, max_length=160)
    phone: Optional[str] = Field(None, max_length=30)
    category: Optional[str] = Field(None, max_length=60)
    message: Optional[str] = Field(None, max_length=600)


@router.post("/referrals/invite")
async def create_invite(data: InviteIn, user: dict = Depends(get_current_user)):
    code = uuid4().hex[:10]
    doc = {
        "code": code,
        "inviter_id": user["id"],
        "inviter_name": user.get("name"),
        "inviter_role": user.get("role"),
        "invited_role": data.invited_role,
        "name": data.name.strip(),
        "email": (data.email or "").strip().lower() or None,
        "phone": (data.phone or "").strip() or None,
        "category": data.category,
        "message": (data.message or "").strip() or None,
        "status": "sent",
        "created_at": _now(),
    }
    await db.referral_invites.insert_one(dict(doc))
    import os
    front = os.environ.get("FRONTEND_URL", "https://propmanage.ro").rstrip("/")
    link = f"{front}/register?invite={code}&ref={user['id']}"
    if data.invited_role == "specialist":
        link += "&role=specialist" + (f"&category={data.category}" if data.category else "")
    # Email best-effort (gated de sandbox-ul Resend)
    if doc["email"]:
        try:
            from email_service import send_email as resend_send
            who = user.get("name") or "Un utilizator PropManage"
            role_txt = "specialist" if data.invited_role == "specialist" else "proprietar"
            note = f"<p style='color:#555'>„{doc['message']}”</p>" if doc.get("message") else ""
            html = (
                f"<h2>{who} te invită pe PropManage</h2>"
                f"<p>Ai fost invitat ca <b>{role_txt}</b> pe platforma care ține istoricul complet al caselor din România.</p>{note}"
                f"<p><a href='{link}' style='display:inline-block;background:#d4ff3a;color:#0a0a0b;padding:12px 24px;border-radius:999px;text-decoration:none;font-weight:bold'>Creează contul</a></p>"
                f"<p style='color:#888;font-size:12px'>Linkul tău de invitație: {link}</p>"
            )
            asyncio.create_task(resend_send(doc["email"], f"{who} te invită pe PropManage", html))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"invite email failed: {e}")
    try:
        await log_event(None, "referral_invite_created", actor=user, payload={"invited_role": data.invited_role, "has_email": bool(doc["email"])})
    except Exception:
        pass
    return {"ok": True, "code": code, "link": link}


@router.get("/referrals/mine")
async def my_referrals(user: dict = Depends(get_current_user)):
    invites = await db.referral_invites.find({"inviter_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    registered = sum(1 for i in invites if i.get("status") == "registered")
    referred = await db.users.count_documents({"referrer_id": user["id"]})
    import os
    front = os.environ.get("FRONTEND_URL", "https://propmanage.ro").rstrip("/")
    return {
        "invites": invites,
        "stats": {"sent": len(invites), "registered": registered, "referred_total": referred},
        "referral_url": f"{front}/register?ref={user['id']}",
        "referral_url_specialist": f"{front}/register?ref={user['id']}&role=specialist",
    }


@router.post("/referrals/claim")
async def claim_invite(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """Apelat de noul cont după register/login cu ?invite=CODE. Idempotent."""
    code = str(body.get("code") or "").strip()
    if not code:
        raise HTTPException(400, "Cod lipsă")
    inv = await db.referral_invites.find_one({"code": code})
    if not inv:
        raise HTTPException(404, "Invitație inexistentă")
    if inv.get("claimed_by") == user["id"]:
        return {"ok": True, "already": True}
    if inv.get("claimed_by"):
        raise HTTPException(409, "Invitație deja folosită")
    if inv.get("inviter_id") == user["id"]:
        raise HTTPException(400, "Nu îți poți folosi propria invitație")
    await db.referral_invites.update_one({"code": code}, {"$set": {
        "status": "registered", "claimed_by": user["id"], "claimed_name": user.get("name"), "claimed_at": _now(),
    }})
    # Owner → specialist cu testimonial: devine recomandare pe profil (sursă marcată onest)
    recommendation_created = False
    if inv.get("inviter_role") == "client" and user.get("role") == "specialist" and inv.get("message"):
        exists = await db.recommendations.find_one({"owner_id": inv["inviter_id"], "specialist_id": user["id"]})
        if not exists:
            await db.recommendations.insert_one({
                "id": uuid4().hex[:12],
                "owner_id": inv["inviter_id"],
                "owner_name": inv.get("inviter_name"),
                "specialist_id": user["id"],
                "category": inv.get("category"),
                "note": inv.get("message"),
                "source": "invite",
                "created_at": _now(),
            })
            recommendation_created = True
    try:
        await notify(inv["inviter_id"], "Invitația ta a prins viață 🎉",
                     f"{user.get('name') or 'Persoana invitată'} și-a creat cont pe PropManage prin invitația ta.",
                     type_="success")
        await log_event(None, "referral_invite_claimed", actor=user, payload={"inviter_id": inv["inviter_id"], "role": user.get("role")})
    except Exception:
        pass
    # PB-001.4: beneficiul se acordă DOAR la activare (abonament/primul serviciu plătit) — drept în așteptare
    try:
        from propbenefits.referral_ext import on_referral_claimed
        await on_referral_claimed(inv["inviter_id"], user["id"], user.get("name") or "")
    except Exception:
        pass
    return {"ok": True, "recommendation_created": recommendation_created}


@router.post("/referrals/recommend/{specialist_id}")
async def recommend_specialist(specialist_id: str, body: dict = Body(default={}), user: dict = Depends(require_role("client"))):
    """Un proprietar recomandă un specialist EXISTENT cu care a lucrat. Dedupe 1/owner/specialist."""
    if specialist_id == user["id"]:
        raise HTTPException(400, "Auto-recomandarea nu este permisă")
    try:
        spec = await db.users.find_one({"_id": ObjectId(specialist_id), "role": "specialist"})
    except Exception:
        spec = None
    if not spec:
        raise HTTPException(404, "Specialist inexistent")
    exists = await db.recommendations.find_one({"owner_id": user["id"], "specialist_id": specialist_id})
    if exists:
        raise HTTPException(409, "Ai recomandat deja acest specialist")
    worked_together = await db.requests.count_documents({"client_id": user["id"], "specialist_id": specialist_id, "status": "confirmed"}) > 0
    await db.recommendations.insert_one({
        "id": uuid4().hex[:12],
        "owner_id": user["id"],
        "owner_name": user.get("name"),
        "specialist_id": specialist_id,
        "category": body.get("category"),
        "note": str(body.get("note") or "").strip()[:600] or None,
        "source": "worked_together" if worked_together else "declared",
        "created_at": _now(),
    })
    try:
        await notify(specialist_id, "Ai o recomandare nouă ❤️",
                     f"{(user.get('name') or 'Un proprietar').split(' ')[0]} te-a recomandat pe PropManage.",
                     type_="success")
        await log_event(None, "specialist_recommended", actor=user, payload={"specialist_id": specialist_id, "source": "worked_together" if worked_together else "declared"})
    except Exception:
        pass
    return {"ok": True, "source": "worked_together" if worked_together else "declared"}
