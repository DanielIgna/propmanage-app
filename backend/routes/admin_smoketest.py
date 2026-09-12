"""PropManage — Admin Smoke Test (E2E health probe)

Runs a sequence of real API calls against the live backend to verify the
critical user flow is healthy (login → me → create property → list → delete
→ logout). Results are stored in `db.smoke_test_runs` for history.

Triggered manually by admin from AI Investigator panel. Designed to be safe to
run repeatedly — uses an isolated demo client account, marks created data with
a `[SMOKE]` prefix, and cleans up after itself.
"""
import os
import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from db import db
from sub_admin_deps import require_admin_scope

logger = logging.getLogger("propmanage.admin_smoketest")
router = APIRouter(prefix="/api/admin/smoke-test", tags=["admin-smoketest"])

# Demo credentials for smoke tests. These accounts are seeded in seed.py and
# reset nightly by demo_reset.py, so a smoke test never corrupts real data.
# Default values match the seeded fixtures — override via env vars if you
# rotate the demo passwords (the seed must be updated too).
SMOKE_EMAIL = os.environ.get("SMOKE_TEST_EMAIL", "client@propmanage.io")
SMOKE_PASSWORD = os.environ.get("SMOKE_TEST_PASSWORD", "Client123!")

# Role-specific demo credentials for multi-role smoke tests.
ROLE_CREDENTIALS = {
    "client":     {"email": os.environ.get("SMOKE_CLIENT_EMAIL", "client@propmanage.io"),
                   "password": os.environ.get("SMOKE_CLIENT_PASSWORD", "Client123!")},
    "specialist": {"email": os.environ.get("SMOKE_SPECIALIST_EMAIL", "specialist@propmanage.io"),
                   "password": os.environ.get("SMOKE_SPECIALIST_PASSWORD", "Spec123!")},
    "admin":      {"email": os.environ.get("SMOKE_ADMIN_EMAIL", "admin@propmanage.io"),
                   "password": os.environ.get("SMOKE_ADMIN_PASSWORD", "Admin123!")},
    "operator":   {"email": os.environ.get("SMOKE_OPERATOR_EMAIL", "operator@propmanage.io"),
                   "password": os.environ.get("SMOKE_OPERATOR_PASSWORD", "Op123!")},
}

# Default base URL preference:
# 1. SMOKE_TEST_BASE_URL (explicit override)
# 2. http://localhost:8001 (safest — tests the backend pod itself, works in both
#    preview and production without depending on external DNS / OAuth whitelist).
# Admin can pass `?base_url=https://propmanage.ro` to test the external prod URL.
DEFAULT_BASE = (
    os.environ.get("SMOKE_TEST_BASE_URL")
    or "http://localhost:8001"
).rstrip("/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _record_step(steps: List[dict], name: str, started: float, ok: bool,
                       status_code: Optional[int] = None,
                       error: Optional[str] = None,
                       payload: Optional[dict] = None) -> None:
    duration_ms = int((time.perf_counter() - started) * 1000)
    steps.append({
        "name": name,
        "ok": ok,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "error": error,
        "payload": payload,
    })


