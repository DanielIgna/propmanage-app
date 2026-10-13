"""Membri Rădăcini: profilul propriu (interese, localitate, bio)."""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso
from .constants import COUNTY, INTEREST_IDS, LOCALITIES

router = APIRouter(route_class=RadaciniRoute)

_MEMBER_FIELDS = ("id", "user_id", "interests", "county", "locality", "bio", "created_at", "updated_at")


class MemberIn(BaseModel):
    interests: list[str]
    county: str
    locality: str
    bio: Optional[str] = None

    @field_validator("interests")
    @classmethod
    def _interests(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Alege cel puțin un interes.")
        if any(i not in INTEREST_IDS for i in v):
            raise ValueError("Interes necunoscut.")
        return list(dict.fromkeys(v))

    @field_validator("county")
    @classmethod
    def _county(cls, v: str) -> str:
        if v != COUNTY:
            raise ValueError("Județul trebuie să fie Cluj.")
        return v

    @field_validator("locality")
    @classmethod
    def _locality(cls, v: str) -> str:
        if v not in LOCALITIES:
            raise ValueError("Localitate necunoscută.")
        return v

    @field_validator("bio")
    @classmethod
    def _bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Biografia are cel mult 500 de caractere.")
        return v or None


def _member_out(doc: dict) -> dict:
    data = serialize_doc(doc)
    return {k: data.get(k) for k in _MEMBER_FIELDS}


async def get_member_doc(user_id: str) -> Optional[dict]:
    return await db.radacini_members.find_one({"user_id": str(user_id)})


@router.get("/members/me")
async def get_my_member(user: dict = Depends(get_current_user)):
    doc = await get_member_doc(user["id"])
    if not doc:
        return {"exists": False}
    return {"exists": True, "member": _member_out(doc)}


@router.put("/members/me")
async def put_my_member(body: MemberIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    now = now_iso()
    fields = {
        "interests": body.interests,
        "county": body.county,
        "locality": body.locality,
        "bio": body.bio,
        "updated_at": now,
    }
    existing = await get_member_doc(uid)
    if existing:
        await db.radacini_members.update_one({"_id": existing["_id"]}, {"$set": fields})
        doc = {**existing, **fields}
    else:
        doc = mark_demo({"user_id": uid, **fields, "created_at": now})
        await db.radacini_members.insert_one(doc)
    member = _member_out(doc)
    await emit(
        "radacini.member_updated",
        actor=user,
        payload={"member_id": member["id"], "locality": body.locality, "interests": body.interests},
    )
    return {"member": member}
