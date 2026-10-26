"""Helpere comune Rădăcini: timp, marcaj demo, ID-uri, utilizatori, erori de validare."""
import asyncio
import logging
import math
import os
import time
from collections import deque
from datetime import date, datetime, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from .bridge import admin_audit, db, get_current_user
from .notifications import internal_path, radacini_notify

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
    """Text de utilizator → inofensiv în notificări: fără < >, fără caractere de control, lungime limitată
    (emailul e escape-uit oricum în `radacini_notify`; aici protejăm și afișarea din aplicație)."""
    out = str(text if text is not None else "").replace("<", "‹").replace(">", "›")
    out = "".join(ch for ch in out if ch in "\n\t" or ord(ch) >= 32)
    if single_line:
        out = " ".join(out.split())
    return out[:limit]


def _safe_link(link: Optional[str]) -> Optional[str]:
    """Doar căi interne (generate de noi); orice altceva nu intră în atributul href."""
    return internal_path(link)


async def _deliver_notification(user_id: str, title: str, message: str, link: Optional[str], type_: str) -> None:
    try:
        await radacini_notify(user_id, title, message, link, type_=type_)
    except Exception:  # noqa: BLE001
        log.warning("radacini: notificarea nu a putut fi trimisă", exc_info=True)


async def safe_notify(user_id: str, title: str, message: str, link: Optional[str] = None, type_: str = "info") -> None:
    """Notificare care nu blochează niciodată acțiunea principală: textul e neutralizat, iar trimiterea
    (inserare în aplicație + email „Rădăcini: …” + push) rulează în fundal, prin `radacini_notify`."""
    task = asyncio.create_task(_deliver_notification(
        str(user_id),
        _neutralize(title, _TITLE_MAX, single_line=True),
        _neutralize(message, _MESSAGE_MAX),
        _safe_link(link),
        type_,
    ))
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)


# ------------------------------------------------------------------------------------------ audit personal

async def audit_staff(user: dict, action: str, target_type: str, target_id, details: Optional[dict] = None) -> None:
    """Acțiune de personal/administrare în jurnalul de audit PropManage (`admin_console.audit`). Nu aruncă
    niciodată. În modul impersonare se păstrează și adminul real."""
    try:
        after = dict(details) if details else {}
        note = None
        imp = user.get("impersonation")
        if imp:
            after["impersonated_by"] = {k: imp.get(k) for k in ("admin_id", "admin_email", "log_id")}
            note = "acțiune în mod impersonare"
        name = action if action.startswith("radacini.") else f"radacini.{action}"
        await admin_audit(
            name,
            user,
            target={"type": target_type, "id": None if target_id is None else str(target_id)},
            after=after or None,
            note=note,
        )
    except Exception:  # noqa: BLE001
        log.warning("radacini: jurnalul de audit nu a putut fi scris (%s)", action, exc_info=True)


# ------------------------------------------------------------------------------------------ rate limit

class SlidingWindowLimiter:
    """Fereastră glisantă în memorie, per proces (aceeași idee ca `rate_limit.py` din PropManage, care e doar
    middleware pentru alte prefixe și nu poate fi refolosit pe rute). Memorie mărginită: peste `max_keys`
    chei se elimină cea mai veche."""

    def __init__(self, window: float = 60.0, max_keys: int = 20_000):
        self.window = window
        self.max_keys = max_keys
        self._hits: dict = {}
        self._last_gc = time.monotonic()

    def _gc(self, now: float) -> None:
        self._last_gc = now
        for key in [k for k, dq in self._hits.items() if not dq or now - dq[-1] > self.window]:
            self._hits.pop(key, None)

    def hit(self, key: str, limit: int) -> bool:
        """True dacă cererea e permisă (și o înregistrează); False dacă limita a fost depășită."""
        now = time.monotonic()
        if now - self._last_gc > 300:
            self._gc(now)
        dq = self._hits.get(key)
        if dq is None:
            if len(self._hits) >= self.max_keys:
                self._gc(now)
                if len(self._hits) >= self.max_keys:
                    self._hits.pop(next(iter(self._hits)), None)
            dq = self._hits[key] = deque()
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