async def _run_smoke_sequence(base_url: str) -> dict:
    """Runs the full smoke test against `base_url`. Returns a structured report."""
    steps: List[dict] = []
    run_id = str(uuid.uuid4())
    started_at = _now()
    overall_ok = True
    created_property_id: Optional[str] = None
    auth_cookie_header: Optional[str] = None  # raw "Cookie: access_token=..." value

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=15.0,
        follow_redirects=True,
    ) as cli:
        # === 1. LOGIN ===
        t = time.perf_counter()
        try:
            r = await cli.post(
                "/api/auth/login",
                json={"email": SMOKE_EMAIL, "password": SMOKE_PASSWORD},
            )
            # Extract access_token from Set-Cookie. Backend marks it Secure, which
            # blocks the cookie jar from auto-sending it back over HTTP (localhost).
            # We forward it manually via Cookie header for subsequent requests.
            token = r.cookies.get("access_token")
            ok = r.status_code == 200 and bool(token)
            if ok:
                auth_cookie_header = f"access_token={token}"
            await _record_step(
                steps, "Login (demo client)", t, ok,
                status_code=r.status_code,
                error=None if ok else (r.text[:200] if r.text else "no cookie"),
            )
            if not ok:
                overall_ok = False
                raise RuntimeError("login failed")
        except Exception as e:  # noqa: BLE001
            if not steps or steps[-1]["name"] != "Login (demo client)":
                await _record_step(steps, "Login (demo client)", t, False, error=str(e)[:200])
            overall_ok = False
            return _finalize(run_id, started_at, steps, overall_ok, base_url)

        auth_headers = {"Cookie": auth_cookie_header} if auth_cookie_header else {}

        # === 2. GET /auth/me ===
        t = time.perf_counter()
        try:
            r = await cli.get("/api/auth/me", headers=auth_headers)
            data = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and data.get("role") == "client" and data.get("email") == SMOKE_EMAIL
            await _record_step(
                steps, "GET /auth/me", t, ok,
                status_code=r.status_code,
                error=None if ok else f"unexpected response: {str(data)[:120]}",
                payload={"email": data.get("email"), "role": data.get("role")} if ok else None,
            )
            if not ok:
                overall_ok = False
        except Exception as e:  # noqa: BLE001
            await _record_step(steps, "GET /auth/me", t, False, error=str(e)[:200])
            overall_ok = False

        # === 3. CREATE PROPERTY ===
        t = time.perf_counter()
        marker = f"[SMOKE {run_id[:8]}]"
        try:
            r = await cli.post(
                "/api/properties",
                headers=auth_headers,
                json={
                    "name": f"{marker} Test Apartment",
                    "address": "Strada Test nr. 1, București",
                    "type": "apartament",
                    "surface": 65.5,
                    "rooms": 2,
                },
            )
            ok = r.status_code == 200 and bool(r.json().get("id"))
            if ok:
                created_property_id = r.json()["id"]
            await _record_step(
                steps, "POST /properties (creare apartament)", t, ok,
                status_code=r.status_code,
                error=None if ok else r.text[:200],
                payload={"id": created_property_id} if ok else None,
            )
            if not ok:
                overall_ok = False
        except Exception as e:  # noqa: BLE001
            await _record_step(steps, "POST /properties (creare apartament)", t, False, error=str(e)[:200])
            overall_ok = False

        # === 4. LIST PROPERTIES → verify it's there ===
        t = time.perf_counter()
        try:
            r = await cli.get("/api/properties", headers=auth_headers)
            items = r.json() if r.status_code == 200 else []
            found = any(p.get("id") == created_property_id for p in items) if created_property_id else False
            ok = r.status_code == 200 and (found or not created_property_id)
            await _record_step(
                steps, "GET /properties (listare + verificare)", t, ok,
                status_code=r.status_code,
                error=None if ok else f"property not in list (count={len(items)})",
                payload={"count": len(items)},
            )
            if not ok:
                overall_ok = False
        except Exception as e:  # noqa: BLE001
            await _record_step(steps, "GET /properties (listare + verificare)", t, False, error=str(e)[:200])
            overall_ok = False

        # === 5. DELETE the test property (cleanup) ===
        if created_property_id:
            t = time.perf_counter()
            try:
                r = await cli.delete(f"/api/properties/{created_property_id}", headers=auth_headers)
                ok = r.status_code in (200, 204)
                await _record_step(
                    steps, "DELETE /properties (cleanup)", t, ok,
                    status_code=r.status_code,
                    error=None if ok else r.text[:200],
                )
                if not ok:
                    overall_ok = False
            except Exception as e:  # noqa: BLE001
                await _record_step(steps, "DELETE /properties (cleanup)", t, False, error=str(e)[:200])
                overall_ok = False

        # === 6. LOGOUT ===
        t = time.perf_counter()
        try:
            r = await cli.post("/api/auth/logout", headers=auth_headers)
            ok = r.status_code in (200, 204)
            await _record_step(
                steps, "POST /auth/logout", t, ok,
                status_code=r.status_code,
                error=None if ok else r.text[:200],
            )
            if not ok:
                overall_ok = False
        except Exception as e:  # noqa: BLE001
            await _record_step(steps, "POST /auth/logout", t, False, error=str(e)[:200])
            overall_ok = False

    return _finalize(run_id, started_at, steps, overall_ok, base_url)


