"""PropManage — Healthcheck service (integration probes).

Extracted from routes/admin_healthcheck.py to break the circular dependency
admin_briefing_digest.py ↔ routes/admin_healthcheck.py. Route handlers and the
morning-briefing digest both import `compute_healthcheck_report` from here.

Checks: MongoDB ping, Emergent LLM Key, Resend/SendGrid, Stripe, Google OAuth,
VAPID push keys, admin alert emails.
"""
import os
import time
import logging
from datetime import datetime, timezone

import httpx

from db import db, client as mongo_client

logger = logging.getLogger("propmanage.healthcheck_service")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(name: str, started: float, ok: bool, status: str = "",
           detail: str = "", severity: str = "high") -> dict:
    """Build a normalized check result.

    Severity: 'high' (critical — app won't work), 'warning' (degraded),
    'info' (optional integration).
    """
    return {
        "name": name,
        "ok": ok,
        "status": status,        # short label: "ok", "missing_key", "down", etc.
        "detail": detail,         # human-readable explanation
        "severity": severity,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }


# ============================================================================
# INDIVIDUAL PROBES
# ============================================================================


async def _probe_mongo() -> dict:
    t = time.perf_counter()
    try:
        await mongo_client.admin.command("ping")
        # Count a known collection to confirm read access too
        users_count = await db.users.estimated_document_count()
        return _check(
            "MongoDB",
            t,
            ok=True,
            status="ok",
            detail=f"Conectat · {users_count} useri în DB",
            severity="high",
        )
    except Exception as e:  # noqa: BLE001
        return _check("MongoDB", t, ok=False, status="down",
                      detail=f"Eroare conexiune: {str(e)[:200]}", severity="high")


async def _probe_emergent_llm() -> dict:
    """Light verification: confirm key is present and has expected format.

    We avoid making an actual LLM call here to save credits — `Smoke Test`
    can cover live LLM calls separately if needed.
    """
    t = time.perf_counter()
    key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not key:
        return _check("Emergent LLM Key", t, ok=False, status="missing_key",
                      detail="EMERGENT_LLM_KEY nu e configurată în .env",
                      severity="high")
    if not key.startswith("sk-emergent-"):
        return _check("Emergent LLM Key", t, ok=False, status="invalid_format",
                      detail=f"Cheia nu începe cu 'sk-emergent-' (primele 12 char: {key[:12]}...)",
                      severity="high")
    return _check("Emergent LLM Key", t, ok=True, status="ok",
                  detail=f"Configurată corect (sk-emergent-***{key[-4:]})",
                  severity="high")


async def _probe_email_provider() -> dict:
    """Verify Resend or SendGrid is configured. Doesn't send a real email."""
    t = time.perf_counter()
    resend = (os.environ.get("RESEND_API_KEY") or "").strip()
    sendgrid = (os.environ.get("SENDGRID_API_KEY") or "").strip()

    if resend:
        if not resend.startswith("re_"):
            return _check("Email (Resend)", t, ok=False, status="invalid_format",
                          detail="RESEND_API_KEY nu începe cu 're_'",
                          severity="warning")
        # Light verify: call /domains endpoint to ensure key authenticates
        try:
            async with httpx.AsyncClient(timeout=5.0) as cli:
                r = await cli.get(
                    "https://api.resend.com/domains",
                    headers={"Authorization": f"Bearer {resend}"},
                )
                if r.status_code == 200:
                    domains = r.json().get("data", [])
                    verified = sum(1 for d in domains if d.get("status") == "verified")
                    return _check("Email (Resend)", t, ok=True, status="ok",
                                  detail=f"Conectat · {verified}/{len(domains)} domenii verificate",
                                  severity="warning")
                return _check("Email (Resend)", t, ok=False, status="auth_failed",
                              detail=f"API key invalid sau revocat (HTTP {r.status_code})",
                              severity="warning")
        except Exception as e:  # noqa: BLE001
            return _check("Email (Resend)", t, ok=False, status="unreachable",
                          detail=f"Resend API unreachable: {str(e)[:120]}",
                          severity="warning")

    if sendgrid:
        if not sendgrid.startswith("SG."):
            return _check("Email (SendGrid)", t, ok=False, status="invalid_format",
                          detail="SENDGRID_API_KEY nu începe cu 'SG.'",
                          severity="warning")
        return _check("Email (SendGrid)", t, ok=True, status="ok",
                      detail="Configurat (SG.***)", severity="warning")

    # No provider configured → emails go to console/db log fallback
    return _check("Email Provider", t, ok=False, status="not_configured",
                  detail="Nici Resend nici SendGrid nu sunt configurate. Emailurile sunt logate în DB, nu trimise.",
                  severity="warning")