_PUBLIC_RATE_LIMITER = SlidingWindowLimiter()
_PUBLIC_PATH = "/api/radacini/meta"
_PARCELS_PATH = "/api/radacini/parcels"


def client_ip(request: Request) -> str:
    """IP-ul clientului. În spatele proxy-ului (Railway) ultimul element din X-Forwarded-For e adăugat de proxy
    (cel din stânga poate fi falsificat de client); `RADACINI_RATE_LIMIT_PROXY_HOPS` (implicit 1) = câte proxy-uri
    de încredere adaugă un element; 0 = ignoră antetul."""
    direct = request.client.host if request.client else "?"
    hops = _env_int("RADACINI_RATE_LIMIT_PROXY_HOPS", 1)
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if hops > 0 and len(parts) >= hops and len(parts[-hops]) <= 64:
        return parts[-hops]
    return direct


async def public_rate_limit(request: Request) -> None:
    """Dependență la nivel de router: limitează GET /meta și GET /parcels* pe IP (429 + Retry-After).
    Cererile fără credențiale: `RADACINI_PUBLIC_RATE_LIMIT_PER_MIN` (60). Cele cu cookie/Authorization nu se
    validează aici (fără interogare în bază), dar au tot o limită, mai mare, ca un antet fals să nu ocolească
    protecția: `RADACINI_AUTH_RATE_LIMIT_PER_MIN` (600). Valoarea 0 dezactivează limita respectivă."""
    if request.method != "GET":
        return
    path = request.url.path.rstrip("/")
    if path != _PUBLIC_PATH and path != _PARCELS_PATH and not path.startswith(_PARCELS_PATH + "/"):
        return
    has_credentials = bool(request.cookies.get("access_token") or request.headers.get("authorization"))
    if has_credentials:
        kind, limit = "auth", _env_int("RADACINI_AUTH_RATE_LIMIT_PER_MIN", 600)
    else:
        kind, limit = "anon", _env_int("RADACINI_PUBLIC_RATE_LIMIT_PER_MIN", 60)
    if limit <= 0:
        return
    if not _PUBLIC_RATE_LIMITER.hit(f"{kind}:{client_ip(request)}", limit):
        raise HTTPException(429, "Prea multe cereri. Încearcă din nou într-un minut.", headers={"Retry-After": "60"})


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


ERROR_RETENTION_DAYS = 14
_last_error_gc = 0.0


async def record_error(method: str, route: str, exc: BaseException) -> None:
    """Eroare neprevăzută (500) în jurnalul `radacini_errors`, pentru pagina „Stare sistem”. Se salvează doar
    șablonul rutei (fără ID-uri sau date personale) și tipul erorii. Nu aruncă niciodată."""
    global _last_error_gc
    try:
        await db.radacini_errors.insert_one({
            "method": method, "route": route, "error_type": type(exc).__name__,
            "message": str(exc)[:300], "at": now_iso(),
        })
        now = time.monotonic()
        if now - _last_error_gc > 3600:
            _last_error_gc = now
            cutoff = datetime.fromtimestamp(time.time() - ERROR_RETENTION_DAYS * 86400, timezone.utc).isoformat()
            await db.radacini_errors.delete_many({"at": {"$lt": cutoff}})
    except Exception:  # noqa: BLE001
        log.warning("radacini: eroarea nu a putut fi salvată", exc_info=True)


class RadaciniRoute(APIRoute):
    """Erorile de validare (body/query) întorc 400 cu mesaj în română, nu 422. Erorile neprevăzute se salvează
    în `radacini_errors` (apoi merg mai departe, la handler-ul obișnuit de 500)."""

    def get_route_handler(self):
        handler = super().get_route_handler()
        route = self.path_format

        async def validated_handler(request: Request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                raise HTTPException(400, _validation_message(exc)) from None
            except StarletteHTTPException:
                raise
            except Exception as exc:  # noqa: BLE001
                await record_error(request.method, route, exc)
                raise

        return validated_handler