def _finalize(run_id: str, started_at: str, steps: list, overall_ok: bool, base_url: str) -> dict:
    total_duration_ms = sum(s.get("duration_ms", 0) for s in steps)
    return {
        "id": run_id,
        "started_at": started_at,
        "finished_at": _now(),
        "ok": overall_ok,
        "base_url": base_url,
        "total_duration_ms": total_duration_ms,
        "steps": steps,
        "passed": sum(1 for s in steps if s["ok"]),
        "failed": sum(1 for s in steps if not s["ok"]),
        "total": len(steps),
    }


@router.post("/run")
async def run_smoke_test(
    base_url: Optional[str] = Query(None, description="Override base URL (default: APP_PUBLIC_URL)"),
    user: dict = Depends(require_admin_scope("testing")),
):
    """Run the smoke test sequence and persist the result."""
    target = (base_url or DEFAULT_BASE).rstrip("/")
    logger.info(f"[SmokeTest] starting against {target} (triggered by {user.get('email')})")
    report = await _run_smoke_sequence(target)
    report["triggered_by"] = user.get("email")
    try:
        await db.smoke_test_runs.insert_one(report.copy())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SmokeTest] failed to persist run: {e}")
    logger.info(f"[SmokeTest] done — ok={report['ok']} passed={report['passed']}/{report['total']}")
    return report


@router.get("/history")
async def list_smoke_test_runs(
    limit: int = Query(20, le=100),
    user: dict = Depends(require_admin_scope("testing")),
):
    """Return last N smoke test runs (newest first)."""
    cursor = db.smoke_test_runs.find({}, {"_id": 0}).sort("started_at", -1).limit(limit)
    items = await cursor.to_list(limit)
    return {"items": items, "count": len(items)}


# ===========================================================================
# PER-ROLE SMOKE TESTS
# ===========================================================================
# Each role-specific test runs a representative flow for that user type:
# - specialist: login → marketplace → /auth/me → logout
# - operator: login → operator queue → /auth/me → logout
# - admin: login → admin stats → /auth/me → logout
# All tests are read-only (no writes) → safe to run repeatedly without cleanup.


async def _login_and_get_cookie(cli: httpx.AsyncClient, email: str, password: str,
                                steps: List[dict]) -> Optional[str]:
    """Helper: login + return Cookie header string. Returns None on failure."""
    t = time.perf_counter()
    try:
        r = await cli.post("/api/auth/login", json={"email": email, "password": password})
        token = r.cookies.get("access_token")
        ok = r.status_code == 200 and bool(token)
        await _record_step(
            steps, f"Login ({email})", t, ok,
            status_code=r.status_code,
            error=None if ok else (r.text[:200] if r.text else "no cookie"),
        )
        return f"access_token={token}" if ok else None
    except Exception as e:  # noqa: BLE001
        await _record_step(steps, f"Login ({email})", t, False, error=str(e)[:200])
        return None


async def _verify_role(cli: httpx.AsyncClient, cookie: str, expected_role: str,
                       steps: List[dict]) -> bool:
    """Helper: GET /auth/me and verify role matches expectation."""
    t = time.perf_counter()
    try:
        r = await cli.get("/api/auth/me", headers={"Cookie": cookie})
        data = r.json() if r.status_code == 200 else {}
        actual = data.get("role")
        ok = r.status_code == 200 and actual == expected_role
        await _record_step(
            steps, f"GET /auth/me (verifică rol={expected_role})", t, ok,
            status_code=r.status_code,
            error=None if ok else f"got role={actual}",
            payload={"role": actual, "email": data.get("email")} if ok else None,
        )
        return ok
    except Exception as e:  # noqa: BLE001
        await _record_step(steps, f"GET /auth/me (verifică rol={expected_role})", t, False,
                           error=str(e)[:200])
        return False


async def _logout(cli: httpx.AsyncClient, cookie: str, steps: List[dict]) -> None:
    t = time.perf_counter()
    try:
        r = await cli.post("/api/auth/logout", headers={"Cookie": cookie})
        ok = r.status_code in (200, 204)
        await _record_step(steps, "POST /auth/logout", t, ok,
                           status_code=r.status_code,
                           error=None if ok else r.text[:200])
    except Exception as e:  # noqa: BLE001
        await _record_step(steps, "POST /auth/logout", t, False, error=str(e)[:200])


