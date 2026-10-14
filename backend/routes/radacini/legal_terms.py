"""Termeni Rădăcini (S8): documente, acceptări și dependența `require_terms`.

Colecții proprii (separate de poarta legală PropManage): `radacini_legal_documents` și `radacini_legal_acceptances`.
Rute: `GET /legal/documents` (public) · `GET /legal/me` · `POST /legal/accept`. Admin: `GET /admin/legal/acceptances` (admin.py).
"""
import asyncio
import ipaddress
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .bridge import block_in_impersonation, db, get_current_user
from .common import RadaciniRoute, now_iso
from .legal_texts import PRIVACY_BODY, PRIVACY_SUMMARY, PRIVACY_TITLE, TERMS_BODY, TERMS_SUMMARY, TERMS_TITLE, VERSION

router = APIRouter(route_class=RadaciniRoute)

TYPES = ("terms", "privacy")
CACHE_TTL = 60.0
_UA_MAX = 300
_SEEDS = {
    "terms": (TERMS_TITLE, TERMS_SUMMARY, TERMS_BODY),
    "privacy": (PRIVACY_TITLE, PRIVACY_SUMMARY, PRIVACY_BODY),
}
_cache: dict = {"at": 0.0, "docs": None}
_seed_lock = asyncio.Lock()
_seeded = False


async def ensure_seed() -> None:
    """Idempotent: inserează documentele pilot lipsă (o singură dată per proces, apoi verificare doar la nevoie)."""
    global _seeded
    if _seeded:
        return
    async with _seed_lock:
        if _seeded:
            return
        for typ, (title, summary, body) in _SEEDS.items():
            if not await db.radacini_legal_documents.find_one({"type": typ, "version": VERSION}, {"_id": 1}):
                await db.radacini_legal_documents.insert_one({
                    "type": typ, "version": VERSION, "title": title, "summary": summary, "body": body,
                    "active": True, "created_at": now_iso(),
                })
        _seeded = True


async def current_documents() -> dict:
    """{type: document} pentru cea mai recentă versiune activă din fiecare tip (cache 60 s)."""
    now = time.monotonic()
    if _cache["docs"] is not None and now - _cache["at"] < CACHE_TTL:
        return _cache["docs"]
    await ensure_seed()
    docs = await db.radacini_legal_documents.find({"active": True}).limit(200).to_list(200)
    best: dict = {}
    for d in docs:
        t = d.get("type")
        if t in TYPES and (t not in best or str(d.get("version", "")) > str(best[t].get("version", ""))):
            best[t] = d
    _cache["docs"], _cache["at"] = best, now
    return best


async def required_versions() -> list:
    docs = await current_documents()
    return [{"type": t, "version": docs[t]["version"]} for t in TYPES if t in docs]


async def _accepted_set(uid: str) -> set:
    rows = await db.radacini_legal_acceptances.find({"user_id": uid}, {"type": 1, "version": 1, "revoked_at": 1}).limit(100).to_list(100)
    return {(r.get("type"), r.get("version")) for r in rows if not r.get("revoked_at")}


async def require_terms(user: dict = Depends(get_current_user)) -> dict:
    """Dependență pentru rutele de acțiune: ambele documente curente trebuie acceptate (altfel 428, `detail.code`)."""
    required = await required_versions()
    accepted = await _accepted_set(str(user["id"]))
    if not required or any((r["type"], r["version"]) not in accepted for r in required):
        raise HTTPException(428, {"code": "terms_required", "message": "Acceptă termenii Rădăcini pentru a continua."})
    return user


def _client_ip(request: Request) -> str:
    first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if first:
        try:
            return str(ipaddress.ip_address(first))
        except ValueError:
            pass
    return (request.client.host if request.client else "")[:64]


def _doc_out(d: dict) -> dict:
    return {k: d.get(k) for k in ("type", "version", "title", "summary", "body", "created_at")}


@router.get("/legal/documents")
async def list_documents():
    docs = await current_documents()
    return {"items": [_doc_out(docs[t]) for t in TYPES if t in docs]}


async def _status(uid: str) -> dict:
    required = await required_versions()
    accepted = await _accepted_set(uid)
    mine = [r for r in required if (r["type"], r["version"]) in accepted]
    return {"required": required, "accepted": mine, "ok": bool(required) and len(mine) == len(required)}


@router.get("/legal/me")
async def my_status(user: dict = Depends(get_current_user)):
    return await _status(str(user["id"]))


class AcceptIn(BaseModel):
    type: Literal["terms", "privacy"]
    version: str


@router.post("/legal/accept")
async def accept(body: AcceptIn, request: Request, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "acceptarea termenilor")
    uid = str(user["id"])
    docs = await current_documents()
    if body.type not in docs or docs[body.type]["version"] != body.version:
        raise HTTPException(409, "Versiunea nu mai este cea curentă. Reîncarcă pagina.")
    rows = await db.radacini_legal_acceptances.find({"user_id": uid, "type": body.type}).limit(100).to_list(100)
    if not any(r.get("version") == body.version and not r.get("revoked_at") for r in rows):
        now = now_iso()
        for r in rows:  # acceptările versiunilor mai vechi se marchează ca revocate
            if r.get("version") != body.version and not r.get("revoked_at"):
                await db.radacini_legal_acceptances.update_one({"_id": r["_id"]}, {"$set": {"revoked_at": now}})
        await db.radacini_legal_acceptances.insert_one({
            "user_id": uid, "type": body.type, "version": body.version, "accepted_at": now,
            "ip": _client_ip(request), "user_agent": (request.headers.get("user-agent") or "")[:_UA_MAX],
        })
    return await _status(uid)
