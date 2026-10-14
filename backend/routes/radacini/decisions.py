"""Decizii și vot (S6-C): întrebări cu 2–6 opțiuni pentru o comunitate sau un proiect.

Colecție: `radacini_decisions`. Votul e unic per utilizator: actualizare condiționată pe `rev` (reîncercată
de câteva ori; 409 dacă userul a votat deja). Rezultatele se văd după ce ai votat sau după închidere.
Identitatea votanților nu se expune niciodată.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404
from .communities import active_community_role
from .projects import member_role

router = APIRouter(route_class=RadaciniRoute)

MAX_DAYS = 365
VOTE_RETRIES = 6


def _parse_dt(v) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class DecisionIn(BaseModel):
    scope: str
    scope_id: str
    question: str
    options: list[str]
    closes_at: str

    @field_validator("scope")
    @classmethod
    def _scope(cls, v):
        if v not in ("community", "project"):
            raise ValueError("Domeniu necunoscut (community sau project).")
        return v

    @field_validator("question")
    @classmethod
    def _q(cls, v):
        v = (v or "").strip()
        if not (5 <= len(v) <= 200):
            raise ValueError("Întrebarea are între 5 și 200 de caractere.")
        return v

    @field_validator("options")
    @classmethod
    def _opts(cls, v):
        opts = [(o or "").strip() for o in v]
        if not (2 <= len(opts) <= 6):
            raise ValueError("Sunt necesare 2–6 opțiuni.")
        if any(not (1 <= len(o) <= 100) for o in opts):
            raise ValueError("Fiecare opțiune are între 1 și 100 de caractere.")
        if len({o.lower() for o in opts}) != len(opts):
            raise ValueError("Opțiunile trebuie să fie distincte.")
        return opts

    @field_validator("closes_at")
    @classmethod
    def _closes(cls, v):
        dt = _parse_dt(v)
        if dt is None:
            raise ValueError("Data închiderii nu este validă.")
        now = datetime.now(timezone.utc)
        if dt <= now:
            raise ValueError("Data închiderii trebuie să fie în viitor.")
        if dt > now + timedelta(days=MAX_DAYS):
            raise ValueError("Decizia poate rămâne deschisă cel mult un an.")
        return dt.astimezone(timezone.utc).isoformat()


class VoteIn(BaseModel):
    option_index: int


async def _role_in_scope(scope: str, scope_id: str, user_id: str) -> Optional[str]:
    """'coordinator' | 'member' dacă userul e membru activ al comunității/proiectului, altfel None."""
    if scope == "community":
        return await active_community_role(scope_id, user_id)
    if not (len(scope_id) == 24 and ObjectId.is_valid(scope_id)):
        return None
    project = await db.radacini_projects.find_one({"_id": ObjectId(scope_id)})
    if not project:
        return None
    role = member_role(project, user_id)
    return "coordinator" if role == "coordinator" else ("member" if role else None)


async def _lazy_close(doc: dict) -> dict:
    if doc.get("status") == "open":
        dt = _parse_dt(doc.get("closes_at"))
        if dt is not None and dt <= datetime.now(timezone.utc):
            at = now_iso()
            await db.radacini_decisions.update_one(
                {"_id": doc["_id"], "status": "open"}, {"$set": {"status": "closed", "closed_at": at}})
            doc = {**doc, "status": "closed", "closed_at": at}
    return doc


def _view(doc: dict, uid: str) -> dict:
    votes = doc.get("votes") or []
    mine = next((v for v in votes if v.get("user_id") == uid), None)
    out = serialize_doc(doc)
    out.pop("votes", None)
    out.pop("rev", None)
    out.pop("is_demo", None)
    out["votes_count"] = len(votes)
    out["my_vote"] = mine.get("option_index") if mine else None
    out["can_close"] = doc.get("created_by") == uid and doc.get("status") == "open"
    if mine is not None or doc.get("status") == "closed":
        counts = [0] * len(doc.get("options") or [])
        for v in votes:
            i = v.get("option_index")
            if isinstance(i, int) and 0 <= i < len(counts):
                counts[i] += 1
        out["results"] = counts
    else:
        out["results"] = None
    return out


@router.get("/decisions")
async def list_decisions(scope: str, scope_id: str, user: dict = Depends(get_current_user)):
    if scope not in ("community", "project"):
        raise HTTPException(400, "Domeniu necunoscut (community sau project).")
    uid = str(user["id"])
    if not await _role_in_scope(scope, scope_id, uid):
        raise HTTPException(403, "Doar membrii pot vedea deciziile.")
    docs = await db.radacini_decisions.find({"scope": scope, "scope_id": scope_id}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": [_view(await _lazy_close(d), uid) for d in docs]}


@router.post("/decisions")
async def create_decision(body: DecisionIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    if await _role_in_scope(body.scope, body.scope_id, uid) != "coordinator":
        raise HTTPException(403, "Doar un coordonator poate crea o decizie.")
    doc = mark_demo({
        "scope": body.scope, "scope_id": body.scope_id, "question": body.question, "options": body.options,
        "closes_at": body.closes_at, "created_by": uid, "status": "open", "votes": [], "rev": 0,
        "created_at": now_iso(),
    })
    res = await db.radacini_decisions.insert_one(doc)
    doc["_id"] = res.inserted_id
    await emit("radacini.decision_created", actor=user, payload={"decision_id": str(res.inserted_id), "scope": body.scope, "scope_id": body.scope_id})
    return {"decision": _view(doc, uid)}


@router.post("/decisions/{decision_id}/vote")
async def vote(decision_id: str, body: VoteIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "votul")
    uid = str(user["id"])
    oid = oid_or_404(decision_id)
    for _ in range(VOTE_RETRIES):
        doc = await db.radacini_decisions.find_one({"_id": oid})
        if not doc:
            raise HTTPException(404, "Decizia nu există.")
        doc = await _lazy_close(doc)
        if doc.get("status") != "open":
            raise HTTPException(409, "Decizia este închisă.")
        if not await _role_in_scope(doc["scope"], doc["scope_id"], uid):
            raise HTTPException(403, "Doar membrii activi pot vota.")
        if not (0 <= body.option_index < len(doc["options"])):
            raise HTTPException(400, "Opțiune inexistentă.")
        votes = doc.get("votes") or []
        if any(v.get("user_id") == uid for v in votes):
            raise HTTPException(409, "Ai votat deja.")
        rev = doc.get("rev", 0)
        res = await db.radacini_decisions.update_one(
            {"_id": oid, "rev": rev, "status": "open"},
            {"$set": {"votes": [*votes, {"user_id": uid, "option_index": body.option_index, "at": now_iso()}], "rev": rev + 1}},
        )
        if res.modified_count == 1:
            fresh = await db.radacini_decisions.find_one({"_id": oid}) or doc
            await emit("radacini.decision_voted", actor=user, payload={"decision_id": decision_id})
            return {"decision": _view(fresh, uid)}
    raise HTTPException(409, "Votul nu a putut fi înregistrat din cauza altor voturi simultane. Încearcă din nou.")


@router.post("/decisions/{decision_id}/close")
async def close_decision(decision_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await db.radacini_decisions.find_one({"_id": oid_or_404(decision_id)})
    if not doc:
        raise HTTPException(404, "Decizia nu există.")
    if doc.get("created_by") != uid:
        raise HTTPException(403, "Doar creatorul poate închide decizia.")
    res = await db.radacini_decisions.update_one(
        {"_id": doc["_id"], "status": "open"}, {"$set": {"status": "closed", "closed_at": now_iso()}})
    if res.modified_count != 1:
        raise HTTPException(409, "Decizia este deja închisă.")
    fresh = await db.radacini_decisions.find_one({"_id": doc["_id"]}) or doc
    await emit("radacini.decision_closed", actor=user, payload={"decision_id": decision_id})
    return {"decision": _view(fresh, uid)}
