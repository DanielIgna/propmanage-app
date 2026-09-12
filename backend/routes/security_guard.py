"""PropManage — Behavioral Security Guard (Phase 47)

Deterministic Python heuristics that protect AI endpoints (Concierge, Admin AI)
from bots, scrapers, VPN abuse, geo-fenced misuse and prompt-injection-driven
cost exfiltration.

NO LLM credits are spent on detection — only on legitimate replies.

All blocking events are persisted in `security_events` AND mirrored to
`admin_ai_findings` so the Admin Investigator surfaces them automatically.
"""
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Body, Query

from db import db
from deps import get_current_user
from sub_admin_deps import require_admin_scope

logger = logging.getLogger("propmanage.security_guard")
router = APIRouter(prefix="/api/admin/security", tags=["admin-security"])

# ============= CONFIG (DB-backed with sane defaults) =============

DEFAULT_CONFIG = {
    "geo_block_enabled": False,           # OFF by default — admin must opt in
    "geo_allowed_countries": ["RO"],      # ISO codes
    "vpn_block_enabled": True,
    "bot_block_enabled": True,
    "rate_limit_per_minute": 30,          # cap req/min per IP on protected endpoints
    "concierge_msgs_per_hour": 25,        # per authenticated user
    "concierge_msgs_per_day": 200,
    "updated_at": None,
}


async def _get_config() -> dict:
    from settings_store import get_settings
    doc = await get_settings("security")
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in doc.items() if k != "_id"})
    return merged


async def _save_config(updates: dict, actor_id: str):
    from settings_store import patch_settings
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = actor_id
    await patch_settings("security", updates, who=actor_id)


# ============= HEURISTICS =============

# User-Agent patterns that are obviously non-browser. We allow legitimate mobile/desktop
# browsers. Headless browsers + scraping libs are blocked.
BOT_UA_REGEX = re.compile(
    r"(curl|wget|python-requests|httpx|aiohttp|libwww|scrapy|httpie|"
    r"go-http-client|java/|okhttp|node-fetch|axios/|phantomjs|headlesschrome|"
    r"slimerjs|selenium|puppeteer|playwright|bot\b|spider|crawler|"
    r"semrush|ahrefsbot|mj12bot|dotbot|googlebot|bingbot|yandexbot|baiduspider)",
    re.IGNORECASE,
)

# IPs (or first /16) commonly used by cloud / VPN providers.
# Lightweight heuristic — not a paid IP intel service. Admin can extend list in DB.
VPN_HINTS_REGEX = re.compile(
    r"(nordvpn|expressvpn|protonvpn|surfshark|mullvad|cyberghost|vpn|proxy|tor-exit|hide\.me)",
    re.IGNORECASE,
)

# Well-known datacenter ASN prefixes (very small built-in list, NOT exhaustive).
# Production should integrate MaxMind or IP2Proxy — this is the deterministic MVP heuristic.
DATACENTER_PREFIXES = (
    "13.", "18.", "34.", "35.", "52.", "54.",          # AWS
    "104.196.", "104.197.", "104.198.", "104.199.",   # GCP
    "20.", "40.", "51.", "104.40.", "104.41.",        # Azure
    "165.227.", "159.65.", "167.71.", "134.122.",     # DigitalOcean
    "45.32.", "45.63.", "45.76.",                       # Vultr
    "207.154.", "138.197.", "146.190.",                 # Random VPS providers
)


def _extract_ip(req: Request) -> str:
    h = req.headers
    fwd = h.get("x-forwarded-for") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    real = h.get("x-real-ip")
    if real:
        return real.strip()
    return (req.client.host if req.client else "0.0.0.0")


def _extract_country(req: Request) -> Optional[str]:
    """Best-effort country detection from common edge headers (Cloudflare, AWS CloudFront, custom)."""
    h = req.headers
    cc = (
        h.get("cf-ipcountry")
        or h.get("x-country")
        or h.get("x-country-code")
        or h.get("x-vercel-ip-country")
        or h.get("cloudfront-viewer-country")
        or ""
    ).strip().upper()
    if cc and cc not in ("XX", "T1"):
        return cc
    return None


