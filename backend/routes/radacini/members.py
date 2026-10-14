"""Membri Rădăcini: profilul propriu (interese, localitate, bio)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso
from .constants import COUNTY, INTEREST_IDS, LOCALITIES

router = APIRouter(route_class=RadaciniRoute)

_MEMBER_FIELDS = ("id", "user_id", "interests", "county", "locality", "bio", "created_at", "updated_at", "onboarding")

ONBOARDING_STEPS = ("terms", "profile", "discover", "notifications")


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


class StepIn(BaseModel):
    step: str

    @field_validator("step")
    @classmethod
    def _step(cls, v: str) -> str:
        if v not in ONBOARDING_STEPS:
            raise ValueError("Pas de ghid necunoscut.")
        return v


def _onboarding_view(member_ob: Optional[dict], pre_ob: Optional[dict]) -> dict:
    """Ghidul de pornire: pașii din profil + cei salvați înainte de crearea profilului (doar „terms”)."""
    steps = list((member_ob or {}).get("steps_done") or [])
    for s in (pre_ob or {}).get("steps_done") or []:
        if s not in steps:
            steps.append(s)
    return {"completed_at": (member_ob or {}).get("completed_at"), "steps_done": steps}


def _member_out(doc: dict, pre_ob: Optional[dict] = None) -> dict:
    data = serialize_doc(doc)
    out = {k: data.get(k) for k in _MEMBER_FIELDS}
    out["onboarding"] = _onboarding_view(doc.get("onboarding"), pre_ob)
    return out


async def _pre_onboarding(user_id: str) -> Optional[dict]:
    return await db.radacini_onboarding.find_one({"user_id": str(user_id)})


async def get_member_doc(user_id: str) -> Optional[dict]:
    return await db.radacini_members.find_one({"user_id": str(user_id)})


@router.get("/members/me")
async def get_my_member(user: dict = Depends(get_current_user)):
    doc = await get_member_doc(user["id"])
    pre = await _pre_onboarding(user["id"])
    if not doc:
        return {"exists": False, "onboarding": _onboarding_view(None, pre)}
    return {"exists": True, "member": _member_out(doc, pre), "onboarding": _onboarding_view(doc.get("onboarding"), pre)}


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
    # Upsert pe user_id (serializat de pgmongo): două PUT simultane nu pot crea două profiluri.
    await db.radacini_members.update_one(
        {"user_id": uid},
        {"$set": fields, "$setOnInsert": mark_demo({"user_id": uid, "created_at": now})},
        upsert=True,
    )
    doc = await get_member_doc(uid)
    member = _member_out(doc, await _pre_onboarding(uid))
    await emit(
        "radacini.member_updated",
        actor=user,
        payload={"member_id": member["id"], "locality": body.locality, "interests": body.interests},
    )
    return {"member": member}


# ------------------------------------------------------------------ onboarding
# Fără profil de membru, doar pasul „terms” se poate salva (în `radacini_onboarding`, cheie user_id);
# la citire se îmbină cu pașii din profil. Celelalte acțiuni cer profilul (409 „Completează profilul”).

NEED_PROFILE = "Completează profilul."


@router.post("/members/me/onboarding")
async def onboarding_step(body: StepIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    now = now_iso()
    member = await get_member_doc(uid)
    if member:
        await db.radacini_members.update_one(
            {"user_id": uid}, {"$addToSet": {"onboarding.steps_done": body.step}, "$set": {"updated_at": now}})
    elif body.step == "terms":
        await db.radacini_onboarding.update_one(
            {"user_id": uid}, {"$addToSet": {"steps_done": body.step},
                               "$setOnInsert": mark_demo({"user_id": uid, "created_at": now})}, upsert=True)
    else:
        raise HTTPException(409, NEED_PROFILE)
    member = await get_member_doc(uid)
    pre = await _pre_onboarding(uid)
    return {"onboarding": _onboarding_view((member or {}).get("onboarding"), pre)}


@router.post("/members/me/onboarding/complete")
async def onboarding_complete(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    if not await get_member_doc(uid):
        raise HTTPException(409, NEED_PROFILE)
    now = now_iso()
    await db.radacini_members.update_one(
        {"user_id": uid}, {"$set": {"onboarding.completed_at": now, "updated_at": now}})
    member = await get_member_doc(uid)
    return {"onboarding": _onboarding_view(member.get("onboarding"), await _pre_onboarding(uid))}


@router.post("/members/me/onboarding/reset")
async def onboarding_reset(user: dict = Depends(get_current_user)):
    """Reia ghidul din Setări: șterge pașii și data finalizării (acceptarea termenilor rămâne valabilă)."""
    uid = str(user["id"])
    if not await get_member_doc(uid):
        raise HTTPException(409, NEED_PROFILE)
    await db.radacini_members.update_one(
        {"user_id": uid}, {"$set": {"onboarding": {"steps_done": [], "completed_at": None}, "updated_at": now_iso()}})
    await db.radacini_onboarding.delete_many({"user_id": uid})
    return {"onboarding": _onboarding_view(None, None)}
