"""
Community Zone (Phase 4 — Feb 2026)
====================================
Topics + Replies + Likes for Forum, Groups, and FAQ.

Collections:
  - community_topics: { id, category, title, body, author_id, author_name, author_role,
                        replies_count, likes_count, pinned, created_at, updated_at }
  - community_replies: { id, topic_id, body, author_id, author_name, author_role,
                         likes_count, created_at }
  - community_likes: { id, target_type (topic|reply), target_id, user_id, created_at }

Endpoints:
  - GET  /api/community/topics?category=&q=&sort=
  - POST /api/community/topics
  - GET  /api/community/topics/{id}
  - PATCH/DELETE /api/community/topics/{id}  (author or admin)
  - GET  /api/community/topics/{id}/replies
  - POST /api/community/topics/{id}/replies
  - POST /api/community/likes/toggle  body={target_type, target_id}
  - GET  /api/community/stats (counts per category)

Categories:
  forum, groups, faq, reviews
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone, timedelta
import uuid

from deps import get_current_user
from db import db

router = APIRouter(prefix="/api/community", tags=["community"])

ALLOWED_CATEGORIES = {"forum", "groups", "faq", "reviews"}


# ============= MODELS =============
class TopicCreate(BaseModel):
    category: Literal["forum", "groups", "faq", "reviews"]
    title: str = Field(..., min_length=4, max_length=200)
    body: str = Field(..., min_length=10, max_length=10000)


class TopicPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=4, max_length=200)
    body: Optional[str] = Field(None, min_length=10, max_length=10000)
    pinned: Optional[bool] = None


class ReplyCreate(BaseModel):
    body: str = Field(..., min_length=2, max_length=5000)


class LikeToggle(BaseModel):
    target_type: Literal["topic", "reply"]
    target_id: str


# ============= HELPERS =============
def _serialize_topic(doc: dict) -> dict:
    if not doc:
        return None
    doc["id"] = doc.get("id") or str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============= TOPICS =============
@router.get("/topics")
async def list_topics(
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: str = Query("recent"),  # recent | popular | pinned
    limit: int = Query(50, ge=1, le=100),
):
    query = {}
    if category and category in ALLOWED_CATEGORIES:
        query["category"] = category
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"body": {"$regex": q, "$options": "i"}},
        ]
    sort_field = "created_at"
    if sort == "popular":
        sort_field = "likes_count"
    items = []
    cursor = db.community_topics.find(query).sort([
        ("pinned", -1),
        (sort_field, -1),
    ]).limit(limit)
    async for d in cursor:
        items.append(_serialize_topic(d))
    return items


@router.post("/topics")
async def create_topic(payload: TopicCreate, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Trebuie să fii conectat")
    doc = {
        "id": str(uuid.uuid4()),
        "category": payload.category,
        "title": payload.title.strip(),
        "body": payload.body.strip(),
        "author_id": user.get("id") or str(user.get("_id")),
        "author_name": user.get("name") or "Utilizator",
        "author_role": user.get("role") or "client",
        "replies_count": 0,
        "likes_count": 0,
        "pinned": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.community_topics.insert_one(doc)
    return _serialize_topic(doc)


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    doc = await db.community_topics.find_one({"id": topic_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subiect inexistent")
    return _serialize_topic(doc)


@router.patch("/topics/{topic_id}")
async def patch_topic(topic_id: str, payload: TopicPatch, user=Depends(get_current_user)):
    doc = await db.community_topics.find_one({"id": topic_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subiect inexistent")
    is_admin = user.get("role") in ("admin", "operator")
    is_author = (user.get("id") or str(user.get("_id"))) == doc["author_id"]
    if not (is_admin or is_author):
        raise HTTPException(status_code=403, detail="Nu ai permisiune")
    update = {"updated_at": _now_iso()}
    if payload.title is not None and (is_admin or is_author):
        update["title"] = payload.title.strip()
    if payload.body is not None and (is_admin or is_author):
        update["body"] = payload.body.strip()
    if payload.pinned is not None:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Doar admin poate pin")
        update["pinned"] = payload.pinned
    await db.community_topics.update_one({"id": topic_id}, {"$set": update})
    doc = await db.community_topics.find_one({"id": topic_id})
    return _serialize_topic(doc)


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str, user=Depends(get_current_user)):
    doc = await db.community_topics.find_one({"id": topic_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subiect inexistent")
    is_admin = user.get("role") in ("admin", "operator")
    is_author = (user.get("id") or str(user.get("_id"))) == doc["author_id"]
    if not (is_admin or is_author):
        raise HTTPException(status_code=403, detail="Nu ai permisiune")
    await db.community_topics.delete_one({"id": topic_id})
    await db.community_replies.delete_many({"topic_id": topic_id})
    await db.community_likes.delete_many({"target_type": "topic", "target_id": topic_id})
    return {"ok": True}


# ============= REPLIES =============
@router.get("/topics/{topic_id}/replies")
async def list_replies(topic_id: str, limit: int = Query(100, ge=1, le=300)):
    items = []
    cursor = db.community_replies.find({"topic_id": topic_id}).sort("created_at", 1).limit(limit)
    async for d in cursor:
        d["id"] = d.get("id") or str(d.get("_id"))
        d.pop("_id", None)
        items.append(d)
    return items


@router.post("/topics/{topic_id}/replies")
async def create_reply(topic_id: str, payload: ReplyCreate, user=Depends(get_current_user)):
    topic = await db.community_topics.find_one({"id": topic_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Subiect inexistent")
    doc = {
        "id": str(uuid.uuid4()),
        "topic_id": topic_id,
        "body": payload.body.strip(),
        "author_id": user.get("id") or str(user.get("_id")),
        "author_name": user.get("name") or "Utilizator",
        "author_role": user.get("role") or "client",
        "likes_count": 0,
        "created_at": _now_iso(),
    }
    await db.community_replies.insert_one(doc)
    await db.community_topics.update_one(
        {"id": topic_id},
        {"$inc": {"replies_count": 1}, "$set": {"updated_at": _now_iso()}},
    )
    doc.pop("_id", None)
    return doc


# ============= LIKES =============
@router.post("/likes/toggle")
async def toggle_like(payload: LikeToggle, user=Depends(get_current_user)):
    user_id = user.get("id") or str(user.get("_id"))
    existing = await db.community_likes.find_one({
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "user_id": user_id,
    })
    target_collection = db.community_topics if payload.target_type == "topic" else db.community_replies
    if existing:
        await db.community_likes.delete_one({"_id": existing["_id"]})
        await target_collection.update_one({"id": payload.target_id}, {"$inc": {"likes_count": -1}})
        return {"liked": False}
    else:
        await db.community_likes.insert_one({
            "id": str(uuid.uuid4()),
            "target_type": payload.target_type,
            "target_id": payload.target_id,
            "user_id": user_id,
            "created_at": _now_iso(),
        })
        await target_collection.update_one({"id": payload.target_id}, {"$inc": {"likes_count": 1}})
        return {"liked": True}


@router.get("/likes/my")
async def list_my_likes(user=Depends(get_current_user)):
    """Returns set of (target_type, target_id) the current user liked — for highlighting in UI."""
    user_id = user.get("id") or str(user.get("_id"))
    items = []
    async for d in db.community_likes.find({"user_id": user_id}):
        items.append({"target_type": d["target_type"], "target_id": d["target_id"]})
    return items


# ============= STATS =============
@router.get("/stats")
async def community_stats():
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    ]
    counts = {c: 0 for c in ALLOWED_CATEGORIES}
    async for d in db.community_topics.aggregate(pipeline):
        if d["_id"] in counts:
            counts[d["_id"]] = d["count"]
    total_replies = await db.community_replies.count_documents({})
    return {
        "topics_per_category": counts,
        "total_topics": sum(counts.values()),
        "total_replies": total_replies,
    }


# ============= AUTO WELCOME TOPIC (called from welcome voucher flow) =============
async def auto_create_welcome_topic(user_id: str, user_name: str, role: str = "specialist"):
    """
    Auto-create a 'Hello' community post when a new user receives the welcome voucher.
    Adds MEMBER_OF_THE_WEEK badge for 7 days. Idempotent per user.
    Called from routes.marketplace_offers.issue_welcome_voucher_for_specialist
    and (future) from client registration flow.
    """
    # Idempotency: check if user already has a welcome post
    existing = await db.community_topics.find_one({
        "author_id": user_id,
        "tags": {"$in": ["welcome_post"]},
    })
    if existing:
        return None

    role_label = "Specialist" if role == "specialist" else "Proprietar"
    title = f"Salutare, sunt {user_name.split()[0] if user_name else 'nou'}! Mă alătur PropManage 👋"
    body = (
        f"Bună tuturor!\n\n"
        f"Tocmai m-am înregistrat ca **{role_label.lower()}** pe PropManage și voiam să mă prezint comunității. "
        f"Aștept cu interes să cunosc oamenii de aici și să găsesc parteneriate de încredere.\n\n"
        f"Dacă ai un sfat util pentru un nou membru, te rog lasă un comentariu mai jos. Mulțumesc! 🙌"
    )
    now = _now_iso()
    week_from_now = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "category": "forum",
        "title": title,
        "body": body,
        "author_id": user_id,
        "author_name": user_name or "Nou venit",
        "author_role": role,
        "replies_count": 0,
        "likes_count": 0,
        "pinned": False,
        "tags": ["welcome_post", "member_of_the_week"],
        "badge": "MEMBER_OF_THE_WEEK",
        "badge_expires_at": week_from_now,
        "created_at": now,
        "updated_at": now,
    }
    await db.community_topics.insert_one(doc)
    return doc.get("id")

async def seed_community_demo():
    """Seed a few demo topics if collection is empty."""
    count = await db.community_topics.count_documents({})
    if count > 0:
        return
    demo_topics = [
        {
            "category": "forum",
            "title": "Cum aleg un electrician verificat în București?",
            "body": "Salut! Caut recomandări pentru un electrician serios pentru un apartament în Pipera. Verificați aici au prețuri ok? Mulțumesc.",
            "author_name": "Andrei Popescu",
            "author_role": "client",
        },
        {
            "category": "forum",
            "title": "Experiență cu serviciul Digital Twin — merită?",
            "body": "Tocmai mi-am scanat apartamentul cu PropManage. Vreau să întreb dacă vouchere se aplică și pe upgrade-uri viitoare.",
            "author_name": "Maria Ionescu",
            "author_role": "client",
        },
        {
            "category": "groups",
            "title": "Grup proprietari Skyline Loft A4",
            "body": "Suntem 12 proprietari din complex. Vrem să organizăm reparațiile zonelor comune folosind platforma. Cine se alătură?",
            "author_name": "Cristian Dima",
            "author_role": "client",
        },
        {
            "category": "faq",
            "title": "Cum funcționează plata escrow?",
            "body": "Banii rămân blocați la PropManage până confirmi finalizarea lucrării. Specialistul primește plata doar după ce apeși 'Confirmă'. Asta îți garantează că primești ce ai cerut.",
            "author_name": "Echipa PropManage",
            "author_role": "admin",
        },
        {
            "category": "faq",
            "title": "Ce înseamnă specialist VERIFIED?",
            "body": "Un specialist verificat a încărcat documente de identitate, certificări profesionale (după caz), și a fost aprobat manual de echipa noastră. Vine cu un badge verde.",
            "author_name": "Echipa PropManage",
            "author_role": "admin",
        },
    ]
    now = _now_iso()
    for t in demo_topics:
        doc = {
            "id": str(uuid.uuid4()),
            "category": t["category"],
            "title": t["title"],
            "body": t["body"],
            "author_id": "demo-seed",
            "author_name": t["author_name"],
            "author_role": t["author_role"],
            "replies_count": 0,
            "likes_count": 0,
            "pinned": t["category"] == "faq",
            "tags": [],
            "badge": None,
            "badge_expires_at": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.community_topics.insert_one(doc)