def _classify_ua(ua: str) -> Optional[str]:
    if not ua:
        return "missing_ua"
    if BOT_UA_REGEX.search(ua):
        return "bot_ua"
    # Browser UAs always contain Mozilla/ — naive but effective.
    if "mozilla" not in ua.lower():
        return "non_browser_ua"
    return None


def _is_datacenter_ip(ip: str) -> bool:
    if not ip or ip == "0.0.0.0":
        return False
    return any(ip.startswith(pfx) for pfx in DATACENTER_PREFIXES)


# ============= EVENT LOGGING + MIRROR TO ADMIN AI FINDINGS =============

async def _log_event(kind: str, reason: str, req: Request, user: Optional[dict] = None, severity: str = "high"):
    ev = {
        "kind": kind,
        "reason": reason,
        "severity": severity,
        "ip": _extract_ip(req),
        "country": _extract_country(req),
        "user_agent": req.headers.get("user-agent", "")[:300],
        "path": str(req.url.path),
        "user_id": (user or {}).get("id"),
        "user_email": (user or {}).get("email"),
        "user_role": (user or {}).get("role"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.security_events.insert_one(ev)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SecGuard] failed to persist event: {e}")

    # Mirror to admin_ai_findings (idempotent per (kind, ip))
    composite_key = f"security_{kind}::{ev['ip']}"
    try:
        existing = await db.admin_ai_findings.find_one({"composite_key": composite_key})
        now_iso = ev["created_at"]
        if existing:
            await db.admin_ai_findings.update_one(
                {"_id": existing["_id"]},
                {"$set": {"last_seen_at": now_iso}, "$inc": {"occurrences": 1}},
            )
        else:
            await db.admin_ai_findings.insert_one({
                "composite_key": composite_key,
                "pattern": f"security_{kind}",
                "label": f"Blocare securitate: {reason}",
                "severity": severity,
                "description": f"IP {ev['ip']} blocat ({reason}) pe endpoint protejat.",
                "entity_type": "security_event",
                "entity_id": ev["ip"],
                "entity_label": f"{ev['ip']} → {ev['path']}",
                "context": {"reason": reason, "ua": ev["user_agent"][:120], "country": ev["country"]},
                "status": "open",
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
                "occurrences": 1,
                "scan_id": "security_guard",
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SecGuard] failed to mirror finding: {e}")


# ============= RATE LIMITER (Mongo-backed, sliding window per IP) =============

async def _check_rate_limit(ip: str, key_prefix: str, limit: int, window_seconds: int) -> bool:
    """Returns True if request is allowed, False if rate-limited.
    Uses a simple counter doc with TTL via cleanup on each check (no TTL index needed for MVP).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
    bucket_id = f"{key_prefix}::{ip}"
    try:
        # Drop expired hits
        await db.security_rate_buckets.update_one(
            {"_id": bucket_id},
            {"$pull": {"hits": {"$lt": cutoff}}},
        )
        # Read current count
        doc = await db.security_rate_buckets.find_one({"_id": bucket_id})
        current = len((doc or {}).get("hits", []))
        if current >= limit:
            return False
        # Append new hit
        await db.security_rate_buckets.update_one(
            {"_id": bucket_id},
            {"$push": {"hits": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SecGuard] rate limit error: {e} — allowing request")
        return True


# ============= MAIN GUARD DEPENDENCY =============

async def security_guard(request: Request, user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency that runs all heuristic checks BEFORE the endpoint executes.
    Admin role bypasses geo/vpn/bot blocks (but is still rate-limited to avoid loops).
    """
    cfg = await _get_config()
    ip = _extract_ip(request)
    ua = request.headers.get("user-agent", "")

    # Admins always pass content checks
    is_admin = user.get("role") == "admin"

    # 1) Bot UA block
    if cfg["bot_block_enabled"] and not is_admin:
        ua_violation = _classify_ua(ua)
        if ua_violation:
            await _log_event("bot_blocked", ua_violation, request, user)
            raise HTTPException(status_code=403, detail="Acces blocat: client neacceptat.")

    # 2) GEO block
    if cfg["geo_block_enabled"] and not is_admin:
        cc = _extract_country(request)
        allowed = [c.upper() for c in cfg.get("geo_allowed_countries", [])]
        if cc and allowed and cc not in allowed:
            await _log_event("geo_blocked", f"country={cc}", request, user, severity="warning")
            raise HTTPException(status_code=403, detail="Acces blocat: regiune neacceptată.")

    # 3) VPN / datacenter heuristic
    if cfg["vpn_block_enabled"] and not is_admin:
        if _is_datacenter_ip(ip) or VPN_HINTS_REGEX.search(ua):
            await _log_event("vpn_blocked", "datacenter_or_vpn_ua", request, user, severity="warning")
            raise HTTPException(status_code=403, detail="Acces blocat: detectat VPN/proxy.")

    # 4) Rate limit per IP (60s window)
    allowed_ip = await _check_rate_limit(ip, "ip_min", cfg["rate_limit_per_minute"], 60)
    if not allowed_ip:
        await _log_event("rate_limit_ip", f"{cfg['rate_limit_per_minute']}/min", request, user, severity="warning")
        raise HTTPException(status_code=429, detail="Prea multe cereri. Reia peste 1 minut.")

    # 5) Rate limit per user (concierge specific — only if path contains /concierge)
    if "/concierge" in request.url.path and not is_admin:
        uid = user.get("id") or "anon"
        allowed_h = await _check_rate_limit(uid, "user_h", cfg["concierge_msgs_per_hour"], 3600)
        allowed_d = await _check_rate_limit(uid, "user_d", cfg["concierge_msgs_per_day"], 86400)
        if not (allowed_h and allowed_d):
            await _log_event(
                "concierge_quota_exhausted",
                f"hour={cfg['concierge_msgs_per_hour']} day={cfg['concierge_msgs_per_day']}",
                request, user, severity="warning",
            )
            raise HTTPException(status_code=429, detail="Ai atins limita zilnică de mesaje pentru asistent. Revino mai târziu.")

    return user


# ============= ADMIN ENDPOINTS =============

@router.get("/config")
async def get_config(user: dict = Depends(require_admin_scope("security"))):
    return await _get_config()


@router.put("/config")
async def update_config(payload: dict = Body(...), user: dict = Depends(require_admin_scope("security"))):
    allowed_fields = {
        "geo_block_enabled", "geo_allowed_countries",
        "vpn_block_enabled", "bot_block_enabled",
        "rate_limit_per_minute", "concierge_msgs_per_hour", "concierge_msgs_per_day",
    }
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    if "geo_allowed_countries" in updates:
        if not isinstance(updates["geo_allowed_countries"], list):
            raise HTTPException(400, "geo_allowed_countries must be a list")
        updates["geo_allowed_countries"] = [str(c).upper().strip()[:2] for c in updates["geo_allowed_countries"] if c]
    for nkey in ("rate_limit_per_minute", "concierge_msgs_per_hour", "concierge_msgs_per_day"):
        if nkey in updates:
            try:
                updates[nkey] = max(1, int(updates[nkey]))
            except (TypeError, ValueError):
                raise HTTPException(400, f"{nkey} must be a positive integer")
    await _save_config(updates, user["id"])
    return await _get_config()


@router.get("/events")
async def list_events(
    limit: int = Query(100, le=500),
    kind: Optional[str] = None,
    user: dict = Depends(require_admin_scope("security")),
):
    filt = {}
    if kind:
        filt["kind"] = kind
    cursor = db.security_events.find(filt).sort("created_at", -1).limit(limit)
    items = []
    async for ev in cursor:
        ev["_id"] = str(ev["_id"])
        items.append(ev)
    # Count summary by kind in last 24h
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$kind", "count": {"$sum": 1}}},
    ]
    by_kind = {row["_id"]: row["count"] async for row in db.security_events.aggregate(pipeline)}
    return {"items": items, "by_kind_24h": by_kind, "total": len(items)}
