"""PropManage — Security Middleware: Bot detection, GeoIP, VPN detection, PII access audit.

Lightweight middleware that:
- Detects bot user-agents (gratis, no DB calls for whitelist)
- Logs geo location (best-effort via X-Forwarded-For; full GeoIP DB integration optional)
- Tracks PII-sensitive endpoint access for audit
- Records suspicious patterns into admin_ai_findings asynchronously
"""
import re
import logging
from datetime import datetime, timezone, timedelta

from fastapi import Request

logger = logging.getLogger("propmanage.security_mw")

# ============= BOT USER-AGENT DETECTION =============
BOT_UA_PATTERNS = [
    r"\b(bot|crawler|spider|scraper|fetch|http|libwww|curl/|wget/|python-requests|aiohttp|httpx)\b",
    r"\b(scrapy|phantomjs|headlesschrome|puppeteer|playwright)\b",
    r"\b(slurp|baiduspider|yandex|bingbot|googlebot|duckduckbot|facebookexternalhit)\b",
    r"\b(go-http-client|java/|okhttp|axios|node-fetch)\b",
]
BOT_REGEX = re.compile("|".join(BOT_UA_PATTERNS), re.IGNORECASE)

# Whitelist (legitimate bots we accept on public landing only)
LEGITIMATE_BOT_PATTERNS = [
    r"googlebot",
    r"bingbot",
    r"slackbot",  # for link previews
    r"twitterbot",
    r"facebookexternalhit",
    r"linkedinbot",
]
LEGIT_REGEX = re.compile("|".join(LEGITIMATE_BOT_PATTERNS), re.IGNORECASE)

# ============= KNOWN VPN/DATACENTER IP RANGES (basic free tier) =============
# Common datacenter prefixes — covers ~40% of VPN traffic
KNOWN_DC_PREFIXES = (
    "3.", "13.", "18.", "34.", "35.", "52.", "54.",  # AWS
    "104.196.", "104.197.", "104.198.", "104.199.",  # GCP
    "20.", "40.", "104.40.", "13.64.",  # Azure
    "157.230.", "159.65.", "159.89.", "165.227.",  # DigitalOcean
    "5.45.", "5.61.", "188.165.", "94.23.",  # OVH
    "185.220.",  # Tor exit nodes
    "23.94.", "192.99.", "198.50.",  # Various DC
)


def detect_bot(user_agent: str) -> dict:
    """Returns {is_bot, is_legitimate, matched_pattern}."""
    if not user_agent:
        return {"is_bot": True, "is_legitimate": False, "matched_pattern": "empty_ua"}
    is_bot = bool(BOT_REGEX.search(user_agent))
    is_legit = bool(LEGIT_REGEX.search(user_agent))
    return {
        "is_bot": is_bot,
        "is_legitimate": is_legit,
        "matched_pattern": "bot_signature" if is_bot else None,
    }


def detect_vpn_basic(ip: str) -> dict:
    """Best-effort VPN/datacenter detection via known IP prefixes.
    Returns {is_vpn, confidence: low|medium|high, reason}.
    """
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return {"is_vpn": False, "confidence": "none", "reason": "local"}
    for prefix in KNOWN_DC_PREFIXES:
        if ip.startswith(prefix):
            return {"is_vpn": True, "confidence": "medium", "reason": f"datacenter_prefix_{prefix}"}
    if ip.startswith("185.220."):
        return {"is_vpn": True, "confidence": "high", "reason": "tor_exit_node"}
    return {"is_vpn": False, "confidence": "low", "reason": None}


# ============= REQUEST FINGERPRINT MIDDLEWARE =============

