"""Passport Analytics — EO-026: fiecare pașaport partajat devine măsurabil.

Evenimente first-party, GDPR-safe: view / leave (timp pe pagină) / share / cta_click /
register (conversie) / og_fetch (bot social). IP-ul NU se stochează — doar hash trunchiat
+ țara (best-effort, cache per IP).
"""
import asyncio
import hashlib
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from routes.property_dna import _load_property_for
from routes.property_passport import BOT_UA

logger = logging.getLogger("propmanage.passport_analytics")
router = APIRouter(prefix="/api", tags=["passport_analytics"])

VALID_EVENTS = {"view", "leave", "share", "cta_click"}
KNOWN_SRC = {"qr", "wa", "link", "share", "facebook", "direct", "other"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ua(ua: str) -> dict:
    u = (ua or "").lower()
    if "ipad" in u or "tablet" in u:
        device = "tablet"
    elif "mobi" in u or "android" in u or "iphone" in u:
        device = "mobile"
    else:
        device = "desktop"
    if "edg/" in u:
        browser = "Edge"
    elif "samsungbrowser" in u:
        browser = "Samsung"
    elif "opr/" in u or "opera" in u:
        browser = "Opera"
    elif "firefox" in u or "fxios" in u:
        browser = "Firefox"
    elif "chrome" in u or "crios" in u:
        browser = "Chrome"
    elif "safari" in u:
        browser = "Safari"
    else:
        browser = "Alt"
    if "android" in u:
        os_name = "Android"
    elif "iphone" in u or "ipad" in u:
        os_name = "iOS"
    elif "windows" in u:
        os_name = "Windows"
    elif "mac os" in u or "macintosh" in u:
        os_name = "macOS"
    elif "linux" in u:
        os_name = "Linux"
    else:
        os_name = "Alt"
    return {"device": device, "browser": browser, "os": os_name}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def _country_from_headers(request: Request):
    for h in ("cf-ipcountry", "x-vercel-ip-country", "x-country-code"):
        v = request.headers.get(h)
        if v and len(v) == 2 and v.isalpha():
            return v.upper()
    return None


def _classify_src(src: str, referrer: str) -> str:
    s = (src or "").lower()
    if s in KNOWN_SRC:
        return s
    r = (referrer or "").lower()
    if "wa.me" in r or "whatsapp" in r:
        return "wa"
    if "facebook" in r or "fb.com" in r or "instagram" in r:
        return "facebook"
    if not r:
        return "direct"
    return "other"


async def _resolve_country_bg(event_id: str, ip: str):
    """Best-effort GeoIP (ip-api.com, cache per hash IP). Nu blochează requestul."""
    key = hashlib.sha256(ip.encode()).hexdigest()[:24]
    try:
        cached = await db.geo_ip_cache.find_one({"_id": key})
        country = (cached or {}).get("country")
        if not country:
            import httpx
            async with httpx.AsyncClient(timeout=2.5) as c:
                r = await c.get(f"http://ip-api.com/json/{ip}?fields=status,countryCode")
                j = r.json()
                country = j.get("countryCode") if j.get("status") == "success" else None
            if country:
                await db.geo_ip_cache.update_one(
                    {"_id": key}, {"$set": {"country": country, "cached_at": _now()}}, upsert=True)
        if country:
            await db.passport_events.update_one({"event_id": event_id}, {"$set": {"country": country}})
    except Exception:
        pass


class PassportTrackIn(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=64)
    event: str
    src: str = ""
    referrer: str = ""
    duration_s: int = 0
    screen_w: int = 0


@router.post("/public/passport/{slug}/track")
async def track_passport_event(slug: str, body: PassportTrackIn, request: Request):
    if body.event not in VALID_EVENTS:
        raise HTTPException(400, "Eveniment necunoscut")
    prop = await db.properties.find_one({"passport.slug": slug, "passport.enabled": True}, {"_id": 1})
    if not prop:
        raise HTTPException(404, "Pașaportul nu există")
    ua = request.headers.get("user-agent", "")
    if BOT_UA.search(ua):
        return {"ok": True, "skipped": "bot"}
    ip = _client_ip(request)
    event_id = uuid.uuid4().hex
    doc = {
        "event_id": event_id,
        "slug": slug,
        "property_id": str(prop["_id"]),
        "type": body.event,
        "visitor_id": body.visitor_id,
        "src": _classify_src(body.src, body.referrer),
        "referrer": (body.referrer or "")[:300],
        "duration_s": max(0, min(body.duration_s, 3600)),
        "screen_w": max(0, min(body.screen_w, 10000)),
        **_parse_ua(ua),
        "country": _country_from_headers(request) or "??",
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else "",
        "day": _now()[:10],
        "ts": _now(),
    }
    await db.passport_events.insert_one(doc)
    if doc["country"] == "??" and ip and not ip.startswith(("10.", "192.168.", "172.", "127.")):
        asyncio.create_task(_resolve_country_bg(event_id, ip))
    return {"ok": True}


@router.post("/track/passport-conversion")
async def passport_conversion(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """După register: leagă contul nou de pașaportul care l-a adus (o singură dată, first-touch)."""
    slug = str(body.get("slug") or "")[:24]
    visitor_id = str(body.get("visitor_id") or "")[:64]
    if not slug:
        return {"ok": False}
    prop = await db.properties.find_one({"passport.slug": slug}, {"_id": 1})
    if not prop:
        return {"ok": False}
    udoc = await db.users.find_one({"email": user.get("email")}, {"acquisition": 1})
    if not udoc or udoc.get("acquisition"):
        return {"ok": True, "already": True}
    now = _now()
    await db.users.update_one(
        {"_id": udoc["_id"]},
        {"$set": {"acquisition": {"source": "passport", "slug": slug, "visitor_id": visitor_id, "ts": now}}})
    await db.passport_events.insert_one({
        "event_id": uuid.uuid4().hex, "slug": slug, "property_id": str(prop["_id"]),
        "type": "register", "visitor_id": visitor_id, "src": "conversion",
        "day": now[:10], "ts": now,
    })
    return {"ok": True, "attributed": True}


@router.get("/properties/{prop_id}/passport/analytics")
async def passport_owner_analytics(prop_id: str, days: int = 30, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    slug = (prop.get("passport") or {}).get("slug")
    if not slug:
        return {"has_data": False, "views": 0, "unique_visitors": 0, "qr_scans": 0, "shares": 0,
                "cta_clicks": 0, "registers": 0, "properties_created": 0, "avg_read_s": 0,
                "bounce_rate_pct": None, "sources": [], "devices": [], "countries": [], "browsers": [], "daily": []}
    days = max(1, min(days, 90))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = await db.passport_events.find(
        {"slug": slug, "ts": {"$gte": since}},
        {"_id": 0, "type": 1, "visitor_id": 1, "src": 1, "device": 1, "browser": 1,
         "country": 1, "duration_s": 1, "day": 1},
    ).to_list(50000)
    views = [r for r in rows if r["type"] == "view"]
    leaves = [r for r in rows if r["type"] == "leave"]
    uniq = {r.get("visitor_id") for r in views}
    durations = [r.get("duration_s", 0) for r in leaves if r.get("duration_s", 0) > 0]
    per_visitor_views = Counter(r.get("visitor_id") for r in views)
    per_visitor_max_dur = {}
    for r in leaves:
        v = r.get("visitor_id")
        per_visitor_max_dur[v] = max(per_visitor_max_dur.get(v, 0), r.get("duration_s", 0))
    bounced = [v for v in uniq if per_visitor_views.get(v, 0) <= 1 and per_visitor_max_dur.get(v, 0) < 10]
    reg_users = await db.users.find({"acquisition.slug": slug}, {"_id": 1}).to_list(1000)
    owner_ids = [str(u["_id"]) for u in reg_users]
    props_created = await db.properties.count_documents({"owner_id": {"$in": owner_ids}}) if owner_ids else 0

    def top(field, n=6):
        c = Counter(r.get(field) or "??" for r in views)
        return [{"key": k, "count": v} for k, v in c.most_common(n)]

    daily_c = Counter(r.get("day") for r in views)
    day_list = [(datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat() for i in range(days - 1, -1, -1)]
    return {
        "has_data": bool(rows),
        "window_days": days,
        "views": len(views),
        "unique_visitors": len(uniq),
        "qr_scans": len([r for r in views if r.get("src") == "qr"]),
        "shares": len([r for r in rows if r["type"] == "share"]),
        "og_fetches": len([r for r in rows if r["type"] == "og_fetch"]),
        "cta_clicks": len([r for r in rows if r["type"] == "cta_click"]),
        "registers": len(reg_users),
        "properties_created": props_created,
        "avg_read_s": round(sum(durations) / len(durations)) if durations else 0,
        "bounce_rate_pct": round(len(bounced) * 100 / len(uniq)) if uniq else None,
        "sources": top("src"),
        "devices": top("device", 3),
        "countries": top("country"),
        "browsers": top("browser"),
        "daily": [{"day": d, "views": daily_c.get(d, 0)} for d in day_list] if days <= 31 else [],
    }