async def _run_role_sequence(base_url: str, role: str) -> dict:
    """Run a role-specific smoke test sequence.

    Each role has its own representative endpoint to call after login,
    chosen to be lightweight (read-only) and high-signal (failure indicates
    a broken core flow for that role).
    """
    creds = ROLE_CREDENTIALS.get(role)
    if not creds:
        raise ValueError(f"Unknown role: {role}")

    steps: List[dict] = []
    run_id = str(uuid.uuid4())
    started_at = _now()
    overall_ok = True

    async with httpx.AsyncClient(base_url=base_url, timeout=15.0, follow_redirects=True) as cli:
        cookie = await _login_and_get_cookie(cli, creds["email"], creds["password"], steps)
        if not cookie:
            return _finalize_role(run_id, started_at, steps, False, base_url, role)

        if not await _verify_role(cli, cookie, role, steps):
            overall_ok = False

        # Role-specific representative endpoint
        role_endpoints = {
            "specialist": ("/api/marketplace/specialists", "Marketplace specialiști vizibilă"),
            "operator":   ("/api/operator/twins",          "Lista twins de operator"),
            "admin":      ("/api/admin/stats",             "Admin stats dashboard"),
            "client":     ("/api/properties",              "Lista proprietăților clientului"),
        }
        endpoint, label = role_endpoints[role]
        t = time.perf_counter()
        try:
            r = await cli.get(endpoint, headers={"Cookie": cookie})
            ok = r.status_code == 200
            payload = None
            if ok:
                data = r.json()
                if isinstance(data, list):
                    payload = {"count": len(data)}
                elif isinstance(data, dict):
                    payload = {"keys": list(data.keys())[:6]}
            await _record_step(steps, f"GET {endpoint} ({label})", t, ok,
                               status_code=r.status_code,
                               error=None if ok else r.text[:200],
                               payload=payload)
            if not ok:
                overall_ok = False
        except Exception as e:  # noqa: BLE001
            await _record_step(steps, f"GET {endpoint} ({label})", t, False,
                               error=str(e)[:200])
            overall_ok = False

        await _logout(cli, cookie, steps)

    return _finalize_role(run_id, started_at, steps, overall_ok, base_url, role)


def _finalize_role(run_id: str, started_at: str, steps: list, overall_ok: bool,
                   base_url: str, role: str) -> dict:
    return {
        "id": run_id,
        "role": role,
        "started_at": started_at,
        "finished_at": _now(),
        "ok": overall_ok,
        "base_url": base_url,
        "total_duration_ms": sum(s.get("duration_ms", 0) for s in steps),
        "steps": steps,
        "passed": sum(1 for s in steps if s["ok"]),
        "failed": sum(1 for s in steps if not s["ok"]),
        "total": len(steps),
    }


@router.post("/run-all-roles")
async def run_all_roles(
    base_url: Optional[str] = Query(None),
    user: dict = Depends(require_admin_scope("testing")),
):
    """Run smoke tests for ALL 4 roles (client, specialist, operator, admin)
    in parallel. Returns one aggregated report.
    """
    import asyncio
    target = (base_url or DEFAULT_BASE).rstrip("/")
    logger.info(f"[SmokeTest][all-roles] starting against {target}")

    # Run client variant via the existing full E2E sequence (which exercises CRUD)
    # to keep the rich smoke for that role. Others use the lighter read-only flow.
    runs = await asyncio.gather(
        _run_smoke_sequence(target),               # client full E2E (existing)
        _run_role_sequence(target, "specialist"),
        _run_role_sequence(target, "operator"),
        _run_role_sequence(target, "admin"),
    )
    # Stamp the client run with role="client" so the UI can render uniformly
    runs[0]["role"] = "client"

    overall_ok = all(r["ok"] for r in runs)
    aggregated = {
        "started_at": runs[0]["started_at"],
        "finished_at": _now(),
        "ok": overall_ok,
        "base_url": target,
        "triggered_by": user.get("email"),
        "total_duration_ms": max(r["total_duration_ms"] for r in runs),  # parallel → max
        "roles": runs,
        "summary": {
            "total_roles": len(runs),
            "passed_roles": sum(1 for r in runs if r["ok"]),
            "failed_roles": sum(1 for r in runs if not r["ok"]),
        },
    }
    # Persist individual runs so they appear in history alongside manual runs
    try:
        for r in runs:
            r_copy = r.copy()
            r_copy["triggered_by"] = f"all-roles ({user.get('email')})"
            await db.smoke_test_runs.insert_one(r_copy)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[SmokeTest][all-roles] done · {aggregated['summary']}")
    return aggregated




