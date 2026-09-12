"""Enterprise Knowledge Center (Execution Order 002) — security + endpoint tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
FOUNDER = ("danieligna1@gmail.com", "Founder2026!kc")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def founder():
    return _login(*FOUNDER)


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


# --- Access gate ---
class TestAccessGate:
    def test_unauth_tree_401(self):
        r = requests.get(f"{BASE_URL}/api/founder/knowledge/tree", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_admin_access_flag_false(self, admin):
        r = admin.get(f"{BASE_URL}/api/founder/knowledge/access", timeout=30)
        assert r.status_code == 200
        assert r.json() == {"is_founder": False}

    def test_founder_access_flag_true(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/access", timeout=30)
        assert r.status_code == 200
        assert r.json() == {"is_founder": True}

    @pytest.mark.parametrize("path", ["tree", "doc?path=memory/prompts/SYSTEM_ZERO.md", "search?q=truth", "registry"])
    def test_admin_gets_403(self, admin, path):
        r = admin.get(f"{BASE_URL}/api/founder/knowledge/{path}", timeout=30)
        assert r.status_code == 403, f"{path}: expected 403 got {r.status_code}"


# --- Tree ---
class TestTree:
    def test_tree_shape(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/tree", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 100, f"expected >=100 docs, got {data['total']}"
        cat_names = [c["name"] for c in data["categories"]]
        for req in ["System Zero", "Execution Orders", "Board Directives", "Governance"]:
            assert req in cat_names, f"missing category {req}"
        # per-doc metadata fields
        sample = data["categories"][0]["docs"][0]
        for k in ("path", "title", "category", "version", "status", "author", "updated"):
            assert k in sample, f"doc missing field {k}"


# --- Doc + path traversal ---
class TestDoc:
    def test_valid_doc_system_zero(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/doc",
                        params={"path": "memory/prompts/SYSTEM_ZERO.md"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["meta"]["path"] == "memory/prompts/SYSTEM_ZERO.md"
        assert len(d["content"]) > 0
        rels = d["relationships"]
        # used_by should contain Master Executive Prompt v3 with VERIFIED evidence
        used_names = [u.get("other_name", "") for u in rels.get("used_by", [])]
        assert any("Master Executive Prompt v3" in n for n in used_names), f"missing MEP v3 link, got {used_names}"
        for u in rels.get("used_by", []):
            if "Master Executive Prompt v3" in u.get("other_name", ""):
                assert u.get("verification_status") == "VERIFIED"
                assert u.get("evidence"), "evidence must be non-empty"

    @pytest.mark.parametrize("bad", [
        "../../etc/passwd",
        "memory/../../../etc/passwd",
        "/etc/passwd",
        "etc/passwd",
        "memory/nonexistent.md",
    ])
    def test_path_traversal_blocked(self, founder, bad):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/doc",
                        params={"path": bad}, timeout=30)
        assert r.status_code in (400, 404), f"{bad}: got {r.status_code} body={r.text[:200]}"
        # ensure no /etc/passwd content leaked
        assert "root:" not in r.text


# --- Search ---
class TestSearch:
    def test_search_truth(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/search", params={"q": "truth"}, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["query"] == "truth"
        assert isinstance(d["documents"], list) and len(d["documents"]) > 0
        assert all("snippet" in x and "occurrences" in x for x in d["documents"])
        assert isinstance(d["registry_nodes"], list)


# --- Registry ---
class TestRegistry:
    def test_registry_shape(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/registry", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["stats"]["nodes"] == 46, f"expected 46 nodes, got {d['stats']['nodes']}"
        assert d["stats"]["edges"] == 44, f"expected 44 edges, got {d['stats']['edges']}"
        assert d["stats"]["edges_by_status"].get("VERIFIED") == 44
        required = {"id", "source", "target", "type", "description", "evidence",
                    "evidence_type", "confidence", "verification_status", "last_verified",
                    "verified_by", "version"}
        for e in d["edges"]:
            missing = required - set(e.keys())
            assert not missing, f"edge {e.get('id')} missing fields: {missing}"


# --- Regression ---
class TestRegression:
    def test_operations_still_up(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/operations", timeout=30)
        assert r.status_code == 200

    def test_ceo_briefing_still_up(self, admin):
        # try common endpoints
        for path in ["/api/admin/ceo-briefing", "/api/admin/ceo/briefing", "/api/admin/business-health"]:
            r = admin.get(f"{BASE_URL}{path}", timeout=30)
            if r.status_code == 200:
                return
        pytest.fail("no CEO briefing / business-health endpoint responded 200")
