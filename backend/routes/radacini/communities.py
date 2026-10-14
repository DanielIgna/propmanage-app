"""Comunități Rădăcini (S6-A): comunități locale, membri (open/closed), anunțuri.

Colecții: `radacini_communities`, `radacini_community_members` (unic pe (community, user), prin upsert),
`radacini_community_posts`. `members_count` se ține cu `$inc` doar pentru membri `active`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify
from .constants import LOCALITIES

router = APIRouter(route_class=RadaciniRoute)

MAX_CREATED_PER_USER = 10
IN_CHUNK = 100


def _first_name(name: Optional[str]) -> str:
    parts = (name or "").split()
    return parts[0] if parts else "Membru"


def community_link(cid) -> str:
    return f"/radacini/comunitati/{cid}"


async def get_community_member(community_id: str, user_id: str) -> Optional[dict]:
    return await db.radacini_community_members.find_one({"community_id": str(community_id), "user_id": str(user_id)})


async def active_community_role(community_id: str, user_id: str) -> Optional[str]:
    """'coordinator' | 'member' dacă userul e membru activ, altfel None (folosit și de decizii)."""
    m = await get_community_member(community_id, user_id)
    return m.get("role") if m and m.get("status") == "active" else None


async def _load_community(community_id: str) -> dict:
    doc = await db.radacini_communities.find_one({"_id": oid_or_404(community_id)})
    if not doc:
        raise HTTPException(404, "Comunitatea nu există.")
    return doc


async def _need_coordinator(community_id: str, user: dict) -> None:
    if await active_community_role(community_id, user["id"]) != "coordinator":
        raise HTTPException(403, "Doar coordonatorii comunității pot face această acțiune.")


def _text(v: str, lo: int, hi: int, msg: str) -> str:
    v = (v or "").strip()
    if not (lo <= len(v) <= hi):
        raise ValueError(msg)
    return v


class CommunityIn(BaseModel):
    name: str
    locality: str
    description: str = ""
    visibility: str = "open"

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _text(v, 3, 80, "Numele are între 3 și 80 de caractere.")

    @field_validator("locality")
    @classmethod
    def _loc(cls, v):
        if v not in LOCALITIES:
            raise ValueError("Localitate necunoscută.")
        return v

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        v = (v or "").strip()
        if len(v) > 1000:
            raise ValueError("Descrierea are cel mult 1000 de caractere.")
        return v

    @field_validator("visibility")
    @classmethod
    def _vis(cls, v):
        if v not in ("open", "closed"):
            raise ValueError("Vizibilitate necunoscută (open sau closed).")
        return v


class PostIn(BaseModel):
    text: str
    pinned: bool = False

    @field_validator("text")
    @classmethod
    def _t(cls, v):
        return _text(v, 1, 2000, "Anunțul are între 1 și 2000 de caractere.")


class PinIn(BaseModel):
    pinned: bool = True


def _community_out(doc: dict, mine: Optional[dict] = None) -> dict:
    out = serialize_doc(doc)
    out.pop("is_demo", None)
    out["my_role"] = mine.get("role") if mine else None
    out["my_status"] = mine.get("status") if mine else None
    return out


# ------------------------------------------------------------------------------------------ comunități

@router.get("/communities")
async def list_communities(locality: Optional[str] = None, q: Optional[str] = None, user: dict = Depends(get_current_user)):
    flt: dict = {}
    if locality:
        flt["locality"] = locality
    docs = await db.radacini_communities.find(flt).sort("members_count", -1).limit(300).to_list(300)
    needle = (q or "").strip().lower()
    if needle:
        docs = [d for d in docs if needle in (d.get("name") or "").lower() or needle in (d.get("description") or "").lower()]
    docs = docs[:100]
    mine: dict = {}
    ids = [str(d["_id"]) for d in docs]
    for i in range(0, len(ids), IN_CHUNK):
        rows = await db.radacini_community_members.find(
            {"user_id": str(user["id"]), "community_id": {"$in": ids[i:i + IN_CHUNK]}}
        ).limit(IN_CHUNK).to_list(IN_CHUNK)
        mine.update({r["community_id"]: r for r in rows})
    return {"items": [_community_out(d, mine.get(str(d["_id"]))) for d in docs]}


@router.post("/communities")
async def create_community(body: CommunityIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    if await db.radacini_communities.count_documents({"created_by": uid}) >= MAX_CREATED_PER_USER:
        raise HTTPException(409, f"Poți crea cel mult {MAX_CREATED_PER_USER} comunități.")
    now = now_iso()
    doc = mark_demo({
        "name": body.name, "locality": body.locality, "description": body.description,
        "visibility": body.visibility, "created_by": uid, "members_count": 1, "created_at": now,
    })
    res = await db.radacini_communities.insert_one(doc)
    cid = str(res.inserted_id)
    doc["_id"] = res.inserted_id
    member = mark_demo({
        "community_id": cid, "user_id": uid, "name": _first_name(user.get("name")),
        "role": "coordinator", "status": "active", "joined_at": now,
    })
    await db.radacini_community_members.update_one(
        {"community_id": cid, "user_id": uid}, {"$setOnInsert": member}, upsert=True)
    await emit("radacini.community_created", actor=user, payload={"community_id": cid})
    return {"community": _community_out(doc, member)}


@router.get("/communities/{community_id}")
async def get_community(community_id: str, user: dict = Depends(get_current_user)):
    doc = await _load_community(community_id)
    mine = await get_community_member(community_id, user["id"])
    out = _community_out(doc, mine)
    members = []
    pending = []
    if mine and mine.get("status") == "active":
        rows = await db.radacini_community_members.find({"community_id": community_id}).sort("joined_at", 1).limit(500).to_list(500)
        for r in rows:
            item = {"user_id": r["user_id"], "name": r.get("name"), "role": r.get("role"), "joined_at": r.get("joined_at")}
            if r.get("status") == "active":
                members.append(item)
            elif mine.get("role") == "coordinator":
                pending.append({**item, "status": "pending"})
    return {"community": out, "members": members, "pending": pending}


async def _insert_membership(community: dict, user: dict, status: str) -> bool:
    cid = str(community["_id"])
    uid = str(user["id"])
    doc = mark_demo({
        "community_id": cid, "user_id": uid, "name": _first_name(user.get("name")),
        "role": "member", "status": status, "joined_at": now_iso(),
    })
    res = await db.radacini_community_members.update_one(
        {"community_id": cid, "user_id": uid}, {"$setOnInsert": doc}, upsert=True)
    return res.upserted_id is not None


@router.post("/communities/{community_id}/join")
async def join_community(community_id: str, user: dict = Depends(get_current_user)):
    community = await _load_community(community_id)
    status = "active" if community.get("visibility") == "open" else "pending"
    if not await _insert_membership(community, user, status):
        raise HTTPException(409, "Ești deja membru sau ai o cerere în așteptare.")
    if status == "active":
        await db.radacini_communities.update_one({"_id": community["_id"]}, {"$inc": {"members_count": 1}})
    else:
        coords = await db.radacini_community_members.find(
            {"community_id": community_id, "role": "coordinator"}).limit(50).to_list(50)
        for c in coords:
            await safe_notify(c["user_id"], "Cerere de intrare în comunitate",
                              f"{_first_name(user.get('name'))} vrea să intre în „{community['name']}”.",
                              link=community_link(community_id), type_="community")
    await emit("radacini.community_joined", actor=user, payload={"community_id": community_id, "status": status})
    return {"status": status}


@router.post("/communities/{community_id}/leave")
async def leave_community(community_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    await _load_community(community_id)
    mine = await get_community_member(community_id, uid)
    if not mine:
        raise HTTPException(404, "Nu ești în această comunitate.")
    if mine.get("status") == "active" and mine.get("role") == "coordinator":
        others = await db.radacini_community_members.find(
            {"community_id": community_id, "role": "coordinator", "status": "active"}).limit(5).to_list(5)
        if not any(o["user_id"] != uid for o in others):
            raise HTTPException(409, "Ești ultimul coordonator. Promovează un alt membru înainte să pleci.")
    res = await db.radacini_community_members.delete_one({"_id": mine["_id"]})
    if res.deleted_count == 1 and mine.get("status") == "active":
        await db.radacini_communities.update_one({"_id": oid_or_404(community_id)}, {"$inc": {"members_count": -1}})
    await emit("radacini.community_left", actor=user, payload={"community_id": community_id})
    return {"ok": True}


async def _target_member(community_id: str, uid: str) -> dict:
    m = await get_community_member(community_id, uid)
    if not m:
        raise HTTPException(404, "Membrul nu există.")
    return m


@router.post("/communities/{community_id}/members/{member_uid}/approve")
async def approve_member(community_id: str, member_uid: str, user: dict = Depends(get_current_user)):
    community = await _load_community(community_id)
    await _need_coordinator(community_id, user)
    m = await _target_member(community_id, member_uid)
    res = await db.radacini_community_members.update_one(
        {"_id": m["_id"], "status": "pending"}, {"$set": {"status": "active", "joined_at": now_iso()}})
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea nu mai este în așteptare.")
    await db.radacini_communities.update_one({"_id": community["_id"]}, {"$inc": {"members_count": 1}})
    await safe_notify(member_uid, "Ai intrat în comunitate", f"Cererea ta în „{community['name']}” a fost aprobată.",
                      link=community_link(community_id), type_="community")
    await emit("radacini.community_member_approved", actor=user, payload={"community_id": community_id, "member_user_id": member_uid})
    return {"ok": True}


@router.post("/communities/{community_id}/members/{member_uid}/reject")
async def reject_member(community_id: str, member_uid: str, user: dict = Depends(get_current_user)):
    community = await _load_community(community_id)
    await _need_coordinator(community_id, user)
    m = await _target_member(community_id, member_uid)
    if m.get("status") != "pending":
        raise HTTPException(409, "Cererea nu mai este în așteptare.")
    res = await db.radacini_community_members.delete_one({"_id": m["_id"], "status": "pending"})
    if res.deleted_count != 1:
        raise HTTPException(409, "Cererea nu mai este în așteptare.")
    await safe_notify(member_uid, "Cerere respinsă", f"Cererea ta în „{community['name']}” nu a fost aprobată.",
                      link=community_link(community_id), type_="community")
    await emit("radacini.community_member_rejected", actor=user, payload={"community_id": community_id, "member_user_id": member_uid})
    return {"ok": True}


@router.post("/communities/{community_id}/members/{member_uid}/promote")
async def promote_member(community_id: str, member_uid: str, user: dict = Depends(get_current_user)):
    community = await _load_community(community_id)
    await _need_coordinator(community_id, user)
    m = await _target_member(community_id, member_uid)
    if m.get("status") != "active":
        raise HTTPException(409, "Doar membrii activi pot fi promovați.")
    if m.get("role") == "coordinator":
        raise HTTPException(409, "Este deja coordonator.")
    res = await db.radacini_community_members.update_one(
        {"_id": m["_id"], "status": "active", "role": "member"}, {"$set": {"role": "coordinator"}})
    if res.modified_count != 1:
        raise HTTPException(409, "Membrul s-a schimbat între timp.")
    await safe_notify(member_uid, "Ești coordonator", f"Ai fost promovat coordonator în „{community['name']}”.",
                      link=community_link(community_id), type_="community")
    await emit("radacini.community_member_promoted", actor=user, payload={"community_id": community_id, "member_user_id": member_uid})
    return {"ok": True}


# ------------------------------------------------------------------------------------------ anunțuri

@router.get("/communities/{community_id}/posts")
async def list_posts(community_id: str, limit: int = 30, skip: int = 0, user: dict = Depends(get_current_user)):
    await _load_community(community_id)
    if not await active_community_role(community_id, user["id"]):
        raise HTTPException(403, "Doar membrii comunității pot citi anunțurile.")
    limit = max(1, min(limit, 100))
    skip = max(0, skip)
    pinned = await db.radacini_community_posts.find(
        {"community_id": community_id, "pinned": True}).sort("created_at", -1).limit(1).to_list(1)
    rows = await db.radacini_community_posts.find({"community_id": community_id}).sort("created_at", -1) \
        .skip(skip).limit(limit + 1).to_list(limit + 1)
    if pinned:
        rows = [r for r in rows if r["_id"] != pinned[0]["_id"]]
        if skip == 0:
            rows = pinned + rows
    return {"items": [serialize_doc(r) for r in rows[:limit]]}


@router.post("/communities/{community_id}/posts")
async def create_post(community_id: str, body: PostIn, user: dict = Depends(get_current_user)):
    await _load_community(community_id)
    role = await active_community_role(community_id, user["id"])
    if not role:
        raise HTTPException(403, "Doar membrii comunității pot publica anunțuri.")
    if body.pinned and role != "coordinator":
        raise HTTPException(403, "Doar coordonatorul poate fixa un anunț.")
    doc = mark_demo({
        "community_id": community_id, "author_id": str(user["id"]), "author_name": _first_name(user.get("name")),
        "text": body.text, "pinned": False, "created_at": now_iso(),
    })
    res = await db.radacini_community_posts.insert_one(doc)
    doc["_id"] = res.inserted_id
    if body.pinned:
        await _pin(community_id, doc["_id"])
        doc["pinned"] = True
    await emit("radacini.community_post_created", actor=user, payload={"community_id": community_id, "post_id": str(res.inserted_id)})
    return {"post": serialize_doc(doc)}


async def _pin(community_id: str, post_id) -> None:
    """Un singur anunț fixat: întâi se scoate pinul de pe celelalte, apoi se fixează."""
    await db.radacini_community_posts.update_many(
        {"community_id": community_id, "pinned": True, "_id": {"$ne": post_id}}, {"$set": {"pinned": False}})
    await db.radacini_community_posts.update_one({"_id": post_id}, {"$set": {"pinned": True}})


@router.post("/posts/{post_id}/pin")
async def pin_post(post_id: str, body: PinIn, user: dict = Depends(get_current_user)):
    post = await db.radacini_community_posts.find_one({"_id": oid_or_404(post_id)})
    if not post:
        raise HTTPException(404, "Anunțul nu există.")
    await _need_coordinator(post["community_id"], user)
    if body.pinned:
        await _pin(post["community_id"], post["_id"])
    else:
        await db.radacini_community_posts.update_one({"_id": post["_id"]}, {"$set": {"pinned": False}})
    return {"ok": True, "pinned": body.pinned}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(get_current_user)):
    post = await db.radacini_community_posts.find_one({"_id": oid_or_404(post_id)})
    if not post:
        raise HTTPException(404, "Anunțul nu există.")
    if post.get("author_id") != str(user["id"]) and await active_community_role(post["community_id"], user["id"]) != "coordinator":
        raise HTTPException(403, "Doar autorul sau un coordonator poate șterge anunțul.")
    await db.radacini_community_posts.delete_one({"_id": post["_id"]})
    return {"ok": True}


@router.delete("/communities/{community_id}")
async def delete_community(community_id: str, user: dict = Depends(get_current_user)):
    """Doar creatorul, doar dacă a rămas singurul membru; șterge și anunțurile."""
    doc = await _load_community(community_id)
    if doc.get("created_by") != str(user["id"]):
        raise HTTPException(403, "Doar creatorul poate șterge comunitatea.")
    if (doc.get("members_count") or 0) > 1:
        raise HTTPException(409, "Comunitatea are alți membri.")
    await db.radacini_community_posts.delete_many({"community_id": community_id})
    await db.radacini_decisions.delete_many({"scope": "community", "scope_id": community_id})
    await db.radacini_community_members.delete_many({"community_id": community_id})
    await db.radacini_communities.delete_one({"_id": doc["_id"]})
    return {"ok": True}
