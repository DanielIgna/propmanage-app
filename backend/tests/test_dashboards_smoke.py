"""
Pre-deploy smoke test — Dashboard sanity check
==============================================
Logs in as admin, then impersonates each of the 12 demo profiles
(3 base + 3 client tiers + 6 specialist tiers) and verifies:
  - dashboard page loads (status 200)
  - ErrorBoundary is NOT rendered ("Ceva nu a mers cum trebuie")
  - At least one known data-testid exists for the role

Run with:
    cd /app/backend && python -m pytest tests/test_dashboards_smoke.py -v -s

Or as standalone script (no pytest needed):
    cd /app/backend && python tests/test_dashboards_smoke.py
"""
import asyncio
import os
import sys
from tests.test_config import OWNER_ADMIN_PASSWORD

# Read env or fall back to preview URL
BASE_URL = os.environ.get(
    "SMOKE_BASE_URL",
    "https://phased-document.preview.emergentagent.com",
)
ADMIN_EMAIL = os.environ.get("SMOKE_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORD = os.environ.get("SMOKE_ADMIN_PASSWORD", OWNER_ADMIN_PASSWORD)

# Profiles to validate — must mirror ROLE_PROFILES in AdminLayoutMetronic.jsx
PROFILES = [
    # Base
    {"email": "client@propmanage.io",            "role": "client",     "tier": "base",      "must_have_testid": "client-tab-request"},
    {"email": "specialist@propmanage.io",        "role": "specialist", "tier": "base",      "must_have_testid": "spec-tab-opportunities"},
    {"email": "operator@propmanage.io",          "role": "operator",   "tier": "base",      "must_have_testid": None},  # operator has different layout
    # Client tiers
    {"email": "client.junior@propmanage.io",     "role": "client",     "tier": "JUNIOR",    "must_have_testid": "client-tab-request"},
    {"email": "client.verified@propmanage.io",   "role": "client",     "tier": "VERIFIED",  "must_have_testid": "client-tab-request"},
    {"email": "client.premium@propmanage.io",    "role": "client",     "tier": "PREMIUM",   "must_have_testid": "client-tab-request"},
    # Specialist tiers
    {"email": "spec.entry@propmanage.io",        "role": "specialist", "tier": "ENTRY",     "must_have_testid": "spec-tab-opportunities"},
    {"email": "spec.junior@propmanage.io",       "role": "specialist", "tier": "JUNIOR",    "must_have_testid": "spec-tab-opportunities"},
    {"email": "spec.verified@propmanage.io",     "role": "specialist", "tier": "VERIFIED",  "must_have_testid": "spec-tab-opportunities"},
    {"email": "spec.advanced@propmanage.io",     "role": "specialist", "tier": "ADVANCED",  "must_have_testid": "spec-stat-wallet"},
    {"email": "spec.premium@propmanage.io",      "role": "specialist", "tier": "PREMIUM",   "must_have_testid": "spec-stat-wallet"},
    {"email": "spec.top@propmanage.io",          "role": "specialist", "tier": "TOP",       "must_have_testid": "spec-tab-opportunities"},
]

# Strings that indicate the ErrorBoundary is being shown (smoke test FAIL)
ERROR_FINGERPRINTS = [
    "Ceva nu a mers cum trebuie",
    "is not defined",
    "ReferenceError",
    "TypeError",
]

DASHBOARD_PATH = {
    "client": "/client",
    "specialist": "/specialist",
    "operator": "/operator",
}


async def _login_as_admin(page) -> bool:
    """Login as the admin user. Returns True on success."""
    # Clear cookies to ensure clean session (we may have just impersonated someone)
    try:
        await page.context.clear_cookies()
    except Exception:
        pass
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
    try:
        await page.fill('input[type="email"]', ADMIN_EMAIL, timeout=10000)
        await page.fill('input[type="password"]', ADMIN_PASSWORD, timeout=10000)
        await page.click('button[type="submit"]', timeout=10000)
    except Exception:
        return False
    await asyncio.sleep(3)
    return "/admin" in page.url or ("/login" not in page.url and "/client" not in page.url and "/specialist" not in page.url)


async def _impersonate(page, target_email: str, target_role: str) -> bool:
    """Use the admin /api/admin/impersonate endpoint via JS fetch. Returns True on success."""
    js = """
        async ({ email, role }) => {
            const apiUrl = window.location.origin + '/api';
            const search = await fetch(apiUrl + '/admin/users?q=' + encodeURIComponent(email) + '&limit=10', { credentials: 'include' });
            const data = await search.json();
            const items = data.items || [];
            // Prefer EXACT email match (avoids confusing client@propmanage.io with client.junior@propmanage.io)
            let target = items.find(u => u.email === email && u.role === role);
            if (!target) target = items.find(u => u.role === role);
            if (!target) target = items[0];
            if (!target) return { ok: false, reason: 'user_not_found' };
            const resp = await fetch(apiUrl + '/admin/impersonate', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: target.id, reason: 'Pre-deploy automated smoke test for dashboard health' }),
            });
            if (!resp.ok) return { ok: false, reason: 'impersonate_failed', status: resp.status };
            return await resp.json();
        }
    """
    result = await page.evaluate(js, {"email": target_email, "role": target_role})
    return bool(result and result.get("ok") is not False and "redirect_to" in result)


async def _check_dashboard(page, profile: dict) -> dict:
    """Navigate to the dashboard for the role and check for errors. Returns {ok, errors[]}."""
    errors = []
    dash_path = DASHBOARD_PATH.get(profile["role"], "/")
    await page.goto(f"{BASE_URL}{dash_path}", wait_until="networkidle", timeout=30000)
    # Give the dashboard a bit more time to render (cookies/dashboards may lazy-load)
    await asyncio.sleep(3)

    # Wait for required testid up to 5s if it's defined
    if profile.get("must_have_testid"):
        try:
            await page.locator(f'[data-testid="{profile["must_have_testid"]}"]').first.wait_for(timeout=5000)
        except Exception:
            pass

    body_text = await page.locator("body").inner_text()

    for fingerprint in ERROR_FINGERPRINTS:
        if fingerprint in body_text:
            errors.append(f"ErrorBoundary fingerprint detected: '{fingerprint}'")

    # Check required testid is present
    if profile.get("must_have_testid"):
        cnt = await page.locator(f'[data-testid="{profile["must_have_testid"]}"]').count()
        if cnt == 0:
            errors.append(f"Required testid not found: '{profile['must_have_testid']}'")

    return {"ok": len(errors) == 0, "errors": errors}


async def _test_unauthenticated_redirects(page) -> list:
    """Verify that protected dashboards redirect to /login?next= when no session.
    Catches regressions on the email-link → auth-guard → post-login redirect flow."""
    errors = []
    protected = [("/admin", "next=/admin"), ("/client", "next=/client"), ("/specialist", "next=/specialist")]
    for path, expected_next in protected:
        try:
            await page.context.clear_cookies()
            await page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            if "/login" not in page.url:
                errors.append(f"{path}: did NOT redirect to /login (final url: {page.url})")
            elif expected_next not in page.url:
                errors.append(f"{path}: missing '{expected_next}' in url (got: {page.url})")
        except Exception as e:
            errors.append(f"{path}: exception {e}")
    return errors


async def _run_smoke_test() -> tuple[int, int, list]:
    """Run the smoke test on all profiles. Returns (passed, failed, failures_list)."""
    from playwright.async_api import async_playwright

    failures = []
    passed = 0
    failed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Pre-test: unauthenticated → /admin /client /specialist must redirect to /login?next=
        print("  → unauthenticated dashboard redirects...", end=" ", flush=True)
        redirect_errors = await _test_unauthenticated_redirects(page)
        if redirect_errors:
            failed += 1
            failures.append({"profile": "UNAUTH_REDIRECTS", "errors": redirect_errors})
            print(f"❌ FAIL: {redirect_errors}")
        else:
            passed += 1
            print("✅ PASS")

        for profile in PROFILES:
            print(f"  → {profile['email']} ({profile['tier']})...", end=" ", flush=True)
            try:
                # Re-login as admin before each impersonation (impersonate replaces session)
                if not await _login_as_admin(page):
                    failures.append({"profile": profile["email"], "errors": ["admin re-login failed"]})
                    failed += 1
                    print("❌ ADMIN RE-LOGIN FAILED")
                    continue
                # Impersonate
                impersonated = await _impersonate(page, profile["email"], profile["role"])
                if not impersonated:
                    failures.append({"profile": profile["email"], "errors": ["Failed to impersonate"]})
                    failed += 1
                    print("❌ IMPERSONATE FAILED")
                    continue
                # Check dashboard
                result = await _check_dashboard(page, profile)
                if result["ok"]:
                    passed += 1
                    print("✅ PASS")
                else:
                    failed += 1
                    failures.append({"profile": profile["email"], "errors": result["errors"]})
                    print(f"❌ FAIL: {result['errors']}")
            except Exception as e:
                failed += 1
                failures.append({"profile": profile["email"], "errors": [f"Exception: {e}"]})
                print(f"❌ EXCEPTION: {e}")

        await browser.close()

    return passed, failed, failures


# ============= PYTEST INTEGRATION =============
def test_all_dashboards_smoke():
    """Pre-deploy smoke test: all 12 demo profiles must load without ErrorBoundary."""
    passed, failed, failures = asyncio.run(_run_smoke_test())
    assert failed == 0, (
        f"\n\n❌ {failed}/{len(PROFILES)} dashboards FAILED:\n"
        + "\n".join(f"  - {f['profile']}: {', '.join(f['errors'])}" for f in failures)
    )


# ============= STANDALONE SCRIPT =============
def main():
    print(f"\n🔥 Pre-Deploy Dashboard Smoke Test")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Profiles: {len(PROFILES)}\n")
    passed, failed, failures = asyncio.run(_run_smoke_test())
    print(f"\n📊 Result: {passed} passed · {failed} failed · {len(PROFILES)} total")
    if failed > 0:
        print("\n❌ FAILURES:")
        for f in failures:
            print(f"  - {f['profile']}: {', '.join(f['errors'])}")
        sys.exit(1)
    print("\n✅ All dashboards healthy. Safe to deploy.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
