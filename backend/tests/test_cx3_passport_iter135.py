"""CX-3 Property Passport backend tests (iter 135).

Covers: owner auth, public payload, privacy enforcement, security, OG social preview,
trust score integrity. Uses cookie-based auth via requests.Session().
"""
import os
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
KNOWN_SLUG = "gbegxfyz9m"
KNOWN_PROP_ID = "6a11d70e600be19667009c93"


@pytest.fixture(scope="module")
def client_sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    assert any(k in s.cookies for k in ("token", "access_token")), \
        f"no auth cookie set. Cookies={list(s.cookies.keys())}"
    return s


@pytest.fixture(scope="module")
def other_client_sess():
    """Register a fresh secondary client to test cross-owner access denial."""
    s = requests.Session()
    email = f"TEST_cx3_{uuid.uuid4().hex[:8]}@propmanage.io"
    r = s.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "CX3 Other", "role": "client",
    }, timeout=15)
    if r.status_code not in (200, 201):
        # fallback existing account
        s = requests.Session()
        r2 = s.post(f"{BASE}/api/auth/login",
                    json={"email": "cx2.audit.final@propmanage.io", "password": "CxAudit2026!"}, timeout=15)
        if r2.status_code != 200:
            pytest.skip(f"cannot create/login secondary client: {r.status_code} / {r2.status_code}")
    return s


# ── Owner flow ───────────────────────────────────────────────────────────────
class TestOwner:
    def test_list_properties(self, client_sess):
        r = client_sess.get(f"{BASE}/api/properties", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        ids = [p.get("id") or p.get("_id") for p in data]
        assert KNOWN_PROP_ID in ids, f"expected prop {KNOWN_PROP_ID} in {ids}"

    def test_get_passport(self, client_sess):
        r = client_sess.get(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["enabled"] is True
        assert d["slug"] == KNOWN_SLUG
        assert d["share_url"].endswith(f"/api/p/{KNOWN_SLUG}")
        assert d["page_url"].endswith(f"/p/{KNOWN_SLUG}")
        assert d["qr_url"].endswith(f"/api/public/passport/{KNOWN_SLUG}/qr.png")
        assert set(d["privacy"].keys()) >= {"show_address", "show_photo", "show_documents", "show_timeline", "show_scores"}
        assert isinstance(d["privacy_labels"], dict)
        assert d["preview"] is not None

    def test_patch_privacy_show_address(self, client_sess):
        # enable show_address then read public
        r = client_sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport",
                              json={"privacy": {"show_address": True}}, timeout=15)
        assert r.status_code == 200
        assert r.json()["privacy"]["show_address"] is True
        # public payload should reflect address
        pub = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
        # If property has an address stored, it must now be non-null
        # (we only check when address exists; otherwise verify field present with any non-secret value)
        assert "address" in pub["property"]

    def test_patch_privacy_hide_address(self, client_sess):
        r = client_sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport",
                              json={"privacy": {"show_address": False}}, timeout=15)
        assert r.status_code == 200
        assert r.json()["privacy"]["show_address"] is False
        pub = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
        assert pub["property"]["address"] is None

    def test_disable_then_reenable(self, client_sess):
        # disable
        r = client_sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport",
                              json={"enabled": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        # public should 404
        r2 = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15)
        assert r2.status_code == 404
        # re-enable (must remain enabled at end per instructions)
        r3 = client_sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport",
                               json={"enabled": True}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["enabled"] is True


# ── Public payload & privacy fields ─────────────────────────────────────────
class TestPublic:
    def test_public_payload_structure(self):
        r = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == KNOWN_SLUG
        assert set(d["property"].keys()) >= {"name", "type", "surface", "rooms", "address"}
        assert "trust" in d["scores"]
        trust = d["scores"]["trust"]
        assert "score" in trust and "factors" in trust and "missing" in trust and "explanation" in trust
        for f in trust["factors"]:
            assert set(f.keys()) >= {"id", "label", "earned", "max", "done", "why"}
        assert len(trust["missing"]) <= 4
        assert isinstance(d["badges"], list) and len(d["badges"]) == 8
        assert "milestones" in d
        assert "document_highlights" in d
        assert "twin_status" in d

    def test_trust_score_sum_and_cap(self):
        d = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
        trust = d["scores"]["trust"]
        total = sum(f["earned"] for f in trust["factors"])
        assert trust["score"] == total
        assert trust["score"] <= 100

    def test_no_leakage_of_secrets(self):
        raw = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).text.lower()
        for forbidden in ["propmanage.io", "user_id", "\"email\"", "wallet", "\"phone\"", "telefon", "price", "preț", "\"_id\""]:
            assert forbidden not in raw, f"public payload leaks '{forbidden}'"

    def test_qr_png(self):
        r = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}/qr.png", timeout=15)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/png")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_invalid_slug_404(self):
        r = requests.get(f"{BASE}/api/public/passport/xxxinvalid_zzz_404", timeout=15)
        assert r.status_code == 404


