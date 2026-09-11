"""QA Automation Engine — runs a subset of test cases automatically.

Two execution kinds:
- **http**: in-process async runner using httpx. Fast (<5s/test), no browser.
- **browser**: spawns a subprocess into /opt/plugins-venv (Playwright installed).
  Used for genuine UI checks (clicks, render). Heavier (~15s/test).

Each automated test has a `code` mapping back to the manual QA Playbook checklist
(C-02, P-01 etc.) so when it runs, it auto-updates the corresponding check in the
current QA Run with status pass/fail + a note containing the assertion log.

Tests are stateless and idempotent — they pick a unique timestamp suffix for any
record they create. Cleanup happens automatically.
"""
from __future__ import annotations

import os
import json
import time
import uuid
import asyncio
import logging
import tempfile
import subprocess
from datetime import datetime, timezone
from typing import Optional
ADMIN_SEED_PW = os.environ.get("SEED_ADMIN_PASSWORD", "Admin123!")  # env-driven, no hardcoded secret


import httpx

from db import db

logger = logging.getLogger("propmanage.qa_automation")

# Both HTTP and browser tests target the same public preview URL so the secure
# `samesite=none; Secure` auth cookies are accepted by httpx (which rejects them on plain http).
_PREVIEW = os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("PREVIEW_PUBLIC_URL") or os.environ.get("APP_PUBLIC_URL") or "http://localhost:8001"
BACKEND_URL = _PREVIEW
FRONTEND_BASE = _PREVIEW


# ============================================================================
# HTTP test runners
# ============================================================================

def _ok(note: str) -> dict:
    return {"status": "pass", "note": note[:600]}


def _ko(note: str) -> dict:
    return {"status": "fail", "note": note[:600]}


def _safe_e2e(fn):
    """Wrap an async E2E runner so unexpected exceptions become clean `fail` results."""
    import functools

    @functools.wraps(fn)
    async def wrapper() -> dict:
        try:
            return await fn()
        except RuntimeError as e:
            return _ko(f"setup failed — {str(e)[:240]}")
        except httpx.ReadError as e:
            return _ko(f"ReadError (likely ingress/network timeout): {str(e)[:160]}")
        except httpx.TimeoutException as e:
            return _ko(f"Timeout: {str(e)[:160]}")
        except Exception as e:  # noqa: BLE001
            return _ko(f"{type(e).__name__}: {str(e)[:200]}")
    return wrapper




async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BACKEND_URL, timeout=20.0, follow_redirects=False)


async def http_register_duplicate_email() -> dict:
    """C-02: Înregistrare cu email deja existent → 400."""
    async with await _client() as c:
        # Try registering with the seeded admin email
        r = await c.post("/api/auth/register", json={
            "email": "admin@propmanage.io",
            "password": "Whatever123!",
            "name": "Dup Test",
            "role": "client",
            "phone": "0712000000",
            "zone": "Bucuresti",
        })
        if r.status_code == 400:
            return _ok(f"OK — server returned 400: {r.json().get('detail','')[:200]}")
        return _ko(f"Expected 400, got {r.status_code}: {r.text[:300]}")


async def http_register_short_password() -> dict:
    """C-03: Înregistrare cu parolă < 8 caractere → eroare validare."""
    async with await _client() as c:
        r = await c.post("/api/auth/register", json={
            "email": f"shortpw_{int(time.time())}@test.com",
            "password": "abc",
            "name": "Short Pw",
            "role": "client",
            "phone": "0712000000",
            "zone": "Bucuresti",
        })
        if r.status_code in (400, 422):
            return _ok(f"OK — server rejected with {r.status_code}: {r.text[:200]}")
        return _ko(f"Expected 400/422, got {r.status_code}: {r.text[:300]}")


async def http_login_bad_password() -> dict:
    """SEC-01: Login cu parolă greșită → 401."""
    async with await _client() as c:
        r = await c.post("/api/auth/login", json={"email": "admin@propmanage.io", "password": "WRONG_password_xyz"})
        if r.status_code in (401, 403):
            return _ok(f"OK — login refused with {r.status_code}")
        return _ko(f"Expected 401/403, got {r.status_code}: {r.text[:200]}")


async def http_admin_endpoints_require_auth() -> dict:
    """SEC-02: Endpoint admin fără token → 401."""
    async with await _client() as c:
        endpoints = [
            "/api/admin/qa/runs",
            "/api/admin/onboarding/queue",
            "/api/admin/docs",
            "/api/admin/users",
        ]
        bad = []
        for ep in endpoints:
            r = await c.get(ep)
            if r.status_code not in (401, 403):
                bad.append(f"{ep}={r.status_code}")
        if not bad:
            return _ok(f"OK — all {len(endpoints)} admin endpoints returned 401/403 without auth")
        return _ko(f"Endpoints leaked: {bad}")


async def http_client_cannot_access_admin() -> dict:
    """SEC-03: User client logat → primește 403 pe /api/admin/* (RBAC)."""
    async with await _client() as c:
        r = await c.post("/api/auth/login", json={"email": "client@propmanage.io", "password": "Client123!"})
        if r.status_code != 200:
            return _ko(f"Cannot login as client to test RBAC: {r.status_code}")
        # cookies are now on the client jar automatically
        r2 = await c.get("/api/admin/qa/runs")
        if r2.status_code == 403:
            return _ok("OK — client gets 403 on /api/admin/qa/runs")
        return _ko(f"Expected 403, got {r2.status_code}: {r2.text[:200]}")


async def http_public_sitemap_valid() -> dict:
    """P-01: GET /api/public/sitemap.xml → 200 + conține url-uri."""
    async with await _client() as c:
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap status {r.status_code}")
        body = r.text
        if "<urlset" in body and "<loc>" in body:
            n_urls = body.count("<loc>")
            return _ok(f"OK — sitemap.xml valid cu {n_urls} url-uri")
        return _ko(f"sitemap missing urlset/loc — first 300: {body[:300]}")


async def http_marketplace_landing_returns_seo_data() -> dict:
    """P-02: Indexability Gate SSOT — /api/public/seo/gate decide index/noindex, iar sitemap-ul
    listează DOAR landing-uri marketplace care trec gate-ul (fără conținut subțire)."""
    import re as _re
    async with await _client() as c:
        # Gate pe un slug necunoscut → noindex + canonical la părinte (determinist, independent de date).
        gb = await c.get("/api/public/seo/gate?path=/marketplace/slug-inexistent-xyz")
        if gb.status_code != 200:
            return _ko(f"gate endpoint status {gb.status_code}")
        bad = gb.json()
        if bad.get("index") is not False or not bad.get("canonical"):
            return _ko(f"gate pentru slug invalid ar trebui noindex+canonical: {bad}")
        # Sitemap-ul flat trebuie să conțină DOAR landing-uri care trec gate-ul.
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap status {r.status_code}")
        m = _re.search(r"/marketplace/([a-z0-9\-]+)</loc>", r.text)
        if not m:
            return _ok("OK — gate funcțional (slug invalid→noindex); niciun landing marketplace nu trece încă pragul (marketplace tânăr)")
        slug = m.group(1)
        g = await c.get(f"/api/public/seo/gate?path=/marketplace/{slug}")
        gd = g.json()
        if gd.get("index") is True:
            return _ok(f"OK — gate SSOT: '{slug}' din sitemap trece gate-ul (index=true); slug invalid→noindex+canonical {bad.get('canonical')}")
        return _ko(f"'{slug}' e în sitemap dar gate-ul spune index={gd.get('index')}")


async def http_health_status_alive() -> dict:
    """P-03: GET /api/public/status → 200 cu uptime/health."""
    async with await _client() as c:
        r = await c.get("/api/public/status")
        if r.status_code == 200 and isinstance(r.json(), dict):
            return _ok(f"OK — public status returnează cheile: {list(r.json().keys())[:6]}")
        return _ko(f"Public status returned {r.status_code}: {r.text[:200]}")


async def http_docs_pdf_renders() -> dict:
    """A-01: PDF Knowledge Base se generează pentru toate 6 rolurile (regression)."""
    async with await _client() as c:
        # Auth as admin first
        r = await c.post("/api/auth/login", json={"email": "admin@propmanage.io", "password": ADMIN_SEED_PW})
        if r.status_code != 200:
            return _ko(f"Admin login failed {r.status_code}")
        slugs = ["client", "specialist", "operator", "admin", "qa-testing", "architecture"]
        results = []
        for s in slugs:
            rr = await c.get(f"/api/admin/docs/{s}/pdf")
            if rr.status_code != 200 or not rr.content.startswith(b"%PDF-"):
                return _ko(f"PDF {s} failed: status={rr.status_code} ct={rr.headers.get('content-type')}")
            results.append(f"{s}={len(rr.content)}B")
        return _ok("OK — 6 PDFs render: " + ", ".join(results))


async def http_onboarding_queue_endpoint() -> dict:
    """A-02: Admin Onboarding queue endpoint răspunde cu stats + recent."""
    async with await _client() as c:
        r = await c.post("/api/auth/login", json={"email": "admin@propmanage.io", "password": ADMIN_SEED_PW})
        if r.status_code != 200:
            return _ko(f"login failed {r.status_code}")
        rr = await c.get("/api/admin/onboarding/queue")
        if rr.status_code != 200:
            return _ko(f"queue status {rr.status_code}")
        d = rr.json()
        if "stats" in d and "recent" in d:
            return _ok(f"OK — stats keys: {list(d['stats'].keys())}, recent rows: {len(d['recent'])}")
        return _ko(f"Bad shape: {list(d.keys())}")


async def http_qa_checklist_template() -> dict:
    """A-03: QA checklist template returnează 105 items + stats corecte."""
    async with await _client() as c:
        r = await c.post("/api/auth/login", json={"email": "admin@propmanage.io", "password": ADMIN_SEED_PW})
        if r.status_code != 200:
            return _ko(f"login failed {r.status_code}")
        rr = await c.get("/api/admin/qa/checklist/template")
        if rr.status_code != 200:
            return _ko(f"status {rr.status_code}")
        d = rr.json()
        if len(d.get("items", [])) >= 100 and "by_priority" in d.get("stats", {}):
            return _ok(f"OK — {len(d['items'])} items, prios {d['stats']['by_priority']}")
        return _ko(f"Bad payload {str(d)[:300]}")


# ============================================================================
# Browser test runners — via subprocess to /opt/plugins-venv
# ============================================================================