# ===========================================================================
# AUTO-MONITOR (APScheduler background job)
# ===========================================================================
# Runs the smoke test every N minutes and sends an email alert to ADMIN_EMAILS
# when:
#   - Status transitions OK → FAIL (immediate alert)
#   - Failures persist (1 alert every 3h cooldown to avoid spam)
# Config stored in db.smoke_test_config (singleton doc with _id="config").

DEFAULT_INTERVAL_MIN = 30
COOLDOWN_HOURS = 3


async def _get_monitor_config() -> dict:
    """Singleton config doc. Defaults to monitoring DISABLED until admin enables it."""
    cfg = await db.smoke_test_config.find_one({"_id": "config"})
    if not cfg:
        cfg = {
            "_id": "config",
            "enabled": False,
            "interval_minutes": DEFAULT_INTERVAL_MIN,
            "base_url": DEFAULT_BASE,
            "last_alert_at": None,
            "last_status": None,  # "ok" | "fail" | None
            "updated_at": _now(),
        }
        await db.smoke_test_config.insert_one(cfg)
    return cfg


async def _send_failure_alert(report: dict, prev_status: Optional[str]) -> None:
    """Email the admins. Imported lazily to avoid circular deps at module load."""
    from services import send_email  # noqa: WPS433 — lazy import is intentional
    admin_emails_raw = os.environ.get("ADMIN_EMAILS", "") or os.environ.get("ADMIN_EMAIL", "")
    recipients = [e.strip() for e in admin_emails_raw.split(",") if e.strip()]
    if not recipients:
        logger.warning("[SmokeTest][monitor] No ADMIN_EMAILS configured — skipping alert email")
        return

    is_recovery = report["ok"] and prev_status == "fail"
    if is_recovery:
        subject = "✅ PropManage Smoke Test — RECOVERED"
        intro = "Smoke test-ul a revenit la <strong>PASS</strong> după o eșuare anterioară."
        color = "#10b981"
    else:
        subject = f"🚨 PropManage Smoke Test FAILED ({report['failed']}/{report['total']})"
        intro = (
            f"Smoke test-ul automat a detectat <strong>{report['failed']} pași eșuați</strong> "
            f"din {report['total']} pe <code>{report['base_url']}</code>."
        )
        color = "#ef4444"

    rows = ""
    for s in report.get("steps", []):
        icon = "✅" if s["ok"] else "❌"
        code = s.get("status_code") or "—"
        err = f"<div style='color:#fca5a5;font-size:11px;margin-top:4px;font-family:monospace'>{s.get('error','')[:200]}</div>" if not s["ok"] and s.get("error") else ""
        rows += (
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #292524'>"
            f"{icon} {s['name']}{err}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #292524;font-family:monospace;color:#a8a29e'>{code}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #292524;font-family:monospace;color:#a8a29e;text-align:right'>{s['duration_ms']}ms</td></tr>"
        )

    html = (
        f"<div style='font-family:Inter,sans-serif;max-width:640px;margin:0 auto;background:#0a0a0b;color:#fafaf9;padding:24px;border-radius:12px'>"
        f"<h2 style='font-family:Georgia,serif;color:{color};margin:0 0 8px'>{subject}</h2>"
        f"<p style='color:#d6d3d1;font-size:14px;line-height:1.6'>{intro}</p>"
        f"<p style='color:#a8a29e;font-size:12px'>Started: {report['started_at']} · Total: {report['total_duration_ms']}ms</p>"
        f"<table style='width:100%;border-collapse:collapse;margin:16px 0;font-size:13px;background:#1c1917;border-radius:8px;overflow:hidden'>"
        f"<thead><tr style='background:#292524'>"
        f"<th style='padding:8px 10px;text-align:left;color:#a8a29e'>Pas</th>"
        f"<th style='padding:8px 10px;text-align:left;color:#a8a29e'>HTTP</th>"
        f"<th style='padding:8px 10px;text-align:right;color:#a8a29e'>Durată</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
        f"<p style='color:#78716c;font-size:11px;text-align:center'>"
        f"Acest email este trimis automat de <strong>PropManage AI Investigator</strong> când Smoke Test-ul detectează probleme. "
        f"Poți dezactiva monitorul din AI Investigator → Smoke Test E2E → toggle 'Monitorizare automată'.</p>"
        f"</div>"
    )
    try:
        for r in recipients:
            await send_email(r, subject, html)
        logger.info(f"[SmokeTest][monitor] Alert email sent to {len(recipients)} admin(s)")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SmokeTest][monitor] failed to send alert: {e}")