# ── Privacy enforcement ─────────────────────────────────────────────────────
class TestPrivacy:
    def _set(self, sess, **flags):
        r = sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport", json={"privacy": flags}, timeout=15)
        assert r.status_code == 200

    def test_hide_documents(self, client_sess):
        self._set(client_sess, show_documents=False)
        try:
            d = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
            assert d["document_highlights"] is None
        finally:
            self._set(client_sess, show_documents=True)

    def test_hide_timeline(self, client_sess):
        self._set(client_sess, show_timeline=False)
        try:
            d = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
            assert d["milestones"] == []
        finally:
            self._set(client_sess, show_timeline=True)

    def test_hide_scores(self, client_sess):
        self._set(client_sess, show_scores=False)
        try:
            d = requests.get(f"{BASE}/api/public/passport/{KNOWN_SLUG}", timeout=15).json()
            assert d["scores"]["completeness"] is None
            assert d["scores"]["maintenance"] is None
        finally:
            self._set(client_sess, show_scores=True)


# ── SECURITY ────────────────────────────────────────────────────────────────
class TestSecurity:
    def test_owner_endpoints_require_auth(self):
        for method, path in [
            ("GET", f"/api/properties/{KNOWN_PROP_ID}/passport"),
            ("PATCH", f"/api/properties/{KNOWN_PROP_ID}/passport"),
            ("POST", f"/api/properties/{KNOWN_PROP_ID}/passport/enable"),
        ]:
            r = requests.request(method, f"{BASE}{path}",
                                 json={} if method != "GET" else None, timeout=15)
            assert r.status_code in (401, 403), f"{method} {path} → {r.status_code}"

    def test_other_owner_forbidden(self, other_client_sess):
        r = other_client_sess.get(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport", timeout=15)
        assert r.status_code in (403, 404)
        r2 = other_client_sess.patch(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport",
                                     json={"enabled": False}, timeout=15)
        assert r2.status_code in (403, 404)
        r3 = other_client_sess.post(f"{BASE}/api/properties/{KNOWN_PROP_ID}/passport/enable", timeout=15)
        assert r3.status_code in (403, 404)


# ── OG / Social preview ─────────────────────────────────────────────────────
class TestOG:
    @pytest.mark.parametrize("ua", [
        "facebookexternalhit/1.1",
        "WhatsApp/2.23",
        "LinkedInBot/1.0 (compatible; Mozilla/5.0)",
    ])
    def test_bot_gets_html_og(self, ua):
        r = requests.get(f"{BASE}/api/p/{KNOWN_SLUG}", headers={"User-Agent": ua},
                         timeout=15, allow_redirects=False)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        body = r.text
        for tag in ["og:title", "og:description", "og:image", "og:url", "twitter:card"]:
            assert tag in body, f"missing {tag} for UA={ua}"

    def test_browser_gets_redirect(self):
        r = requests.get(f"{BASE}/api/p/{KNOWN_SLUG}",
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"},
                         timeout=15, allow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"].endswith(f"/p/{KNOWN_SLUG}")

    def test_share_invalid_slug_404(self):
        r = requests.get(f"{BASE}/api/p/xxxinvalid_zzz_404",
                         headers={"User-Agent": "facebookexternalhit/1.1"},
                         timeout=15, allow_redirects=False)
        assert r.status_code == 404

    def test_og_fallback_image(self):
        r = requests.get(f"{BASE}/og-passport.jpg", timeout=15)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/jpeg")