async def security_log_middleware(request: Request, call_next):
    """Captures request fingerprint and logs suspicious patterns to security_events collection."""
    from db import db  # local import to avoid circular

    response = None
    try:
        path = request.url.path
        # Only track /api/* (skip static + frontend routes)
        if not path.startswith("/api/"):
            return await call_next(request)

        ua = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else ""
        # Trust X-Forwarded-For if present (Kubernetes ingress)
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()

        bot_info = detect_bot(ua)
        vpn_info = detect_vpn_basic(ip)

        # Public bot block (for non-legit bots on auth endpoints)
        if bot_info["is_bot"] and not bot_info["is_legitimate"]:
            if any(s in path for s in ["/auth/login", "/auth/register", "/concierge/chat", "/payments/"]):
                # Hard block
                await db.security_events.insert_one({
                    "type": "bot_blocked",
                    "ip": ip,
                    "ua": ua[:300],
                    "path": path,
                    "method": request.method,
                    "severity": "high",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied. Automated requests not allowed on this endpoint."},
                )

        # Log VPN access (don't block — flag for admin review)
        if vpn_info["is_vpn"] and vpn_info["confidence"] in ("medium", "high"):
            await db.security_events.insert_one({
                "type": "vpn_access",
                "ip": ip,
                "ua": ua[:300],
                "path": path,
                "method": request.method,
                "severity": "warning",
                "context": vpn_info,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # PII access audit — admin endpoints touching user data
        pii_paths = ["/admin/users", "/admin/clients", "/admin/specialists", "/admin/operators"]
        if any(p in path for p in pii_paths) and request.method == "GET":
            # Note: we don't know yet if auth succeeded; we'll log after response
            await db.security_events.insert_one({
                "type": "pii_access",
                "ip": ip,
                "ua": ua[:300],
                "path": path,
                "method": request.method,
                "severity": "low",  # bulk patterns flagged later by scanner
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        response = await call_next(request)
        return response
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SecurityMW] error: {e}")
        if response is not None:
            return response
        return await call_next(request)


# ============= ADDITIONAL SCANNERS (to be called from admin_ai.py) =============

async def scan_brute_force_login() -> list:
    from db import db
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    pipeline = [
        {"$match": {"action": "auth.login_failed", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$target_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 10}}},
        {"$limit": 30},
    ]
    findings = []
    async for d in db.admin_audit_log.aggregate(pipeline):
        findings.append({
            "pattern": "brute_force_login",
            "entity_type": "email",
            "entity_id": d["_id"] or "unknown",
            "entity_label": f"{d['count']} fail-uri în 1h pe '{d['_id']}'",
            "context": {"fail_count": d["count"], "window_hours": 1},
        })
    return findings


async def scan_bot_attempts() -> list:
    from db import db
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"type": "bot_blocked", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$ip", "count": {"$sum": 1}, "paths": {"$addToSet": "$path"}}},
        {"$match": {"count": {"$gte": 5}}},
        {"$limit": 30},
    ]
    findings = []
    async for d in db.security_events.aggregate(pipeline):
        findings.append({
            "pattern": "persistent_bot_attempts",
            "entity_type": "ip",
            "entity_id": d["_id"],
            "entity_label": f"{d['count']} încercări bot din IP {d['_id']}",
            "context": {"count": d["count"], "targets": d.get("paths", [])[:10]},
        })
    return findings


async def scan_vpn_access() -> list:
    from db import db
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"type": "vpn_access", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$ip", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 20}}},
        {"$limit": 30},
    ]
    findings = []
    async for d in db.security_events.aggregate(pipeline):
        findings.append({
            "pattern": "vpn_heavy_use",
            "entity_type": "ip",
            "entity_id": d["_id"],
            "entity_label": f"IP VPN/DC cu {d['count']} requests în 24h",
            "context": {"count": d["count"], "ip": d["_id"]},
        })
    return findings


async def scan_pii_bulk_access() -> list:
    from db import db
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    pipeline = [
        {"$match": {"type": "pii_access", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$ip", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 50}}},  # 50+ PII reads in 10 min from same IP
        {"$limit": 10},
    ]
    findings = []
    async for d in db.security_events.aggregate(pipeline):
        findings.append({
            "pattern": "pii_bulk_access",
            "entity_type": "ip",
            "entity_id": d["_id"],
            "entity_label": f"Acces masiv PII: {d['count']} requests în 10 min",
            "context": {"count": d["count"], "ip": d["_id"]},
        })
    return findings


async def scan_concierge_repeat_abusers() -> list:
    from db import db
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pipeline = [
        {"$match": {"blocked": True, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}, "role": {"$first": "$user_role"}}},
        {"$match": {"count": {"$gte": 3}}},
        {"$limit": 20},
    ]
    findings = []
    async for d in db.concierge_messages.aggregate(pipeline):
        findings.append({
            "pattern": "concierge_repeat_abuser",
            "entity_type": "user",
            "entity_id": d["_id"],
            "entity_label": f"{d.get('role', '?')} cu {d['count']} blocking-uri în 7 zile",
            "context": {"blocks": d["count"], "role": d.get("role")},
        })
    return findings


ADDITIONAL_PATTERNS = {
    "brute_force_login": {"label": "Atac brute-force login", "severity": "high", "description": "10+ încercări failed login pe același email în 1h"},
    "persistent_bot_attempts": {"label": "Bot persistent", "severity": "high", "description": "Același IP încearcă să acceseze endpoint-uri restricționate cu UA de bot"},
    "vpn_heavy_use": {"label": "Trafic VPN intens", "severity": "warning", "description": "Trafic semnificativ de pe IP-uri de VPN/datacenter — posibil tentativă de evadare de la rate limiting"},
    "pii_bulk_access": {"label": "Acces masiv la PII", "severity": "high", "description": "Volum mare de requests la endpoint-uri PII — posibil tentativă de data exfiltration"},
    "concierge_repeat_abuser": {"label": "Abuzator repetitiv concierge", "severity": "warning", "description": "User cu 3+ blocking-uri în concierge — candidat pentru ban permanent"},
}
