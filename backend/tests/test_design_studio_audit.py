"""Backend tests for Design Studio + Design Audit modules (iter 101).

Covers:
  - Design Studio: tokens (public GET), presets (list/apply/save/delete),
    reset, components registry, design lock toggle.
  - Design Audit: pages registry (13), analyze (LLM Claude), summary.
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PWD = "1!nasov01ADMIN"


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def public_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


# ── Design Studio: Tokens (public) ─────────────────────────────────────────
class TestDesignStudioTokens:
    def test_tokens_public_read(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "tokens" in data
        assert "preset_id" in data
        colors = data["tokens"]["colors"]
        assert len(colors) == 20, f"Expected 20 color tokens, got {len(colors)}: {list(colors.keys())}"
        # verify key sections
        for section in ("colors", "typography", "radii", "shadows", "components"):
            assert section in data["tokens"], f"Missing section: {section}"
        # spot-check
        assert "primary" in colors
        assert colors["primary"].startswith("#")

    def test_reset_to_default(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/admin/design-studio/reset", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["preset_id"] == "default"
        assert data["tokens"]["colors"]["primary"] == "#d4ff3a"
        # verify persistence via GET
        r2 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=10)
        assert r2.status_code == 200
        assert r2.json()["preset_id"] == "default"

    def test_apply_neon_lab_preset(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-studio/presets/apply",
            json={"preset_id": "neon_lab"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["preset_id"] == "neon_lab"
        assert data["tokens"]["colors"]["primary"] == "#d4ff3a"
        # verify persistence
        r2 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=10)
        assert r2.status_code == 200
        j2 = r2.json()
        assert j2["preset_id"] == "neon_lab"
        assert j2["tokens"]["colors"]["primary"] == "#d4ff3a"
        # reset to default for cleanup
        admin_client.post(f"{BASE_URL}/api/admin/design-studio/reset", timeout=10)


# ── Design Studio: Presets ─────────────────────────────────────────────────
class TestDesignStudioPresets:
    def test_list_builtin_presets(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-studio/presets", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "presets" in data
        ids = {p["id"] for p in data["presets"]}
        expected = {"default", "corporate", "minimal_dark", "warm_linen", "neon_lab", "material_you"}
        assert expected.issubset(ids), f"Missing built-ins. Got: {ids}"

    def test_save_and_delete_custom_preset(self, admin_client):
        name = f"TEST_preset_{int(time.time())}"
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-studio/presets",
            json={"name": name, "description": "test preset"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["name"] == name
        assert doc["builtin"] is False
        preset_id = doc["id"]

        # verify it appears in list
        r2 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/presets", timeout=10)
        assert preset_id in {p["id"] for p in r2.json()["presets"]}

        # delete
        r3 = admin_client.delete(f"{BASE_URL}/api/admin/design-studio/presets/{preset_id}", timeout=10)
        assert r3.status_code == 200, r3.text
        assert r3.json().get("ok") is True

        # verify gone
        r4 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/presets", timeout=10)
        assert preset_id not in {p["id"] for p in r4.json()["presets"]}

    def test_cannot_delete_builtin(self, admin_client):
        r = admin_client.delete(f"{BASE_URL}/api/admin/design-studio/presets/default", timeout=10)
        assert r.status_code == 400


# ── Design Studio: Components + Lock ───────────────────────────────────────
class TestDesignStudioComponentsAndLock:
    def test_components_list(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-studio/components", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 17, f"Expected 17 components, got {data['total']}"
        assert len(data["components"]) == 17
        # Each has tokens list
        for c in data["components"]:
            assert "key" in c and "label" in c and "tokens" in c

    def test_lock_default(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-studio/lock", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("enabled") is True
        assert len(data.get("rules", [])) == 8

    def test_lock_toggle(self, admin_client):
        # disable
        r = admin_client.put(f"{BASE_URL}/api/admin/design-studio/lock", json={"enabled": False}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["enabled"] is False
        # re-enable (restore state)
        r2 = admin_client.put(f"{BASE_URL}/api/admin/design-studio/lock", json={"enabled": True}, timeout=10)
        assert r2.status_code == 200
        assert r2.json()["enabled"] is True


# ── Design Audit ───────────────────────────────────────────────────────────
class TestDesignAudit:
    def test_pages_list(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-audit/pages", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cache_hours"] == 12
        assert len(data["pages"]) == 13, f"Expected 13 pages, got {len(data['pages'])}"
        zones = {p["zone"] for p in data["pages"]}
        assert {"public", "client", "specialist", "operator", "admin"}.issubset(zones)
        # verify structure
        for p in data["pages"]:
            for k in ("key", "path", "zone", "label", "brief"):
                assert k in p, f"Missing field {k} in page {p.get('key')}"

    def test_analyze_landing_llm(self, admin_client):
        # LLM call — can take up to 30s. Use force=false to allow cache.
        r = admin_client.get(f"{BASE_URL}/api/admin/design-audit/analyze?key=landing", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # verify scores
        for k in ("mobile_score", "desktop_score", "unity_score", "hicks_law_score"):
            assert k in data
            assert isinstance(data[k], int)
            assert 0 <= data[k] <= 100
        assert isinstance(data.get("findings"), list) and len(data["findings"]) >= 1
        assert isinstance(data.get("recommendations"), list) and len(data["recommendations"]) >= 1
        assert data.get("page", {}).get("key") == "landing"

    def test_analyze_cached_second_call(self, admin_client):
        # Second call without force should return cached=true
        r = admin_client.get(f"{BASE_URL}/api/admin/design-audit/analyze?key=landing", timeout=15)
        assert r.status_code == 200
        assert r.json().get("cached") is True

    def test_analyze_unknown_key(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-audit/analyze?key=doesnotexist", timeout=10)
        assert r.status_code == 404

    def test_summary_aggregates(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-audit/summary", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_pages"] == 13
        # after we've audited at least 1 page (landing) in previous test:
        assert data["audited"] >= 1
        for k in ("coverage", "avg_mobile", "avg_desktop", "avg_unity"):
            assert k in data


# ── Auth guards ────────────────────────────────────────────────────────────
class TestAuthGuards:
    def test_tokens_public_no_auth_ok(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=10)
        assert r.status_code == 200  # public read

    def test_presets_requires_admin(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/admin/design-studio/presets", timeout=10)
        assert r.status_code in (401, 403)

    def test_audit_pages_requires_admin(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/admin/design-audit/pages", timeout=10)
        assert r.status_code in (401, 403)
