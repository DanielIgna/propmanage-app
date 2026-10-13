"""Helpere comune Rădăcini: timp, marcaj demo, ID-uri, utilizatori, erori de validare."""
import asyncio
import logging
import math
import os
from datetime import date, datetime, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from .bridge import db, get_current_user, notify

log = logging.getLogger(__name__)


BUCHAREST = ZoneInfo("Europe/Bucharest")
MAX_PRICE_RON = 10_000_000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_bucharest() -> date:
    """Data de azi în Europe/Bucharest (frontend-ul calculează datele locale, nu UTC)."""
    return datetime.now(BUCHAREST).date()


def check_price(v: Optional[float]) -> Optional[float]:
    """Preț RON/an: număr finit, 0 ≤ preț ≤ 10 000 000 (ValueError cu mesaj în română)."""
    if v is None:
        return None
    if not math.isfinite(v):
        raise ValueError("Prețul trebuie să fie un număr valid.")
    if v < 0:
        raise ValueError("Prețul nu poate fi negativ.")
    if v > MAX_PRICE_RON:
        raise ValueError("Prețul nu poate depăși 10 000 000 RON.")
    return v


def check_finite(v: Optional[float], message: str = "Valoarea trebuie să fie un număr valid.") -> Optional[float]:
    if v is not None and not math.isfinite(v):
        raise ValueError(message)
    return v


def mark_demo(doc: dict) -> dict:
    """Marchează documentul ca demo când RADACINI_MARK_DEMO=true (doar local)."""
    if os.environ.get("RADACINI_MARK_DEMO", "").lower() == "true":
        doc["is_demo"] = True
    return doc


def oid_or_404(id_: str) -> ObjectId:
    if not (isinstance(id_, str) and len(id_) == 24 and ObjectId.is_valid(id_)):
        raise HTTPException(404, "Nu există.")
    return ObjectId(id_)


_TITLE_MAX, _MESSAGE_MAX = 120, 500
_BG_TASKS: set = set()  # referințe tari: asyncio ține doar referințe slabe la task-uri


def _neutralize(text, limit: int, *, single_line: bool = False) -> str:
    """Text de utilizator → inofensiv în emailul HTML al `notify` (care nu face escape): fără < >, fără
    caractere de control, lungime limitată."""
    out = str(text if text is not None else "").replace("<", "‹").replace(">", "›")
    out = "".join(ch for ch in out if ch in "\n\t" or ord(ch) >= 32)
    if single_line:
        out = " ".join(out.split())
    return out[:limit]


def _safe_link(link: Optional[str]) -> Optional[str]:
    """Doar căi interne (generate de noi); orice altceva nu intră în atributul href."""
    if isinstance(link, str) and link.startswith("/") and not link.startswith("//") \
            and not any(c in link for c in ' "\'<>'):
        return link
    return None


async def _deliver_notification(user_id: str, title: str, message: str, link: Optional[str], type_: str) -> None:
    try:
        await notify(user_id, title, message, type_=type_, link=link)
    except Exception:  # noqa: BLE001
        log.warning("radacini: notificarea nu a putut fi trimisă", exc_info=True)


async def safe_notify(user_id: str, title: str, message: str, link: Optional[str] = None, type_: str = "info") -> None:
    """Notificare care nu blochează niciodată acțiunea principală: textul e neutralizat (emailul e HTML),
    iar trimiterea (inserare în aplicație + email SendGrid + push) rulează în fundal."""
    task = asyncio.create_task(_deliver_notification(
        str(user_id),
        _neutralize(title, _TITLE_MAX, single_line=True),
        _neutralize(message, _MESSAGE_MAX),
        _safe_link(link),
        type_,
    ))
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)


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