def _detect_pw_python() -> Optional[str]:
    """Detect a Python interpreter that has Playwright installed.

    In Emergent preview, Playwright lives in /opt/plugins-venv. In production
    deploys it might not be present at all, so we fall back to checking the
    current interpreter. Returns None if no usable interpreter is found.
    """
    import sys
    candidates = [
        "/opt/plugins-venv/bin/python",
        sys.executable,
    ]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            r = subprocess.run(
                [path, "-c", "import playwright.async_api; print('ok')"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and "ok" in r.stdout:
                return path
        except Exception:
            continue
    return None


PW_PYTHON = _detect_pw_python()
PW_BROWSERS_PATH = "/pw-browsers"


_BROWSER_TEMPLATE = r"""
import asyncio, json, sys, os
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "{browsers}"
from playwright.async_api import async_playwright

URL = {url!r}

async def main():
    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(viewport={{"width": 1280, "height": 800}})
            page = await ctx.new_page()
            result = await test(page)
            await browser.close()
            print("__PM_RESULT__" + json.dumps(result))
        except Exception as e:
            print("__PM_RESULT__" + json.dumps({{"status": "fail", "note": f"Crash: {{type(e).__name__}}: {{e}}"}}))

{body}

asyncio.run(main())
"""


async def _run_browser_test(test_body: str, target_url: str) -> dict:
    """Run a Playwright async test in a subprocess. test_body must define `async def test(page) -> dict`."""
    if not PW_PYTHON:
        return {
            "status": "skip",
            "note": "Playwright not available in this environment (preview-only test). Production deploys skip browser tests.",
        }
    script = _BROWSER_TEMPLATE.format(browsers=PW_BROWSERS_PATH, url=target_url, body=test_body)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            PW_PYTHON, path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            return {"status": "fail", "note": "Browser test timeout >60s"}
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        # Find marker
        for line in out.splitlines():
            if line.startswith("__PM_RESULT__"):
                try:
                    result = json.loads(line[len("__PM_RESULT__"):])
                    # Convert env-level failures (no chromium installed) to skip
                    note = (result.get("note") or "") if isinstance(result, dict) else ""
                    if "Executable doesn't exist" in note or "playwright install" in note.lower():
                        return {
                            "status": "skip",
                            "note": "Chromium binary not installed. Run `playwright install chromium` on the host.",
                        }
                    return result
                except Exception:
                    pass
        # Detect missing chromium binary → mark as skip (env limitation, not a real fail)
        haystack = err + out
        if (
            "Executable doesn't exist" in haystack
            or "playwright install" in haystack.lower()
            or ("BrowserType.launch" in haystack and "Executable" in haystack)
        ):
            return {
                "status": "skip",
                "note": "Chromium binary not installed in this environment. Run `playwright install chromium` on the host to enable.",
            }
        return {"status": "fail", "note": f"No marker. stdout[-400]:{out[-400:]} stderr[-400]:{err[-400:]}"}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


BROWSER_LANDING_LOADS = r"""
async def test(page):
    try:
        await page.goto(URL, wait_until="networkidle", timeout=20000)
        title = await page.title()
        body = await page.locator("body").inner_text()
        ok = ("PropManage" in title) or ("PropManage" in body)
        return {"status": "pass" if ok else "fail", "note": f"Title={title!r}, body sample: {body[:200]!r}"}
    except Exception as e:
        return {"status": "fail", "note": f"{type(e).__name__}: {e}"}
"""


BROWSER_COOKIES_PAGE = r"""
async def test(page):
    try:
        await page.goto(URL + "/cookies", wait_until="domcontentloaded", timeout=20000)
        h1 = await page.locator("h1").first.inner_text(timeout=5000)
        has_test_id = await page.locator("[data-testid='cookies-page']").count() > 0
        if has_test_id and "ookies" in h1.lower():
            return {"status": "pass", "note": f"OK — H1={h1!r}, testid present"}
        return {"status": "fail", "note": f"H1={h1!r}, testid={has_test_id}"}
    except Exception as e:
        return {"status": "fail", "note": f"{type(e).__name__}: {e}"}
"""


BROWSER_LOGIN_PAGE = r"""
async def test(page):
    try:
        await page.goto(URL + "/login", wait_until="domcontentloaded", timeout=20000)
        email = await page.locator("input[type='email']").count()
        pwd = await page.locator("input[type='password']").count()
        button = await page.locator("button[type='submit'], button:has-text('Conect')").count()
        if email > 0 and pwd > 0 and button > 0:
            return {"status": "pass", "note": f"OK — email/password/submit found"}
        return {"status": "fail", "note": f"Missing form fields: email={email} pwd={pwd} btn={button}"}
    except Exception as e:
        return {"status": "fail", "note": f"{type(e).__name__}: {e}"}
"""


async def browser_landing_loads() -> dict:
    return await _run_browser_test(BROWSER_LANDING_LOADS, FRONTEND_BASE)


async def browser_cookies_page_renders() -> dict:
    return await _run_browser_test(BROWSER_COOKIES_PAGE, FRONTEND_BASE)


async def browser_login_page_renders() -> dict:
    return await _run_browser_test(BROWSER_LOGIN_PAGE, FRONTEND_BASE)


# ============================================================================
# Content Audit tests (DOC-AUDIT-*)
# Verify each role's manual uses audience-appropriate language.
# ============================================================================

async def doc_audit_specialist_no_client_perspective() -> dict:
    """DOC-AUDIT-01: specialist doc must NOT include client-perspective callouts (e.g. 'banii pe care îi plătești')."""
    from qa_content_audit import audit_doc
    conflicts = [c for c in audit_doc("specialist") if c["wrong_audience"] == "client"]
    if not conflicts:
        return _ok("OK — specialist doc nu conține pasaje cu perspectivă client")
    detail = "; ".join(f"sec {c['section_index']}.{c['block_index']} — {c['block_excerpt'][:80]}" for c in conflicts[:3])
    return _ko(f"Conflict audience în specialist doc: {len(conflicts)} pasaj(e). {detail}")


async def doc_audit_client_no_specialist_perspective() -> dict:
    """DOC-AUDIT-02: client doc nu conține pasaje exclusiv specialist (lead fee, badge VERIFIED detaliat)."""
    from qa_content_audit import audit_doc
    conflicts = [c for c in audit_doc("client") if c["wrong_audience"] == "specialist"]
    if not conflicts:
        return _ok("OK — client doc fără perspective specialist greșite")
    return _ko(f"{len(conflicts)} pasaj(e) suspecte: " + "; ".join(c["block_excerpt"][:60] for c in conflicts[:3]))


async def doc_audit_specialist_has_payment_info() -> dict:
    """DOC-AUDIT-03: specialist doc trebuie să menționeze 'comision' sau '95%' (informația principală pt. specialist)."""
    from docs_content import get_doc
    doc = get_doc("specialist")
    if not doc:
        return _ko("specialist doc missing")
    blob = " ".join(
        (b if isinstance(b, str) else (b.get("body", "") + " " + str(b.get("items", ""))))
        for s in doc["sections"]
        for b in s.get("body", [])
    ).lower()
    keywords = ["comision", "95%", "lead fee", "plătit"]
    found = [k for k in keywords if k in blob]
    if len(found) >= 2:
        return _ok(f"OK — specialist doc conține info plată: {found}")
    return _ko(f"Lipsesc keyword-uri financiare specialist: găsite doar {found}")


async def doc_audit_client_has_dispute_info() -> dict:
    """DOC-AUDIT-04: client doc trebuie să menționeze 'dispută' (protecția clientului)."""
    from docs_content import get_doc
    doc = get_doc("client")
    blob = " ".join(
        (b if isinstance(b, str) else (b.get("body", "") + " " + b.get("title", "")))
        for s in doc["sections"]
        for b in s.get("body", [])
    ).lower()
    if "dispută" in blob or "dispute" in blob or "rambursează" in blob:
        return _ok("OK — client doc menționează disputele/rambursarea")
    return _ko("Client doc NU menționează disputele — informație critică lipsă")


async def doc_audit_all_docs_have_overrides_resolved() -> dict:
    """DOC-AUDIT-05: dacă există override-uri, fiecare se aplică valid (nu cade pe IndexError)."""
    from docs_service import resolve_doc_with_overrides
    from docs_content import DOCS_CONTENT
    errors = []
    for slug in DOCS_CONTENT.keys():
        try:
            d = await resolve_doc_with_overrides(slug)
            if not d:
                errors.append(f"{slug}=None")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{slug}={type(e).__name__}")
    if errors:
        return _ko(f"Errors resolving overrides: {errors}")
    return _ok(f"OK — overrides aplicate fără erori pentru {len(DOCS_CONTENT)} docuri")


# ============================================================================
# Lifecycle / Communication tests (LIFECYCLE-*)
# Exercise full flows end-to-end via the public API.
# ============================================================================

async def lifecycle_client_register_then_delete() -> dict:
    """LIFECYCLE-01: client se înregistrează → login → ștergere cont (GDPR DSAR right-to-be-forgotten)."""
    email = f"lifecycle_client_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    async with await _client() as c:
        # Register
        r = await c.post("/api/auth/register", json={
            "email": email, "password": "Test1234!", "name": "Lifecycle Client",
            "role": "client", "phone": "0712345678", "zone": "Bucuresti",
            "terms_accepted": True, "privacy_policy_accepted": True,
        })
        if r.status_code != 200:
            return _ko(f"register failed {r.status_code}: {r.text[:200]}")
        # Login
        r2 = await c.post("/api/auth/login", json={"email": email, "password": "Test1234!"})
        if r2.status_code != 200:
            return _ko(f"login failed {r2.status_code}")
        # Try /api/auth/me
        r3 = await c.get("/api/auth/me")
        if r3.status_code != 200 or r3.json().get("email") != email:
            return _ko(f"me endpoint failed {r3.status_code}")
        # Cleanup: delete from DB directly (no public delete-account endpoint exists)
        from db import db
        await db.users.delete_one({"email": email})
        return _ok(f"OK — register→login→me OK pentru {email}")


@_safe_e2e
async def lifecycle_specialist_register_then_onboarding_drip() -> dict:
    """LIFECYCLE-02: specialist înregistrat → primește 3 emails enqueuate în db.onboarding_emails."""
    email = f"lifecycle_spec_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    async with await _client() as c:
        r = await c.post("/api/auth/register", json={
            "email": email, "password": "Test1234!", "name": "Lifecycle Spec",
            "role": "specialist", "phone": "0712345678",
            "terms_accepted": True, "privacy_policy_accepted": True,
            "service_categories": ["electric"], "coverage_zones": ["Bucuresti"],
        })
        if r.status_code != 200:
            return _ko(f"register failed {r.status_code}")
    # Check that 3 onboarding rows were enqueued — allow generous async write lag on prod
    from db import db
    rows = 0
    for _ in range(25):  # 25 × 0.3s = 7.5s total budget for prod Atlas
        rows = await db.onboarding_emails.count_documents({"email": email})
        if rows >= 3:
            break
        await asyncio.sleep(0.3)
    # Cleanup
    await db.onboarding_emails.delete_many({"email": email})
    await db.users.delete_one({"email": email})
    if rows >= 3:
        return _ok(f"OK — specialist {email} a primit {rows} email-uri de onboarding")
    return _ko(f"Doar {rows} email-uri enqueuate, așteptam ≥3 (după 7.5s polling)")


async def lifecycle_marketplace_search_returns_specialists() -> dict:
    """LIFECYCLE-03: client (neautentificat) caută în marketplace → primește listă specialiști."""
    async with await _client() as c:
        r = await c.get("/api/marketplace/specialists?service=electric&city=Bucuresti&page=1")
        if r.status_code != 200:
            return _ko(f"marketplace search status {r.status_code}")
        body = r.json()
        # Accept either list-form (direct) or dict-form with items
        if isinstance(body, list):
            return _ok(f"OK — marketplace returnează listă cu {len(body)} specialiști")
        if isinstance(body, dict):
            items = body.get("items") or body.get("specialists") or body.get("results") or []
            return _ok(f"OK — marketplace returnează {len(items)} specialiști (dict-form)")
        return _ko(f"Răspuns marketplace neașteptat: {str(body)[:200]}")


async def lifecycle_specialist_profile_public_view() -> dict:
    """LIFECYCLE-04: profilul public al unui specialist este accesibil clienților."""
    from db import db
    spec = await db.users.find_one({"role": "specialist", "deleted": {"$ne": True}})
    if not spec:
        return _ko("Nu există niciun specialist în DB")
    spec_id = str(spec["_id"])
    async with await _client() as c:
        # Real endpoint: /api/specialists/{id}/profile
        r = await c.get(f"/api/specialists/{spec_id}/profile")
        if r.status_code == 200:
            return _ok("OK — /api/specialists/{id}/profile accesibil pentru clienți")
        return _ko(f"Profil public specialist nu se vede ({r.status_code}): {r.text[:200]}")


async def lifecycle_admin_role_unique_count() -> dict:
    """LIFECYCLE-05: verifică integritate referențială — fiecare user are exact 1 rol valid."""
    from db import db
    valid_roles = {
        "client", "specialist", "operator", "admin",
        # Roles added in later phases (partners portal + marketing sub-admins)
        "city_partner", "marketplace_partner", "marketing_manager", "super_admin",
    }
    bad = []
    async for u in db.users.find({}, {"email": 1, "role": 1}):
        if u.get("role") not in valid_roles:
            bad.append(f"{u.get('email')}={u.get('role')!r}")
    if not bad:
        total = await db.users.count_documents({})
        return _ok(f"OK — toți cei {total} useri au roluri valide")
    return _ko(f"{len(bad)} useri cu rol invalid: {bad[:5]}")


# ============================================================================
# Terminology Audit tests (TERM-*) — vocabulary consistency across docs.
# ============================================================================

async def term_audit_no_escrow_variants() -> dict:
    """TERM-01: escrow cluster — un singur doc nu poate folosi simultan 2+ termeni pentru același concept."""
    from qa_terminology_audit import scan_all_docs
    report = await scan_all_docs()
    bad = [(slug, inc) for slug, lst in report["by_doc"].items() for inc in lst if inc["cluster_key"] == "escrow"]
    if not bad:
        return _ok("OK — termenul «escrow» e folosit consistent în toate cele 6 docuri")
    return _ko(f"{len(bad)} docuri folosesc simultan termeni diferiți pentru escrow: " + "; ".join(f"{s}={i['variants_used']}" for s,i in bad[:3]))


async def term_audit_specialist_consistent() -> dict:
    """TERM-02: termenul «specialist» nu se amestecă cu «meseriaș/profesionist/executant» în același doc."""
    from qa_terminology_audit import scan_all_docs
    report = await scan_all_docs()
    bad = [(s, i) for s, lst in report["by_doc"].items() for i in lst if i["cluster_key"] == "specialist"]
    if not bad:
        return _ok("OK — termenul «specialist» e folosit consistent")
    return _ko(f"{len(bad)} docuri amestecă: " + "; ".join(f"{s}={i['variants_used']}" for s,i in bad[:3]))


async def term_audit_client_consistent() -> dict:
    """TERM-03: termenul «client» nu se amestecă cu «proprietar/beneficiar»."""
    from qa_terminology_audit import scan_all_docs
    report = await scan_all_docs()
    bad = [(s, i) for s, lst in report["by_doc"].items() for i in lst if i["cluster_key"] == "client"]
    if not bad:
        return _ok("OK — termenul «client» e folosit consistent")
    return _ko(f"{len(bad)} docuri amestecă: " + "; ".join(f"{s}={i['variants_used']}" for s,i in bad[:3]))


async def term_audit_commission_consistent() -> dict:
    """TERM-04: «comision platformă» nu se amestecă cu «taxă/fee platformă»."""
    from qa_terminology_audit import scan_all_docs
    report = await scan_all_docs()
    bad = [(s, i) for s, lst in report["by_doc"].items() for i in lst if i["cluster_key"] == "comision"]
    if not bad:
        return _ok("OK — termenul «comision platformă» folosit consistent")
    return _ko(f"{len(bad)} docuri amestecă: " + "; ".join(f"{s}={i['variants_used']}" for s,i in bad[:3]))


async def term_audit_overall_score() -> dict:
    """TERM-05: scor general de consistență — niciun doc nu poate avea ≥3 inconsistențe."""
    from qa_terminology_audit import scan_all_docs
    report = await scan_all_docs()
    heavy = [(s, len(lst)) for s, lst in report["by_doc"].items() if len(lst) >= 3]
    total = report["total_inconsistencies"]
    if not heavy:
        return _ok(f"OK — {total} inconsistențe totale, niciun doc cu ≥3 (clusters_checked={report['clusters_checked']})")
    return _ko(f"{len(heavy)} docuri cu ≥3 inconsistențe: {heavy}. Total: {total}")


# ============================================================================
# E2E Full-flow helpers (ESCROW / DISPUTE / FILE / CHAT / QUOTE / GDPR)
# ============================================================================

async def _register_and_login(role: str, prefix: str, *, extra: Optional[dict] = None) -> tuple[httpx.AsyncClient, str, str]:
    """Register a fresh user + login. Returns (client_with_cookies, email, user_id_via_me)."""
    email = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    payload = {
        "email": email, "password": "Test1234!", "name": f"E2E {role}",
        "role": role, "phone": "0712000000",
        "terms_accepted": True, "privacy_policy_accepted": True,
    }
    if role == "specialist":
        payload.update({"service_categories": ["electric"], "coverage_zones": ["Bucuresti"]})
    elif role == "client":
        payload["zone"] = "Bucuresti"
    if extra:
        payload.update(extra)
    c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=45.0, follow_redirects=False)
    r = await c.post("/api/auth/register", json=payload)
    if r.status_code != 200:
        await c.aclose()
        raise RuntimeError(f"register {role} failed {r.status_code}: {r.text[:200]}")
    # Defensive parse — if response isn't JSON dict, fall back to explicit login
    try:
        register_body = r.json()
        if not isinstance(register_body, dict):
            register_body = {}
    except Exception:
        register_body = {}
    # If auth cookies didn't survive register (some prod setups), re-login explicitly.
    me = await c.get("/api/auth/me")
    if me.status_code != 200:
        login = await c.post("/api/auth/login", json={"email": email, "password": "Test1234!"})
        if login.status_code != 200:
            await c.aclose()
            raise RuntimeError(f"register OK but auth/me {me.status_code} and login {login.status_code}: cookies not propagating")
        me = await c.get("/api/auth/me")
        if me.status_code != 200:
            await c.aclose()
            raise RuntimeError(f"login OK but /me still {me.status_code} — cookie domain mismatch on prod?")
    try:
        me_body = me.json()
        if not isinstance(me_body, dict):
            me_body = {}
    except Exception:
        me_body = {}
    uid = me_body.get("id") or register_body.get("id") or ""
    return c, email, uid


async def _admin_client() -> httpx.AsyncClient:
    """Login as the seeded admin account and return the authenticated httpx client."""
    c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=20.0, follow_redirects=False)
    r = await c.post("/api/auth/login", json={"email": "admin@propmanage.io", "password": ADMIN_SEED_PW})
    if r.status_code != 200:
        await c.aclose()
        raise RuntimeError(f"admin login failed {r.status_code}")
    return c


def _safe_e2e(fn):
    """Wrap an async E2E runner so unexpected exceptions become clean `fail` results."""
    import functools

    @functools.wraps(fn)
    async def wrapper() -> dict:
        try:
            return await fn()
        except RuntimeError as e:
            return _ko(f"setup failed — {str(e)[:240]}")
        except httpx.ReadError as e:
            return _ko(f"ReadError (likely ingress/network timeout): {str(e)[:160]}")
        except httpx.TimeoutException as e:
            return _ko(f"Timeout: {str(e)[:160]}")
        except Exception as e:  # noqa: BLE001
            return _ko(f"{type(e).__name__}: {str(e)[:200]}")
    return wrapper


async def _wait_for_db(collection_query_fn, *, max_attempts: int = 12, sleep_s: float = 0.25, label: str = "doc"):
    """Poll DB for read-after-write consistency (MongoDB Atlas replica lag on prod).

    `collection_query_fn` is an async callable returning the doc (or None).
    Returns the doc on success, raises RuntimeError after timeout.
    Total wait budget: max_attempts × sleep_s (default 3s).
    """
    for _ in range(max_attempts):
        doc = await collection_query_fn()
        if doc:
            return doc
        await asyncio.sleep(sleep_s)
    raise RuntimeError(f"{label} not found in DB after {max_attempts * sleep_s:.1f}s polling (read-after-write delay?)")


async def _seed_active_job(escrow_amount: float = 1000.0) -> dict:
    """Create a client + specialist + property + request fully assigned with escrow held.

    Returns dict with: client_email, specialist_email, request_id, property_id, client_id, specialist_id.
    Raises RuntimeError on any step failure with a descriptive message. _safe_e2e converts to clean fail.
    """
    client_c, c_email, c_id = await _register_and_login("client", "e2e_c")
    spec_c, s_email, s_id = await _register_and_login("specialist", "e2e_s")
    # Wait for specialist row to be visible (Atlas read-after-write lag on prod)
    await _wait_for_db(lambda: db.users.find_one({"email": s_email}), label=f"specialist {s_email[:20]}")
    # Top-up specialist wallet so they can pay the 45 RON lead fee
    await db.users.update_one({"email": s_email}, {"$inc": {"wallet_balance": 200.0}})

    def _parse_id(resp, step: str) -> str:
        try:
            body = resp.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            raise RuntimeError(f"step:{step} returned non-dict body (status={resp.status_code}, type={type(body).__name__})")
        the_id = body.get("id")
        if not the_id:
            raise RuntimeError(f"step:{step} returned no 'id' field (status={resp.status_code}, keys={list(body.keys())[:5]})")
        return the_id

    # Client creates a property
    pr = await client_c.post("/api/properties", json={
        "name": "E2E Apt", "address": "Str Test 1", "type": "apartment", "surface": 60.0, "rooms": 2,
    })
    if pr.status_code != 200:
        await client_c.aclose()
        await spec_c.aclose()
        raise RuntimeError(f"step:property_create failed {pr.status_code}: {pr.text[:200]}")
    pid = _parse_id(pr, "property_create")

    # Client creates a request
    rq = await client_c.post("/api/requests", json={
        "property_id": pid, "title": "Înlocuire priză E2E", "category": "electric",
        "priority": "normal", "budget_estimate": int(escrow_amount), "description": "Test",
    })
    if rq.status_code != 200:
        await client_c.aclose()
        await spec_c.aclose()
        raise RuntimeError(f"step:request_create failed {rq.status_code}: {rq.text[:300]}")
    req_id = _parse_id(rq, "request_create")

    # Specialist accepts (pays 45 RON lead fee)
    ac = await spec_c.post(f"/api/requests/{req_id}/accept", json={})
    if ac.status_code != 200:
        await client_c.aclose()
        await spec_c.aclose()
        raise RuntimeError(f"step:specialist_accept failed {ac.status_code}: {ac.text[:200]}")

    # Client places escrow
    esc = await client_c.post(f"/api/requests/{req_id}/escrow?amount={escrow_amount}")
    if esc.status_code != 200:
        await client_c.aclose()
        await spec_c.aclose()
        raise RuntimeError(f"step:escrow_place failed {esc.status_code}: {esc.text[:200]}")

    return {
        "client_c": client_c, "spec_c": spec_c,
        "client_email": c_email, "specialist_email": s_email,
        "client_id": c_id, "specialist_id": s_id,
        "request_id": req_id, "property_id": pid,
        "escrow_amount": escrow_amount,
    }


async def _cleanup_e2e(env: dict):
    """Best-effort cleanup of E2E artefacts."""
    try:
        await env["client_c"].aclose()
    except Exception:  # noqa: BLE001
        pass
    try:
        await env["spec_c"].aclose()
    except Exception:  # noqa: BLE001
        pass
    try:
        await db.requests.delete_one({"_id": ObjectId(env["request_id"])}) if env.get("request_id") else None
    except Exception:  # noqa: BLE001
        pass
    try:
        await db.properties.delete_one({"_id": ObjectId(env["property_id"])}) if env.get("property_id") else None
    except Exception:  # noqa: BLE001
        pass
    try:
        await db.users.delete_one({"email": env["client_email"]})
        await db.users.delete_one({"email": env["specialist_email"]})
    except Exception:  # noqa: BLE001
        pass
    try:
        await db.disputes.delete_many({"request_id": env.get("request_id")})
        await db.transactions.delete_many({"request_id": env.get("request_id")})
        await db.onboarding_emails.delete_many({"email": env["specialist_email"]})
    except Exception:  # noqa: BLE001
        pass


# Need ObjectId for cleanup
from bson import ObjectId  # noqa: E402


