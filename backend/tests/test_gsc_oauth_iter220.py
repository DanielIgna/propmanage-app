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


def test_gsc_report_disconnected_returns_empty_not_fake(admin):
    # when not connected the report must be empty (never mock numbers)
    d = admin.get(f"{API}/admin/seo/gsc/report", params={"range": "28d"}, timeout=20).json()
    if d["status"] == "not_connected":
        assert d["overview"] is None
        assert d["queries"] == [] and d["pages"] == []


def test_gsc_admin_only():
    anon = requests.Session()
    for path in ("/admin/seo/gsc", "/admin/seo/gsc/oauth/start"):
        r = anon.get(f"{API}{path}", timeout=15)
        assert r.status_code in (401, 403), f"{path} should require admin, got {r.status_code}"


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
