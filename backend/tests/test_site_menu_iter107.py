"""Iteration 107 — Site Menu CMS + Interior Design AI rate limit tests.

Covers:
- GET /api/public/site-menu (no auth)
- GET /api/admin/site-menu (401/403 without admin auth)
- PUT /api/admin/site-menu with deactivation + verify hidden on public + reset
- POST /api/admin/site-menu/reset restores defaults
- POST /api/interior-design/assistant rate limit (10 req / 10 min per IP)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "1!nasov01ADMIN")
ADMIN = {"email": "admin@propmanage.io", "password": SEED_ADMIN_PASSWORD}


# ────────────────────────── Fixtures ──────────────────────────
@pytest.fixture(scope="module")
def public_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="module", autouse=True)
def _restore_menu_after_tests(admin_client):
    """Ensure the menu is reset to default AFTER tests, no matter what."""
    yield
    try:
        admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)
    except Exception:
        pass


# ────────────────────────── Public menu ──────────────────────────
class TestPublicSiteMenu:
    def test_public_no_auth_returns_200(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 5

    def test_public_default_structure(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        data = r.json()
        ids = [it["id"] for it in data["items"]]
        for expected in ["acasa", "servicii", "proprietari", "companie", "cont_guest", "cont_auth"]:
            assert expected in ids, f"missing top item {expected}; got {ids}"

    def test_public_servicii_has_12_children(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        servicii = next(it for it in r.json()["items"] if it["id"] == "servicii")
        assert len(servicii["children"]) == 12, f"expected 12, got {len(servicii['children'])}"
        # verify a couple of ids present
        child_ids = [c["id"] for c in servicii["children"]]
        for x in ["imobile_verificate", "design_interior", "specialisti"]:
            assert x in child_ids

    def test_public_proprietari_has_4_children(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        prop = next(it for it in r.json()["items"] if it["id"] == "proprietari")
        assert len(prop["children"]) == 4

    def test_public_companie_has_3_children(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        comp = next(it for it in r.json()["items"] if it["id"] == "companie")
        assert len(comp["children"]) == 3

    def test_public_cont_guest_has_login_register(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        cg = next(it for it in r.json()["items"] if it["id"] == "cont_guest")
        assert cg["visibility"] == "guests"
        child_ids = [c["id"] for c in cg["children"]]
        assert "login" in child_ids and "register" in child_ids

    def test_public_cont_auth_children(self, public_client):
        r = public_client.get(f"{API}/public/site-menu", timeout=15)
        ca = next(it for it in r.json()["items"] if it["id"] == "cont_auth")
        assert ca["visibility"] == "auth"
        ids = [c["id"] for c in ca["children"]]
        for x in ["dashboard", "proiecte", "mesaje", "notificari", "setari", "logout"]:
            assert x in ids


# ────────────────────────── Admin menu ──────────────────────────
class TestAdminSiteMenuAuth:
    def test_admin_get_without_auth_forbidden(self, public_client):
        r = public_client.get(f"{API}/admin/site-menu", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_admin_put_without_auth_forbidden(self, public_client):
        r = public_client.put(f"{API}/admin/site-menu", json={"items": []}, timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_reset_without_auth_forbidden(self, public_client):
        r = public_client.post(f"{API}/admin/site-menu/reset", timeout=15)
        assert r.status_code in (401, 403)


class TestAdminSiteMenuOperations:
    def test_admin_get_returns_items_with_active_flag(self, admin_client):
        r = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and len(data["items"]) > 0
        # active flag must be present
        for it in data["items"]:
            assert "active" in it
            assert isinstance(it["active"], bool)

    def test_admin_reset_first_ensures_baseline(self, admin_client):
        r = admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_deactivate_item_hides_from_public_then_restore(self, admin_client, public_client):
        # 1. Get current items
        r = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        items = r.json()["items"]

        # 2. Deactivate "companie"
        modified = []
        for it in items:
            copy = dict(it)
            if copy["id"] == "companie":
                copy["active"] = False
            modified.append(copy)

        # 3. PUT
        pr = admin_client.put(f"{API}/admin/site-menu", json={"items": modified}, timeout=15)
        assert pr.status_code == 200, pr.text

        # 4. Verify public GET excludes it
        pub = public_client.get(f"{API}/public/site-menu", timeout=15).json()
        pub_ids = [it["id"] for it in pub["items"]]
        assert "companie" not in pub_ids, f"deactivated 'companie' still visible: {pub_ids}"
        assert "servicii" in pub_ids  # others still visible

        # 5. Restore via reset
        rr = admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)
        assert rr.status_code == 200

        # 6. Verify restored
        pub2 = public_client.get(f"{API}/public/site-menu", timeout=15).json()
        assert "companie" in [it["id"] for it in pub2["items"]]

    def test_reorder_persists(self, admin_client):
        r = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        items = r.json()["items"]
        # swap first 2
        swapped = [items[1], items[0]] + items[2:]
        ordered_ids = [it["id"] for it in swapped]
        pr = admin_client.put(f"{API}/admin/site-menu", json={"items": swapped}, timeout=15)
        assert pr.status_code == 200

        r2 = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        got_ids = [it["id"] for it in r2.json()["items"]]
        assert got_ids[:2] == ordered_ids[:2]

        # restore
        admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)

    def test_relabel_persists(self, admin_client):
        r = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        items = r.json()["items"]
        modified = []
        for it in items:
            copy = dict(it)
            if copy["id"] == "acasa":
                copy["label"] = "TEST_Acasă"
            modified.append(copy)
        pr = admin_client.put(f"{API}/admin/site-menu", json={"items": modified}, timeout=15)
        assert pr.status_code == 200

        # Verify persistence
        r2 = admin_client.get(f"{API}/admin/site-menu", timeout=15)
        acasa = next(it for it in r2.json()["items"] if it["id"] == "acasa")
        assert acasa["label"] == "TEST_Acasă"

        # restore
        admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)

    def test_reset_returns_default_structure(self, admin_client):
        r = admin_client.post(f"{API}/admin/site-menu/reset", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        ids = [it["id"] for it in items]
        assert ids[0] == "acasa"
        assert "servicii" in ids
        servicii = next(it for it in items if it["id"] == "servicii")
        assert len(servicii["children"]) == 12


# ────────────────────────── AI rate limit ──────────────────────────
class TestInteriorDesignAIRateLimit:
    """Note: rate limit is in-memory per IP. Preview server may be shared across
    tests. This test may need to run in isolation. Backend restart resets it.
    """

    def test_rate_limit_returns_429_with_romanian_message(self, public_client):
        """Fire up to 25 requests. Expect at least one 429 with Romanian message.
        Note: server has uvicorn --reload; reloader may reset counters mid-run.
        """
        endpoint = f"{API}/interior-design/assistant"
        payload = {"question": "test rate limit"}
        status_codes = []
        got_ro_msg = False
        for i in range(25):
            try:
                r = public_client.post(endpoint, json=payload, timeout=45)
                status_codes.append(r.status_code)
                if r.status_code == 429:
                    body = r.text.lower()
                    if "limit" in body or "reîncearcă" in body or "reincearca" in body:
                        got_ro_msg = True
                        break
            except requests.Timeout:
                status_codes.append("TIMEOUT")

        assert 429 in status_codes, f"No 429 seen in 25 requests: {status_codes}"
        assert got_ro_msg, "429 returned but message not Romanian as expected"