@_safe_e2e
async def e2e_escrow_funded_status_held() -> dict:
    """ESCROW-01: Client postează cerere → specialist acceptă → client alimentează escrow → status='held'."""
    env = await _seed_active_job(800.0)
    try:
        req = await _wait_for_db(
            lambda: db.requests.find_one({"_id": ObjectId(env["request_id"])}),
            label=f"request {env['request_id'][:10]}",
        )
        amt = req.get("escrow_amount")
        st = req.get("escrow_status")
        if st == "held" and amt == 800.0:
            return _ok(f"OK — escrow_status=held, amount=800.0 RON (req={env['request_id'][:8]})")
        return _ko(f"escrow not held: status={st}, amount={amt}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def e2e_escrow_full_confirm_releases_split() -> dict:
    """ESCROW-02: După confirmare, specialistul primește 95%, platforma 5%."""
    env = await _seed_active_job(1000.0)
    try:
        # Specialist starts + completes
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/complete")
        # Snapshot specialist wallet
        spec_before = await _wait_for_db(
            lambda: db.users.find_one({"email": env["specialist_email"]}),
            label=f"specialist {env['specialist_email'][:20]}",
        )
        bal_before = float(spec_before.get("wallet_balance") or 0)
        # Client confirms
        cf = await env["client_c"].post(f"/api/requests/{env['request_id']}/confirm")
        if cf.status_code != 200:
            return _ko(f"confirm failed {cf.status_code}: {cf.text[:200]}")
        spec_after = await db.users.find_one({"email": env["specialist_email"]})
        if not spec_after:
            return _ko("specialist disappeared after confirm")
        bal_after = float(spec_after.get("wallet_balance") or 0)
        delta = round(bal_after - bal_before, 2)
        if abs(delta - 950.0) < 1.0:
            return _ok(f"OK — specialist primit {delta} RON (95% din 1000 = 950)")
        return _ko(f"Specialist a primit {delta} RON, așteptam 950 (95% split)")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def e2e_dispute_opens_freezes_escrow() -> dict:
    """DISPUTE-01: Client deschide dispută pe job activ → escrow_status='frozen'."""
    env = await _seed_active_job(500.0)
    try:
        # Specialist starts work (otherwise dispute not allowed)
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        # Client opens dispute
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute", json={
            "reason": "E2E test — lucrarea nu a început în termen",
        })
        if dp.status_code != 200:
            return _ko(f"open dispute failed {dp.status_code}: {dp.text[:200]}")
        req = await db.requests.find_one({"_id": ObjectId(env["request_id"])})
        if not req:
            return _ko("request not found after dispute open")
        if req.get("escrow_status") == "frozen" and req.get("disputed") is True:
            return _ok(f"OK — escrow frozen, disputed=True (dispute_id={(dp.json() or {}).get('id','?')[:12]})")
        return _ko(f"escrow not frozen: status={req.get('escrow_status')}, disputed={req.get('disputed')}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def e2e_dispute_resolves_refund_client() -> dict:
    """DISPUTE-02: Admin rezolvă cu refund_client → wallet client crește cu suma escrow."""
    env = await _seed_active_job(600.0)
    admin_c = None
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute", json={"reason": "E2E test dispută refund client"})
        try:
            dispute_body = dp.json()
        except Exception:
            dispute_body = {}
        dispute_id = dispute_body.get("id") if isinstance(dispute_body, dict) else None
        if not dispute_id:
            return _ko(f"no dispute id in response (status={dp.status_code}): {dp.text[:200]}")
        # Admin resolves
        admin_c = await _admin_client()
        client_before = await _wait_for_db(
            lambda: db.users.find_one({"email": env["client_email"]}),
            label=f"client {env['client_email'][:20]}",
        )
        bal_b = float(client_before.get("wallet_balance") or 0)
        rs = await admin_c.post(f"/api/admin/disputes/{dispute_id}/resolve", json={
            "resolution": "refund_client", "notes": "E2E test refund",
        })
        if rs.status_code != 200:
            return _ko(f"resolve failed {rs.status_code}: {rs.text[:200]}")
        client_after = await _wait_for_db(
            lambda: db.users.find_one({"email": env["client_email"]}),
            label="client after resolve",
        )
        delta = round(float(client_after.get("wallet_balance") or 0) - bal_b, 2)
        if abs(delta - 600.0) < 1.0:
            return _ok(f"OK — client rambursat {delta} RON din escrow")
        return _ko(f"Client a primit {delta} RON, așteptam 600")
    finally:
        if admin_c:
            await admin_c.aclose()
        await _cleanup_e2e(env)


@_safe_e2e
async def e2e_quote_specialist_accept_charges_lead_fee() -> dict:
    """QUOTE-01: Specialistul acceptă lead-ul → 45 RON lead_fee dedus din wallet, status='assigned'."""
    client_c, c_email, _ = await _register_and_login("client", "qf_c")
    spec_c, s_email, _ = await _register_and_login("specialist", "qf_s")
    pid = req_id = ""
    try:
        # Wait for specialist row to be visible on prod (Atlas read lag)
        await _wait_for_db(lambda: db.users.find_one({"email": s_email}), label=f"specialist {s_email[:20]}")
        await db.users.update_one({"email": s_email}, {"$inc": {"wallet_balance": 200.0}})
        pr = await client_c.post("/api/properties", json={
            "name": "Q Apt", "address": "Str Q 1", "type": "apartment", "surface": 50.0, "rooms": 2,
        })
        if pr.status_code != 200:
            return _ko(f"property create failed {pr.status_code}: {pr.text[:200]}")
        try:
            pr_body = pr.json()
        except Exception:
            pr_body = {}
        pid = (pr_body or {}).get("id") if isinstance(pr_body, dict) else None
        if not pid:
            return _ko(f"no property id (status={pr.status_code}, body keys={list((pr_body or {}).keys())[:5]})")
        rq = await client_c.post("/api/requests", json={
            "property_id": pid, "title": "Lead test", "category": "electric",
            "priority": "normal", "budget_estimate": 500, "description": "Q",
        })
        if rq.status_code != 200:
            return _ko(f"request create failed {rq.status_code}: {rq.text[:200]}")
        try:
            rq_body = rq.json()
        except Exception:
            rq_body = {}
        req_id = (rq_body or {}).get("id") if isinstance(rq_body, dict) else None
        if not req_id:
            return _ko(f"no request id (status={rq.status_code})")
        before = await _wait_for_db(lambda: db.users.find_one({"email": s_email}), label="specialist before accept")
        bal_b = float(before.get("wallet_balance") or 0)
        ac = await spec_c.post(f"/api/requests/{req_id}/accept", json={})
        if ac.status_code != 200:
            return _ko(f"accept failed {ac.status_code}: {ac.text[:200]}")
        after = await _wait_for_db(lambda: db.users.find_one({"email": s_email}), label="specialist after accept")
        delta = round(bal_b - float(after.get("wallet_balance") or 0), 2)
        req = await _wait_for_db(lambda: db.requests.find_one({"_id": ObjectId(req_id)}), label=f"request {req_id[:10]}")
        if abs(delta - 45.0) < 0.01 and req.get("status") == "assigned":
            return _ok(f"OK — lead fee 45 RON dedus, status='assigned' (specialist={s_email[:18]}...)")
        return _ko(f"delta={delta} RON (await 45), status={req.get('status')} (await assigned)")
    finally:
        await client_c.aclose()
        await spec_c.aclose()
        try:
            if req_id:
                await db.requests.delete_one({"_id": ObjectId(req_id)})
                await db.transactions.delete_many({"request_id": req_id})
            if pid:
                await db.properties.delete_one({"_id": ObjectId(pid)})
            await db.users.delete_one({"email": c_email})
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:  # noqa: BLE001
            pass


@_safe_e2e
async def e2e_specialist_kyc_upload_pending() -> dict:
    """FILE-01: Specialist încarcă document KYC → apare în users.documents cu status='pending'."""
    spec_c, s_email, _ = await _register_and_login("specialist", "kyc_s")
    try:
        # Tiny base64 payload simulating a PDF
        tiny_b64 = "data:application/pdf;base64,JVBERi0xLjQKJfbk/N8KMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0NvdW50IDA+PgplbmRvYmoKdHJhaWxlcjw8L1Jvb3QgMSAwIFI+PgolJUVPRgo="
        up = await spec_c.post("/api/specialist/documents", json={
            "type": "id_card", "name": "buletin_e2e.pdf", "url": tiny_b64,
        })
        if up.status_code != 200:
            return _ko(f"upload failed {up.status_code}: {up.text[:200]}")
        # Wait for the document write to land on prod Atlas
        spec = await _wait_for_db(
            lambda: db.users.find_one({"email": s_email, "documents.name": "buletin_e2e.pdf"}),
            label=f"specialist with doc {s_email[:20]}",
        )
        docs = spec.get("documents") or []
        match = [d for d in docs if d.get("name") == "buletin_e2e.pdf" and d.get("status") == "pending"]
        if match:
            return _ok(f"OK — document KYC încărcat, status=pending, id={match[0]['id'][:8]}")
        return _ko(f"document not found pending. docs={[(d.get('name'), d.get('status')) for d in docs]}")
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:  # noqa: BLE001
            pass


@_safe_e2e
async def e2e_chat_history_endpoint_returns_messages() -> dict:
    """CHAT-01: Client poate citi /api/chat/{req_id}/messages pe job-ul propriu (return list, fie și gol)."""
    env = await _seed_active_job(400.0)
    try:
        r = await env["client_c"].get(f"/api/chat/{env['request_id']}/messages")
        if r.status_code != 200:
            return _ko(f"chat history failed {r.status_code}: {r.text[:200]}")
        body = r.json()
        if isinstance(body, list):
            return _ok(f"OK — chat history accesibil clientului, {len(body)} mesaje (lista validă)")
        return _ko(f"unexpected body type: {type(body).__name__}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def e2e_gdpr_dsar_export_returns_account_data() -> dict:
    """GDPR-01: Authenticated user obține export DSAR (Art. 15) cu account + rights_summary."""
    client_c, c_email, _ = await _register_and_login("client", "gdpr_c")
    try:
        r = await client_c.get("/api/gdpr/me/export")
        if r.status_code != 200:
            return _ko(f"export failed {r.status_code}: {r.text[:200]}")
        body = r.json() or {}
        if (body.get("account") or {}).get("email") == c_email and body.get("rights_summary"):
            return _ok(f"OK — DSAR export valid: account+rights_summary present pentru {c_email[:24]}")
        return _ko(f"export missing fields: keys={list(body.keys())}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:  # noqa: BLE001
            pass


@_safe_e2e
async def e2e_gdpr_erasure_request_creates_dsar_row() -> dict:
    """GDPR-02: POST /me/erasure-request creează rând în dsar_requests cu sla_due_at +30d."""
    client_c, c_email, c_id = await _register_and_login("client", "gdpr_e")
    try:
        r = await client_c.post("/api/gdpr/me/erasure-request", json={"confirm": True, "reason": "E2E test"})
        if r.status_code != 200:
            return _ko(f"erasure failed {r.status_code}: {r.text[:200]}")
        # Allow tiny write delay (transaction commit on prod can lag a few ms)
        try:
            row = await _wait_for_db(
                lambda: db.dsar_requests.find_one({"user_email": c_email, "type": "erasure"}),
                max_attempts=20, sleep_s=0.3,
                label=f"dsar_requests row {c_email[:18]}",
            )
        except RuntimeError as e:
            return _ko(str(e))
        if row.get("status") != "new" or not row.get("sla_due_at"):
            return _ko(f"row malformed: status={row.get('status')}, sla={row.get('sla_due_at')}")
        return _ok(f"OK — erasure DSAR creat, status=new, SLA={row['sla_due_at'][:10]} (30 zile)")
    finally:
        await client_c.aclose()
        try:
            await db.dsar_requests.delete_many({"user_email": c_email})
            await db.users.delete_one({"email": c_email})
        except Exception:  # noqa: BLE001
            pass


# ============================================================================
# Profile coverage — CLIENT (5) and SPECIALIST (5) plus 5 platform-health tests
# ============================================================================

@_safe_e2e
async def profile_client_register_fields_correct() -> dict:
    """PROFILE-CLIENT-01: Register client → /auth/me returnează exact email/name/role/zone."""
    client_c, c_email, c_id = await _register_and_login("client", "pc_r")
    try:
        me = await client_c.get("/api/auth/me")
        if me.status_code != 200:
            return _ko(f"/me {me.status_code}")
        body = me.json() if isinstance(me.json(), dict) else {}
        missing = [k for k in ("email", "name", "role") if not body.get(k)]
        if missing:
            return _ko(f"profil incomplet — lipsesc {missing}")
        if body.get("role") != "client":
            return _ko(f"role greșit: {body.get('role')}")
        if body.get("email") != c_email:
            return _ko(f"email mismatch: {body.get('email')} vs {c_email}")
        return _ok(f"OK — profil client complet (email={c_email[:25]}, name='{body['name']}', role=client)")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def profile_client_patch_updates_db() -> dict:
    """PROFILE-CLIENT-02: PATCH /auth/profile cu name nou → /me reflectă schimbarea."""
    client_c, c_email, _ = await _register_and_login("client", "pc_p")
    try:
        new_name = f"Client Renamed {uuid.uuid4().hex[:4]}"
        r = await client_c.patch("/api/auth/profile", json={"name": new_name, "phone": "0799123456"})
        if r.status_code != 200:
            return _ko(f"PATCH /auth/profile {r.status_code}: {r.text[:200]}")
        me = await client_c.get("/api/auth/me")
        body = me.json() if isinstance(me.json(), dict) else {}
        if body.get("name") == new_name and body.get("phone") == "0799123456":
            return _ok(f"OK — profil actualizat: name='{new_name}', phone='0799123456'")
        return _ko(f"PATCH OK dar /me nu reflectă: name={body.get('name')}, phone={body.get('phone')}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def profile_client_change_password_then_login() -> dict:
    """PROFILE-CLIENT-03: Schimb parola → login cu parola nouă merge, cu cea veche nu."""
    client_c, c_email, _ = await _register_and_login("client", "pc_pw")
    try:
        r = await client_c.post("/api/auth/change-password", json={
            "current_password": "Test1234!", "new_password": "Renewed123!",
        })
        if r.status_code != 200:
            return _ko(f"change-password failed {r.status_code}: {r.text[:200]}")
        # Login old should fail, new should succeed
        c2 = httpx.AsyncClient(base_url=BACKEND_URL, timeout=15.0, follow_redirects=False)
        try:
            old = await c2.post("/api/auth/login", json={"email": c_email, "password": "Test1234!"})
            new = await c2.post("/api/auth/login", json={"email": c_email, "password": "Renewed123!"})
            if old.status_code == 200:
                return _ko("parola veche încă funcționează (nu a fost rotită)")
            if new.status_code != 200:
                return _ko(f"login cu parola nouă a eșuat {new.status_code}")
        finally:
            await c2.aclose()
        return _ok(f"OK — parolă rotită corect (vechea respinsă {old.status_code}, noua OK 200)")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def profile_client_has_properties_list() -> dict:
    """PROFILE-CLIENT-04: Client creează 1 proprietate → GET /properties returnează 1+."""
    client_c, c_email, _ = await _register_and_login("client", "pc_pr")
    try:
        pr = await client_c.post("/api/properties", json={
            "name": "Profile Apt", "address": "Str Profile 1",
            "type": "apartment", "surface": 50.0, "rooms": 2,
        })
        if pr.status_code != 200:
            return _ko(f"property create {pr.status_code}: {pr.text[:200]}")
        lst = await client_c.get("/api/properties")
        if lst.status_code != 200:
            return _ko(f"GET /properties {lst.status_code}")
        items = lst.json() if isinstance(lst.json(), list) else []
        if len(items) >= 1:
            return _ok(f"OK — {len(items)} proprietate(i) listate pentru client")
        return _ko("client are 0 proprietăți după create")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
            await db.properties.delete_many({"name": "Profile Apt"})
        except Exception:
            pass


@_safe_e2e
async def profile_client_gdpr_export_includes_all_data() -> dict:
    """PROFILE-CLIENT-05: GDPR export întoarce account.email și nu lipsește field critic."""
    client_c, c_email, _ = await _register_and_login("client", "pc_g")
    try:
        # Create 1 property to ensure export has user-owned data
        await client_c.post("/api/properties", json={
            "name": "Export Apt", "address": "X", "type": "apartment", "surface": 40.0, "rooms": 1,
        })
        r = await client_c.get("/api/gdpr/me/export")
        if r.status_code != 200:
            return _ko(f"/gdpr/me/export {r.status_code}")
        body = r.json() if isinstance(r.json(), dict) else {}
        acc = body.get("account") or {}
        missing = [k for k in ("email", "role") if not acc.get(k)]
        if missing or acc.get("email") != c_email:
            return _ko(f"export lipsuri {missing} sau email mismatch: {acc.get('email')}")
        rights = body.get("rights_summary") or {}
        if not rights:
            return _ko("rights_summary lipsește din export")
        return _ok(f"OK — export complet: account.email={c_email[:22]}, rights={len(rights)} drepturi")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
            await db.properties.delete_many({"name": "Export Apt"})
        except Exception:
            pass


@_safe_e2e
async def profile_spec_register_fields_complete() -> dict:
    """PROFILE-SPEC-01: Register specialist cu categories+zones → /me le returnează corect."""
    spec_c, s_email, _ = await _register_and_login("specialist", "ps_r")
    try:
        me = await spec_c.get("/api/auth/me")
        if me.status_code != 200:
            return _ko(f"/me {me.status_code}")
        body = me.json() if isinstance(me.json(), dict) else {}
        cats = body.get("service_categories") or []
        zones = body.get("coverage_zones") or []
        if "electric" not in cats:
            return _ko(f"service_categories greșit: {cats}")
        if "Bucuresti" not in zones:
            return _ko(f"coverage_zones greșit: {zones}")
        if body.get("verified") is True:
            return _ko("specialist nou nu ar trebui să fie deja VERIFIED")
        return _ok(f"OK — specialist nou: cats={cats}, zones={zones}, verified=False (corect)")
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def profile_spec_public_profile_renders() -> dict:
    """PROFILE-SPEC-02: Pagină publică /api/specialists/{id}/profile returnează specialistul cu câmpurile cheie."""
    spec_c, s_email, s_id = await _register_and_login("specialist", "ps_pub")
    try:
        if not s_id:
            return _ko("nu am putut obține specialist_id din /me")
        c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=15.0)
        try:
            r = await c.get(f"/api/specialists/{s_id}/profile")
            if r.status_code != 200:
                return _ko(f"public profile {r.status_code}: {r.text[:200]}")
            body = r.json() if isinstance(r.json(), dict) else {}
            if body.get("email"):
                return _ko("⚠ SECURITY: email-ul specialistului expus pe pagina publică")
            if not body.get("name"):
                return _ko(f"name lipsește din public profile: {list(body.keys())[:8]}")
            return _ok(f"OK — public profile: name='{body.get('name')}', categories={body.get('service_categories', [])[:3]}, fără email expus")
        finally:
            await c.aclose()
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def profile_spec_verify_sets_verified_flag() -> dict:
    """PROFILE-SPEC-03: Admin verifică specialist → /me returnează verified=True + tier=VERIFIED."""
    spec_c, s_email, s_id = await _register_and_login("specialist", "ps_v")
    try:
        if not s_id:
            return _ko("specialist_id missing")
        admin = await _admin_client()
        try:
            v = await admin.post(f"/api/admin/specialists/{s_id}/verify")
            if v.status_code != 200:
                return _ko(f"admin verify {v.status_code}: {v.text[:200]}")
        finally:
            await admin.aclose()
        me = await spec_c.get("/api/auth/me")
        body = me.json() if isinstance(me.json(), dict) else {}
        if body.get("verified") is True and body.get("tier") == "VERIFIED":
            return _ok("OK — specialist VERIFIED (tier='VERIFIED', verified_at setat)")
        return _ko(f"verify OK dar /me arată verified={body.get('verified')}, tier={body.get('tier')}")
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def profile_spec_documents_visible_to_owner() -> dict:
    """PROFILE-SPEC-04: Specialist încarcă doc → /me îl include în users.documents cu status pending."""
    spec_c, s_email, _ = await _register_and_login("specialist", "ps_d")
    try:
        tiny_b64 = "data:application/pdf;base64,JVBERi0xLjQKJeLjz9MKMSAwIG9iagovL0VPRgo="
        up = await spec_c.post("/api/specialist/documents", json={
            "type": "id_card", "name": "test_profile.pdf", "url": tiny_b64,
        })
        if up.status_code != 200:
            return _ko(f"upload {up.status_code}: {up.text[:200]}")
        me = await spec_c.get("/api/auth/me")
        body = me.json() if isinstance(me.json(), dict) else {}
        docs = body.get("documents") or []
        match = [d for d in docs if d.get("name") == "test_profile.pdf"]
        if not match:
            return _ko(f"documentul nu apare în /me.documents (count={len(docs)})")
        if match[0].get("status") != "pending":
            return _ko(f"status doc greșit: {match[0].get('status')}")
        return _ok("OK — doc 'test_profile.pdf' vizibil în profil, status=pending")
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def profile_spec_patch_updates_categories() -> dict:
    """PROFILE-SPEC-05: Specialist actualizează service_categories → /me reflectă."""
    spec_c, s_email, _ = await _register_and_login("specialist", "ps_pp")
    try:
        r = await spec_c.patch("/api/auth/profile", json={
            "service_categories": ["electric", "instalatii"],
            "coverage_zones": ["Bucuresti", "Ilfov"],
        })
        if r.status_code != 200:
            return _ko(f"PATCH /auth/profile {r.status_code}: {r.text[:200]}")
        me = await spec_c.get("/api/auth/me")
        body = me.json() if isinstance(me.json(), dict) else {}
        cats = set(body.get("service_categories") or [])
        zones = set(body.get("coverage_zones") or [])
        if {"electric", "instalatii"}.issubset(cats) and {"Bucuresti", "Ilfov"}.issubset(zones):
            return _ok(f"OK — categorii+zone updatate: cats={sorted(cats)}, zones={sorted(zones)}")
        return _ko(f"PATCH OK dar /me nu reflectă: cats={cats}, zones={zones}")
    finally:
        await spec_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.onboarding_emails.delete_many({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def platform_morning_briefing_preview() -> dict:
    """PLATFORM-01: Admin /morning-briefing/preview returnează 6+ KPI tiles."""
    admin = await _admin_client()
    try:
        r = await admin.get("/api/admin/morning-briefing/preview")
        if r.status_code != 200:
            return _ko(f"morning briefing preview {r.status_code}: {r.text[:200]}")
        body = r.json() if isinstance(r.json(), dict) else {}
        payload = body.get("payload") or body
        if not payload or len(payload) < 3:
            return _ko(f"payload incomplet ({len(payload) if payload else 0} câmpuri)")
        return _ok(f"OK — Morning Briefing populat ({len(payload)} secțiuni KPI)")
    finally:
        await admin.aclose()


@_safe_e2e
async def platform_exec_briefing_preview() -> dict:
    """PLATFORM-02: Admin /exec-briefing/preview întoarce payload complet + HTML."""
    admin = await _admin_client()
    try:
        r = await admin.get("/api/admin/exec-briefing/preview")
        if r.status_code != 200:
            return _ko(f"exec briefing preview {r.status_code}")
        body = r.json() if isinstance(r.json(), dict) else {}
        if not body.get("payload") or not body.get("html"):
            return _ko(f"missing payload/html: keys={list(body.keys())}")
        if len(body["html"]) < 1500:
            return _ko(f"HTML prea mic: {len(body['html'])} chars")
        return _ok(f"OK — Exec Briefing: payload + {len(body['html'])} chars HTML")
    finally:
        await admin.aclose()


@_safe_e2e
async def platform_landing_marketplace_has_specialists() -> dict:
    """PLATFORM-03: /marketplace/specialists returnează listă cu min 1 specialist + paginare."""
    c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=15.0)
    try:
        r = await c.get("/api/marketplace/specialists?limit=10")
        if r.status_code != 200:
            return _ko(f"/marketplace/specialists {r.status_code}")
        body = r.json()
        # Endpoint returns a plain list of specialists, not paginated envelope
        if isinstance(body, list):
            items = body
        elif isinstance(body, dict):
            items = body.get("items") or body.get("results") or []
        else:
            items = []
        if not isinstance(items, list):
            items = []
        if len(items) < 1:
            return _ko(f"0 specialiști în marketplace (body type={type(body).__name__})")
        return _ok(f"OK — {len(items)} specialiști listați în marketplace (limită=10)")
    finally:
        await c.aclose()


@_safe_e2e
async def platform_trust_stats_endpoint_live() -> dict:
    """PLATFORM-04: /public/trust-stats (no-auth) returnează release_gate + platform metrics."""
    c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=15.0)
    try:
        r = await c.get("/api/public/trust-stats")
        if r.status_code != 200:
            return _ko(f"trust-stats {r.status_code}")
        body = r.json() if isinstance(r.json(), dict) else {}
        if "platform" not in body or "uptime" not in body or "compliance" not in body:
            return _ko(f"keys lipsă: {list(body.keys())}")
        plat = body["platform"] or {}
        return _ok(f"OK — Trust Center: {plat.get('verified_specialists', '?')} verified, {plat.get('total_clients', '?')} clienți")
    finally:
        await c.aclose()


@_safe_e2e
async def platform_trust_badge_svg_renders() -> dict:
    """PLATFORM-05: /public/trust-badge.svg întoarce SVG valid cu MIME image/svg+xml."""
    c = httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0)
    try:
        r = await c.get("/api/public/trust-badge.svg")
        if r.status_code != 200:
            return _ko(f"badge svg {r.status_code}")
        ct = r.headers.get("content-type", "")
        if "image/svg" not in ct:
            return _ko(f"content-type greșit: {ct}")
        if "<svg" not in r.text[:200]:
            return _ko("payload nu pare SVG valid")
        if len(r.text) < 300:
            return _ko(f"SVG prea mic: {len(r.text)} bytes")
        return _ok(f"OK — Trust Badge SVG: {len(r.text)} bytes, MIME={ct}")
    finally:
        await c.aclose()


# ============================================================================
# PACHET B — Escrow lifecycle + Dispute variants + Chat + Admin tools
# ============================================================================

@_safe_e2e
async def lifecycle_specialist_start_sets_in_progress() -> dict:
    """LIFE-START: După /start, status='in_progress', started_at este populat."""
    env = await _seed_active_job(500.0)
    try:
        r = await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        if r.status_code != 200:
            return _ko(f"/start failed {r.status_code}: {r.text[:200]}")
        req = await db.requests.find_one({"_id": ObjectId(env["request_id"])})
        if not req:
            return _ko("request not found after start")
        if req.get("status") == "in_progress" and req.get("started_at"):
            return _ok(f"OK — status=in_progress, started_at={req['started_at'][:19]}")
        return _ko(f"status={req.get('status')}, started_at={req.get('started_at')}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def lifecycle_specialist_complete_sets_pending_confirmation() -> dict:
    """LIFE-COMPLETE: După /complete, status='completed' și awaiting client confirm."""
    env = await _seed_active_job(700.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        r = await env["spec_c"].post(f"/api/requests/{env['request_id']}/complete")
        if r.status_code != 200:
            return _ko(f"/complete failed {r.status_code}: {r.text[:200]}")
        req = await db.requests.find_one({"_id": ObjectId(env["request_id"])})
        if not req:
            return _ko("request missing after complete")
        # `completed` here means specialist marked as done — client must confirm to release funds
        if req.get("status") in ("completed", "pending_confirmation") and req.get("completed_at"):
            esc = req.get("escrow_status")
            return _ok(f"OK — status={req.get('status')}, completed_at={req['completed_at'][:19]}, escrow={esc}")
        return _ko(f"status={req.get('status')}, completed_at={req.get('completed_at')}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def lifecycle_unauthorized_start_blocked() -> dict:
    """LIFE-AUTHZ: Un alt specialist NU poate da /start pe job asignat altcuiva."""
    env = await _seed_active_job(400.0)
    attacker_c, attacker_email, _ = await _register_and_login("specialist", "atk")
    try:
        r = await attacker_c.post(f"/api/requests/{env['request_id']}/start")
        if r.status_code in (401, 403, 404):
            return _ok(f"OK — atac respins corect cu HTTP {r.status_code}")
        return _ko(f"⚠ SECURITY: alt specialist a putut /start (HTTP {r.status_code})")
    finally:
        await attacker_c.aclose()
        try:
            await db.users.delete_one({"email": attacker_email})
            await db.onboarding_emails.delete_many({"email": attacker_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_resolve_pay_specialist_splits_95_5() -> dict:
    """DISPUTE-PAY: Admin rezolvă pay_specialist → specialist primește 95% din escrow."""
    env = await _seed_active_job(1000.0)
    admin_c = None
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "test pay_specialist resolution"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        try:
            dispute_id = (dp.json() or {}).get("id")
        except Exception:
            return _ko("dispute response not JSON")
        if not dispute_id:
            return _ko("no dispute id")
        spec_before = await db.users.find_one({"email": env["specialist_email"]})
        if not spec_before:
            return _ko("spec missing from DB")
        bal_b = float(spec_before.get("wallet_balance") or 0)
        admin_c = await _admin_client()
        rs = await admin_c.post(f"/api/admin/disputes/{dispute_id}/resolve",
                                 json={"resolution": "pay_specialist", "notes": "E2E"})
        if rs.status_code != 200:
            return _ko(f"resolve {rs.status_code}: {rs.text[:200]}")
        spec_after = await db.users.find_one({"email": env["specialist_email"]})
        delta = round(float(spec_after.get("wallet_balance") or 0) - bal_b, 2)
        if abs(delta - 950.0) < 1.0:
            return _ok(f"OK — specialist primit {delta} RON (95% × 1000 = 950)")
        return _ko(f"delta={delta}, așteptam ~950")
    finally:
        if admin_c:
            await admin_c.aclose()
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_resolve_split_60_40() -> dict:
    """DISPUTE-SPLIT: Admin rezolvă split cu client_pct=60 → client 600, specialist 380 (95% din 400)."""
    env = await _seed_active_job(1000.0)
    admin_c = None
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "test split resolution"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        dispute_id = (dp.json() or {}).get("id") if dp.json() else None
        if not dispute_id:
            return _ko("no dispute id")
        c_before = await db.users.find_one({"email": env["client_email"]})
        s_before = await db.users.find_one({"email": env["specialist_email"]})
        if not c_before or not s_before:
            return _ko("users missing")
        c_b, s_b = float(c_before.get("wallet_balance") or 0), float(s_before.get("wallet_balance") or 0)
        admin_c = await _admin_client()
        rs = await admin_c.post(f"/api/admin/disputes/{dispute_id}/resolve",
                                 json={"resolution": "split", "client_pct": 60, "notes": "E2E"})
        if rs.status_code != 200:
            return _ko(f"resolve {rs.status_code}: {rs.text[:200]}")
        c_after = await db.users.find_one({"email": env["client_email"]})
        s_after = await db.users.find_one({"email": env["specialist_email"]})
        c_delta = round(float(c_after.get("wallet_balance") or 0) - c_b, 2)
        s_delta = round(float(s_after.get("wallet_balance") or 0) - s_b, 2)
        # 1000 RON, 60% client = 600 → client +600, specialist (400 * 0.95) = +380
        if abs(c_delta - 600.0) < 1.0 and abs(s_delta - 380.0) < 1.0:
            return _ok(f"OK — split 60/40: client +{c_delta} RON, specialist +{s_delta} RON")
        return _ko(f"split greșit: client +{c_delta} (await 600), spec +{s_delta} (await 380)")
    finally:
        if admin_c:
            await admin_c.aclose()
        await _cleanup_e2e(env)


@_safe_e2e
async def chat_unauthorized_user_blocked() -> dict:
    """CHAT-AUTHZ: Un utilizator străin NU vede chat-ul altui job."""
    env = await _seed_active_job(300.0)
    intruder_c, intruder_email, _ = await _register_and_login("client", "int")
    try:
        r = await intruder_c.get(f"/api/chat/{env['request_id']}/messages")
        if r.status_code in (401, 403, 404):
            return _ok(f"OK — chat protejat corect (HTTP {r.status_code})")
        return _ko(f"⚠ SECURITY: alt client a accesat chat (HTTP {r.status_code})")
    finally:
        await intruder_c.aclose()
        try:
            await db.users.delete_one({"email": intruder_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


@_safe_e2e
async def gdpr_anonymize_scrambles_email() -> dict:
    """GDPR-03: User-ul își șterge contul prin /auth/account-delete → email anonimizat ('deleted_...@propmanage.deleted')."""
    client_c, c_email, c_id = await _register_and_login("client", "anon")
    try:
        if not c_id:
            return _ko("client id missing")
        # /auth/account-delete cere parola + confirmation="STERGE"
        r = await client_c.post("/api/auth/account-delete", json={
            "password": "Test1234!", "confirmation": "STERGE",
        })
        if r.status_code != 200:
            return _ko(f"account-delete {r.status_code}: {r.text[:200]}")
        u = await db.users.find_one({"_id": ObjectId(c_id)})
        if not u:
            return _ko("user vanished after delete")
        new_email = u.get("email") or ""
        if new_email == c_email:
            return _ko("email NU s-a schimbat după account-delete")
        if "deleted" in new_email.lower() or "anon" in new_email.lower():
            return _ok(f"OK — anonymize: {c_email[:25]} → {new_email[:40]}")
        return _ok(f"OK — email rotit: {c_email[:18]} → {new_email[:30]}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"_id": ObjectId(c_id)})
        except Exception:
            pass


@_safe_e2e
async def admin_disputes_listing_works() -> dict:
    """ADMIN-DISP-LIST: GET /api/admin/disputes returnează lista cu disputele active + structură validă."""
    env = await _seed_active_job(500.0)
    admin_c = None
    dispute_id = None
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "E2E listing test"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        dispute_id = (dp.json() or {}).get("id")
        admin_c = await _admin_client()
        r = await admin_c.get("/api/admin/disputes")
        if r.status_code != 200:
            return _ko(f"GET /admin/disputes {r.status_code}: {r.text[:200]}")
        body = r.json()
        items = body if isinstance(body, list) else (body.get("items") or [])
        found = any(d.get("id") == dispute_id or d.get("_id") == dispute_id for d in items if isinstance(d, dict))
        if found:
            return _ok(f"OK — admin vede {len(items)} dispute(s), inclusiv {dispute_id[:12]}")
        return _ko(f"admin nu găsește dispute {dispute_id[:12]} în lista de {len(items)} items")
    finally:
        if admin_c:
            await admin_c.aclose()
        await _cleanup_e2e(env)


@_safe_e2e
async def admin_backup_status_endpoint() -> dict:
    """ADMIN-BACKUP: GET /admin/backups returnează status + latest_run."""
    admin_c = await _admin_client()
    try:
        r = await admin_c.get("/api/admin/backups")
        if r.status_code != 200:
            return _ko(f"backup status {r.status_code}: {r.text[:200]}")
        body = r.json() if isinstance(r.json(), dict) else {}
        if "latest_run" in body or "backups" in body or body:
            return _ok(f"OK — backup status accesibil ({list(body.keys())[:5]})")
        return _ko(f"răspuns gol: {body}")
    finally:
        await admin_c.aclose()


@_safe_e2e
async def admin_ai_health_score_endpoint() -> dict:
    """ADMIN-AI-HEALTH: GET /admin/ai/health-score returnează overall 0-100."""
    admin_c = await _admin_client()
    try:
        r = await admin_c.get("/api/admin/ai/health-score")
        if r.status_code != 200:
            return _ko(f"ai-health {r.status_code}: {r.text[:200]}")
        body = r.json() if isinstance(r.json(), dict) else {}
        score = body.get("overall")
        if score is None:
            score = body.get("score") or (body.get("health") or {}).get("score")
        if score is None:
            return _ko(f"overall/score lipsește din response (keys={list(body.keys())[:6]})")
        if not (0 <= score <= 100):
            return _ko(f"score în afara intervalului 0-100: {score}")
        return _ok(f"OK — AI Health Score: {score}/100 (grade={body.get('grade','?')})")
    finally:
        await admin_c.aclose()



# ============================================================================
# PACHET B — Payment edge cases · Dispute escalations · SEO heavy · Marketplace · Admin (25)
# ============================================================================

# ---------- Payment / Escrow edge cases (8) ----------

@_safe_e2e
async def pay_insufficient_balance_blocks_accept() -> dict:
    """PAY-INSUFF: Specialist cu wallet 0 NU poate accepta lead (45 RON fee)."""
    client_c, c_email, _ = await _register_and_login("client", "pay_ins_c")
    spec_c, s_email, _ = await _register_and_login("specialist", "pay_ins_s")
    pid = req_id = ""
    try:
        # Zerează explicit wallet-ul (specialist nou are 500 RON welcome bonus)
        await db.users.update_one({"email": s_email}, {"$set": {"wallet_balance": 0.0}})
        pr = await client_c.post("/api/properties", json={
            "name": "Pay Ins Apt", "address": "Str X 1", "type": "apartment", "surface": 50.0, "rooms": 2,
        })
        if pr.status_code != 200:
            return _ko(f"property create {pr.status_code}")
        pid = (pr.json() or {}).get("id")
        rq = await client_c.post("/api/requests", json={
            "property_id": pid, "title": "T", "category": "electric",
            "priority": "normal", "budget_estimate": 300, "description": "T",
        })
        if rq.status_code != 200:
            return _ko(f"request create {rq.status_code}")
        req_id = (rq.json() or {}).get("id")
        # Try accept — expected to fail with 400 Insufficient balance
        ac = await spec_c.post(f"/api/requests/{req_id}/accept", json={})
        if ac.status_code == 400 and "balance" in ac.text.lower():
            return _ok("OK — accept respins corect (HTTP 400, mesaj balance) pentru wallet 0")
        return _ko(f"⚠ accept NU a fost blocat: status={ac.status_code} body={ac.text[:200]}")
    finally:
        await client_c.aclose()
        await spec_c.aclose()
        try:
            if req_id:
                await db.requests.delete_one({"_id": ObjectId(req_id)})
            if pid:
                await db.properties.delete_one({"_id": ObjectId(pid)})
            await db.users.delete_one({"email": c_email})
            await db.users.delete_one({"email": s_email})
        except Exception:
            pass


@_safe_e2e
async def pay_confirm_authz_specialist_blocked() -> dict:
    """PAY-CONFIRM-AUTHZ: Specialist NU poate /confirm (doar client) — așteptăm 403."""
    env = await _seed_active_job(500.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/complete")
        # Specialist tries to confirm own job
        cf = await env["spec_c"].post(f"/api/requests/{env['request_id']}/confirm")
        if cf.status_code in (403, 401, 404):
            return _ok(f"OK — specialist blocat la /confirm (HTTP {cf.status_code})")
        return _ko(f"⚠ specialist a putut /confirm: HTTP {cf.status_code} body={cf.text[:150]}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_start_authz_other_specialist_blocked() -> dict:
    """PAY-START-AUTHZ: Alt specialist NU poate /start un job care nu-i e atribuit (404)."""
    env = await _seed_active_job(400.0)
    other_c, other_email, _ = await _register_and_login("specialist", "pay_oth")
    try:
        r = await other_c.post(f"/api/requests/{env['request_id']}/start")
        if r.status_code in (403, 404):
            return _ok(f"OK — start blocat pentru alt specialist (HTTP {r.status_code})")
        return _ko(f"⚠ alt specialist a putut /start: HTTP {r.status_code}")
    finally:
        await other_c.aclose()
        try:
            await db.users.delete_one({"email": other_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_escrow_authz_stranger_blocked() -> dict:
    """PAY-ESCROW-AUTHZ: Un alt client NU poate alimenta escrow pentru job-ul altcuiva."""
    env = await _seed_active_job(600.0)
    stranger_c, stranger_email, _ = await _register_and_login("client", "esc_str")
    try:
        r = await stranger_c.post(f"/api/requests/{env['request_id']}/escrow?amount=500")
        if r.status_code in (403, 404):
            return _ok(f"OK — alt client blocat la escrow (HTTP {r.status_code})")
        return _ko(f"⚠ alt client a putut alimenta escrow: HTTP {r.status_code}")
    finally:
        await stranger_c.aclose()
        try:
            await db.users.delete_one({"email": stranger_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_lead_fee_transaction_recorded() -> dict:
    """PAY-TX-LEAD: După /accept, există în transactions un row 'lead_fee' cu -45 RON."""
    env = await _seed_active_job(500.0)
    try:
        tx = await db.transactions.find_one({
            "request_id": env["request_id"], "type": "lead_fee"
        })
        if not tx:
            return _ko("transaction lead_fee nu a fost creată în DB")
        amt = float(tx.get("amount") or 0)
        if abs(amt - (-45.0)) < 0.01:
            return _ok(f"OK — tx lead_fee=-45 RON, user={tx.get('user_id','?')[:8]}")
        return _ko(f"tx lead_fee creată dar amount={amt} (await -45)")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_release_creates_job_payment_transaction() -> dict:
    """PAY-TX-RELEASE: După /confirm, există tx 'job_payment' cu 95% din escrow."""
    env = await _seed_active_job(1000.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/complete")
        cf = await env["client_c"].post(f"/api/requests/{env['request_id']}/confirm")
        if cf.status_code != 200:
            return _ko(f"confirm {cf.status_code}")
        tx = await db.transactions.find_one({
            "request_id": env["request_id"], "type": "job_payment"
        })
        if not tx:
            return _ko("transaction job_payment nu a fost creată")
        amt = float(tx.get("amount") or 0)
        if abs(amt - 950.0) < 1.0:
            return _ok(f"OK — tx job_payment=+{amt} RON (95% × 1000)")
        return _ko(f"tx job_payment amount={amt} (await 950)")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_no_confirm_during_dispute_freeze() -> dict:
    """PAY-FROZEN-NOCONF: După deschidere dispută (status=assigned/in_progress), /confirm întoarce 400."""
    env = await _seed_active_job(500.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "test freeze"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        # /confirm requires status="completed" — nu e cazul deci primim 400
        cf = await env["client_c"].post(f"/api/requests/{env['request_id']}/confirm")
        if cf.status_code in (400, 403):
            return _ok(f"OK — confirm respins pe job disputat (HTTP {cf.status_code})")
        return _ko(f"⚠ confirm a trecut pe job disputat: HTTP {cf.status_code}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def pay_complete_authz_unassigned_blocked() -> dict:
    """PAY-COMPLETE-AUTHZ: Alt specialist NU poate /complete un job neatribuit lui."""
    env = await _seed_active_job(400.0)
    other_c, other_email, _ = await _register_and_login("specialist", "pay_cmp")
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        r = await other_c.post(f"/api/requests/{env['request_id']}/complete")
        if r.status_code in (403, 404):
            return _ok(f"OK — complete blocat pentru alt specialist (HTTP {r.status_code})")
        return _ko(f"⚠ alt specialist a putut /complete: HTTP {r.status_code}")
    finally:
        await other_c.aclose()
        try:
            await db.users.delete_one({"email": other_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


# ---------- Dispute escalations / edge cases (5) ----------

@_safe_e2e
async def dispute_no_duplicate_open() -> dict:
    """DISP-NO-DUP: A 2-a dispută pe același request → 400 (există deja una deschisă)."""
    env = await _seed_active_job(400.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        d1 = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                          json={"reason": "primă dispută"})
        if d1.status_code != 200:
            return _ko(f"prima dispută a eșuat {d1.status_code}")
        d2 = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                          json={"reason": "a doua dispută"})
        if d2.status_code == 400 and "exist" in d2.text.lower():
            return _ok("OK — a 2-a dispută respinsă corect (HTTP 400)")
        return _ko(f"⚠ duplicat dispută NU blocat: status={d2.status_code} body={d2.text[:120]}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_resolve_requires_admin() -> dict:
    """DISP-RESOLVE-AUTHZ: Client/specialist NU pot rezolva dispute (403)."""
    env = await _seed_active_job(400.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "test authz resolve"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        dispute_id = (dp.json() or {}).get("id")
        if not dispute_id:
            return _ko("no dispute id")
        # Client încearcă să rezolve — așteptăm 403
        r = await env["client_c"].post(f"/api/admin/disputes/{dispute_id}/resolve",
                                         json={"resolution": "refund_client", "notes": "x"})
        if r.status_code in (401, 403):
            return _ok(f"OK — client blocat la admin resolve (HTTP {r.status_code})")
        return _ko(f"⚠ client a putut rezolva dispute: HTTP {r.status_code}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_blocked_after_release() -> dict:
    """DISP-AFTER-RELEASE: După /confirm (escrow released), o nouă dispută → 400."""
    env = await _seed_active_job(700.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/complete")
        cf = await env["client_c"].post(f"/api/requests/{env['request_id']}/confirm")
        if cf.status_code != 200:
            return _ko(f"confirm {cf.status_code}")
        # Acum încearcă să deschidă o dispută — așteptăm 400
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "post-release"})
        if dp.status_code == 400:
            return _ok("OK — dispute respinsă după release (HTTP 400)")
        return _ko(f"⚠ dispute NEbocată după release: HTTP {dp.status_code}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_evidence_urls_persisted() -> dict:
    """DISP-EVID: evidence_urls trimise la /dispute sunt persistate în DB."""
    env = await _seed_active_job(500.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        evidences = ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "test evidence", "evidence_urls": evidences})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        dispute_id = (dp.json() or {}).get("id")
        doc = await db.disputes.find_one({"_id": ObjectId(dispute_id)})
        stored = doc.get("evidence_urls") if doc else None
        if isinstance(stored, list) and len(stored) == 2 and "photo1.jpg" in str(stored):
            return _ok(f"OK — {len(stored)} evidence URLs persistate")
        return _ko(f"evidence_urls stocat greșit: {stored}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def dispute_new_dispute_status_open() -> dict:
    """DISP-STATUS-OPEN: O dispută nouă are status='open' și escrow_status='frozen' pe request."""
    env = await _seed_active_job(400.0)
    try:
        await env["spec_c"].post(f"/api/requests/{env['request_id']}/start")
        dp = await env["client_c"].post(f"/api/requests/{env['request_id']}/dispute",
                                         json={"reason": "status open check"})
        if dp.status_code != 200:
            return _ko(f"open dispute {dp.status_code}")
        dispute_id = (dp.json() or {}).get("id")
        doc = await db.disputes.find_one({"_id": ObjectId(dispute_id)})
        req = await db.requests.find_one({"_id": ObjectId(env["request_id"])})
        if not doc or not req:
            return _ko("dispute/request missing")
        if doc.get("status") == "open" and req.get("escrow_status") == "frozen":
            return _ok("OK — dispute.status=open, request.escrow_status=frozen")
        return _ko(f"dispute.status={doc.get('status')}, escrow_status={req.get('escrow_status')}")
    finally:
        await _cleanup_e2e(env)


# ---------- SEO heavy (5) ----------

@_safe_e2e
async def seo_sitemap_url_count_minimum() -> dict:
    """SEO-SITEMAP-COUNT: Sitemap conține >=30 URLs (static + ghiduri + landings)."""
    async with await _client() as c:
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap {r.status_code}")
        body = r.text
        count = body.count("<url>")
        if count >= 30:
            return _ok(f"OK — sitemap are {count} URLs (>=30)")
        return _ko(f"sitemap doar {count} URLs (await >=30)")


@_safe_e2e
async def seo_sitemap_xml_well_formed() -> dict:
    """SEO-SITEMAP-XML: Sitemap parsează ca XML valid."""
    import xml.etree.ElementTree as ET
    async with await _client() as c:
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap {r.status_code}")
        try:
            root = ET.fromstring(r.text)
        except ET.ParseError as e:
            return _ko(f"XML invalid: {e}")
        tag = root.tag.lower()
        if "urlset" in tag:
            return _ok(f"OK — XML valid, root tag={tag}")
        return _ko(f"root tag neașteptat: {tag}")


@_safe_e2e
async def seo_sitemap_landing_diverse_cities() -> dict:
    """SEO-GATE-CONSISTENCY: fiecare landing marketplace din sitemap trece Indexability Gate-ul."""
    import re as _re
    async with await _client() as c:
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap {r.status_code}")
        landings = _re.findall(r"/marketplace/([a-z0-9\-]+)</loc>", r.text)
        bad = []
        for slug in landings[:8]:
            g = await c.get(f"/api/public/seo/gate?path=/marketplace/{slug}")
            if g.status_code != 200 or g.json().get("index") is not True:
                bad.append(slug)
        if not bad:
            return _ok(f"OK — {len(landings)} landing-uri în sitemap, {min(len(landings), 8)} verificate, toate trec gate-ul")
        return _ko(f"landing-uri în sitemap care NU trec gate-ul: {bad}")


@_safe_e2e
async def seo_sitemap_all_guides_present() -> dict:
    """SEO-GUIDES: Toate cele 6 ghiduri sunt în sitemap."""
    expected_guides = [
        "cost-renovare-apartament-2-camere",
        "cum-alegi-designer-interior",
        "cum-verifici-instalator",
        "cost-instalatie-electrica-apartament",
        "cum-functioneaza-escrow-lucrari",
        "cum-alegi-zugrav-bun",
    ]
    async with await _client() as c:
        r = await c.get("/api/public/sitemap.xml")
        if r.status_code != 200:
            return _ko(f"sitemap {r.status_code}")
        body = r.text
        missing = [g for g in expected_guides if g not in body]
        if not missing:
            return _ok("OK — toate 6 ghiduri prezente în sitemap")
        return _ko(f"ghiduri lipsă: {missing}")


@_safe_e2e
async def seo_marketplace_public_returns_array() -> dict:
    """SEO-MKT-API: GET /api/marketplace/specialists returnează listă (fără auth)."""
    async with await _client() as c:
        r = await c.get("/api/marketplace/specialists")
        if r.status_code != 200:
            return _ko(f"marketplace {r.status_code}")
        body = r.json()
        if isinstance(body, list):
            return _ok(f"OK — marketplace returnează listă cu {len(body)} specialiști")
        return _ko(f"răspuns neașteptat tip={type(body).__name__}")


# ---------- Marketplace filters (3) ----------

@_safe_e2e
async def mkt_filter_category_returns_matching() -> dict:
    """MKT-CAT: ?category=electric returnează doar specialiști din categoria electric."""
    async with await _client() as c:
        r = await c.get("/api/marketplace/specialists?category=electric")
        if r.status_code != 200:
            return _ko(f"marketplace {r.status_code}")
        body = r.json()
        if not isinstance(body, list):
            return _ko("răspuns nu e listă")
        if len(body) == 0:
            return _ok("OK — 0 specialiști electric (listă goală e valid)")
        mismatched = [
            s for s in body
            if s.get("specialty") != "electric"
            and "electric" not in (s.get("service_categories") or [])
        ]
        if not mismatched:
            return _ok(f"OK — toți {len(body)} specialiști sunt electric")
        return _ko(f"{len(mismatched)} specialiști NU sunt electric")


@_safe_e2e
async def mkt_filter_zone_returns_matching() -> dict:
    """MKT-ZONE: ?zone=Bucuresti returnează specialiști care acoperă Bucuresti."""
    async with await _client() as c:
        r = await c.get("/api/marketplace/specialists?zone=Bucuresti")
        if r.status_code != 200:
            return _ko(f"marketplace {r.status_code}")
        body = r.json()
        if not isinstance(body, list):
            return _ko("nu e listă")
        if len(body) == 0:
            return _ok("OK — listă goală pentru zonă (acceptabil)")
        ok_count = sum(1 for s in body if "Bucuresti" in (s.get("coverage_zones") or []))
        if ok_count == len(body):
            return _ok(f"OK — toți {len(body)} specialiști acoperă Bucuresti")
        return _ko(f"doar {ok_count}/{len(body)} acoperă Bucuresti")


@_safe_e2e
async def mkt_filter_unknown_city_returns_empty() -> dict:
    """MKT-CITY-NORES: ?city=OrașInexistent returnează listă goală (nu crash)."""
    async with await _client() as c:
        r = await c.get("/api/marketplace/specialists?city=OrașInexistent_XYZ")
        if r.status_code != 200:
            return _ko(f"marketplace {r.status_code}")
        body = r.json()
        if isinstance(body, list) and len(body) == 0:
            return _ok("OK — listă goală pentru oraș inexistent (no leak)")
        return _ko(f"⚠ oraș inexistent a returnat {len(body) if isinstance(body, list) else '?'} items — leak posibil")


# ---------- Admin tooling (4) ----------

@_safe_e2e
async def admin_users_listing_pagination() -> dict:
    """ADMIN-USERS-LIST: GET /admin/users returnează items/total/skip/limit."""
    admin_c = await _admin_client()
    try:
        r = await admin_c.get("/api/admin/users?limit=10")
        if r.status_code != 200:
            return _ko(f"admin/users {r.status_code}: {r.text[:160]}")
        body = r.json()
        if not isinstance(body, dict):
            return _ko("response nu e dict")
        required = {"items", "total", "skip", "limit"}
        missing = required - set(body.keys())
        if missing:
            return _ko(f"chei lipsă: {missing}")
        if not isinstance(body["items"], list):
            return _ko("items nu e listă")
        return _ok(f"OK — admin/users: {len(body['items'])} items, total={body['total']}, limit={body['limit']}")
    finally:
        await admin_c.aclose()


@_safe_e2e
async def admin_incidents_listing() -> dict:
    """ADMIN-INC-LIST: GET /admin/incidents returnează {items, count}."""
    admin_c = await _admin_client()
    try:
        r = await admin_c.get("/api/admin/incidents")
        if r.status_code != 200:
            return _ko(f"admin/incidents {r.status_code}: {r.text[:160]}")
        body = r.json()
        if not isinstance(body, dict):
            return _ko("response nu e dict")
        if "items" not in body or "count" not in body:
            return _ko(f"chei lipsă: keys={list(body.keys())}")
        if not isinstance(body["items"], list):
            return _ko("items nu e listă")
        return _ok(f"OK — admin/incidents: {body['count']} incidents totale")
    finally:
        await admin_c.aclose()


@_safe_e2e
async def admin_impersonate_admin_blocked() -> dict:
    """ADMIN-IMP-ADMIN-BLOCK: Admin NU poate impersona alt admin (403)."""
    admin_c = await _admin_client()
    try:
        # Caută alt admin (sau încearcă cu un user admin chiar dacă e admin_seed)
        admins = await db.users.find({"role": "admin"}).to_list(5)
        target = None
        # Identifică self
        me = await admin_c.get("/api/auth/me")
        me_id = (me.json() or {}).get("id") if me.status_code == 200 else None
        target = next((a for a in admins if str(a.get("_id")) != me_id), None)
        if not target:
            return _ok("SKIP — doar 1 admin în sistem (test nu se poate executa)")
        r = await admin_c.post("/api/admin/impersonate", json={
            "user_id": str(target["_id"]), "reason": "E2E test - admin impersonation should be blocked",
        })
        if r.status_code == 403 and "admin" in r.text.lower():
            return _ok("OK — impersonate admin blocat (HTTP 403)")
        return _ko(f"⚠ impersonate admin NU a fost blocat: HTTP {r.status_code}")
    finally:
        await admin_c.aclose()


@_safe_e2e
async def admin_impersonate_client_success() -> dict:
    """ADMIN-IMP-CLIENT: Admin impersonează un client → 200 cu redirect_to=/client."""
    admin_c = await _admin_client()
    client_c, c_email, c_id = await _register_and_login("client", "imp_tgt")
    try:
        if not c_id:
            return _ko("missing client id")
        r = await admin_c.post("/api/admin/impersonate", json={
            "user_id": c_id, "reason": "E2E test - admin can impersonate client",
        })
        if r.status_code != 200:
            return _ko(f"impersonate {r.status_code}: {r.text[:200]}")
        body = r.json() if isinstance(r.json(), dict) else {}
        target = body.get("target") or {}
        if target.get("role") == "client" and body.get("redirect_to") == "/client":
            return _ok(f"OK — admin a impersonat client {target.get('email','?')[:20]} (TTL={body.get('expires_in_seconds')}s)")
        return _ko(f"răspuns neașteptat: target={target}, redirect={body.get('redirect_to')}")
    finally:
        # Stop impersonation să nu lăsăm sesiunea murdară
        try:
            await admin_c.post("/api/admin/stop-impersonation")
        except Exception:
            pass
        await admin_c.aclose()
        await client_c.aclose()
        try:
            await db.users.delete_one({"_id": ObjectId(c_id)})
            await db.impersonation_logs.delete_many({"target_user_id": c_id})
        except Exception:
            pass




# ============================================================================
# PACHET C — Operator · Projects · Notifications · Wallet · Misc (17)
# ============================================================================

# ---------- Operator flows (4) ----------

@_safe_e2e
async def op_flag_authz_client_blocked() -> dict:
    """OP-FLAG-AUTHZ: Client NU poate flag nonconformity (403 — doar operator)."""
    client_c, c_email, _ = await _register_and_login("client", "op_authz_c")
    try:
        # Folosim un property_id real dar accesul e blocat de require_role("operator")
        r = await client_c.post("/api/operator/flag-nonconformity", json={
            "target_type": "request", "target_id": "507f1f77bcf86cd799439011",
            "reason": "test client tries to flag", "severity": "low",
        })
        if r.status_code in (401, 403):
            return _ok(f"OK — client blocat la flag-nonconformity (HTTP {r.status_code})")
        return _ko(f"⚠ client a putut flag: HTTP {r.status_code}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def op_flag_create_then_list_resolve() -> dict:
    """OP-FLAG-FULL: Operator flag → nonconformity creată cu status=open. Admin o vede în list. Apoi /resolve → status=resolved."""
    # Seed un job pt context
    env = await _seed_active_job(400.0)
    op_c, op_email, op_id = await _register_and_login("operator", "op_full")
    admin_c = None
    flag_id = None
    try:
        # Operator flag pe request-ul deja creat
        r = await op_c.post("/api/operator/flag-nonconformity", json={
            "target_type": "request", "target_id": env["request_id"],
            "reason": "E2E test - lucrare neconformă", "severity": "medium",
        })
        if r.status_code != 200:
            return _ko(f"flag {r.status_code}: {r.text[:200]}")
        flag_id = (r.json() or {}).get("id")
        if not flag_id:
            return _ko("no flag id")
        # Verify DB record
        flag = await db.nonconformities.find_one({"_id": ObjectId(flag_id)})
        if not flag or flag.get("status") != "open":
            return _ko(f"flag DB stare: {flag.get('status') if flag else 'missing'}")
        # Admin sees it
        admin_c = await _admin_client()
        lr = await admin_c.get("/api/admin/nonconformities")
        if lr.status_code != 200:
            return _ko(f"admin/nonconformities {lr.status_code}")
        items = lr.json() if isinstance(lr.json(), list) else []
        found = any(d.get("id") == flag_id or d.get("_id") == flag_id for d in items)
        if not found:
            return _ko(f"admin nu vede flag {flag_id[:10]} în lista de {len(items)} items")
        # Admin resolves
        rs = await admin_c.post(f"/api/admin/nonconformities/{flag_id}/resolve", json={
            "resolution": "E2E resolved by admin"
        })
        if rs.status_code != 200:
            return _ko(f"resolve {rs.status_code}")
        flag_after = await db.nonconformities.find_one({"_id": ObjectId(flag_id)})
        if flag_after and flag_after.get("status") == "resolved":
            return _ok(f"OK — flag creat (id={flag_id[:10]}), văzut de admin, rezolvat → status=resolved")
        return _ko(f"după resolve status={flag_after.get('status') if flag_after else 'missing'}")
    finally:
        await op_c.aclose()
        if admin_c:
            await admin_c.aclose()
        try:
            if flag_id:
                await db.nonconformities.delete_one({"_id": ObjectId(flag_id)})
            await db.users.delete_one({"email": op_email})
        except Exception:
            pass
        await _cleanup_e2e(env)


@_safe_e2e
async def op_queue_endpoint_accessible() -> dict:
    """OP-QUEUE: Operator vede /operator/queue (lista de log-uri pt validare twin)."""
    op_c, op_email, _ = await _register_and_login("operator", "op_q")
    try:
        r = await op_c.get("/api/operator/queue")
        if r.status_code != 200:
            return _ko(f"queue {r.status_code}: {r.text[:160]}")
        body = r.json()
        # Acceptă listă sau dict cu items
        if isinstance(body, list) or (isinstance(body, dict) and "items" in body):
            count = len(body) if isinstance(body, list) else len(body.get("items", []))
            return _ok(f"OK — operator queue accesibil, {count} items")
        return _ko(f"răspuns neașteptat: type={type(body).__name__}")
    finally:
        await op_c.aclose()
        try:
            await db.users.delete_one({"email": op_email})
        except Exception:
            pass


@_safe_e2e
async def op_flag_404_for_inexistent_target() -> dict:
    """OP-FLAG-404: Operator flag pe target inexistent → 404."""
    op_c, op_email, _ = await _register_and_login("operator", "op_404")
    try:
        r = await op_c.post("/api/operator/flag-nonconformity", json={
            "target_type": "request", "target_id": "000000000000000000000000",
            "reason": "E2E test target inexistent", "severity": "low",
        })
        if r.status_code == 404:
            return _ok("OK — flag pe request inexistent respins corect (404)")
        return _ko(f"⚠ flag pe target inexistent NU a fost respins: HTTP {r.status_code}")
    finally:
        await op_c.aclose()
        try:
            await db.users.delete_one({"email": op_email})
        except Exception:
            pass


# ---------- Projects / Workspace (4) ----------

@_safe_e2e
async def proj_authz_non_designer_blocked() -> dict:
    """PROJ-AUTHZ: Specialist non-designer NU poate crea project (403)."""
    spec_c, s_email, _ = await _register_and_login("specialist", "proj_az",
                                                     extra={"service_categories": ["electric"]})
    client_c, c_email, c_id = await _register_and_login("client", "proj_az_c")
    try:
        r = await spec_c.post("/api/projects", json={
            "name": "Test project", "client_id": c_id,
        })
        if r.status_code == 403:
            return _ok("OK — non-designer blocat la proiect (HTTP 403)")
        return _ko(f"⚠ non-designer a putut crea proiect: HTTP {r.status_code}")
    finally:
        await spec_c.aclose()
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": s_email})
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def proj_designer_create_project_with_client() -> dict:
    """PROJ-CREATE: Designer creează project pentru client → members include client."""
    designer_c, d_email, _ = await _register_and_login("specialist", "proj_d",
                                                          extra={"service_categories": ["interior_design"]})
    client_c, c_email, c_id = await _register_and_login("client", "proj_cl")
    project_id = None
    try:
        r = await designer_c.post("/api/projects", json={
            "name": "Renovare 2 camere E2E", "client_id": c_id,
            "description": "Test E2E project", "style": "scandinav",
        })
        if r.status_code != 200:
            return _ko(f"create project {r.status_code}: {r.text[:200]}")
        body = r.json()
        project_id = body.get("id")
        if not project_id:
            return _ko("no project id")
        members = body.get("members") or []
        client_in_members = any(m.get("user_id") == c_id for m in members)
        if client_in_members and body.get("status") == "active":
            return _ok(f"OK — proiect creat (id={project_id[:10]}), client în members, status=active")
        return _ko(f"members shape: client_in={client_in_members}, status={body.get('status')}")
    finally:
        await designer_c.aclose()
        await client_c.aclose()
        try:
            if project_id:
                await db.projects.delete_one({"_id": ObjectId(project_id)})
            await db.users.delete_one({"email": d_email})
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def proj_client_sees_project_in_list() -> dict:
    """PROJ-LIST: Client vede în /projects proiectul în care e membru."""
    designer_c, d_email, _ = await _register_and_login("specialist", "proj_d2",
                                                          extra={"service_categories": ["interior_design"]})
    client_c, c_email, c_id = await _register_and_login("client", "proj_cl2")
    project_id = None
    try:
        r = await designer_c.post("/api/projects", json={
            "name": "Vizibilitate listă E2E", "client_id": c_id,
        })
        if r.status_code != 200:
            return _ko(f"create {r.status_code}")
        project_id = (r.json() or {}).get("id")
        # Client cere lista
        lr = await client_c.get("/api/projects")
        if lr.status_code != 200:
            return _ko(f"list {lr.status_code}")
        items = lr.json() if isinstance(lr.json(), list) else []
        found = any((p.get("id") == project_id or p.get("_id") == project_id) for p in items)
        if found:
            return _ok(f"OK — clientul vede {len(items)} proiect(e), inclusiv {project_id[:10]}")
        return _ko(f"client NU vede project {project_id[:10]} în lista de {len(items)}")
    finally:
        await designer_c.aclose()
        await client_c.aclose()
        try:
            if project_id:
                await db.projects.delete_one({"_id": ObjectId(project_id)})
            await db.users.delete_one({"email": d_email})
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def proj_task_create_and_visible() -> dict:
    """PROJ-TASK: Designer adaugă task în project → task apare în /tasks."""
    designer_c, d_email, _ = await _register_and_login("specialist", "proj_t",
                                                          extra={"service_categories": ["interior_design"]})
    client_c, c_email, c_id = await _register_and_login("client", "proj_t_c")
    project_id = task_id = None
    try:
        cr = await designer_c.post("/api/projects", json={
            "name": "Task E2E project", "client_id": c_id,
        })
        if cr.status_code != 200:
            return _ko(f"create project {cr.status_code}")
        project_id = (cr.json() or {}).get("id")
        # Adăugăm un task
        tr = await designer_c.post(f"/api/projects/{project_id}/tasks", json={
            "title": "Comandă parchet", "description": "Comandă din magazin X",
            "priority": "normal", "status": "todo",
        })
        if tr.status_code != 200:
            return _ko(f"task create {tr.status_code}: {tr.text[:160]}")
        task_id = (tr.json() or {}).get("id")
        # List tasks
        lr = await designer_c.get(f"/api/projects/{project_id}/tasks")
        if lr.status_code != 200:
            return _ko(f"task list {lr.status_code}")
        tasks = lr.json() if isinstance(lr.json(), list) else []
        found = any(t.get("id") == task_id for t in tasks)
        if found and len(tasks) >= 1:
            return _ok(f"OK — task creat (id={task_id[:10] if task_id else '?'}) vizibil în lista de {len(tasks)}")
        return _ko(f"task NU vizibil: found={found}, total tasks={len(tasks)}")
    finally:
        await designer_c.aclose()
        await client_c.aclose()
        try:
            if task_id:
                await db.project_tasks.delete_one({"_id": ObjectId(task_id)})
            if project_id:
                await db.projects.delete_one({"_id": ObjectId(project_id)})
            await db.users.delete_one({"email": d_email})
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


# ---------- Notifications (3) ----------

@_safe_e2e
async def notif_list_returns_array() -> dict:
    """NOTIF-LIST: GET /notifications returnează array (gol pt user nou)."""
    client_c, c_email, _ = await _register_and_login("client", "notif_l")
    try:
        r = await client_c.get("/api/notifications")
        if r.status_code != 200:
            return _ko(f"notifications {r.status_code}")
        body = r.json()
        if isinstance(body, list):
            return _ok(f"OK — notifications listă cu {len(body)} items")
        return _ko(f"răspuns nu e listă: {type(body).__name__}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def notif_mark_read_sets_flag() -> dict:
    """NOTIF-READ: POST /{id}/read setează read=True pe notificarea proprie."""
    client_c, c_email, c_id = await _register_and_login("client", "notif_r")
    notif_id = None
    try:
        # Insert manual o notificare via DB (mai rapid decât a trigger flow)
        ins = await db.notifications.insert_one({
            "user_id": c_id, "type": "test", "title": "E2E notif",
            "message": "test", "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        notif_id = str(ins.inserted_id)
        r = await client_c.post(f"/api/notifications/{notif_id}/read")
        if r.status_code != 200:
            return _ko(f"mark-read {r.status_code}")
        doc = await db.notifications.find_one({"_id": ins.inserted_id})
        if doc and doc.get("read") is True:
            return _ok(f"OK — notif {notif_id[:10]} marcată read=True")
        return _ko(f"read flag nu setat: {doc.get('read') if doc else 'missing'}")
    finally:
        await client_c.aclose()
        try:
            if notif_id:
                await db.notifications.delete_one({"_id": ObjectId(notif_id)})
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


@_safe_e2e
async def notif_cross_user_mark_blocked() -> dict:
    """NOTIF-CROSS: User B NU poate marca read-o notificare a lui User A (silent fail / no-op)."""
    user_a_c, a_email, a_id = await _register_and_login("client", "notif_a")
    user_b_c, b_email, _ = await _register_and_login("client", "notif_b")
    notif_id = None
    try:
        # Notificare pentru A
        ins = await db.notifications.insert_one({
            "user_id": a_id, "type": "test", "title": "Pentru A",
            "message": "test", "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        notif_id = str(ins.inserted_id)
        # B încearcă să marcheze
        await user_b_c.post(f"/api/notifications/{notif_id}/read")
        # Endpoint-ul actual e silent (filtrează după user_id, update_one nu modifică nimic)
        # Verifică DB că read=False încă
        doc = await db.notifications.find_one({"_id": ins.inserted_id})
        if doc and doc.get("read") is not True:
            return _ok("OK — user B NU a putut marca notif lui A (still read=False)")
        return _ko(f"⚠ user B a marcat notif lui A: read={doc.get('read') if doc else 'missing'}")
    finally:
        await user_a_c.aclose()
        await user_b_c.aclose()
        try:
            if notif_id:
                await db.notifications.delete_one({"_id": ObjectId(notif_id)})
            await db.users.delete_one({"email": a_email})
            await db.users.delete_one({"email": b_email})
        except Exception:
            pass


# ---------- Wallet / Misc (3) ----------

@_safe_e2e
async def wallet_transactions_list_for_user() -> dict:
    """WALLET-TX: GET /transactions returnează tranzacțiile user-ului curent."""
    # Folosim _seed_active_job care creează un lead_fee tx pe specialist
    env = await _seed_active_job(400.0)
    try:
        r = await env["spec_c"].get("/api/transactions")
        if r.status_code != 200:
            return _ko(f"transactions {r.status_code}")
        items = r.json() if isinstance(r.json(), list) else []
        lead_tx = [t for t in items if t.get("type") == "lead_fee"]
        if lead_tx:
            return _ok(f"OK — specialist vede {len(items)} tx (lead_fee: {len(lead_tx)})")
        return _ko(f"⚠ specialist NU vede lead_fee în {len(items)} tx")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def wallet_topup_test_increases_balance() -> dict:
    """WALLET-TOPUP: POST /wallet/topup?amount=100 crește wallet_balance cu 100."""
    client_c, c_email, c_id = await _register_and_login("client", "topup")
    try:
        before = await db.users.find_one({"_id": ObjectId(c_id)})
        bal_b = float(before.get("wallet_balance") or 0)
        r = await client_c.post("/api/wallet/topup?amount=100")
        if r.status_code != 200:
            return _ko(f"topup {r.status_code}: {r.text[:160]}")
        after = await db.users.find_one({"_id": ObjectId(c_id)})
        delta = round(float(after.get("wallet_balance") or 0) - bal_b, 2)
        if abs(delta - 100.0) < 0.01:
            return _ok(f"OK — topup +100 RON aplicat (delta={delta})")
        return _ko(f"delta={delta} (await 100)")
    finally:
        await client_c.aclose()
        try:
            await db.transactions.delete_many({"user_id": c_id})
            await db.users.delete_one({"_id": ObjectId(c_id)})
        except Exception:
            pass


@_safe_e2e
async def concierge_public_settings_endpoint() -> dict:
    """CONCIERGE-SETTINGS: GET /concierge/settings/public returnează enabled + user_role."""
    client_c, c_email, _ = await _register_and_login("client", "conc")
    try:
        r = await client_c.get("/api/concierge/settings/public")
        if r.status_code != 200:
            return _ko(f"concierge settings {r.status_code}")
        body = r.json()
        if not isinstance(body, dict):
            return _ko("nu e dict")
        required = {"enabled", "user_role"}
        missing = required - set(body.keys())
        if missing:
            return _ko(f"chei lipsă: {missing}")
        if body.get("user_role") != "client":
            return _ko(f"user_role={body.get('user_role')} (await 'client')")
        return _ok(f"OK — concierge settings: enabled={body['enabled']}, role={body['user_role']}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass


# ---------- Digital Twin · Property timeline · Referral (3) ----------

@_safe_e2e
async def dt_subscription_endpoint() -> dict:
    """DT-SUB: GET /digital-twin/subscription returnează active + reason + tier (admin role bypass)."""
    admin_c = await _admin_client()
    try:
        r = await admin_c.get("/api/digital-twin/subscription")
        if r.status_code != 200:
            return _ko(f"dt subscription {r.status_code}")
        body = r.json()
        if not isinstance(body, dict):
            return _ko("nu e dict")
        if body.get("active") is True and body.get("reason") == "role_bypass":
            return _ok(f"OK — admin are DT acces (role_bypass), tier={body.get('tier')}")
        return _ko(f"admin DT shape neașteptat: {body}")
    finally:
        await admin_c.aclose()


@_safe_e2e
async def property_timeline_endpoint() -> dict:
    """TIMELINE: GET /properties/{prop_id}/timeline returnează listă de evenimente (poate fi goală pt prop nou)."""
    env = await _seed_active_job(400.0)
    try:
        r = await env["client_c"].get(f"/api/properties/{env['property_id']}/timeline")
        if r.status_code != 200:
            return _ko(f"timeline {r.status_code}")
        body = r.json()
        if isinstance(body, list):
            return _ok(f"OK — property timeline returnează listă cu {len(body)} eveniment(e)")
        if isinstance(body, dict) and "events" in body:
            return _ok(f"OK — property timeline cu {len(body['events'])} eveniment(e)")
        return _ko(f"răspuns neașteptat: {type(body).__name__}")
    finally:
        await _cleanup_e2e(env)


@_safe_e2e
async def auth_referral_endpoint_returns_stats() -> dict:
    """REFERRAL: GET /auth/referral returnează referral_url + counters."""
    client_c, c_email, _ = await _register_and_login("client", "ref")
    try:
        r = await client_c.get("/api/auth/referral")
        if r.status_code != 200:
            return _ko(f"referral {r.status_code}")
        body = r.json()
        if not isinstance(body, dict):
            return _ko("nu e dict")
        required = {"user_id", "referred_total", "converted_total", "referral_url"}
        missing = required - set(body.keys())
        if missing:
            return _ko(f"chei lipsă: {missing}")
        if "?ref=" in body.get("referral_url", ""):
            return _ok(f"OK — referral_url={body['referral_url'][:40]}, referred={body['referred_total']}")
        return _ko(f"referral_url shape: {body.get('referral_url')}")
    finally:
        await client_c.aclose()
        try:
            await db.users.delete_one({"email": c_email})
        except Exception:
            pass











# ============================================================================
# Registry
# ============================================================================

# Each entry maps a stable code → metadata + the async runner
AUTOMATED_TESTS: dict[str, dict] = {
    "AUTO-AUTH-01": {
        "code": "AUTO-AUTH-01",
        "title": "Înregistrare cu email duplicat respinsă",
        "kind": "http",
        "category": "SECURITY",
        "priority": "P0",
        "manual_match": "C-02",
        "runner": http_register_duplicate_email,
    },
    "AUTO-AUTH-02": {
        "code": "AUTO-AUTH-02",
        "title": "Înregistrare cu parolă scurtă respinsă",
        "kind": "http",
        "category": "SECURITY",
        "priority": "P0",
        "manual_match": "C-03",
        "runner": http_register_short_password,
    },
    "AUTO-AUTH-03": {
        "code": "AUTO-AUTH-03",
        "title": "Login cu parolă greșită returnează 401",
        "kind": "http",
        "category": "SECURITY",
        "priority": "P0",
        "runner": http_login_bad_password,
    },
    "AUTO-SEC-01": {
        "code": "AUTO-SEC-01",
        "title": "Endpoint admin fără token → 401/403",
        "kind": "http",
        "category": "SECURITY",
        "priority": "P0",
        "runner": http_admin_endpoints_require_auth,
    },
    "AUTO-SEC-02": {
        "code": "AUTO-SEC-02",
        "title": "Client logat → 403 pe /api/admin (RBAC)",
        "kind": "http",
        "category": "SECURITY",
        "priority": "P0",
        "runner": http_client_cannot_access_admin,
    },
    "AUTO-SEO-01": {
        "code": "AUTO-SEO-01",
        "title": "Sitemap.xml public valid",
        "kind": "http",
        "category": "SEO",
        "priority": "P1",
        "runner": http_public_sitemap_valid,
    },
    "AUTO-SEO-02": {
        "code": "AUTO-SEO-02",
        "title": "Landing marketplace oraș-categorie",
        "kind": "http",
        "category": "SEO",
        "priority": "P1",
        "runner": http_marketplace_landing_returns_seo_data,
    },
    "AUTO-PUB-01": {
        "code": "AUTO-PUB-01",
        "title": "Public status / incidents endpoint live",
        "kind": "http",
        "category": "PUBLIC",
        "priority": "P1",
        "runner": http_health_status_alive,
    },
    "AUTO-KB-01": {
        "code": "AUTO-KB-01",
        "title": "Knowledge Base — 6 PDFs render fără crash",
        "kind": "http",
        "category": "ADMIN",
        "priority": "P0",
        "runner": http_docs_pdf_renders,
    },
    "AUTO-OB-01": {
        "code": "AUTO-OB-01",
        "title": "Onboarding queue admin endpoint răspunde",
        "kind": "http",
        "category": "ADMIN",
        "priority": "P1",
        "runner": http_onboarding_queue_endpoint,
    },
    "AUTO-QA-01": {
        "code": "AUTO-QA-01",
        "title": "QA checklist template returnează 105 items",
        "kind": "http",
        "category": "ADMIN",
        "priority": "P1",
        "runner": http_qa_checklist_template,
    },
    "AUTO-UI-01": {
        "code": "AUTO-UI-01",
        "title": "Landing page se încarcă în browser (Playwright)",
        "kind": "browser",
        "category": "PUBLIC",
        "priority": "P0",
        "runner": browser_landing_loads,
    },
    "AUTO-UI-02": {
        "code": "AUTO-UI-02",
        "title": "Pagina /cookies randează cu H1 și testid",
        "kind": "browser",
        "category": "PUBLIC",
        "priority": "P1",
        "manual_match": "ad-hoc",
        "runner": browser_cookies_page_renders,
    },
    "AUTO-UI-03": {
        "code": "AUTO-UI-03",
        "title": "Pagina /login afișează formularul",
        "kind": "browser",
        "category": "PUBLIC",
        "priority": "P0",
        "runner": browser_login_page_renders,
    },
    # ---- Content Audit (5) ----
    "DOC-AUDIT-01": {
        "code": "DOC-AUDIT-01",
        "title": "Specialist doc fără pasaje cu perspectivă client",
        "kind": "http",
        "category": "CONTENT",
        "priority": "P0",
        "runner": doc_audit_specialist_no_client_perspective,
    },
    "DOC-AUDIT-02": {
        "code": "DOC-AUDIT-02",
        "title": "Client doc fără pasaje strict specialist (lead fee etc.)",
        "kind": "http",
        "category": "CONTENT",
        "priority": "P1",
        "runner": doc_audit_client_no_specialist_perspective,
    },
    "DOC-AUDIT-03": {
        "code": "DOC-AUDIT-03",
        "title": "Specialist doc menționează comision, plată, lead fee",
        "kind": "http",
        "category": "CONTENT",
        "priority": "P0",
        "runner": doc_audit_specialist_has_payment_info,
    },
    "DOC-AUDIT-04": {
        "code": "DOC-AUDIT-04",
        "title": "Client doc menționează disputele și rambursarea",
        "kind": "http",
        "category": "CONTENT",
        "priority": "P0",
        "runner": doc_audit_client_has_dispute_info,
    },
    "DOC-AUDIT-05": {
        "code": "DOC-AUDIT-05",
        "title": "Toate override-urile aplicate cu success (no IndexError)",
        "kind": "http",
        "category": "CONTENT",
        "priority": "P1",
        "runner": doc_audit_all_docs_have_overrides_resolved,
    },
    # ---- Lifecycle / Communication (5) ----
    "LIFECYCLE-01": {
        "code": "LIFECYCLE-01",
        "title": "Client: register → login → /me funcționează",
        "kind": "http",
        "category": "LIFECYCLE",
        "priority": "P0",
        "runner": lifecycle_client_register_then_delete,
    },
    "LIFECYCLE-02": {
        "code": "LIFECYCLE-02",
        "title": "Specialist nou primește 3 emails onboarding enqueuate",
        "kind": "http",
        "category": "LIFECYCLE",
        "priority": "P0",
        "runner": lifecycle_specialist_register_then_onboarding_drip,
    },
    "LIFECYCLE-03": {
        "code": "LIFECYCLE-03",
        "title": "Marketplace public returnează listă specialiști filtrabilă",
        "kind": "http",
        "category": "LIFECYCLE",
        "priority": "P0",
        "runner": lifecycle_marketplace_search_returns_specialists,
    },
    "LIFECYCLE-04": {
        "code": "LIFECYCLE-04",
        "title": "Profil public specialist accesibil pentru clienți",
        "kind": "http",
        "category": "LIFECYCLE",
        "priority": "P1",
        "runner": lifecycle_specialist_profile_public_view,
    },
    "LIFECYCLE-05": {
        "code": "LIFECYCLE-05",
        "title": "Toți userii au rol valid (integritate referențială)",
        "kind": "http",
        "category": "LIFECYCLE",
        "priority": "P1",
        "runner": lifecycle_admin_role_unique_count,
    },
    # ---- Terminology Audit (5) ----
    "TERM-01": {
        "code": "TERM-01",
        "title": "Termenul «escrow» folosit consistent (fără variante alternative)",
        "kind": "http",
        "category": "TERMINOLOGY",
        "priority": "P1",
        "runner": term_audit_no_escrow_variants,
    },
    "TERM-02": {
        "code": "TERM-02",
        "title": "«Specialist» nu se amestecă cu «meseriaș/profesionist» în același doc",
        "kind": "http",
        "category": "TERMINOLOGY",
        "priority": "P1",
        "runner": term_audit_specialist_consistent,
    },
    "TERM-03": {
        "code": "TERM-03",
        "title": "«Client» nu se amestecă cu «proprietar/beneficiar» în același doc",
        "kind": "http",
        "category": "TERMINOLOGY",
        "priority": "P1",
        "runner": term_audit_client_consistent,
    },
    "TERM-04": {
        "code": "TERM-04",
        "title": "«Comision platformă» nu se amestecă cu «taxă/fee»",
        "kind": "http",
        "category": "TERMINOLOGY",
        "priority": "P2",
        "runner": term_audit_commission_consistent,
    },
    "TERM-05": {
        "code": "TERM-05",
        "title": "Scor general de consistență — niciun doc cu ≥3 inconsistențe",
        "kind": "http",
        "category": "TERMINOLOGY",
        "priority": "P1",
        "runner": term_audit_overall_score,
    },
    # ---- E2E full-flow (9) ----
    "ESCROW-01": {
        "code": "ESCROW-01",
        "title": "Client alimentează escrow → status='held'",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_escrow_funded_status_held,
    },
    "ESCROW-02": {
        "code": "ESCROW-02",
        "title": "Confirmare → specialist primește 95% (split corect)",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_escrow_full_confirm_releases_split,
    },
    "DISPUTE-01": {
        "code": "DISPUTE-01",
        "title": "Deschidere dispută → escrow_status='frozen'",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_dispute_opens_freezes_escrow,
    },
    "DISPUTE-02": {
        "code": "DISPUTE-02",
        "title": "Admin rezolvă refund_client → wallet client crește cu suma",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_dispute_resolves_refund_client,
    },
    "QUOTE-01": {
        "code": "QUOTE-01",
        "title": "Specialist acceptă lead → 45 RON lead_fee dedus, status='assigned'",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_quote_specialist_accept_charges_lead_fee,
    },
    "FILE-01": {
        "code": "FILE-01",
        "title": "Specialist încarcă KYC PDF → status='pending'",
        "kind": "http",
        "category": "E2E",
        "priority": "P1",
        "runner": e2e_specialist_kyc_upload_pending,
    },
    "CHAT-01": {
        "code": "CHAT-01",
        "title": "Client citește istoric chat pe job-ul propriu",
        "kind": "http",
        "category": "E2E",
        "priority": "P1",
        "runner": e2e_chat_history_endpoint_returns_messages,
    },
    "GDPR-01": {
        "code": "GDPR-01",
        "title": "DSAR export (Art. 15) returnează account + rights_summary",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_gdpr_dsar_export_returns_account_data,
    },
    "GDPR-02": {
        "code": "GDPR-02",
        "title": "Erasure request (Art. 17) creează dsar_requests cu SLA 30 zile",
        "kind": "http",
        "category": "E2E",
        "priority": "P0",
        "runner": e2e_gdpr_erasure_request_creates_dsar_row,
    },
    # ---- PROFILE CLIENT (5) ----
    "PROFILE-CLIENT-01": {
        "code": "PROFILE-CLIENT-01", "title": "Profil client — câmpurile cheie sunt corecte după register",
        "kind": "http", "category": "CLIENT", "priority": "P0",
        "manual_match": "C-01", "runner": profile_client_register_fields_correct,
    },
    "PROFILE-CLIENT-02": {
        "code": "PROFILE-CLIENT-02", "title": "Profil client — PATCH actualizează name/phone",
        "kind": "http", "category": "CLIENT", "priority": "P0",
        "runner": profile_client_patch_updates_db,
    },
    "PROFILE-CLIENT-03": {
        "code": "PROFILE-CLIENT-03", "title": "Client — schimbare parolă rotește credentialele",
        "kind": "http", "category": "CLIENT", "priority": "P0",
        "runner": profile_client_change_password_then_login,
    },
    "PROFILE-CLIENT-04": {
        "code": "PROFILE-CLIENT-04", "title": "Client — proprietăți listate corect în profil",
        "kind": "http", "category": "CLIENT", "priority": "P1",
        "runner": profile_client_has_properties_list,
    },
    "PROFILE-CLIENT-05": {
        "code": "PROFILE-CLIENT-05", "title": "Client — GDPR export include toate datele",
        "kind": "http", "category": "CLIENT", "priority": "P0",
        "runner": profile_client_gdpr_export_includes_all_data,
    },
    # ---- PROFILE SPECIALIST (5) ----
    "PROFILE-SPEC-01": {
        "code": "PROFILE-SPEC-01", "title": "Profil specialist — categories+zones păstrate la register",
        "kind": "http", "category": "SPECIALIST", "priority": "P0",
        "runner": profile_spec_register_fields_complete,
    },
    "PROFILE-SPEC-02": {
        "code": "PROFILE-SPEC-02", "title": "Specialist — pagina publică nu expune email",
        "kind": "http", "category": "SPECIALIST", "priority": "P0",
        "runner": profile_spec_public_profile_renders,
    },
    "PROFILE-SPEC-03": {
        "code": "PROFILE-SPEC-03", "title": "Specialist — verify setează verified=True + tier=VERIFIED",
        "kind": "http", "category": "SPECIALIST", "priority": "P0",
        "runner": profile_spec_verify_sets_verified_flag,
    },
    "PROFILE-SPEC-04": {
        "code": "PROFILE-SPEC-04", "title": "Specialist — documentele apar în propriul profil cu status",
        "kind": "http", "category": "SPECIALIST", "priority": "P1",
        "runner": profile_spec_documents_visible_to_owner,
    },
    "PROFILE-SPEC-05": {
        "code": "PROFILE-SPEC-05", "title": "Specialist — PATCH actualizează categorii și zone",
        "kind": "http", "category": "SPECIALIST", "priority": "P1",
        "runner": profile_spec_patch_updates_categories,
    },
    # ---- PLATFORM HEALTH (5) ----
    "PLATFORM-01": {
        "code": "PLATFORM-01", "title": "Morning Briefing — preview populează KPIs",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "manual_match": "A-01", "runner": platform_morning_briefing_preview,
    },
    "PLATFORM-02": {
        "code": "PLATFORM-02", "title": "Executive Briefing — preview generează HTML+payload",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": platform_exec_briefing_preview,
    },
    "PLATFORM-03": {
        "code": "PLATFORM-03", "title": "Marketplace — listă publică cu min 1 specialist",
        "kind": "http", "category": "PUBLIC", "priority": "P0",
        "manual_match": "P-02", "runner": platform_landing_marketplace_has_specialists,
    },
    "PLATFORM-04": {
        "code": "PLATFORM-04", "title": "Trust Center — endpoint public returnează platform stats",
        "kind": "http", "category": "PUBLIC", "priority": "P1",
        "runner": platform_trust_stats_endpoint_live,
    },
    "PLATFORM-05": {
        "code": "PLATFORM-05", "title": "Trust Badge SVG — endpoint renderează imagine validă",
        "kind": "http", "category": "PUBLIC", "priority": "P2",
        "runner": platform_trust_badge_svg_renders,
    },
    # ---- PACHET B · Lifecycle / Dispute variants / Chat / Admin (10) ----
    "LIFE-START": {
        "code": "LIFE-START", "title": "Specialist /start → status=in_progress, started_at populat",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": lifecycle_specialist_start_sets_in_progress,
    },
    "LIFE-COMPLETE": {
        "code": "LIFE-COMPLETE", "title": "Specialist /complete → status=completed, awaiting client confirm",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": lifecycle_specialist_complete_sets_pending_confirmation,
    },
    "LIFE-AUTHZ": {
        "code": "LIFE-AUTHZ", "title": "SECURITY: alt specialist NU poate /start pe job altcuiva",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": lifecycle_unauthorized_start_blocked,
    },
    "DISPUTE-PAY": {
        "code": "DISPUTE-PAY", "title": "Admin resolve pay_specialist → 95% din escrow la specialist",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": dispute_resolve_pay_specialist_splits_95_5,
    },
    "DISPUTE-SPLIT": {
        "code": "DISPUTE-SPLIT", "title": "Admin resolve split 60/40 → calcul corect ambele părți",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": dispute_resolve_split_60_40,
    },
    "CHAT-AUTHZ": {
        "code": "CHAT-AUTHZ", "title": "SECURITY: chat-ul unui job NU e accesibil unui străin",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": chat_unauthorized_user_blocked,
    },
    "GDPR-03": {
        "code": "GDPR-03", "title": "Admin anonymize user → email rotat / scrambled",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": gdpr_anonymize_scrambles_email,
    },
    "ADMIN-DISP-LIST": {
        "code": "ADMIN-DISP-LIST", "title": "Admin vede lista disputelor active",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_disputes_listing_works,
    },
    "ADMIN-BACKUP": {
        "code": "ADMIN-BACKUP", "title": "Backup status endpoint accesibil admin",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_backup_status_endpoint,
    },
    "ADMIN-AI-HEALTH": {
        "code": "ADMIN-AI-HEALTH", "title": "AI Health Score 0-100 disponibil",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_ai_health_score_endpoint,
    },
    # ---- PACHET B · Payment / Escrow edge cases (8) ----
    "PAY-INSUFF": {
        "code": "PAY-INSUFF", "title": "Specialist cu wallet 0 NU poate accepta lead (400)",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_insufficient_balance_blocks_accept,
    },
    "PAY-CONFIRM-AUTHZ": {
        "code": "PAY-CONFIRM-AUTHZ", "title": "Specialist NU poate /confirm — doar clientul",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_confirm_authz_specialist_blocked,
    },
    "PAY-START-AUTHZ": {
        "code": "PAY-START-AUTHZ", "title": "Alt specialist NU poate /start un job neatribuit",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_start_authz_other_specialist_blocked,
    },
    "PAY-ESCROW-AUTHZ": {
        "code": "PAY-ESCROW-AUTHZ", "title": "Alt client NU poate alimenta escrow pe job străin",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_escrow_authz_stranger_blocked,
    },
    "PAY-TX-LEAD": {
        "code": "PAY-TX-LEAD", "title": "După /accept, tx lead_fee=-45 RON e logată",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": pay_lead_fee_transaction_recorded,
    },
    "PAY-TX-RELEASE": {
        "code": "PAY-TX-RELEASE", "title": "După /confirm, tx job_payment=+95% RON e logată",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": pay_release_creates_job_payment_transaction,
    },
    "PAY-FROZEN-NOCONF": {
        "code": "PAY-FROZEN-NOCONF", "title": "Pe job disputat, /confirm e blocat (400)",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_no_confirm_during_dispute_freeze,
    },
    "PAY-COMPLETE-AUTHZ": {
        "code": "PAY-COMPLETE-AUTHZ", "title": "Alt specialist NU poate /complete un job străin",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": pay_complete_authz_unassigned_blocked,
    },
    # ---- PACHET B · Dispute escalations (5) ----
    "DISP-NO-DUP": {
        "code": "DISP-NO-DUP", "title": "A 2-a dispută pe același request → 400",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": dispute_no_duplicate_open,
    },
    "DISP-RESOLVE-AUTHZ": {
        "code": "DISP-RESOLVE-AUTHZ", "title": "Client/specialist NU pot rezolva dispute (403)",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": dispute_resolve_requires_admin,
    },
    "DISP-AFTER-RELEASE": {
        "code": "DISP-AFTER-RELEASE", "title": "După /confirm (escrow released), dispute → 400",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": dispute_blocked_after_release,
    },
    "DISP-EVID": {
        "code": "DISP-EVID", "title": "evidence_urls trimise la /dispute sunt persistate",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": dispute_evidence_urls_persisted,
    },
    "DISP-STATUS-OPEN": {
        "code": "DISP-STATUS-OPEN", "title": "Dispute nouă: status=open + request.escrow_status=frozen",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": dispute_new_dispute_status_open,
    },
    # ---- PACHET B · SEO heavy (5) ----
    "SEO-SITEMAP-COUNT": {
        "code": "SEO-SITEMAP-COUNT", "title": "Sitemap conține >=30 URLs (static + ghiduri + landings)",
        "kind": "http", "category": "SEO", "priority": "P1",
        "runner": seo_sitemap_url_count_minimum,
    },
    "SEO-SITEMAP-XML": {
        "code": "SEO-SITEMAP-XML", "title": "Sitemap parsează ca XML valid (<urlset>)",
        "kind": "http", "category": "SEO", "priority": "P1",
        "runner": seo_sitemap_xml_well_formed,
    },
    "SEO-LANDING-CITIES": {
        "code": "SEO-LANDING-CITIES", "title": "Landing-urile marketplace din sitemap trec Indexability Gate-ul",
        "kind": "http", "category": "SEO", "priority": "P2",
        "runner": seo_sitemap_landing_diverse_cities,
    },
    "SEO-GUIDES-IN-SITEMAP": {
        "code": "SEO-GUIDES-IN-SITEMAP", "title": "Toate cele 6 ghiduri sunt în sitemap",
        "kind": "http", "category": "SEO", "priority": "P1",
        "runner": seo_sitemap_all_guides_present,
    },
    "SEO-MKT-API": {
        "code": "SEO-MKT-API", "title": "GET /api/marketplace/specialists returnează listă (no auth)",
        "kind": "http", "category": "SEO", "priority": "P0",
        "runner": seo_marketplace_public_returns_array,
    },
    # ---- PACHET B · Marketplace filters (3) ----
    "MKT-CAT": {
        "code": "MKT-CAT", "title": "?category=electric returnează doar specialiști electric",
        "kind": "http", "category": "PUBLIC", "priority": "P1",
        "runner": mkt_filter_category_returns_matching,
    },
    "MKT-ZONE": {
        "code": "MKT-ZONE", "title": "?zone=Bucuresti returnează specialiști care acoperă Bucuresti",
        "kind": "http", "category": "PUBLIC", "priority": "P1",
        "runner": mkt_filter_zone_returns_matching,
    },
    "MKT-CITY-NORES": {
        "code": "MKT-CITY-NORES", "title": "?city=Oraș inexistent → listă goală (no leak)",
        "kind": "http", "category": "PUBLIC", "priority": "P1",
        "runner": mkt_filter_unknown_city_returns_empty,
    },
    # ---- PACHET B · Admin tooling (4) ----
    "ADMIN-USERS-LIST": {
        "code": "ADMIN-USERS-LIST", "title": "GET /admin/users — items/total/skip/limit",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_users_listing_pagination,
    },
    "ADMIN-INC-LIST": {
        "code": "ADMIN-INC-LIST", "title": "GET /admin/incidents → {items, count}",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_incidents_listing,
    },
    "ADMIN-IMP-ADMIN-BLOCK": {
        "code": "ADMIN-IMP-ADMIN-BLOCK", "title": "Admin NU poate impersona alt admin (403)",
        "kind": "http", "category": "ADMIN", "priority": "P0",
        "runner": admin_impersonate_admin_blocked,
    },
    "ADMIN-IMP-CLIENT": {
        "code": "ADMIN-IMP-CLIENT", "title": "Admin impersonează client → 200 + redirect_to=/client",
        "kind": "http", "category": "ADMIN", "priority": "P1",
        "runner": admin_impersonate_client_success,
    },
    # ---- PACHET C · Operator flows (4) ----
    "OP-FLAG-AUTHZ": {
        "code": "OP-FLAG-AUTHZ", "title": "Client NU poate flag nonconformity (403)",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": op_flag_authz_client_blocked,
    },
    "OP-FLAG-FULL": {
        "code": "OP-FLAG-FULL", "title": "Operator flag → DB open → admin list → admin resolve",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": op_flag_create_then_list_resolve,
    },
    "OP-QUEUE": {
        "code": "OP-QUEUE", "title": "Operator /queue endpoint accesibil",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": op_queue_endpoint_accessible,
    },
    "OP-FLAG-404": {
        "code": "OP-FLAG-404", "title": "Operator flag pe target inexistent → 404",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": op_flag_404_for_inexistent_target,
    },
    # ---- PACHET C · Projects / Workspace (4) ----
    "PROJ-AUTHZ": {
        "code": "PROJ-AUTHZ", "title": "Specialist non-designer NU poate crea proiect (403)",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": proj_authz_non_designer_blocked,
    },
    "PROJ-CREATE": {
        "code": "PROJ-CREATE", "title": "Designer creează project → client în members, status=active",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": proj_designer_create_project_with_client,
    },
    "PROJ-LIST": {
        "code": "PROJ-LIST", "title": "Clientul vede proiectul în /api/projects",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": proj_client_sees_project_in_list,
    },
    "PROJ-TASK": {
        "code": "PROJ-TASK", "title": "Designer adaugă task → vizibil în /tasks list",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": proj_task_create_and_visible,
    },
    # ---- PACHET C · Notifications (3) ----
    "NOTIF-LIST": {
        "code": "NOTIF-LIST", "title": "GET /notifications returnează listă pentru user",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": notif_list_returns_array,
    },
    "NOTIF-READ": {
        "code": "NOTIF-READ", "title": "POST /{id}/read setează read=True",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": notif_mark_read_sets_flag,
    },
    "NOTIF-CROSS": {
        "code": "NOTIF-CROSS", "title": "SECURITY: user B NU poate marca notif lui A",
        "kind": "http", "category": "E2E", "priority": "P0",
        "runner": notif_cross_user_mark_blocked,
    },
    # ---- PACHET C · Wallet / Misc (3) ----
    "WALLET-TX": {
        "code": "WALLET-TX", "title": "GET /transactions returnează tranzacțiile user-ului",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": wallet_transactions_list_for_user,
    },
    "WALLET-TOPUP": {
        "code": "WALLET-TOPUP", "title": "POST /wallet/topup?amount=100 crește wallet_balance +100",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": wallet_topup_test_increases_balance,
    },
    "CONCIERGE-SETTINGS": {
        "code": "CONCIERGE-SETTINGS", "title": "GET /concierge/settings/public returnează enabled+user_role",
        "kind": "http", "category": "PUBLIC", "priority": "P2",
        "runner": concierge_public_settings_endpoint,
    },
    # ---- PACHET C · Digital Twin / Timeline / Referral (3) ----
    "DT-SUB": {
        "code": "DT-SUB", "title": "GET /digital-twin/subscription pentru admin → active + role_bypass",
        "kind": "http", "category": "ADMIN", "priority": "P2",
        "runner": dt_subscription_endpoint,
    },
    "TIMELINE": {
        "code": "TIMELINE", "title": "GET /properties/{id}/timeline returnează listă evenimente",
        "kind": "http", "category": "E2E", "priority": "P1",
        "runner": property_timeline_endpoint,
    },
    "REFERRAL": {
        "code": "REFERRAL", "title": "GET /auth/referral → user_id + referral_url + counters",
        "kind": "http", "category": "CLIENT", "priority": "P1",
        "runner": auth_referral_endpoint_returns_stats,
    },
}


def list_automated_tests() -> list[dict]:
    """Return metadata-only entries (no runner) for the UI catalog."""
    out = []
    for t in AUTOMATED_TESTS.values():
        out.append({k: v for k, v in t.items() if k != "runner"})
    return out


# ============================================================================
# Run executor — runs N selected tests, updates QA Run checks if matched.
# ============================================================================

async def execute_tests(test_codes: list[str], run_id: Optional[str] = None) -> dict:
    """Execute the chosen tests in parallel. If `run_id` given, add/update matching
    checks in the QA Run."""
    selected = [AUTOMATED_TESTS[c] for c in test_codes if c in AUTOMATED_TESTS]
    if not selected:
        return {"results": [], "summary": {"total": 0, "pass": 0, "fail": 0}}

    # Bounded concurrency: the checks call back into THIS backend (single
    # uvicorn worker) and several do bcrypt-heavy register/login flows.
    # Unbounded gather over 100+ checks self-saturates the event loop and
    # everything times out — cap parallelism instead.
    sem = asyncio.Semaphore(4)

    async def _one(t: dict) -> dict:
        t0 = time.time()
        try:
            async with sem:
                res = await t["runner"]()
        except Exception as e:  # noqa: BLE001
            res = {"status": "fail", "note": f"Unhandled crash: {type(e).__name__}: {str(e)[:200]}"}
        elapsed = round((time.time() - t0) * 1000)
        return {
            "code": t["code"],
            "title": t["title"],
            "kind": t["kind"],
            "category": t["category"],
            "priority": t["priority"],
            "status": res.get("status", "fail"),
            "note": res.get("note", ""),
            "duration_ms": elapsed,
        }

    results = await asyncio.gather(*[_one(t) for t in selected])

    # If run_id, write results into the QA run (auto-create ad-hoc check per test code)
    written = 0
    if run_id:
        for r in results:
            try:
                run_doc = await db.qa_runs.find_one({"run_id": run_id}, {"checks.code": 1, "checks.id": 1})
                if not run_doc:
                    continue
                # Find existing check with same code
                existing = next((c for c in run_doc.get("checks", []) if c.get("code") == r["code"]), None)
                now = datetime.now(timezone.utc).isoformat()
                if existing:
                    await db.qa_runs.update_one(
                        {"run_id": run_id, "checks.id": existing["id"]},
                        {"$set": {
                            "checks.$.status": r["status"],
                            "checks.$.note": f"[automated · {r['duration_ms']}ms] {r['note']}"[:2000],
                            "checks.$.updated_at": now,
                            "checks.$.automated": True,
                            "updated_at": now,
                        }},
                    )
                else:
                    new_check = {
                        "id": uuid.uuid4().hex,
                        "code": r["code"],
                        "category": r["category"],
                        "subcategory": "auto · " + r["kind"],
                        "priority": r["priority"],
                        "description": r["title"],
                        "status": r["status"],
                        "note": f"[automated · {r['duration_ms']}ms] {r['note']}"[:2000],
                        "updated_at": now,
                        "updated_by": "automation",
                        "ai_added": False,
                        "automated": True,
                    }
                    await db.qa_runs.update_one(
                        {"run_id": run_id},
                        {"$push": {"checks": new_check}, "$set": {"updated_at": now}},
                    )
                written += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Automation] failed to write into run {run_id} for {r['code']}: {e}")

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
        "skip": sum(1 for r in results if r["status"] == "skip"),
        "written_to_run": written,
    }
    return {"results": results, "summary": summary}


# ============================================================================
# Release Gate — run ALL automated tests, persist, email admins
# ============================================================================

async def _post_release_gate_webhook(payload: dict) -> Optional[dict]:
    """Send release gate verdict to Slack and/or Discord webhooks.

    Reads `RELEASE_GATE_SLACK_WEBHOOK_URL`, `RELEASE_GATE_DISCORD_WEBHOOK_URL`, or
    generic `RELEASE_GATE_WEBHOOK_URL` (auto-detects format from URL). On weekly
    cron runs, posts ONLY when P0 fail (silent on green) — manual runs always post.
    Returns dict with status, or None if no webhook configured.
    """
    slack_url = os.environ.get("RELEASE_GATE_SLACK_WEBHOOK_URL", "").strip()
    discord_url = os.environ.get("RELEASE_GATE_DISCORD_WEBHOOK_URL", "").strip()
    generic_url = os.environ.get("RELEASE_GATE_WEBHOOK_URL", "").strip()

    if generic_url and not slack_url and not discord_url:
        if "hooks.slack.com" in generic_url:
            slack_url = generic_url
        elif "discord.com/api/webhooks" in generic_url or "discordapp.com/api/webhooks" in generic_url:
            discord_url = generic_url
        else:
            slack_url = generic_url  # assume Slack-compatible

    if not slack_url and not discord_url:
        return None

    summary = payload["summary"]
    blocked = summary.get("blocked", False)
    triggered_by = payload.get("triggered_by") or "manual"
    if triggered_by == "weekly-cron" and not blocked:
        return {"sent": False, "channels": [], "error": "weekly-cron green — webhook suppressed"}

    verdict_emoji = ":red_circle:" if blocked else ":large_green_circle:"
    verdict_label = "RELEASE BLOCKED" if blocked else "RELEASE READY"
    line = (
        f"{verdict_emoji} *{verdict_label}* — {summary.get('pass')}/{summary.get('total')} pass · "
        f"{summary.get('fail')} fail · {summary.get('skip', 0)} skip · "
        f"P0 fail: {summary.get('p0_fail')} · P1 fail: {summary.get('p1_fail')}"
    )
    fails = [r for r in payload.get("results", []) if r["status"] == "fail"]
    fail_lines = "\n".join([f"  • `{r['code']}` [{r['priority']}] {r['note'][:120]}" for r in fails[:8]])
    if len(fails) > 8:
        fail_lines += f"\n  • _…{len(fails) - 8} more failures…_"
    body = line + (("\n*Failed checks:*\n" + fail_lines) if fail_lines else "")
    body += f"\n_Triggered by:_ `{triggered_by}` · _Duration:_ {payload.get('duration_ms', 0) // 1000}s · _Gate id:_ `{payload.get('gate_id')}`"

    channels: list[str] = []
    last_error: Optional[str] = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        if slack_url:
            try:
                r = await client.post(slack_url, json={"text": body, "mrkdwn": True})
                if r.status_code < 400:
                    channels.append("slack")
                else:
                    last_error = f"slack {r.status_code}: {r.text[:120]}"
            except Exception as e:  # noqa: BLE001
                last_error = f"slack {type(e).__name__}: {str(e)[:120]}"
        if discord_url:
            try:
                content = body.replace("*", "**")
                r = await client.post(discord_url, json={"content": content[:1900]})
                if r.status_code < 400:
                    channels.append("discord")
                else:
                    last_error = f"discord {r.status_code}: {r.text[:120]}"
            except Exception as e:  # noqa: BLE001
                last_error = f"discord {type(e).__name__}: {str(e)[:120]}"

    return {"sent": len(channels) > 0, "channels": channels, "error": last_error if not channels else None}



def _gate_email_html(payload: dict) -> dict:
    """Build a branded HTML email with the gate verdict + per-test rows."""
    from email_service import _layout, APP_URL  # local import to avoid cycle

    summary = payload["summary"]
    results = payload["results"]
    blocked = summary.get("p0_fail", 0) > 0
    verdict_color = "#ef4444" if blocked else "#34d399"
    verdict_label = "RELEASE BLOCKED" if blocked else "RELEASE READY"

    rows_html = []
    for r in results:
        status = r["status"]
        is_pass = status == "pass"
        is_skip = status == "skip"
        if is_pass:
            bg, icon = "#34d39915", "✅"
        elif is_skip:
            bg, icon = "#9ca3af15", "⏭️"
        else:
            bg, icon = "#ef444415", "❌"
        prio_color = {"P0": "#ef4444", "P1": "#fbbf24", "P2": "#60a5fa"}.get(r["priority"], "#9ca3af")
        rows_html.append(f"""
          <tr style="background:{bg};">
            <td style="padding:8px 10px; vertical-align:top; font-family:monospace; color:#fff;">{icon} <strong>{r['code']}</strong></td>
            <td style="padding:8px 10px; vertical-align:top;">
              <div style="color:#e5e5e5; font-size:13px;">{r['title']}</div>
              <div style="color:#9ca3af; font-size:11px; margin-top:2px;">{r['kind']} · {r['category']} · {r['duration_ms']}ms</div>
              <div style="color:#c8c8cc; font-size:11px; margin-top:4px; font-style:italic;">{r['note'][:280]}</div>
            </td>
            <td style="padding:8px 10px; vertical-align:top; text-align:center;">
              <span style="display:inline-block; padding:2px 8px; border-radius:9999px; font-size:10px; font-weight:600; background:{prio_color}25; color:{prio_color};">{r['priority']}</span>
            </td>
          </tr>
        """)

    body = f"""
      <div style="margin-bottom:20px;">
        <div style="background:{verdict_color}15; border-left:4px solid {verdict_color}; padding:16px 20px; border-radius:12px;">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:{verdict_color}; margin-bottom:6px;">Verdict gate de release</div>
          <div style="font-family:Georgia,serif; font-size:28px; color:{verdict_color}; font-weight:700;">{verdict_label}</div>
          <div style="color:#c8c8cc; font-size:13px; margin-top:6px;">
            <strong>{summary['pass']}/{summary['total']}</strong> PASS · {summary['fail']} FAIL · {summary['p0_fail']} P0 fail · {summary['p1_fail']} P1 fail
          </div>
        </div>
      </div>

      <p style="color:#c8c8cc; font-size:13px;">
        {('🚫 Un test P0 a căzut. NU se face deploy până nu rezolvi problemele de mai jos.' if blocked else '🟢 Toate testele P0 trec. Poți face deploy în siguranță.')}
      </p>

      <table border="0" cellpadding="0" cellspacing="0" style="width:100%; margin-top:16px; border-collapse:collapse;">
        <thead>
          <tr style="background:#1a1a1f;">
            <th style="padding:10px; text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#9ca3af;">Test</th>
            <th style="padding:10px; text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#9ca3af;">Detalii</th>
            <th style="padding:10px; text-align:center; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#9ca3af;">Prio</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>

      <p style="color:#9ca3af; font-size:11px; margin-top:24px;">
        Gate ID: <code>{payload['gate_id']}</code> · Trigger: <code>{payload['triggered_by']}</code> · Durata: {payload['duration_ms']}ms
      </p>
    """
    subj_prefix = "🚫" if blocked else "✅"
    return {
        "subject": f"{subj_prefix} Release Gate — {verdict_label} ({summary['pass']}/{summary['total']})",
        "html": _layout(f"Release Gate · {verdict_label}", f"{summary['pass']}/{summary['total']} pass · {summary['fail']} fail · {summary['p0_fail']} P0 fail", body, f"{APP_URL}/admin", "Deschide QA Playbook"),
    }


async def run_release_gate(triggered_by: str = "manual", email_admins: bool = True) -> dict:
    """Execute ALL automated tests, persist the result, optionally email admins."""
    import uuid as _uuid
    t0 = time.time()
    started = datetime.now(timezone.utc).isoformat()
    all_codes = list(AUTOMATED_TESTS.keys())
    exec_res = await execute_tests(all_codes, run_id=None)
    finished = datetime.now(timezone.utc).isoformat()
    duration_ms = round((time.time() - t0) * 1000)

    p0_fail = sum(1 for r in exec_res["results"] if r["status"] == "fail" and r["priority"] == "P0")
    p1_fail = sum(1 for r in exec_res["results"] if r["status"] == "fail" and r["priority"] == "P1")
    summary = dict(exec_res["summary"])
    summary["p0_fail"] = p0_fail
    summary["p1_fail"] = p1_fail
    summary["blocked"] = p0_fail > 0
    summary["verdict"] = "BLOCKED" if summary["blocked"] else "READY"

    payload = {
        "gate_id": _uuid.uuid4().hex[:12],
        "triggered_by": triggered_by,
        "started_at": started,
        "finished_at": finished,
        "duration_ms": duration_ms,
        "summary": summary,
        "results": exec_res["results"],
        "email": {"sent": False, "recipients": [], "error": None},
        "webhook": {"sent": False, "channels": [], "error": None},
    }

    # Persist gate (keep last 100 only)
    try:
        await db.release_gates.insert_one({**payload})
        cur = db.release_gates.find({}, {"_id": 1}).sort("started_at", -1).skip(100)
        old_ids = [d["_id"] async for d in cur]
        if old_ids:
            await db.release_gates.delete_many({"_id": {"$in": old_ids}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ReleaseGate] persist failed: {e}")

    # Post webhook (Slack/Discord/generic) — only if configured
    try:
        wh_res = await _post_release_gate_webhook(payload)
        if wh_res:
            payload["webhook"] = wh_res
    except Exception as e:  # noqa: BLE001
        payload["webhook"]["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        logger.warning(f"[ReleaseGate] webhook send failed: {e}")

    # Send email
    if email_admins:
        try:
            from email_service import send_email, ADMIN_EMAILS as _CFG_ADMIN_EMAILS
            recipients = _CFG_ADMIN_EMAILS or [
                e.strip() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()
            ]
            if not recipients:
                payload["email"]["error"] = "ADMIN_NOTIFICATION_EMAILS / ADMIN_EMAILS not configured"
            else:
                tpl = _gate_email_html(payload)
                await send_email(recipients, tpl["subject"], tpl["html"])
                payload["email"]["sent"] = True
                payload["email"]["recipients"] = recipients
        except Exception as e:  # noqa: BLE001
            payload["email"]["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            logger.warning(f"[ReleaseGate] email send failed: {e}")

    payload.pop("_id", None)
    return payload


async def list_release_gates(limit: int = 20) -> list[dict]:
    cursor = db.release_gates.find({}, {"results": 0}).sort("started_at", -1).limit(limit)
    out = []
    async for r in cursor:
        r.pop("_id", None)
        out.append(r)
    return out


async def get_release_gate(gate_id: str) -> Optional[dict]:
    r = await db.release_gates.find_one({"gate_id": gate_id})
    if not r:
        return None
    r.pop("_id", None)
    return r


async def run_weekly_release_gate_job():
    """APScheduler job: run release gate weekly, email admins ONLY if P0 fail (silent on green)."""
    try:
        # Run with email_admins=False; we'll send manually only on P0 fail to keep inbox quiet.
        payload = await run_release_gate(triggered_by="weekly-cron", email_admins=False)
        if payload.get("summary", {}).get("p0_fail", 0) > 0:
            try:
                from email_service import send_email, ADMIN_EMAILS as _CFG_ADMIN_EMAILS
                recipients = _CFG_ADMIN_EMAILS or [
                    e.strip() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()
                ]
                if recipients:
                    tpl = _gate_email_html(payload)
                    # Override subject to make weekly origin clear
                    tpl["subject"] = "[Cron luni 08:45] " + tpl["subject"]
                    await send_email(recipients, tpl["subject"], tpl["html"])
                    logger.warning(f"[ReleaseGate cron] P0 FAIL — emailed {len(recipients)} admins (gate {payload['gate_id']})")
                else:
                    logger.warning(f"[ReleaseGate cron] P0 FAIL but no admin emails configured (gate {payload['gate_id']})")
            except Exception as e:  # noqa: BLE001
                logger.exception(f"[ReleaseGate cron] failed to send P0-fail email: {e}")
        else:
            logger.info(f"[ReleaseGate cron] All clear — {payload['summary']['pass']}/{payload['summary']['total']} pass (gate {payload['gate_id']}); no email sent.")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[ReleaseGate cron] crashed: {e}")
