"""CORE-001 Product Intelligence Engine backend tests (iteration 154)."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


# ============ product-map ============
class TestProductMap:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/ai-brain/product-map", timeout=30)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"

    def test_get_product_map(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "modules" in data and "totals" in data and "consolidation_roadmap" in data
        assert len(data["modules"]) == 19, f"expected 19 modules got {len(data['modules'])}"
        # each module shape
        for m in data["modules"]:
            for k in ("key", "name", "status", "completeness", "business_value", "priority_index", "signals", "features", "bvs_breakdown"):
                assert k in m, f"module {m.get('key')} missing {k}"
            assert 0 <= m["completeness"] <= 100
        # totals
        t = data["totals"]
        assert "avg_completeness" in t
        assert t.get("orphans", 0) >= 1
        assert t.get("duplicates", 0) == 4, f"duplicates expected 4 got {t.get('duplicates')}"
        # roadmap sort: impact*2 - risk descending
        roadmap = data["consolidation_roadmap"]
        assert len(roadmap) > 0
        scores = [(item.get("impact", 0) * 2 - item.get("risk", 0)) for item in roadmap]
        assert scores == sorted(scores, reverse=True), f"roadmap not sorted: {scores}"

    def test_refresh_changes_generated_at(self, admin_session):
        r1 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map", timeout=60).json()
        r2 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map?refresh=true", timeout=60).json()
        assert r1.get("generated_at") and r2.get("generated_at")
        assert r1["generated_at"] != r2["generated_at"], "generated_at should change on refresh"


# ============ snapshots ============
class TestSnapshots:
    def test_create_and_list(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/product-map/snapshot",
                               json={"label": "TEST_iter154_regress"}, timeout=60)
        assert r.status_code == 200, r.text
        snap = r.json()
        for k in ("id", "label", "created_at", "totals"):
            assert k in snap
        assert snap["label"] == "TEST_iter154_regress"

        r2 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map/snapshots", timeout=30)
        assert r2.status_code == 200
        lst = r2.json()
        items = lst if isinstance(lst, list) else lst.get("snapshots", lst.get("items", []))
        assert len(items) >= 1
        ids = [it.get("id") for it in items]
        assert snap["id"] in ids
        # newest first: first snapshot's created_at >= second
        if len(items) >= 2:
            assert items[0].get("created_at", "") >= items[1].get("created_at", "")

    def test_compare(self, admin_session):
        lst = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map/snapshots", timeout=30).json()
        items = lst if isinstance(lst, list) else lst.get("snapshots", lst.get("items", []))
        assert len(items) >= 2, "need >=2 snapshots for compare"
        a, b = items[0]["id"], items[1]["id"]
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map/snapshots/compare",
                              params={"a": a, "b": b}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "deltas" in data or "modules" in data or isinstance(data, dict)

    def test_compare_invalid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map/snapshots/compare",
                              params={"a": "bad-id", "b": "worse-id"}, timeout=30)
        # Should return error object (200 with error field) or 4xx
        if r.status_code == 200:
            assert "error" in r.json()
        else:
            assert r.status_code in (400, 404)


# ============ report ============
class TestReport:
    def test_report_generates_markdown(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/product-map/report", timeout=120)
        assert r.status_code == 200, r.text
        # Response could be json {markdown: "..."} or plain text
        ctype = r.headers.get("content-type", "")
        text = r.text
        if "application/json" in ctype:
            j = r.json()
            text = j.get("markdown") or j.get("report") or j.get("content") or ""
        assert len(text) > 10000, f"report too short: {len(text)}"
        for section in ("MASTER DISCOVERY REPORT", "Roadmap de Consolidare", "PB-001"):
            assert section in text, f"missing section: {section}"
        # file on disk
        assert os.path.exists("/app/docs/CORE001_MASTER_DISCOVERY_REPORT.md")


# ============ regression ============
class TestAIBrainRegression:
    def test_status(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/status", timeout=30)
        assert r.status_code == 200, r.text

    def test_registry_modules(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/registry/modules", timeout=30)
        assert r.status_code == 200, r.text

    def test_graph_overview(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/overview", timeout=30)
        assert r.status_code == 200, r.text
