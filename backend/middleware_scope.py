"""Admin-Scope HTTP middleware.

Applies a URL-pattern → required-scope map across all `/api/admin/*` routes
without requiring per-endpoint annotations. Sub-admins are blocked at the
HTTP layer if their ``admin_scope`` is not in the required set for the path.

Super admins (admin_scope == "general") and any path that maps to "general"
are always allowed. Non-admins are NOT blocked here (existing per-route
``require_role`` / ``require_admin_scope`` deps handle those).

Auth check uses the same JWT cookie/Bearer flow as ``deps.get_current_user``
to keep behaviour consistent. If the token is invalid/missing we let the
downstream route handler decide (it will return 401 itself).

The middleware also writes a lightweight audit log entry for any denied
request, using the same ``admin_actions_log`` collection.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional

import jwt
from bson import ObjectId
from fastapi import Request
from starlette.responses import JSONResponse

from db import db
from core_utils import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger("propmanage.admin_scope_mw")

# URL-prefix → scope map. Order matters: first match wins.
# All patterns are anchored to the start of the path.
SCOPE_RULES = [
    # ----- TESTING -----
    (re.compile(r"^/api/admin/smoke-test"),              "testing"),
    (re.compile(r"^/api/admin/qa-(copilot|playbook)"),   "testing"),
    (re.compile(r"^/api/admin/data-integrity"),          "testing"),
    (re.compile(r"^/api/admin/healthcheck"),             "testing"),
    # ----- SECURITY -----
    (re.compile(r"^/api/admin/security"),                "security"),
    (re.compile(r"^/api/admin/gdpr"),                    "security"),
    (re.compile(r"^/api/admin/impersonat"),              "security"),
    (re.compile(r"^/api/admin/ai-security"),             "security"),
    (re.compile(r"^/api/kyc/admin"),                     "security"),
    # ----- AI -----
    (re.compile(r"^/api/admin/ai-(control|pm|governance|dev-team|docs|investigator)"), "ai"),
    (re.compile(r"^/api/admin/concierge"),               "ai"),
    (re.compile(r"^/api/admin/bug-memory"),              "ai"),
    # ----- OPS -----
    (re.compile(r"^/api/admin/autonomy"),                "ops"),
    (re.compile(r"^/api/admin/auto-match"),              "ops"),
    (re.compile(r"^/api/admin/incidents"),               "ops"),
    (re.compile(r"^/api/admin/backups"),                 "ops"),
    (re.compile(r"^/api/admin/exec-briefing"),           "ops"),
    (re.compile(r"^/api/admin/dev-velocity"),            "ops"),
    # ----- FRONTEND (content / texts / emails) -----
    (re.compile(r"^/api/admin/(cms|texts|emails?|zones|content-audit|term-audit)"), "frontend"),
    (re.compile(r"^/api/admin/feature-configurator"),    "frontend"),
    (re.compile(r"^/api/admin/design"),                  "frontend"),
    # Config surfaces (SEC-001 remediere Iun 2026):
    (re.compile(r"^/api/admin/config-history"),          "frontend"),  # read VIEW peste audit config
    (re.compile(r"^/api/admin/pages"),                   "frontend"),  # Page Registry (conținut/SEO)
    # ----- BACKEND -----
    (re.compile(r"^/api/admin/(backup|data-)"),          "backend"),
    (re.compile(r"^/api/admin/app-settings"),            "backend"),
    (re.compile(r"^/api/admin/architecture-board"),      "backend"),
    # ----- OPS (extindere SEC-001) -----
    (re.compile(r"^/api/admin/renewal-reminders"),       "ops"),
    # ----- GENERAL (everything else under /api/admin/) -----
    # Sub-admins management itself is a super-admin (general) area
    # — but /me/scope must be readable by ANY admin
    (re.compile(r"^/api/admin/sub-admins/me/"),          None),  # bypass — any admin
    (re.compile(r"^/api/admin/approvals(/[^/]+/(approve|reject))?/?$"), None),  # caller-side check
    (re.compile(r"^/api/admin/sub-admins"),              "general"),
    (re.compile(r"^/api/admin/approvals"),               "general"),
    (re.compile(r"^/api/admin/founder-gate"),            "general"),
    (re.compile(r"^/api/admin/stats"),                   "general"),
    (re.compile(r"^/api/admin/finance"),                 "general"),
    (re.compile(r"^/api/admin/users"),                   "general"),
    # Config I/O import/export + Snapshots restore ating TOATE suprafețele de
    # config (design + cms + pages + settings + fees) → doar super-admin.
    (re.compile(r"^/api/admin/config"),                  "general"),
    (re.compile(r"^/api/admin/snapshots"),               "general"),
]


def _required_scope(path: str) -> Optional[str]:
    for pat, scope in SCOPE_RULES:
        if pat.match(path):
            return scope
    return None  # not under management, skip


async def _resolve_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        return user
    except Exception:  # noqa: BLE001
        return None


async def admin_scope_middleware(request: Request, call_next):
    path = request.url.path
    # Only act on /api/admin/*
    if not path.startswith("/api/admin/"):
        return await call_next(request)
    required = _required_scope(path)
    if required is None:
        return await call_next(request)
    user = await _resolve_user(request)
    if not user:
        # Let downstream auth raise 401 — don't double-log here
        return await call_next(request)
    if (user.get("role") or "") != "admin":
        return await call_next(request)  # downstream handles role mismatches
    user_scope = (user.get("admin_scope") or "general").lower()
    allowed = {required, "general"}
    if user_scope in allowed:
        return await call_next(request)

    # DENY — log + 403
    try:
        await db.admin_actions_log.insert_one({
            "user_id": str(user.get("_id")),
            "user_email": user.get("email"),
            "scope": user_scope,
            "method": request.method,
            "path": path,
            "allowed_scopes": sorted(allowed),
            "outcome": "denied",
            "source": "middleware",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:  # noqa: BLE001
        pass
    return JSONResponse(
        {"detail": f"Acces refuzat (middleware) — endpoint-ul necesită admin_scope ∈ {sorted(allowed)} (tu ești '{user_scope}')."},
        status_code=403,
    )
