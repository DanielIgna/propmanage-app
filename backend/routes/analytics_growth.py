"""PropManage Analytics & Growth — tracking propriu + campanii + dashboard KPI.

ARHITECTURĂ MODULARĂ (zona admin: BUSINESS → Statistici & KPI):
  • Tracker first-party: frontend/src/lib/analytics.js → POST /api/track (batch)
  • Integrări externe pluggable (Clarity / GA4 / Meta Pixel) prin analytics_settings
    — scripturile se injectează în frontend DOAR dacă ID-ul e configurat.
  • Link scurt per campanie: GET /api/go/{code} → redirect cu atribuire.

Colecții: analytics_events, analytics_sessions, growth_campaigns, analytics_settings
"""
import csv
import io
import logging
import os
import secrets
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, StreamingResponse, Response
from pydantic import BaseModel, Field

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.analytics_growth")

router = APIRouter(prefix="/api", tags=["analytics-growth"])
admin_router = APIRouter(prefix="/api/admin", tags=["analytics-growth-admin"])

APP_PUBLIC_URL = (os.environ.get("APP_PUBLIC_URL") or "").rstrip("/")

KNOWN_SOURCES = ["whatsapp", "facebook", "google", "direct", "qr", "admin", "other"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day(ts: Optional[str] = None) -> str:
    return (ts or _now())[:10]


def classify_source(referrer: str = "", utm_source: str = "", campaign_code: str = "", via_qr: bool = False) -> str:
    """Clasifică sursa de trafic — modular, ușor de extins."""
    u = (utm_source or "").lower()
    r = (referrer or "").lower()
    if via_qr or u == "qr":
        return "qr"
    if u:
        for s in ("whatsapp", "facebook", "google", "admin"):
            if s in u:
                return s
        return "other"
    if campaign_code:
        return "other"
    if "wa.me" in r or "whatsapp" in r:
        return "whatsapp"
    if "facebook" in r or "fb.com" in r or "instagram" in r:
        return "facebook"
    if "google" in r or "gclid" in r:
        return "google"
    if not r:
        return "direct"
    return "other"


# ═══════════════════════════ TRACKING (public) ═══════════════════════════

class TrackEvent(BaseModel):
    type: str  # pageview | heartbeat | click | funnel | intent | conversion
    path: str = ""
    referrer: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    campaign_code: str = ""
    via_qr: bool = False
    gclid: str = ""                # Google Ads click id (atribuire Google Ads)
    gbraid: str = ""               # Google Ads (app/iOS)
    wbraid: str = ""               # Google Ads (web→app)
    duration_ms: int = 0          # heartbeat: timp acumulat pe pagină
    x_pct: Optional[float] = None  # click: coordonate % (pt heatmap Faza 2)
    y_pct: Optional[float] = None
    funnel_step: str = ""          # signup_started | account_created | property_added | subscription | specialist_request
    intent_signal: str = ""        # GI-2: twin_viewed | audit_viewed | request_started | request_abandoned | offer_requested | whatsapp_opened | ...
    conversion_action: str = ""    # sign_up | first_request | purchase | offer_accepted
    conversion_value: float = 0.0  # valoare RON (ex: sumă escrow pt purchase)
    conversion_currency: str = "RON"
    ab_key: str = ""               # A/B testing: cheia experimentului
    ab_variant: str = ""           # A | B
    ts: str = ""


class TrackBatch(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=64)
    session_id: str = Field(min_length=8, max_length=64)
    user_id: str = ""              # GI-2: identify vizitator↔utilizator
    user_role: str = ""
    events: List[TrackEvent] = Field(max_length=50)


@router.post("/track")
async def ingest_events(batch: TrackBatch, request: Request):
    """Ingestie batch de evenimente de la trackerul first-party. Fără auth (public)."""
    settings = await _get_settings()
    if not settings.get("tracker_enabled", True):
        return {"ok": True, "ingested": 0}
    now = _now()
    docs = []
    sess_updates = {"last_seen_at": now}
    inc = defaultdict(int)
    for ev in batch.events[:50]:
        path = (ev.path or "")[:300]
        if path.startswith("/admin"):
            continue  # nu poluăm statisticile cu trafic admin
        source = classify_source(ev.referrer, ev.utm_source, ev.campaign_code, ev.via_qr)
        docs.append({
            "event_id": str(uuid.uuid4()),
            "type": ev.type[:20],
            "path": path,
            "referrer": (ev.referrer or "")[:300],
            "source": source,
            "utm_source": (ev.utm_source or "")[:100],
            "utm_medium": (ev.utm_medium or "")[:100],
            "utm_campaign": (ev.utm_campaign or "")[:100],
            "campaign_code": (ev.campaign_code or "")[:40],
            "duration_ms": max(0, min(ev.duration_ms, 3_600_000)),
            "x_pct": ev.x_pct, "y_pct": ev.y_pct,
            "funnel_step": (ev.funnel_step or "")[:40],
            "intent_signal": (ev.intent_signal or "")[:40],
            "ab_key": (ev.ab_key or "")[:40],
            "ab_variant": (ev.ab_variant or "")[:2],
            "visitor_id": batch.visitor_id,
            "session_id": batch.session_id,
            "day": _day(now),
            "ts": ev.ts or now,
        })
        if ev.type == "pageview":
            inc["pageviews"] += 1
        elif ev.type == "heartbeat":
            inc["duration_ms"] += max(0, min(ev.duration_ms, 300_000))
        if ev.campaign_code:
            sess_updates["campaign_code"] = ev.campaign_code[:40]
        if ev.utm_source:
            sess_updates["utm_source"] = ev.utm_source[:100]
        if ev.utm_medium:
            sess_updates["utm_medium"] = ev.utm_medium[:100]
        if ev.utm_campaign:
            sess_updates["utm_campaign"] = ev.utm_campaign[:100]
        if source != "direct" or "source" not in sess_updates:
            sess_updates.setdefault("source", source)
        if ev.type == "funnel" and ev.funnel_step:
            sess_updates[f"funnel_{ev.funnel_step[:30]}"] = True
        if ev.type == "intent" and ev.intent_signal:
            sess_updates[f"intent_{ev.intent_signal[:30]}"] = True
        if ev.type == "ab" and ev.ab_key and ev.ab_variant in ("A", "B"):
            sess_updates[f"ab_{ev.ab_key[:30]}"] = ev.ab_variant

        # ── Google Ads attribution (first-touch per visitor) ────────────────
        gclid = (ev.gclid or "")[:200]
        if gclid or ev.utm_source or ev.campaign_code:
            await db.marketing_attributions.update_one(
                {"visitor_id": batch.visitor_id},
                {"$setOnInsert": {
                    "visitor_id": batch.visitor_id,
                    "gclid": gclid, "gbraid": (ev.gbraid or "")[:200], "wbraid": (ev.wbraid or "")[:200],
                    "utm_source": (ev.utm_source or "")[:100], "utm_medium": (ev.utm_medium or "")[:100],
                    "utm_campaign": (ev.utm_campaign or "")[:100], "campaign_code": (ev.campaign_code or "")[:40],
                    "landing_path": path or "/", "source": source, "first_seen_at": now, "day": _day(now),
                }},
                upsert=True,
            )
        # ── Conversion event (client-behavior → Google Ads + intern) ─────────
        if ev.type == "conversion" and ev.conversion_action:
            attr = await db.marketing_attributions.find_one({"visitor_id": batch.visitor_id}, {"_id": 0})
            await db.marketing_conversions.insert_one({
                "conversion_id": str(uuid.uuid4()),
                "action": ev.conversion_action[:40],
                "value": max(0.0, min(float(ev.conversion_value or 0), 10_000_000)),
                "currency": (ev.conversion_currency or "RON")[:8],
                "visitor_id": batch.visitor_id,
                "user_id": (batch.user_id or "")[:40],
                "gclid": (attr or {}).get("gclid", "") or gclid,
                "utm_source": (attr or {}).get("utm_source", "") or (ev.utm_source or ""),
                "utm_campaign": (attr or {}).get("utm_campaign", "") or (ev.utm_campaign or ""),
                "source": (attr or {}).get("source") or source,
                "ad_attributed": bool((attr or {}).get("gclid") or gclid),
                "ts": ev.ts or now, "day": _day(now),
            })
            sess_updates[f"conversion_{ev.conversion_action[:30]}"] = True
    if batch.user_id:
        sess_updates["user_id"] = batch.user_id[:40]
        if batch.user_role:
            sess_updates["user_role"] = batch.user_role[:20]
        await db.visitor_identities.update_one(
            {"visitor_id": batch.visitor_id},
            {"$set": {"user_id": batch.user_id[:40], "role": (batch.user_role or "")[:20], "last_seen_at": now},
             "$setOnInsert": {"first_seen_at": now}},
            upsert=True,
        )
        # leagă atribuirea (first-touch) de utilizator, dacă vizitatorul are una
        await db.marketing_attributions.update_one(
            {"visitor_id": batch.visitor_id, "user_id": {"$exists": False}},
            {"$set": {"user_id": batch.user_id[:40]}},
        )
    if docs:
        await db.analytics_events.insert_many(docs)
    await db.analytics_sessions.update_one(
        {"session_id": batch.session_id},
        {
            "$set": sess_updates,
            "$setOnInsert": {
                "visitor_id": batch.visitor_id,
                "started_at": now,
                "day": _day(now),
                "entry_path": docs[0]["path"] if docs else "/",
            },
            "$inc": dict(inc) if inc else {"pageviews": 0},
        },
        upsert=True,
    )
    return {"ok": True, "ingested": len(docs)}


@router.get("/track/config")
async def tracker_config():
    """Config public pentru tracker + integrări externe (Clarity/GA4/Meta) + widget WhatsApp."""
    s = await _get_settings()
    return {
        "enabled": s.get("tracker_enabled", True),
        "clarity_id": s.get("clarity_id") or "",
        "ga4_id": s.get("ga4_id") or "",
        "meta_pixel_id": s.get("meta_pixel_id") or "",
        "whatsapp_enabled": s.get("whatsapp_enabled", True),
        "whatsapp_phone": s.get("whatsapp_phone") or "",
        "whatsapp_message": s.get("whatsapp_message") or "",
    }


@router.get("/go/{code}")
async def campaign_short_link(code: str, qr: int = 0):
    """Link scurt personalizat per campanie → redirect cu atribuire UTM."""
    camp = await db.growth_campaigns.find_one({"code": code})
    if not camp:
        return RedirectResponse(url="/", status_code=302)
    field = "qr_opens" if qr else "link_opens"
    await db.growth_campaigns.update_one({"code": code}, {"$inc": {field: 1, "opens": 1}})
    src = "qr" if qr else (camp.get("channel") or "other")
    target = f"/?c={code}&utm_source={src}&utm_campaign={code}" + ("&via_qr=1" if qr else "")
    return RedirectResponse(url=target, status_code=302)


# ═══════════════════════ SETTINGS / INTEGRĂRI (admin) ═══════════════════════

async def _get_settings() -> dict:
    defaults = {
        "tracker_enabled": True, "clarity_id": "", "ga4_id": "", "meta_pixel_id": "",
        "whatsapp_enabled": True,
        "whatsapp_phone": "+40790541342",
        "whatsapp_message": "Bună! Doresc informații despre PropManage.",
    }
    s = await db.analytics_settings.find_one({"_id": "integrations"})
    if not s:
        s = {"_id": "integrations", **defaults}
        await db.analytics_settings.insert_one(s)
    # chei canonice garantate chiar dacă documentul e parțial (seed vechi)
    return {**defaults, **s}


class IntegrationsUpdate(BaseModel):
    tracker_enabled: Optional[bool] = None
    clarity_id: Optional[str] = None
    ga4_id: Optional[str] = None
    meta_pixel_id: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_phone: Optional[str] = None
    whatsapp_message: Optional[str] = None


@admin_router.get("/analytics/integrations")
async def get_integrations(user: dict = Depends(require_role("admin"))):
    s = await _get_settings()
    s.pop("_id", None)
    return s


@admin_router.put("/analytics/integrations")
async def update_integrations(body: IntegrationsUpdate, user: dict = Depends(require_role("admin"))):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    updates["updated_at"] = _now()
    updates["updated_by"] = user.get("email")
    await db.analytics_settings.update_one({"_id": "integrations"}, {"$set": updates}, upsert=True)
    logger.info("Analytics integrations updated by %s: %s", user.get("email"), list(updates))
    s = await _get_settings()
    s.pop("_id", None)
    return s


# ═══════════════════════ MARKETING ATTRIBUTION (admin) ═══════════════════════
@admin_router.get("/attribution/summary")
async def attribution_summary(days: int = 30, user: dict = Depends(require_role("admin"))):
    """Atribuire Google Ads → conversii reale (sign_up/first_request/offer_accepted/purchase).
    Leagă comportamentul clientului măsurat de sursa de trafic Google Ads."""
    from routes.attribution import compute_attribution_summary
    return await compute_attribution_summary(days)



# ═══════════════════════ CAMPANII GROWTH (admin) ═══════════════════════

class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    administrator: str = ""
    association: str = ""
    apartments_count: int = 0
    channel: str = "whatsapp"      # canal de distribuție (whatsapp/facebook/google/qr/admin/other)
    recipients_count: int = 0      # câte persoane au primit mesajul
    sent_at: str = ""
    notes: str = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    administrator: Optional[str] = None
    association: Optional[str] = None
    apartments_count: Optional[int] = None
    channel: Optional[str] = None
    recipients_count: Optional[int] = None
    sent_at: Optional[str] = None
    notes: Optional[str] = None
    revenue_manual: Optional[float] = None
    status: Optional[str] = None


def _campaign_public(c: dict) -> dict:
    c.pop("_id", None)
    return c


@admin_router.post("/growth/campaigns")
async def create_campaign(body: CampaignCreate, user: dict = Depends(require_role("admin"))):
    code = secrets.token_urlsafe(4).replace("_", "x").replace("-", "z").lower()[:6]
    doc = {
        "id": str(uuid.uuid4()),
        "code": code,
        "url": f"{APP_PUBLIC_URL}/api/go/{code}",
        "qr_url": f"{APP_PUBLIC_URL}/api/go/{code}?qr=1",
        **body.model_dump(),
        "status": "active",
        "opens": 0, "link_opens": 0, "qr_opens": 0,
        "revenue_manual": 0.0,
        "created_by": user.get("email"),
        "created_at": _now(),
    }
    if not doc["sent_at"]:
        doc["sent_at"] = _now()
    await db.growth_campaigns.insert_one(doc)
    return _campaign_public(doc)


@admin_router.get("/growth/campaigns")
async def list_campaigns(user: dict = Depends(require_role("admin"))):
    docs = await db.growth_campaigns.find({}).sort("created_at", -1).to_list(200)
    items = []
    for c in docs:
        stats = await _campaign_stats(c)
        items.append({**_campaign_public(c), **stats})
    return {"items": items, "count": len(items)}


@admin_router.patch("/growth/campaigns/{cid}")
async def update_campaign(cid: str, body: CampaignUpdate, user: dict = Depends(require_role("admin"))):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    res = await db.growth_campaigns.update_one({"id": cid}, {"$set": updates})
    if not res.matched_count:
        raise HTTPException(404, "Campanie inexistentă")
    c = await db.growth_campaigns.find_one({"id": cid})
    return _campaign_public(c)


@admin_router.delete("/growth/campaigns/{cid}")
async def delete_campaign(cid: str, user: dict = Depends(require_role("admin"))):
    res = await db.growth_campaigns.delete_one({"id": cid})
    if not res.deleted_count:
        raise HTTPException(404, "Campanie inexistentă")
    return {"ok": True}


async def _campaign_stats(camp: dict) -> dict:
    """Indicatorii de startup per campanie:
    primit → deschis link → 30s+ pe site → început înregistrare → cont finalizat → revenit în 7 zile."""
    code = camp.get("code")
    sessions = await db.analytics_sessions.find({"campaign_code": code}).to_list(5000)
    visitors = {}
    for s in sessions:
        v = visitors.setdefault(s["visitor_id"], {"days": set(), "dur": 0, "signup_started": False, "account_created": False, "subscription": False})
        v["days"].add(s.get("day"))
        v["dur"] = max(v["dur"], s.get("duration_ms", 0))
        for f in ("signup_started", "account_created", "subscription", "specialist_request", "property_added"):
            if s.get(f"funnel_{f}"):
                v[f] = True
    recipients = camp.get("recipients_count", 0)
    opened = camp.get("opens", 0)
    unique_visitors = len(visitors)
    over_30s = sum(1 for v in visitors.values() if v["dur"] >= 30_000)
    signup_started = sum(1 for v in visitors.values() if v.get("signup_started"))
    accounts = sum(1 for v in visitors.values() if v.get("account_created"))
    subscriptions = sum(1 for v in visitors.values() if v.get("subscription"))
    returned_7d = sum(1 for v in visitors.values() if len(v["days"]) >= 2)
    conversion = round(accounts / unique_visitors * 100, 1) if unique_visitors else 0.0
    return {
        "stats": {
            "recipients": recipients,
            "opened": opened,
            "unique_visitors": unique_visitors,
            "over_30s": over_30s,
            "signup_started": signup_started,
            "accounts_created": accounts,
            "subscriptions": subscriptions,
            "returned_7d": returned_7d,
            "conversion_pct": conversion,
            "revenue": camp.get("revenue_manual") or 0.0,
        }
    }


@admin_router.get("/growth/campaigns/{cid}/qr")
async def campaign_qr(cid: str, user: dict = Depends(require_role("admin"))):
    """QR personalizat (PNG) pentru linkul campaniei."""
    camp = await db.growth_campaigns.find_one({"id": cid})
    if not camp:
        raise HTTPException(404, "Campanie inexistentă")
    import qrcode
    img = qrcode.make(camp["qr_url"], box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="qr_{camp["code"]}.png"'})


# ═══════════════════════ DASHBOARD KPI (admin) ═══════════════════════

def _period_range(period: str, date_from: str = "", date_to: str = "") -> tuple:
    today = datetime.now(timezone.utc).date()
    if period == "day":
        start = today
    elif period == "week":
        start = today - timedelta(days=6)
    elif period == "month":
        start = today - timedelta(days=29)
    elif period == "60d":
        start = today - timedelta(days=59)
    elif period == "90d":
        start = today - timedelta(days=89)
    elif period == "6m":
        start = today - timedelta(days=181)
    elif period == "12m":
        start = today - timedelta(days=364)
    elif period == "ytd":
        start = today.replace(month=1, day=1)
    else:  # custom
        start = datetime.fromisoformat(date_from).date() if date_from else today - timedelta(days=29)
        today = datetime.fromisoformat(date_to).date() if date_to else today
    return start.isoformat(), today.isoformat()


# Pattern regex pentru toate endpoint-urile care acceptă `period`
_PERIOD_PATTERN = "^(day|week|month|60d|90d|6m|12m|ytd|custom)$"


def _auto_granularity(d_from: str, d_to: str) -> str:
    """Alege granularitatea optimă în funcție de lungimea intervalului."""
    days = (datetime.fromisoformat(d_to).date() - datetime.fromisoformat(d_from).date()).days + 1
    if days <= 60:
        return "day"
    if days <= 183:  # ~6 luni → agregat săptămânal
        return "week"
    return "month"


def _bucket_key(iso_day: str, granularity: str) -> str:
    """Cheia de bucket pentru un ISO day, în funcție de granularitate."""
    d = datetime.fromisoformat(iso_day).date()
    if granularity == "day":
        return d.isoformat()
    if granularity == "week":
        # ISO week Monday
        monday = d - timedelta(days=d.weekday())
        return monday.isoformat()
    # month
    return d.strftime("%Y-%m-01")


def _aggregate_series(series_daily: list, granularity: str) -> list:
    """Agregă seria zilnică la săptămână/lună. Păstrează keys `day`, `sessions`, `visitors`."""
    if granularity == "day":
        return series_daily
    buckets = defaultdict(lambda: {"sessions": 0, "visitors": 0})
    for row in series_daily:
        k = _bucket_key(row["day"], granularity)
        buckets[k]["sessions"] += row.get("sessions", 0)
        buckets[k]["visitors"] += row.get("visitors", 0)
    return [{"day": k, "sessions": v["sessions"], "visitors": v["visitors"]}
            for k, v in sorted(buckets.items())]


@admin_router.get("/analytics/overview")
async def analytics_overview(
    period: str = Query("week", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    granularity: str = Query("auto", pattern="^(auto|day|week|month)$"),
    user: dict = Depends(require_role("admin")),
):
    d_from, d_to = _period_range(period, date_from, date_to)
    q = {"day": {"$gte": d_from, "$lte": d_to}}

    sessions = await db.analytics_sessions.find(q).to_list(50000)
    visitors = {s["visitor_id"] for s in sessions}
    bounces = sum(1 for s in sessions if (s.get("pageviews") or 0) <= 1)
    total_dur = sum(s.get("duration_ms", 0) for s in sessions)

    # Surse trafic
    by_source = defaultdict(lambda: {"sessions": 0, "visitors": set()})
    daily = defaultdict(lambda: {"sessions": 0, "visitors": set()})
    for s in sessions:
        src = s.get("source") or "direct"
        by_source[src]["sessions"] += 1
        by_source[src]["visitors"].add(s["visitor_id"])
        daily[s.get("day")]["sessions"] += 1
        daily[s.get("day")]["visitors"].add(s["visitor_id"])

    # KPI din datele interne (creat în perioadă)
    iso_from, iso_to = d_from, d_to + "T23:59:59"
    accounts = await db.users.count_documents({"created_at": {"$gte": iso_from, "$lte": iso_to}})
    specialists = await db.users.count_documents({"role": "specialist", "created_at": {"$gte": iso_from, "$lte": iso_to}})
    properties = await db.properties.count_documents({"created_at": {"$gte": iso_from, "$lte": iso_to}})
    requests_n = await db.requests.count_documents({"created_at": {"$gte": iso_from, "$lte": iso_to}})
    subs = await db.hh_subscriptions.count_documents({"created_at": {"$gte": iso_from, "$lte": iso_to}})

    # Funnel (vizită → cont → proprietate → abonament → solicitare)
    funnel = [
        {"step": "Vizită", "count": len(visitors)},
        {"step": "Cont creat", "count": accounts},
        {"step": "Proprietate adăugată", "count": properties},
        {"step": "Abonament", "count": subs},
        {"step": "Solicitare specialist", "count": requests_n},
    ]

    # Serie zilnică completă (zile fără trafic = 0)
    series_daily = []
    cur = datetime.fromisoformat(d_from).date()
    end = datetime.fromisoformat(d_to).date()
    while cur <= end:
        k = cur.isoformat()
        series_daily.append({"day": k, "sessions": daily[k]["sessions"], "visitors": len(daily[k]["visitors"])})
        cur += timedelta(days=1)

    # Agregare adaptivă: zilnic ≤60z, săptămânal 90z-6L, lunar 12L
    effective_granularity = _auto_granularity(d_from, d_to) if granularity == "auto" else granularity
    series = _aggregate_series(series_daily, effective_granularity)

    # ── Comparație vs perioada anterioară (previous period, aceeași lungime) ──
    days_len = (datetime.fromisoformat(d_to).date() - datetime.fromisoformat(d_from).date()).days + 1
    p_to = (datetime.fromisoformat(d_from).date() - timedelta(days=1)).isoformat()
    p_from = (datetime.fromisoformat(d_from).date() - timedelta(days=days_len)).isoformat()
    prev_sessions = await db.analytics_sessions.find({"day": {"$gte": p_from, "$lte": p_to}}).to_list(50000)
    prev_visitors = {s["visitor_id"] for s in prev_sessions}
    prev_bounces = sum(1 for s in prev_sessions if (s.get("pageviews") or 0) <= 1)
    pf, pt = p_from, p_to + "T23:59:59"
    kpi_prev = {
        "unique_visitors": len(prev_visitors),
        "sessions": len(prev_sessions),
        "accounts_created": await db.users.count_documents({"created_at": {"$gte": pf, "$lte": pt}}),
        "specialists_signed": await db.users.count_documents({"role": "specialist", "created_at": {"$gte": pf, "$lte": pt}}),
        "properties_added": await db.properties.count_documents({"created_at": {"$gte": pf, "$lte": pt}}),
        "specialist_requests": await db.requests.count_documents({"created_at": {"$gte": pf, "$lte": pt}}),
        "subscriptions": await db.hh_subscriptions.count_documents({"created_at": {"$gte": pf, "$lte": pt}}),
        "bounce_rate_pct": round(prev_bounces / len(prev_sessions) * 100, 1) if prev_sessions else 0.0,
    }

    # ── Comparație Year-over-Year (aceeași perioadă din anul anterior) ──
    # Se calculează doar când perioada e ≥ 60 zile (relevant pentru trend anual).
    kpi_yoy = None
    if days_len >= 60:
        y_from = (datetime.fromisoformat(d_from).date() - timedelta(days=365)).isoformat()
        y_to = (datetime.fromisoformat(d_to).date() - timedelta(days=365)).isoformat()
        yoy_sessions = await db.analytics_sessions.find({"day": {"$gte": y_from, "$lte": y_to}}).to_list(50000)
        yoy_visitors = {s["visitor_id"] for s in yoy_sessions}
        yoy_bounces = sum(1 for s in yoy_sessions if (s.get("pageviews") or 0) <= 1)
        yf, yt = y_from, y_to + "T23:59:59"
        kpi_yoy = {
            "period": {"from": y_from, "to": y_to},
            "unique_visitors": len(yoy_visitors),
            "sessions": len(yoy_sessions),
            "accounts_created": await db.users.count_documents({"created_at": {"$gte": yf, "$lte": yt}}),
            "specialists_signed": await db.users.count_documents({"role": "specialist", "created_at": {"$gte": yf, "$lte": yt}}),
            "properties_added": await db.properties.count_documents({"created_at": {"$gte": yf, "$lte": yt}}),
            "specialist_requests": await db.requests.count_documents({"created_at": {"$gte": yf, "$lte": yt}}),
            "subscriptions": await db.hh_subscriptions.count_documents({"created_at": {"$gte": yf, "$lte": yt}}),
            "bounce_rate_pct": round(yoy_bounces / len(yoy_sessions) * 100, 1) if yoy_sessions else 0.0,
        }

    return {
        "period": {"from": d_from, "to": d_to, "days": days_len},
        "granularity": effective_granularity,
        "kpi": {
            "unique_visitors": len(visitors),
            "sessions": len(sessions),
            "accounts_created": accounts,
            "specialists_signed": specialists,
            "properties_added": properties,
            "specialist_requests": requests_n,
            "subscriptions": subs,
            "bounce_rate_pct": round(bounces / len(sessions) * 100, 1) if sessions else 0.0,
            "avg_session_sec": round(total_dur / len(sessions) / 1000) if sessions else 0,
        },
        "kpi_prev": kpi_prev,
        "kpi_yoy": kpi_yoy,
        "sources": [
            {"source": k, "sessions": v["sessions"], "visitors": len(v["visitors"])}
            for k, v in sorted(by_source.items(), key=lambda x: -x[1]["sessions"])
        ],
        "funnel": funnel,
        "series": series,
    }


@admin_router.get("/analytics/insights")
async def analytics_insights(
    period: str = Query("week", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """AI Insights standard (Design System): bullets + alerts + recomandări derivate din KPI."""
    data = await analytics_overview(period, date_from, date_to, "auto", user)
    k, kp = data["kpi"], data.get("kpi_prev", {})
    bullets, alerts, recs = [], [], []

    def pct(cur, prev):
        return round((cur - prev) / prev * 100) if prev else None

    if k["sessions"] == 0:
        bullets.append("Nu există trafic în perioada selectată — trackerul așteaptă primii vizitatori.")
        recs.append("Conectează integrările (Clarity, GA4) și distribuie primul link de campanie.")
    else:
        dv = pct(k["unique_visitors"], kp.get("unique_visitors", 0))
        if dv is not None and dv != 0:
            bullets.append(f"Vizitatorii unici au {'crescut' if dv > 0 else 'scăzut'} cu {abs(dv)}% față de perioada anterioară.")
        da = pct(k["accounts_created"], kp.get("accounts_created", 0))
        if da is not None and da != 0:
            bullets.append(f"Conturile create au {'crescut' if da > 0 else 'scăzut'} cu {abs(da)}%.")
        elif k["accounts_created"] == 0 and k["unique_visitors"] > 5:
            alerts.append("Trafic fără conversii: niciun cont creat în perioadă.")
            recs.append("Verifică fluxul de înregistrare și CTA-urile de pe paginile cu trafic mare.")
        if data["sources"]:
            top = data["sources"][0]
            bullets.append(f"Sursa «{top['source']}» produce cele mai multe vizite ({top['sessions']} sesiuni).")
        if k["bounce_rate_pct"] >= 55:
            alerts.append(f"Bounce rate ridicat ({k['bounce_rate_pct']}%) — vizitatorii pleacă după o singură pagină.")
            recs.append("Optimizează homepage-ul: mesaj mai clar în primele 3 secunde + un singur CTA dominant.")
        drops = []
        f = data["funnel"]
        for i in range(len(f) - 1):
            if f[i]["count"] > 0:
                drops.append((f[i]["count"] - f[i + 1]["count"], f[i]["step"], f[i + 1]["step"]))
        if drops:
            loss, a, b = max(drops)
            if loss > 0:
                recs.append(f"Cea mai mare pierdere din funnel: «{a}» → «{b}» (−{loss}). Concentrează optimizarea aici.")

    return {"bullets": bullets, "alerts": alerts, "recommendations": recs}


# ═══════════════════════ FUNNEL COMERCIAL (VISITOR→CLIENT→CERERE→SPECIALIST) ═══════════════════════
# Instrumentat prin trackerul first-party existent (trackIntent). Fiecare etapă = flag
# `intent_{signal}` pe sesiune. request_created e verificat ÎNCRUCIȘAT cu db.requests real,
# ca să nu ne bazăm doar pe semnalul client-side. ZERO sistem nou de analytics.
COMMERCIAL_FUNNEL_STAGES = [
    ("client_flow_opened", "Client pe /client"),
    ("client_property_selected", "Proprietate aleasă"),
    ("request_started", "Cerere începută"),
    ("request_created", "Cerere creată"),
    ("specialist_flow_opened", "Specialist deschide leads"),
    ("specialist_action_taken", "Specialist acceptă"),
    ("flow_completed", "Flux finalizat (confirmat)"),
]


@admin_router.get("/analytics/commercial-funnel")
async def analytics_commercial_funnel(
    period: str = Query("90d", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Funnel comercial real: din cei care intră pe /client, câți încep fluxul și câți
    creează o cerere reală → apoi specialistul o vede/acceptă → flux finalizat.
    Etapele vin din semnalele `intent_*` (trackIntent), agregate per vizitator unic.
    `request_created` e verificat încrucișat cu numărul real de cereri din db.requests."""
    d_from, d_to = _period_range(period, date_from, date_to)
    q = {"day": {"$gte": d_from, "$lte": d_to}}

    # Agregare per vizitator unic: o etapă e „atinsă" dacă apare pe oricare sesiune din perioadă
    stage_keys = [k for k, _ in COMMERCIAL_FUNNEL_STAGES]
    proj = {"visitor_id": 1, **{f"intent_{k}": 1 for k in stage_keys}}
    visitor_stages = defaultdict(set)
    async for s in db.analytics_sessions.find(q, proj):
        vid = s.get("visitor_id")
        if not vid:
            continue
        for k in stage_keys:
            if s.get(f"intent_{k}"):
                visitor_stages[vid].add(k)

    stage_counts = {k: 0 for k in stage_keys}
    for stages in visitor_stages.values():
        for k in stages:
            stage_counts[k] += 1

    stages = [{"key": k, "label": label, "count": stage_counts[k]} for k, label in COMMERCIAL_FUNNEL_STAGES]

    # Verificare încrucișată cu backend-ul real (SSOT = db.requests)
    iso_from, iso_to = d_from, d_to + "T23:59:59"
    requests_created_real = await db.requests.count_documents({"created_at": {"$gte": iso_from, "$lte": iso_to}})
    requests_confirmed_real = await db.requests.count_documents(
        {"status": "confirmed", "created_at": {"$gte": iso_from, "$lte": iso_to}}
    )
    signal_request_created = stage_counts["request_created"]

    def _pct(num, den):
        return round(num / den * 100, 1) if den else 0.0

    opened = stage_counts["client_flow_opened"]
    started = stage_counts["request_started"]
    created = stage_counts["request_created"]

    return {
        "period": {"from": d_from, "to": d_to},
        "stages": stages,
        "backend_check": {
            "requests_created_real": requests_created_real,
            "requests_confirmed_real": requests_confirmed_real,
            "signal_request_created": signal_request_created,
            "signal_flow_completed": stage_counts["flow_completed"],
            # diferența semnal vs realitate (vizitatori fără cont / tracker blocat / conturi seed)
            "created_delta": signal_request_created - requests_created_real,
        },
        "kpi": {
            "client_visitors": opened,
            "started": started,
            "created": created,
            # KPI-ul cheie al Fondatorului: din cei intrați pe /client → câți creează o cerere
            "opened_to_started_pct": _pct(started, opened),
            "opened_to_created_pct": _pct(created, opened),
            "started_to_created_pct": _pct(created, started),
        },
    }



@admin_router.get("/analytics/pages")
async def analytics_pages(
    period: str = Query("week", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Per pagină: vizualizări, timp mediu, bounce."""
    d_from, d_to = _period_range(period, date_from, date_to)
    q = {"day": {"$gte": d_from, "$lte": d_to}, "type": {"$in": ["pageview", "heartbeat"]}}
    pages = defaultdict(lambda: {"views": 0, "duration_ms": 0, "sessions": set()})
    async for e in db.analytics_events.find(q, {"path": 1, "type": 1, "duration_ms": 1, "session_id": 1}):
        p = pages[e.get("path") or "/"]
        if e["type"] == "pageview":
            p["views"] += 1
            p["sessions"].add(e["session_id"])
        else:
            p["duration_ms"] += e.get("duration_ms", 0)
    # bounce per pagină de intrare
    entry_counts = defaultdict(lambda: {"entries": 0, "bounces": 0})
    async for s in db.analytics_sessions.find({"day": {"$gte": d_from, "$lte": d_to}}, {"entry_path": 1, "pageviews": 1}):
        ep = s.get("entry_path") or "/"
        entry_counts[ep]["entries"] += 1
        if (s.get("pageviews") or 0) <= 1:
            entry_counts[ep]["bounces"] += 1
    items = []
    for path, p in sorted(pages.items(), key=lambda x: -x[1]["views"]):
        ec = entry_counts.get(path, {"entries": 0, "bounces": 0})
        items.append({
            "path": path,
            "views": p["views"],
            "avg_time_sec": round(p["duration_ms"] / max(1, p["views"]) / 1000),
            "bounce_rate_pct": round(ec["bounces"] / ec["entries"] * 100, 1) if ec["entries"] else 0.0,
        })
    return {"items": items[:100], "period": {"from": d_from, "to": d_to}}


@admin_router.get("/analytics/export.csv")
async def export_csv(
    report: str = Query("overview", pattern="^(overview|campaigns|pages)$"),
    period: str = "month", date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    buf = io.StringIO()
    w = csv.writer(buf)
    if report == "campaigns":
        docs = await db.growth_campaigns.find({}).sort("created_at", -1).to_list(500)
        w.writerow(["nume", "administrator", "asociatie", "apartamente", "canal", "trimis_la", "link", "primit", "deschis",
                    "vizitatori_unici", "peste_30s", "inceput_inregistrare", "conturi", "abonamente", "revenit_7z", "conversie_pct", "venit"])
        for c in docs:
            st = (await _campaign_stats(c))["stats"]
            w.writerow([c.get("name"), c.get("administrator"), c.get("association"), c.get("apartments_count"),
                        c.get("channel"), c.get("sent_at", "")[:10], c.get("url"), st["recipients"], st["opened"],
                        st["unique_visitors"], st["over_30s"], st["signup_started"], st["accounts_created"],
                        st["subscriptions"], st["returned_7d"], st["conversion_pct"], st["revenue"]])
    elif report == "pages":
        data = await analytics_pages(period, date_from, date_to, user)
        w.writerow(["pagina", "vizualizari", "timp_mediu_sec", "bounce_pct"])
        for i in data["items"]:
            w.writerow([i["path"], i["views"], i["avg_time_sec"], i["bounce_rate_pct"]])
    else:
        data = await analytics_overview(period, date_from, date_to, "auto", user)
        w.writerow(["zi", "vizitatori", "sesiuni"])
        for s in data["series"]:
            w.writerow([s["day"], s["visitors"], s["sessions"]])
        w.writerow([])
        w.writerow(["kpi", "valoare"])
        for k, v in data["kpi"].items():
            w.writerow([k, v])
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="propmanage_{report}.csv"'},
    )


# ═══════════ FAZA 2 — HEATMAP / BOUNCE / RETENȚIE / A/B TESTING / PDF ═══════════

import math
import re as _re

FUNNEL_GOALS = ["signup_started", "account_created", "property_added", "subscription", "specialist_request"]

WA_MEDIUM_LABELS = {"group": "Grupuri", "channel": "Canale", "private": "Privat", "status": "Status"}


@admin_router.get("/analytics/whatsapp")
async def analytics_whatsapp(
    period: str = Query("month", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Breakdown trafic WhatsApp pe utm_medium (group/channel/private/status) și utm_campaign."""
    d_from, d_to = _period_range(period, date_from, date_to)
    sessions = await db.analytics_sessions.find({"day": {"$gte": d_from, "$lte": d_to}, "source": "whatsapp"}).to_list(20000)
    by_medium: dict = defaultdict(lambda: {"sessions": 0, "visitors": set(), "accounts": set()})
    by_campaign: dict = defaultdict(lambda: {"sessions": 0, "visitors": set(), "accounts": set()})
    for s in sessions:
        m = ((s.get("utm_medium") or "").lower().strip()) or "nespecificat"
        c = s.get("utm_campaign") or s.get("campaign_code") or "—"
        for key, agg in ((m, by_medium), (c, by_campaign)):
            a = agg[key]
            a["sessions"] += 1
            a["visitors"].add(s["visitor_id"])
            if s.get("funnel_account_created"):
                a["accounts"].add(s["visitor_id"])

    def fmt(agg, labels=None):
        return sorted([{
            "key": k, "label": (labels or {}).get(k, k),
            "sessions": v["sessions"], "visitors": len(v["visitors"]),
            "accounts_created": len(v["accounts"]),
        } for k, v in agg.items()], key=lambda x: -x["sessions"])

    visitors = {s["visitor_id"] for s in sessions}
    accounts = {s["visitor_id"] for s in sessions if s.get("funnel_account_created")}
    return {
        "period": {"from": d_from, "to": d_to},
        "summary": {"sessions": len(sessions), "visitors": len(visitors), "accounts_created": len(accounts)},
        "by_medium": fmt(by_medium, WA_MEDIUM_LABELS),
        "by_campaign": fmt(by_campaign),
    }


@admin_router.get("/analytics/heatmap")
async def analytics_heatmap(
    period: str = Query("month", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "", path: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Click-map: pagini cu click-uri + puncte (x%, y%) pentru pagina selectată."""
    d_from, d_to = _period_range(period, date_from, date_to)
    base_q = {"type": "click", "day": {"$gte": d_from, "$lte": d_to}, "x_pct": {"$ne": None}}
    pipe = [{"$match": base_q}, {"$group": {"_id": "$path", "clicks": {"$sum": 1}}}, {"$sort": {"clicks": -1}}, {"$limit": 50}]
    pages = [{"path": p["_id"] or "/", "clicks": p["clicks"]} async for p in db.analytics_events.aggregate(pipe)]
    points = []
    if path:
        async for e in db.analytics_events.find({**base_q, "path": path}, {"x_pct": 1, "y_pct": 1}).limit(3000):
            points.append({"x": e.get("x_pct") or 0, "y": e.get("y_pct") or 0})
    return {"pages": pages, "points": points, "total_clicks": sum(p["clicks"] for p in pages), "period": {"from": d_from, "to": d_to}}


@admin_router.get("/analytics/bounce")
async def analytics_bounce(
    period: str = Query("week", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Bounce detaliat: serie zilnică, pe surse, pe pagini de intrare, distribuție durată."""
    d_from, d_to = _period_range(period, date_from, date_to)
    sessions = await db.analytics_sessions.find({"day": {"$gte": d_from, "$lte": d_to}}).to_list(20000)
    daily = defaultdict(lambda: {"sessions": 0, "bounces": 0})
    by_source = defaultdict(lambda: {"sessions": 0, "bounces": 0})
    by_entry = defaultdict(lambda: {"sessions": 0, "bounces": 0})
    buckets = {"<10s": 0, "10-30s": 0, "30-60s": 0, "1-3min": 0, ">3min": 0}
    quick = 0
    for s in sessions:
        b = 1 if (s.get("pageviews") or 0) <= 1 else 0
        daily[s.get("day")]["sessions"] += 1
        daily[s.get("day")]["bounces"] += b
        src = by_source[s.get("source") or "direct"]
        src["sessions"] += 1
        src["bounces"] += b
        en = by_entry[s.get("entry_path") or "/"]
        en["sessions"] += 1
        en["bounces"] += b
        dur = (s.get("duration_ms") or 0) / 1000
        if dur < 10:
            buckets["<10s"] += 1
            if b:
                quick += 1
        elif dur < 30:
            buckets["10-30s"] += 1
        elif dur < 60:
            buckets["30-60s"] += 1
        elif dur < 180:
            buckets["1-3min"] += 1
        else:
            buckets[">3min"] += 1
    series = []
    cur = datetime.fromisoformat(d_from).date()
    end = datetime.fromisoformat(d_to).date()
    while cur <= end:
        k = cur.isoformat()
        d = daily[k]
        series.append({"day": k, "sessions": d["sessions"], "bounces": d["bounces"],
                       "bounce_pct": round(d["bounces"] / d["sessions"] * 100, 1) if d["sessions"] else 0.0})
        cur += timedelta(days=1)
    total = len(sessions)
    total_b = sum(1 for s in sessions if (s.get("pageviews") or 0) <= 1)
    return {
        "period": {"from": d_from, "to": d_to},
        "summary": {
            "sessions": total,
            "bounces": total_b,
            "bounce_rate_pct": round(total_b / total * 100, 1) if total else 0.0,
            "quick_bounce_pct": round(quick / total * 100, 1) if total else 0.0,
        },
        "series": series,
        "by_source": sorted(
            [{"source": k, "sessions": v["sessions"], "bounces": v["bounces"],
              "bounce_rate_pct": round(v["bounces"] / v["sessions"] * 100, 1) if v["sessions"] else 0.0}
             for k, v in by_source.items()], key=lambda x: -x["sessions"]),
        "entry_pages": sorted(
            [{"path": k, "sessions": v["sessions"], "bounces": v["bounces"],
              "bounce_rate_pct": round(v["bounces"] / v["sessions"] * 100, 1) if v["sessions"] else 0.0}
             for k, v in by_entry.items()], key=lambda x: -x["sessions"])[:20],
        "duration_buckets": [{"bucket": k, "sessions": v} for k, v in buckets.items()],
    }


def _week_start(day: str) -> str:
    d = datetime.fromisoformat(day).date()
    return (d - timedelta(days=d.weekday())).isoformat()


@admin_router.get("/analytics/retention")
async def analytics_retention(weeks: int = Query(8, ge=2, le=16), user: dict = Depends(require_role("admin"))):
    """Retenție avansată: cohorte săptămânale de vizitatori + rezumat nou vs. revenit."""
    visitors: dict = {}
    async for s in db.analytics_sessions.find({}, {"visitor_id": 1, "day": 1}):
        if not s.get("day") or not s.get("visitor_id"):
            continue
        visitors.setdefault(s["visitor_id"], set()).add(_week_start(s["day"]))
    today = datetime.now(timezone.utc).date()
    this_week = (today - timedelta(days=today.weekday())).isoformat()
    week_starts = [(datetime.fromisoformat(this_week).date() - timedelta(weeks=w)).isoformat() for w in range(weeks - 1, -1, -1)]
    cohorts = []
    for i, ws in enumerate(week_starts):
        cohort = [wkset for wkset in visitors.values() if min(wkset) == ws]
        size = len(cohort)
        row = []
        for j in range(len(week_starts) - i):
            target = week_starts[i + j]
            active = sum(1 for wkset in cohort if target in wkset)
            row.append({"week": j, "active": active, "pct": round(active / size * 100, 1) if size else 0.0})
        cohorts.append({"cohort_week": ws, "size": size, "retention": row})
    returning = sum(1 for wkset in visitors.values() if len(wkset) >= 2)
    total_v = len(visitors)
    return {
        "cohorts": cohorts,
        "summary": {
            "total_visitors": total_v,
            "returning_visitors": returning,
            "returning_pct": round(returning / total_v * 100, 1) if total_v else 0.0,
        },
    }


# ── A/B TESTING ──────────────────────────────────────────────────────────────

class AbExperimentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    page_path: str = "/"
    goal: str = Field("account_created")
    hypothesis: str = ""


class AbExperimentUpdate(BaseModel):
    name: Optional[str] = None
    hypothesis: Optional[str] = None
    status: Optional[str] = None  # active | stopped


def _ab_slug(name: str) -> str:
    return _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:28] or "exp"


def _z_test(c1: int, n1: int, c2: int, n2: int):
    if n1 < 5 or n2 < 5:
        return {"z": None, "p_value": None, "significant": False, "note": "Date insuficiente (min. 5 vizitatori/variantă)"}
    p1, p2 = c1 / n1, c2 / n2
    p = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": None, "p_value": None, "significant": False, "note": "Fără variație"}
    z = (p1 - p2) / se
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return {"z": round(z, 2), "p_value": round(pval, 4), "significant": pval < 0.05, "note": ""}


async def _ab_results(key: str, goal: str) -> dict:
    field = f"ab_{key[:30]}"
    per_visitor: dict = {}
    async for s in db.analytics_sessions.find({field: {"$exists": True}}, {field: 1, "visitor_id": 1, f"funnel_{goal}": 1}):
        v = per_visitor.setdefault(s["visitor_id"], {"variant": s.get(field), "converted": False})
        if s.get(f"funnel_{goal}"):
            v["converted"] = True
    agg = {"A": {"visitors": 0, "conversions": 0}, "B": {"visitors": 0, "conversions": 0}}
    for v in per_visitor.values():
        var = v["variant"] if v["variant"] in ("A", "B") else "A"
        agg[var]["visitors"] += 1
        agg[var]["conversions"] += 1 if v["converted"] else 0
    for var in ("A", "B"):
        a = agg[var]
        a["rate_pct"] = round(a["conversions"] / a["visitors"] * 100, 1) if a["visitors"] else 0.0
    uplift = None
    if agg["A"]["rate_pct"] > 0:
        uplift = round((agg["B"]["rate_pct"] - agg["A"]["rate_pct"]) / agg["A"]["rate_pct"] * 100, 1)
    sig = _z_test(agg["B"]["conversions"], agg["B"]["visitors"], agg["A"]["conversions"], agg["A"]["visitors"])
    winner = ""
    if sig["significant"]:
        winner = "B" if agg["B"]["rate_pct"] > agg["A"]["rate_pct"] else "A"
    return {"variants": agg, "uplift_pct": uplift, "significance": sig, "winner": winner}


@admin_router.post("/analytics/ab")
async def create_ab_experiment(body: AbExperimentCreate, user: dict = Depends(require_role("admin"))):
    if body.goal not in FUNNEL_GOALS:
        raise HTTPException(400, f"Goal invalid. Opțiuni: {', '.join(FUNNEL_GOALS)}")
    key = _ab_slug(body.name)
    if await db.ab_experiments.find_one({"key": key}):
        key = f"{key[:24]}_{secrets.token_hex(2)}"
    doc = {
        "id": str(uuid.uuid4()),
        "key": key,
        **body.model_dump(),
        "status": "active",
        "created_by": user.get("email"),
        "created_at": _now(),
    }
    await db.ab_experiments.insert_one(doc)
    doc.pop("_id", None)
    return doc


@admin_router.get("/analytics/ab")
async def list_ab_experiments(user: dict = Depends(require_role("admin"))):
    docs = await db.ab_experiments.find({}).sort("created_at", -1).to_list(100)
    items = []
    for d in docs:
        d.pop("_id", None)
        d["results"] = await _ab_results(d["key"], d.get("goal") or "account_created")
        items.append(d)
    return {"items": items, "count": len(items)}


@admin_router.patch("/analytics/ab/{eid}")
async def update_ab_experiment(eid: str, body: AbExperimentUpdate, user: dict = Depends(require_role("admin"))):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates.get("status") not in (None, "active", "stopped"):
        raise HTTPException(400, "Status invalid")
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    res = await db.ab_experiments.update_one({"id": eid}, {"$set": updates})
    if not res.matched_count:
        raise HTTPException(404, "Experiment inexistent")
    d = await db.ab_experiments.find_one({"id": eid})
    d.pop("_id", None)
    return d


@admin_router.delete("/analytics/ab/{eid}")
async def delete_ab_experiment(eid: str, user: dict = Depends(require_role("admin"))):
    res = await db.ab_experiments.delete_one({"id": eid})
    if not res.deleted_count:
        raise HTTPException(404, "Experiment inexistent")
    return {"ok": True}


# ── EXPORT PDF (raport complet dashboard) ────────────────────────────────────

@admin_router.get("/analytics/export.pdf")
async def export_pdf(
    period: str = Query("month", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        if "FSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("FSans", "/usr/share/fonts/truetype/freefont/FreeSans.ttf"))
            pdfmetrics.registerFont(TTFont("FSansB", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"))
        F, FB = "FSans", "FSansB"
    except Exception:
        F, FB = "Helvetica", "Helvetica-Bold"

    overview = await analytics_overview(period, date_from, date_to, user)
    pages_data = await analytics_pages(period, date_from, date_to, user)
    bounce = await analytics_bounce(period, date_from, date_to, user)
    retention = await analytics_retention(8, user)
    camps = await db.growth_campaigns.find({}).sort("created_at", -1).to_list(50)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title="Raport Analytics PropManage")
    h1 = ParagraphStyle("h1", fontName=FB, fontSize=17, spaceAfter=2, textColor=colors.HexColor("#0f172a"))
    h2 = ParagraphStyle("h2", fontName=FB, fontSize=11.5, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#1e293b"))
    small = ParagraphStyle("small", fontName=F, fontSize=8.5, textColor=colors.HexColor("#64748b"))

    def tbl(headers, rows, widths=None):
        t = Table([headers] + rows, colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), FB), ("FONTNAME", (0, 1), (-1, -1), F),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    p = overview["period"]
    k = overview["kpi"]
    story = [
        Paragraph("PropManage — Raport Analytics & Growth", h1),
        Paragraph(f"Perioadă: {p['from']} → {p['to']} · Generat: {_now()[:16].replace('T', ' ')} UTC", small),
        Spacer(1, 4),
        Paragraph("Indicatori cheie (KPI)", h2),
        tbl(["Indicator", "Valoare"], [
            ["Vizitatori unici", str(k["unique_visitors"])],
            ["Sesiuni", str(k["sessions"])],
            ["Conturi create", str(k["accounts_created"])],
            ["Specialiști înscriși", str(k["specialists_signed"])],
            ["Proprietăți adăugate", str(k["properties_added"])],
            ["Solicitări specialiști", str(k["specialist_requests"])],
            ["Abonamente", str(k["subscriptions"])],
            ["Bounce rate", f'{k["bounce_rate_pct"]}%'],
            ["Durată medie sesiune", f'{k["avg_session_sec"]}s'],
            ["Vizitatori care revin (istoric)", f'{retention["summary"]["returning_pct"]}%'],
        ], widths=[95 * mm, 40 * mm]),
        Paragraph("Surse de trafic", h2),
        tbl(["Sursă", "Sesiuni", "Vizitatori", "Bounce"],
            [[s["source"], str(s["sessions"]), str(s["visitors"]),
              f'{next((b["bounce_rate_pct"] for b in bounce["by_source"] if b["source"] == s["source"]), 0)}%']
             for s in overview["sources"]] or [["—", "0", "0", "0%"]],
            widths=[55 * mm, 27 * mm, 27 * mm, 27 * mm]),
        Paragraph("Funnel conversie", h2),
        tbl(["Pas", "Număr"], [[f["step"], str(f["count"])] for f in overview["funnel"]], widths=[95 * mm, 40 * mm]),
        Paragraph("Top pagini", h2),
        tbl(["Pagină", "Vizualizări", "Timp mediu", "Bounce"],
            [[i["path"][:60], str(i["views"]), f'{i["avg_time_sec"]}s', f'{i["bounce_rate_pct"]}%'] for i in pages_data["items"][:12]] or [["—", "0", "0s", "0%"]],
            widths=[78 * mm, 20 * mm, 20 * mm, 18 * mm]),
        Paragraph("Bounce detaliat — pagini de intrare", h2),
        tbl(["Pagină de intrare", "Sesiuni", "Bounce"],
            [[e["path"][:60], str(e["sessions"]), f'{e["bounce_rate_pct"]}%'] for e in bounce["entry_pages"][:10]] or [["—", "0", "0%"]],
            widths=[80 * mm, 27 * mm, 27 * mm]),
        Paragraph("Campanii growth", h2),
    ]
    c_rows = []
    for c in camps:
        st = (await _campaign_stats(c))["stats"]
        c_rows.append([str(c.get("name", ""))[:28], c.get("channel", ""), str(st["recipients"]), str(st["opened"]),
                       str(st["unique_visitors"]), str(st["accounts_created"]), f'{st["conversion_pct"]}%'])
    story.append(tbl(["Campanie", "Canal", "Primit", "Deschis", "Vizitatori", "Conturi", "Conversie"],
                     c_rows or [["—"] * 7], widths=[42 * mm, 20 * mm, 16 * mm, 17 * mm, 20 * mm, 16 * mm, 19 * mm]))
    story.append(Paragraph("Retenție — cohorte săptămânale (% activi în săptămânile următoare)", h2))
    coh_rows = [[c["cohort_week"], str(c["size"])] + [f'{r["pct"]}%' for r in c["retention"][:6]] +
                [""] * max(0, 6 - len(c["retention"][:6])) for c in retention["cohorts"][-8:]]
    story.append(tbl(["Cohortă", "Vizitatori", "S0", "S1", "S2", "S3", "S4", "S5"],
                     coh_rows or [["—"] * 8], widths=[26 * mm, 20 * mm] + [14 * mm] * 6))
    doc.build(story)
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="propmanage_raport_{p["from"]}_{p["to"]}.pdf"'})



# ═══════════════════════ CAMPAIGN MARKERS & COMPARE (admin) ═══════════════════════

@admin_router.get("/analytics/campaign-markers")
async def analytics_campaign_markers(
    period: str = Query("month", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Returnează campaniile cu prima activitate în intervalul cerut → markers pe graficul de trafic."""
    d_from, d_to = _period_range(period, date_from, date_to)
    camps = await db.growth_campaigns.find({}).to_list(500)
    markers = []
    for c in camps:
        # prima sesiune atribuită campaniei
        first = await db.analytics_sessions.find_one(
            {"campaign_code": c.get("code")},
            sort=[("day", 1)],
        )
        anchor = None
        if first and first.get("day"):
            anchor = first["day"]
        elif c.get("created_at"):
            anchor = c["created_at"][:10]
        if not anchor:
            continue
        # doar dacă e în intervalul cerut
        if anchor < d_from or anchor > d_to:
            continue
        markers.append({
            "id": c.get("id"),
            "code": c.get("code"),
            "name": c.get("name"),
            "channel": c.get("channel"),
            "day": anchor,
        })
    markers.sort(key=lambda x: x["day"])
    return {"period": {"from": d_from, "to": d_to}, "markers": markers}


async def _campaign_stats_in_period(camp: dict, d_from: str, d_to: str) -> dict:
    """Stats per campanie filtrate pe interval — pentru comparator."""
    code = camp.get("code")
    sessions = await db.analytics_sessions.find({
        "campaign_code": code,
        "day": {"$gte": d_from, "$lte": d_to},
    }).to_list(10000)
    visitors = {}
    for s in sessions:
        v = visitors.setdefault(s["visitor_id"], {"days": set(), "dur": 0})
        v["days"].add(s.get("day"))
        v["dur"] = max(v["dur"], s.get("duration_ms", 0))
        for f in ("signup_started", "account_created", "subscription", "specialist_request", "property_added"):
            if s.get(f"funnel_{f}"):
                v[f] = True
    unique_visitors = len(visitors)
    over_30s = sum(1 for v in visitors.values() if v["dur"] >= 30_000)
    signup_started = sum(1 for v in visitors.values() if v.get("signup_started"))
    accounts = sum(1 for v in visitors.values() if v.get("account_created"))
    subscriptions = sum(1 for v in visitors.values() if v.get("subscription"))
    returned_7d = sum(1 for v in visitors.values() if len(v["days"]) >= 2)
    conversion = round(accounts / unique_visitors * 100, 1) if unique_visitors else 0.0
    # serie zilnică pentru chart-ul comparator
    daily = defaultdict(lambda: {"sessions": 0, "visitors": set()})
    for s in sessions:
        daily[s.get("day")]["sessions"] += 1
        daily[s.get("day")]["visitors"].add(s["visitor_id"])
    series_daily = []
    cur = datetime.fromisoformat(d_from).date()
    end = datetime.fromisoformat(d_to).date()
    while cur <= end:
        k = cur.isoformat()
        series_daily.append({"day": k, "sessions": daily[k]["sessions"], "visitors": len(daily[k]["visitors"])})
        cur += timedelta(days=1)
    granularity = _auto_granularity(d_from, d_to)
    series = _aggregate_series(series_daily, granularity)
    return {
        "id": camp.get("id"),
        "code": code,
        "name": camp.get("name"),
        "channel": camp.get("channel"),
        "recipients": camp.get("recipients_count", 0),
        "stats": {
            "unique_visitors": unique_visitors,
            "over_30s": over_30s,
            "signup_started": signup_started,
            "accounts_created": accounts,
            "subscriptions": subscriptions,
            "returned_7d": returned_7d,
            "conversion_pct": conversion,
        },
        "series": series,
    }


@admin_router.get("/growth/campaigns/compare")
async def compare_campaigns(
    ids: str = Query("", description="Comma-separated campaign ids (max 3)"),
    period: str = Query("month", pattern="^(day|week|month|60d|90d|6m|12m|ytd|custom)$"),
    date_from: str = "", date_to: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Comparator side-by-side pentru 2-3 campanii pe intervalul selectat."""
    id_list = [x.strip() for x in ids.split(",") if x.strip()][:3]
    if len(id_list) < 2:
        raise HTTPException(400, "Selectează minim 2 campanii pentru comparație (max 3).")
    d_from, d_to = _period_range(period, date_from, date_to)
    granularity = _auto_granularity(d_from, d_to)
    results = []
    for cid in id_list:
        camp = await db.growth_campaigns.find_one({"id": cid})
        if not camp:
            continue
        results.append(await _campaign_stats_in_period(camp, d_from, d_to))
    return {"period": {"from": d_from, "to": d_to}, "granularity": granularity, "campaigns": results}
