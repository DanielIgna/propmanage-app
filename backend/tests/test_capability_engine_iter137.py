"""Track B / Faza D1 — Universal Capability Engine tests (iter 137)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

SPEC = ("specialist@propmanage.io", "Spec123!")
SPEC2 = ("specialist2@propmanage.io", "Spec123!")
CLIENT = ("client@propmanage.io", "Client123!")

RESERVED = {"technical_audit", "installation_mapping", "digital_twin_infrastructure",
            "construction_management", "quality_inspection", "final_acceptance", "house_health"}

DEFAULT_CAPS = [
    {"id": "interior_design", "level": "expert"},
    {"id": "kitchen_design", "level": "professional"},
    {"id": "lighting", "level": "intermediate"},
    {"id": "modeling_3d", "level": "professional"},
    {"id": "moodboards", "level": "expert"},
]
DEFAULT_SOFT = ["sketchup", "autocad", "fmt_ifc", "matterport", "blender"]


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def spec_session():
    return _login(*SPEC)


@pytest.fixture(scope="module")
def client_session():
    return _login(*CLIENT)


# ─────────── Catalog ───────────
class TestCatalog:
    def test_catalog_shape(self):
        r = requests.get(f"{API}/capabilities/catalog", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert len(d["phases"]) == 5
        caps = [c for ph in d["phases"] for c in ph["capabilities"]]
        assert len(caps) == 45, f"expected 45 caps, got {len(caps)}"
        reserved = {c["id"] for c in caps if c.get("reserved")}
        assert reserved == RESERVED, f"reserved mismatch: {reserved} != {RESERVED}"
        assert len(d["software"]) == 27
        assert len(d["levels"]) == 4
        assert len(d["responsibility_levels"]) == 4
        assert d["languages"]
        assert d["score_components"]

    def test_responsibility_matrix(self):
        r = requests.get(f"{API}/capabilities/responsibility-matrix", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert len(d["rows"]) == 45
        by_id = {row["capability"]: row for row in d["rows"]}
        dt = by_id["digital_twin_infrastructure"]
        actors = [(a["actor"], a["level"]) for a in dt["actors"]]
        assert actors == [("PropManage", "LEAD"), ("Designer", "CO_PARTNER"), ("Arhitect", "CO_PARTNER")]
        im = by_id["installation_mapping"]
        actors = [(a["actor"], a["level"]) for a in im["actors"]]
        assert actors == [("PropManage", "LEAD"), ("Inginer", "CO_PARTNER"), ("Designer", "SUPPORT")]


# ─────────── PUT capabilities validation ───────────
class TestPutValidation:
    def test_unauth_401(self):
        r = requests.put(f"{API}/professional/capabilities", json={"capabilities": []}, timeout=10)
        assert r.status_code == 401

    def test_client_forbidden_403(self, client_session):
        r = client_session.put(f"{API}/professional/capabilities", json={"capabilities": []}, timeout=10)
        assert r.status_code == 403

    def test_reserved_400(self, spec_session):
        r = spec_session.put(f"{API}/professional/capabilities",
                             json={"capabilities": [{"id": "technical_audit", "level": "expert"}],
                                   "software": DEFAULT_SOFT, "languages": []}, timeout=10)
        assert r.status_code == 400
        assert "PropManage" in r.text or "revend" in r.text

    def test_unknown_capability_400(self, spec_session):
        r = spec_session.put(f"{API}/professional/capabilities",
                             json={"capabilities": [{"id": "nonexistent_cap", "level": "expert"}]}, timeout=10)
        assert r.status_code == 400

    def test_invalid_level_400(self, spec_session):
        r = spec_session.put(f"{API}/professional/capabilities",
                             json={"capabilities": [{"id": "interior_design", "level": "godmode"}]}, timeout=10)
        assert r.status_code == 400


# ─────────── Save + compatibility + progression ───────────
class TestSaveAndScore:
    def test_save_and_score_90_progression_level_4(self, spec_session):
        body = {"capabilities": DEFAULT_CAPS, "software": DEFAULT_SOFT, "languages": ["Română", "Engleză"]}
        r = spec_session.put(f"{API}/professional/capabilities", json=body, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["compatibility"]["score"] == 90, f"expected score 90, got {d['compatibility']['score']}"
        badges = {b["id"]: b["earned"] for b in d["compatibility"]["badges"]}
        assert badges["bim_ready"] is True
        assert badges["digital_twin_ready"] is True
        assert badges["ifc_compatible"] is True
        assert badges["dwg_compatible"] is True
        assert badges["matterport_ready"] is True
        assert badges["point_cloud_ready"] is False
        assert badges["render_3d"] is True
        assert badges["propmanage_verified"] is True
        prog = d["progression"]
        assert prog["level"] == 4, f"expected level 4, got {prog['level']}: {prog}"
        assert prog["name"] == "Premium"
        assert prog["next_requirements"], "should have next_requirements for level 5"

    def test_get_own_capabilities(self, spec_session):
        r = spec_session.get(f"{API}/professional/capabilities", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert len(d["capabilities"]) == 5
        assert d["compatibility"]["score"] == 90
        assert "metrics" in d["progression"]

    def test_public_capabilities_no_metrics(self, spec_session):
        me = spec_session.get(f"{API}/auth/me", timeout=10).json()
        spec_id = me.get("id") or me.get("_id")
        r = requests.get(f"{API}/specialists/{spec_id}/capabilities", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["compatibility"]["score"] == 90
        assert "metrics" not in d["progression"], "metrics must be hidden on public endpoint"
        assert d["progression"]["level"] == 4
        # phase attached
        assert all("phase" in c for c in d["capabilities"])

    def test_public_capabilities_404(self):
        r = requests.get(f"{API}/specialists/000000000000000000000000/capabilities", timeout=10)
        assert r.status_code == 404
        r2 = requests.get(f"{API}/specialists/not-an-id/capabilities", timeout=10)
        assert r2.status_code == 404


# ─────────── Find ───────────
class TestFind:
    def test_find_by_capability(self):
        r = requests.get(f"{API}/capabilities/find", params={"capability": "interior_design", "min_score": 40}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 1
        scores = [x["compatibility_score"] for x in d["results"]]
        assert scores == sorted(scores, reverse=True), "results must be sorted score desc"
        assert all(s >= 40 for s in scores)

    def test_find_by_software(self):
        r = requests.get(f"{API}/capabilities/find", params={"software": "sketchup"}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 1


# ─────────── Portfolio extended fields ───────────
class TestPortfolioExtended:
    def test_add_extended_portfolio(self, spec_session):
        me = spec_session.get(f"{API}/auth/me", timeout=10).json()
        spec_id = me.get("id") or me.get("_id")
        item = {
            "title": "TEST_iter137 Extended",
            "description": "Test project with extended fields",
            "project_type": "residential",
            "services": ["interior_design", "lighting"],
            "role": "LEAD",
            "budget_range": "10000-20000 EUR",
            "tags": ["modern", "minimalist"],
            "before_image": "https://example.com/before.jpg",
            "after_image": "https://example.com/after.jpg",
            "video_url": "https://youtube.com/watch?v=test",
            "cover_image": "https://example.com/cover.jpg",
            "awards": "TEST Award 2025",
            "client_review": "Amazing work",
            "is_public": True,
        }
        r = spec_session.post(f"{API}/specialist/portfolio", json=item, timeout=15)
        assert r.status_code in (200, 201), f"portfolio add failed: {r.status_code} {r.text}"
        created = r.json()
        item_id = created.get("id") or created.get("_id")

        r2 = requests.get(f"{API}/specialists/{spec_id}/portfolio", timeout=10)
        assert r2.status_code == 200
        items = r2.json()
        if isinstance(items, dict):
            items = items.get("items") or items.get("results") or []
        found = next((it for it in items if it.get("title") == "TEST_iter137 Extended"), None)
        assert found is not None, "extended portfolio item not returned in public GET"
        # check extended fields present
        for f in ["project_type", "services", "role", "budget_range", "tags", "before_image",
                  "after_image", "video_url", "awards", "client_review"]:
            assert f in found, f"missing extended field: {f}"
        assert found["project_type"] == "residential"
        assert "modern" in (found.get("tags") or [])

        # cleanup
        if item_id:
            spec_session.delete(f"{API}/specialist/portfolio/{item_id}", timeout=10)


# ─────────── Restore ───────────
class TestRestore:
    def test_restore_default_capabilities(self, spec_session):
        """Restore specialist@propmanage.io default state (per main agent instructions)."""
        body = {"capabilities": DEFAULT_CAPS, "software": DEFAULT_SOFT, "languages": ["Română", "Engleză"]}
        r = spec_session.put(f"{API}/professional/capabilities", json=body, timeout=15)
        assert r.status_code == 200
        assert r.json()["compatibility"]["score"] == 90
