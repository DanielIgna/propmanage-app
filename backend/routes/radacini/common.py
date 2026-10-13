"""Helpere comune Rădăcini: timp, marcaj demo, ID-uri, utilizatori, erori de validare."""
import os
from datetime import datetime, timezone
from typing import Iterable, Optional

from bson import ObjectId
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from .bridge import db, get_current_user


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mark_demo(doc: dict) -> dict:
    """Marchează documentul ca demo când RADACINI_MARK_DEMO=true (doar local)."""
    if os.environ.get("RADACINI_MARK_DEMO", "").lower() == "true":
        doc["is_demo"] = True
    return doc


def oid_or_404(id_: str) -> ObjectId:
    if not (isinstance(id_, str) and len(id_) == 24 and ObjectId.is_valid(id_)):
        raise HTTPException(404, "Nu există.")
    return ObjectId(id_)


async def get_optional_user(request: Request) -> Optional[dict]:
    """Utilizatorul curent dacă e autentificat, altfel None (fără 401)."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def load_owners(user_ids: Iterable[str]) -> dict:
    """Încarcă numele și emailul proprietarilor într-o singură interogare."""
    oids = {ObjectId(u) for u in user_ids if isinstance(u, str) and len(u) == 24 and ObjectId.is_valid(u)}
    if not oids:
        return {}
    users = await db.users.find({"_id": {"$in": list(oids)}}, {"name": 1, "email": 1}).to_list(len(oids))
    return {
        str(u["_id"]): {"name": u.get("name") or "", "email": u.get("email") or ""}
        for u in users
    }


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Date invalide."
    err = errors[0]
    msg = str(err.get("msg", ""))
    if msg.startswith("Value error, "):
        return msg[len("Value error, "):]
    field = next((str(p) for p in reversed(err.get("loc", ())) if p not in ("body", "query", "path")), "")
    if err.get("type") == "missing":
        return f"Câmp obligatoriu: {field}."
    return f"Date invalide: {field}."


class RadaciniRoute(APIRoute):
    """Erorile de validare (body/query) întorc 400 cu mesaj în română, nu 422."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validated_handler(request: Request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                raise HTTPException(400, _validation_message(exc)) from None

        return validated_handler
