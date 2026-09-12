"""GSC OAuth connector + Design Interior CTA attribution (Batch 2.1, iter 220).

Covers the NEW GSC OAuth path (reusing the existing Google login client) and the
honest disconnected fallback. No SEO-foundation change is asserted here (that stays
covered by iter218/iter219). No data side effects (does not create leads).
"""
import os
import urllib.parse as up
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.text[:200]}"
    return s


def test_gsc_status_exposes_oauth_and_redirect_uri(admin):
    d = admin.get(f"{API}/admin/seo/gsc", timeout=20).json()
    # existing Google login client (GOOGLE_CLIENT_ID/SECRET) makes OAuth available
    assert d["oauth_available"] is True
    assert d["redirect_uri"].endswith("/api/admin/seo/gsc/oauth/callback")
    # honest fallback preserved when no credentials stored yet
    if not d.get("connected"):
        assert d["status"] == "not_connected"
        assert d["metrics"] is None  # never fabricated


def test_gsc_oauth_start_builds_valid_consent_url(admin):
    d = admin.get(f"{API}/admin/seo/gsc/oauth/start",
                  params={"property": "sc-domain:propmanage.ro"}, timeout=20).json()
    assert d["ok"] is True
    q = dict(up.parse_qsl(up.urlparse(d["authorization_url"]).query))
    assert q["scope"] == "https://www.googleapis.com/auth/webmasters.readonly"
    assert q["access_type"] == "offline"        # → refresh token
    assert q["prompt"] == "consent"
    assert q["redirect_uri"].endswith("/api/admin/seo/gsc/oauth/callback")
    assert d["authorization_url"].startswith("https://accounts.google.com/")
    # PKCE must be present in the auth request (and the matching verifier is sent at exchange)
    assert q.get("code_challenge_method") == "S256"
    assert len(q.get("code_challenge", "")) >= 20


def test_gsc_report_disconnected_returns_empty_not_fake(admin):
    # when not connected the report must be empty (never mock numbers)
    d = admin.get(f"{API}/admin/seo/gsc/report", params={"range": "28d"}, timeout=20).json()
    if d["status"] == "not_connected":
        assert d["overview"] is None
        assert d["queries"] == [] and d["pages"] == []


def test_callback_direct_exchange_reaches_google_and_surfaces_error(admin):
    """End-to-end guard for the fix: the callback now exchanges the code via a DIRECT
    POST to Google (same pattern as the working login flow), NOT google-auth-oauthlib.
    A valid signed state + a bogus code must reach Google, get 'invalid_grant', and be
    surfaced SAFELY as detail=invalid_grant + persisted last_error (no secrets)."""
    import urllib.parse as up
    # 1) obtain a valid signed state from the real start endpoint
    d = admin.get(f"{API}/admin/seo/gsc/oauth/start", timeout=20).json()
    state = dict(up.parse_qsl(up.urlparse(d["authorization_url"]).query))["state"]

    # 2) hit the callback with the valid state + a bogus code (no real secret involved)
    r = admin.get(f"{API}/admin/seo/gsc/oauth/callback",
                  params={"code": "BOGUS_DIAGNOSTIC_CODE", "state": state},
                  timeout=20, allow_redirects=False)
    assert r.status_code in (302, 307)
    loc = r.headers.get("location", "")
    # proves: state ok → direct exchange executed → Google reachable → invalid_grant surfaced
    assert "gsc=error" in loc and "reason=token_exchange" in loc
    assert "detail=invalid_grant" in loc, f"expected invalid_grant, got: {loc}"

    # 3) status endpoint exposes the safe diagnostic (never a token/secret)
    s = admin.get(f"{API}/admin/seo/gsc", timeout=20).json()
    assert s["connected"] is False
    assert s.get("last_error") == "invalid_grant"

    # 4) cleanup the diagnostic doc so preview admin stays clean
    try:
        import asyncio
        from db import db
        asyncio.run(db.seo_config.delete_many({"key": {"$in": ["gsc_diag", "gsc"]}}))
    except Exception:
        pass


def test_gsc_admin_only():
    anon = requests.Session()
    for path in ("/admin/seo/gsc", "/admin/seo/gsc/oauth/start"):
        r = anon.get(f"{API}{path}", timeout=15)
        assert r.status_code in (401, 403), f"{path} should require admin, got {r.status_code}"


def test_oauth_start_omits_include_granted_scopes(admin):
    """include_granted_scopes must NOT be requested — it causes Google to merge the
    account's login scopes into the GSC grant (root cause of the silent callback fail)."""
    d = admin.get(f"{API}/admin/seo/gsc/oauth/start", timeout=20).json()
    assert d["ok"] is True
    assert "include_granted_scopes" not in d["authorization_url"]


def test_module_relaxes_token_scope_for_google_superset():
    """Regression guard for the 'Not connected after successful consent' bug:
    importing routes.admin_seo must set OAUTHLIB_RELAX_TOKEN_SCOPE=1 so oauthlib tolerates
    Google returning a SUPERSET scope (webmasters.readonly + previously-granted login
    scopes) instead of raising 'Scope has changed …' inside flow.fetch_token()."""
    import importlib
    os.environ.pop("OAUTHLIB_RELAX_TOKEN_SCOPE", None)
    import routes.admin_seo as m
    importlib.reload(m)  # re-run module top-level → must set the flag
    assert os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE") == "1"

    from oauthlib.oauth2 import OAuth2Token
    from oauthlib.oauth2.rfc6749 import parameters
    tok = OAuth2Token(
        {"access_token": "x", "token_type": "Bearer", "expires_in": 3599, "refresh_token": "1//rt",
         "scope": "https://www.googleapis.com/auth/webmasters.readonly openid "
                  "https://www.googleapis.com/auth/userinfo.email"},
        old_scope="https://www.googleapis.com/auth/webmasters.readonly",
    )
    assert tok.scope_changed is True
    parameters.validate_token_parameters(tok)  # must NOT raise now (fix active)


def test_lead_schema_accepts_attribution_fields(admin):
    # The existing lead endpoint must ACCEPT the optional attribution fields
    # (schema validation only — asserted via non-422). Uses a marked test email.
    payload = {
        "name": "ITER220_SCHEMA_PROBE", "email": "iter220_schema_probe@example.com",
        "lead_type": "oferta", "di_slug": "apartament", "seo_cluster": "design_interior",
        "landing_page": "/design-interior/apartament", "source": "google",
        "medium": "organic", "campaign": "", "referrer": "https://www.google.com/",
    }
    r = requests.post(f"{API}/interior-design/leads", json=payload, timeout=15)
    assert r.status_code == 200, f"attribution fields rejected: {r.status_code} {r.text[:200]}"
    assert r.json().get("ok") is True