async def run_smoke_test_monitor_tick() -> Optional[dict]:
    """Scheduler tick: runs smoke test, persists, and conditionally alerts.

    Returns the report dict, or None if monitor is disabled.
    """
    cfg = await _get_monitor_config()
    if not cfg.get("enabled"):
        return None

    base_url = (cfg.get("base_url") or DEFAULT_BASE).rstrip("/")
    logger.info(f"[SmokeTest][monitor] tick — testing {base_url}")
    report = await _run_smoke_sequence(base_url)
    report["triggered_by"] = "auto_monitor"
    try:
        await db.smoke_test_runs.insert_one(report.copy())
    except Exception:  # noqa: BLE001
        pass

    prev_status = cfg.get("last_status")
    new_status = "ok" if report["ok"] else "fail"
    last_alert_at = cfg.get("last_alert_at")

    # Orchestrator signal — auto-creates a QA session with the failed steps
    if not report["ok"]:
        try:
            from orchestrator.engine import emit_signal
            failed_steps = [
                {"name": s.get("name"), "error": (s.get("error") or "")[:300], "status_code": s.get("status_code")}
                for s in report.get("steps", []) if not s.get("ok")
            ]
            await emit_signal("smoke_fail", {
                "failed": report.get("failed"),
                "total": report.get("total"),
                "base_url": base_url,
                "steps": failed_steps,
            })
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[SmokeTest][monitor] orchestrator signal failed: {e}")

    # Decide whether to send an alert
    should_alert = False
    if not report["ok"]:
        # Always alert on first failure after OK (immediate notification)
        if prev_status != "fail":
            should_alert = True
        # Otherwise, alert with cooldown to avoid spamming
        elif last_alert_at:
            try:
                last_dt = datetime.fromisoformat(last_alert_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - last_dt > timedelta(hours=COOLDOWN_HOURS):
                    should_alert = True
            except Exception:  # noqa: BLE001
                should_alert = True
        else:
            should_alert = True
    elif report["ok"] and prev_status == "fail":
        # Recovery notification
        should_alert = True

    if should_alert:
        await _send_failure_alert(report, prev_status)

    await db.smoke_test_config.update_one(
        {"_id": "config"},
        {"$set": {
            "last_status": new_status,
            "last_run_at": report["finished_at"],
            "last_alert_at": _now() if should_alert else last_alert_at,
            "updated_at": _now(),
        }},
    )
    return report


# ===========================================================================
# MONITOR CONFIG ENDPOINTS
# ===========================================================================


@router.get("/monitor/config")
async def get_monitor_config(user: dict = Depends(require_admin_scope("testing"))):
    """Return current monitor config (enabled, interval, last status)."""
    cfg = await _get_monitor_config()
    cfg.pop("_id", None)
    return cfg


@router.post("/monitor/config")
async def update_monitor_config(
    payload: dict = Body(...),
    user: dict = Depends(require_admin_scope("testing")),
):
    """Enable/disable the auto monitor or change its interval / target URL."""
    updates: dict = {}
    if "enabled" in payload:
        updates["enabled"] = bool(payload["enabled"])
    if "interval_minutes" in payload:
        try:
            iv = int(payload["interval_minutes"])
            if iv < 5 or iv > 1440:
                raise HTTPException(400, "interval_minutes must be between 5 and 1440")
            updates["interval_minutes"] = iv
        except (TypeError, ValueError):
            raise HTTPException(400, "interval_minutes must be an integer") from None
    if "base_url" in payload:
        url = (payload["base_url"] or "").strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(400, "base_url must start with http:// or https://")
        updates["base_url"] = url or DEFAULT_BASE
    if not updates:
        raise HTTPException(400, "Nothing to update")
    updates["updated_at"] = _now()
    updates["updated_by"] = user.get("email")
    await db.smoke_test_config.update_one({"_id": "config"}, {"$set": updates}, upsert=True)
    cfg = await _get_monitor_config()
    cfg.pop("_id", None)
    logger.info(f"[SmokeTest][monitor] config updated by {user.get('email')}: {updates}")
    return cfg