async def _probe_stripe() -> dict:
    """Verify Stripe API key by calling /v1/balance (lightweight, no charge)."""
    t = time.perf_counter()
    key = (os.environ.get("STRIPE_API_KEY") or "").strip()
    if not key:
        return _check("Stripe", t, ok=False, status="missing_key",
                      detail="STRIPE_API_KEY nu e configurată", severity="warning")
    if key == "sk_test_emergent" or key.startswith("sk_test_emergent"):
        return _check("Stripe", t, ok=True, status="demo_mode",
                      detail="Cheia 'sk_test_emergent' — Stripe în mod demo (no real charges)",
                      severity="warning")
    if not (key.startswith("sk_test_") or key.startswith("sk_live_")):
        return _check("Stripe", t, ok=False, status="invalid_format",
                      detail="Cheia nu începe cu 'sk_test_' sau 'sk_live_'",
                      severity="warning")
    try:
        async with httpx.AsyncClient(timeout=5.0) as cli:
            r = await cli.get(
                "https://api.stripe.com/v1/balance",
                headers={"Authorization": f"Bearer {key}"},
            )
            if r.status_code == 200:
                mode = "LIVE" if key.startswith("sk_live_") else "TEST"
                return _check("Stripe", t, ok=True, status="ok",
                              detail=f"Conectat · mod {mode}", severity="warning")
            return _check("Stripe", t, ok=False, status="auth_failed",
                          detail=f"Stripe API rejected key (HTTP {r.status_code})",
                          severity="warning")
    except Exception as e:  # noqa: BLE001
        return _check("Stripe", t, ok=False, status="unreachable",
                      detail=f"Stripe API unreachable: {str(e)[:120]}",
                      severity="warning")


async def _probe_google_oauth() -> dict:
    """Verify Google OAuth discovery endpoint is reachable."""
    t = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as cli:
            r = await cli.get(
                "https://accounts.google.com/.well-known/openid-configuration",
            )
            if r.status_code == 200 and "authorization_endpoint" in r.json():
                return _check("Google OAuth", t, ok=True, status="ok",
                              detail="Google OAuth discovery accesibil",
                              severity="info")
            return _check("Google OAuth", t, ok=False, status="bad_response",
                          detail=f"Răspuns neașteptat (HTTP {r.status_code})",
                          severity="info")
    except Exception as e:  # noqa: BLE001
        return _check("Google OAuth", t, ok=False, status="unreachable",
                      detail=f"Google OAuth unreachable: {str(e)[:120]}",
                      severity="info")


async def _probe_vapid_push() -> dict:
    """Verify VAPID keys for web push notifications."""
    t = time.perf_counter()
    pub = (os.environ.get("VAPID_PUBLIC_KEY") or "").strip()
    pem = (os.environ.get("VAPID_PRIVATE_KEY_PEM") or "").strip()
    if not pub or not pem:
        return _check("VAPID Push Notifications", t, ok=False, status="missing_keys",
                      detail="VAPID_PUBLIC_KEY sau VAPID_PRIVATE_KEY_PEM lipsă",
                      severity="info")
    if not pem.startswith("-----BEGIN"):
        return _check("VAPID Push Notifications", t, ok=False, status="invalid_pem",
                      detail="VAPID_PRIVATE_KEY_PEM nu pare format PEM valid",
                      severity="info")
    return _check("VAPID Push Notifications", t, ok=True, status="ok",
                  detail=f"Configurate (public: {pub[:16]}...)",
                  severity="info")


async def _probe_admin_emails() -> dict:
    """Verify ADMIN_EMAILS / ADMIN_EMAIL is configured for alerts."""
    t = time.perf_counter()
    emails = (os.environ.get("ADMIN_EMAILS") or os.environ.get("ADMIN_EMAIL") or "").strip()
    if not emails:
        return _check("Admin Emails (alerts)", t, ok=False, status="missing",
                      detail="Nici ADMIN_EMAILS nici ADMIN_EMAIL configurate. Alertele smoke-test nu vor avea destinatari.",
                      severity="warning")
    count = len([e for e in emails.split(",") if e.strip()])
    return _check("Admin Emails (alerts)", t, ok=True, status="ok",
                  detail=f"{count} destinatar(i) pentru alerte", severity="warning")


# ============================================================================
# AGGREGATOR
# ============================================================================


async def compute_healthcheck_report() -> dict:
    """Internal: run all probes and return structured report. No auth, safe for scheduler use."""
    import asyncio
    started = _now()
    started_t = time.perf_counter()

    results = await asyncio.gather(
        _probe_mongo(),
        _probe_emergent_llm(),
        _probe_email_provider(),
        _probe_stripe(),
        _probe_google_oauth(),
        _probe_vapid_push(),
        _probe_admin_emails(),
        return_exceptions=False,
    )

    total_duration_ms = int((time.perf_counter() - started_t) * 1000)
    critical_failed = sum(1 for r in results if not r["ok"] and r["severity"] == "high")
    warnings_failed = sum(1 for r in results if not r["ok"] and r["severity"] == "warning")
    info_failed = sum(1 for r in results if not r["ok"] and r["severity"] == "info")
    overall_ok = critical_failed == 0

    return {
        "started_at": started,
        "finished_at": _now(),
        "ok": overall_ok,
        "total_duration_ms": total_duration_ms,
        "checks": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["ok"]),
            "critical_failed": critical_failed,
            "warnings_failed": warnings_failed,
            "info_failed": info_failed,
        },
    }
