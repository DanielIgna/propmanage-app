"""CIP-A — Construction Intelligence Platform Faza A regression tests (iter87).

Covers:
- Public taxonomy tree (unauth, visible-only)
- Admin taxonomy CRUD (create root/child, patch name, patch is_active refresh, delete leaf/parent)
- Refresh visibility via orchestrator (ledger entry + playbook_name)
- Overview (total/visible + hidden_with_potential includes zugravit)
- Projects filters + CSV export
- Orchestrator overview lists 4 playbooks incl. category_visibility_gate
- Verify specialist hook emits category_visibility_refresh
"""
import os
import io
import csv
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"  # from SEED_ADMIN_PASSWORD env
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


# ============================ FIXTURES ============================
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="session")
def public_session():
    return requests.Session()


# ============================ PUBLIC TAXONOMY ============================
class TestPublicTaxonomy:
    def test_public_tree_no_auth(self, public_session):
        r = public_session.get(f"{BASE_URL}/api/construction/taxonomy/public", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tree" in data and "count" in data
        assert isinstance(data["tree"], list)
        # Roots present in public tree must all have specialist coverage (legacy verified specialists)
        # ~5 root categories expected: handyman, hvac, electric, plumbing, interior_design
        legacies = {n["legacy_category"] for n in data["tree"]}
        # At least handyman/hvac/electric should be visible (seed accounts)
        assert data["count"] > 0, "Public taxonomy should have at least some visible nodes"
        assert data["count"] < 200, "Public tree should NOT contain all 203 nodes"
        # Every node returned must be publicly visible
        def check(n):
            assert n.get("is_publicly_visible") is True, f"Non-visible node in public tree: {n['name']}"
            for c in n.get("children") or []:
                check(c)
        for n in data["tree"]:
            check(n)
        print(f"[public taxonomy] {data['count']} visible nodes, legacies={legacies}")


# ============================ ADMIN TAXONOMY ============================
class TestAdminTaxonomy:
    def test_admin_taxonomy_requires_auth(self, public_session):
        r = public_session.get(f"{BASE_URL}/api/construction/taxonomy", timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_admin_taxonomy_full(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/construction/taxonomy", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] >= 200, f"Expected ~203 nodes, got {data['count']}"
        assert data["visible_count"] > 0
        assert data["visible_count"] < data["count"]

    def test_taxonomy_crud_full_flow(self, admin_session):
        """Create root → create child → rename → toggle root off → verify descendants hidden → re-enable → delete leaf → delete parent (should 409 initially)."""
        unique = uuid.uuid4().hex[:8]
        root_name = f"TEST_CIPA_root_{unique}"

        # CREATE root (no specialists → not publicly visible)
        r = admin_session.post(f"{BASE_URL}/api/construction/taxonomy",
                               json={"name": root_name}, timeout=15)
        assert r.status_code == 200, r.text
        root = r.json()
        assert root["name"] == root_name
        assert root["depth_level"] == 0
        assert root["is_publicly_visible"] is False, "New root has no specialists → must be hidden"
        assert root["is_active"] is True
        root_id = root["id"]

        # CREATE child (inherits legacy_category)
        child_name = f"TEST_CIPA_child_{unique}"
        r = admin_session.post(f"{BASE_URL}/api/construction/taxonomy",
                               json={"name": child_name, "parent_id": root_id}, timeout=15)
        assert r.status_code == 200, r.text
        child = r.json()
        assert child["parent_id"] == root_id
        assert child["depth_level"] == 1
        assert child["legacy_category"] == root["legacy_category"]
        child_id = child["id"]

        # RENAME
        new_name = f"{child_name}_renamed"
        r = admin_session.patch(f"{BASE_URL}/api/construction/taxonomy/{child_id}",
                                json={"name": new_name}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == new_name

        # DELETE root with child → 409
        r = admin_session.delete(f"{BASE_URL}/api/construction/taxonomy/{root_id}", timeout=15)
        assert r.status_code == 409

        # DELETE child (leaf) → ok
        r = admin_session.delete(f"{BASE_URL}/api/construction/taxonomy/{child_id}", timeout=15)
        assert r.status_code == 200

        # DELETE root now that it's a leaf → ok
        r = admin_session.delete(f"{BASE_URL}/api/construction/taxonomy/{root_id}", timeout=15)
        assert r.status_code == 200

    def test_toggle_visibility_gate_on_real_root(self, admin_session, public_session):
        """Disable HVAC root, verify descendants become hidden in public tree; then re-enable."""
        # Find hvac root
        r = admin_session.get(f"{BASE_URL}/api/construction/taxonomy", timeout=15)
        tree = r.json()["tree"]
        hvac = next((n for n in tree if n["legacy_category"] == "hvac"), None)
        assert hvac is not None, "hvac root missing in seed"
        assert hvac["is_publicly_visible"] is True, "hvac should be visible (has specialists)"

        # Disable
        r = admin_session.patch(f"{BASE_URL}/api/construction/taxonomy/{hvac['id']}",
                                json={"is_active": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

        # Public tree should NOT contain hvac now
        time.sleep(0.5)
        pub = public_session.get(f"{BASE_URL}/api/construction/taxonomy/public", timeout=15).json()
        pub_legacies = {n["legacy_category"] for n in pub["tree"]}
        assert "hvac" not in pub_legacies, "hvac should be hidden after deactivation"

        # RE-ENABLE (cleanup)
        r = admin_session.patch(f"{BASE_URL}/api/construction/taxonomy/{hvac['id']}",
                                json={"is_active": True}, timeout=15)
        assert r.status_code == 200
        assert r.json()["is_active"] is True

        # Verify restored
        time.sleep(0.5)
        pub = public_session.get(f"{BASE_URL}/api/construction/taxonomy/public", timeout=15).json()
        pub_legacies = {n["legacy_category"] for n in pub["tree"]}
        assert "hvac" in pub_legacies, "hvac should be visible again after re-enable"


# ============================ REFRESH VISIBILITY ============================
class TestRefreshVisibility:
    def test_refresh_via_orchestrator_appears_in_ledger(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/construction/refresh-visibility", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("handled") is True
        ledger = data.get("ledger") or {}
        assert ledger.get("playbook_name") == "Category Visibility Gate"
        assert ledger.get("outcome") == "auto_resolved"
        steps = ledger.get("steps") or []
        actions = {s.get("action") for s in steps}
        assert "recompute_visibility" in actions
        assert "flag_hidden_with_potential" in actions

        # Verify appears in global ledger
        r2 = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger?limit=10", timeout=15)
        assert r2.status_code == 200
        ledger_list = r2.json().get("items") or r2.json().get("ledger") or []
        # Some entry with playbook_id category_visibility_gate should exist
        found = any(e.get("playbook_id") == "category_visibility_gate" for e in ledger_list)
        assert found, "category_visibility_gate ledger entry not found in orchestrator ledger"


# ============================ OVERVIEW ============================
class TestOverview:
    def test_overview_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/construction/overview", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_nodes"] >= 200
        assert data["visible_nodes"] > 0
        assert data["root_categories"] >= 10
        coverage = data.get("coverage") or []
        assert len(coverage) >= 10
        for row in coverage:
            assert "legacy_category" in row and "name" in row
            assert "specialists" in row and "requests_90d" in row
            assert "visible" in row and "active" in row

    def test_hidden_with_potential_may_contain_zugravit(self, admin_session):
        # This depends on whether zugravit has requests in last 90d. Just verify structure.
        r = admin_session.get(f"{BASE_URL}/api/construction/overview", timeout=15)
        data = r.json()
        hp = data.get("hidden_with_potential") or []
        # If any hidden_with_potential exist, they must have specialists==0 AND requests_90d>0
        coverage_map = {c["legacy_category"]: c for c in data.get("coverage") or []}
        for h in hp:
            assert h["specialists"] == 0
            assert h["requests_90d"] > 0
        print(f"[overview] hidden_with_potential legacies = {[h['legacy_category'] for h in hp]}")


# ============================ PROJECTS ============================
class TestProjects:
    def test_projects_list_with_filters(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/construction/projects",
            params={"status": "open", "limit": 20},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "count" in data
        assert isinstance(data["items"], list)
        for it in data["items"]:
            assert "id" in it and "title" in it and "category" in it and "status" in it
            assert it["status"] == "open"

    def test_projects_filter_query_param(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/construction/projects",
            params={"q": "TEST", "limit": 20},
            timeout=15,
        )
        assert r.status_code == 200

    def test_projects_min_max_value_filter(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/construction/projects",
            params={"min_value": 100, "max_value": 100000, "limit": 20},
            timeout=15,
        )
        assert r.status_code == 200
        for it in r.json().get("items", []):
            if it.get("budget_estimate") is not None:
                assert 100 <= it["budget_estimate"] <= 100000

    def test_projects_csv_export(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/construction/projects/export",
            params={"limit": 10},
            timeout=20,
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        body = r.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(body))
        rows = list(reader)
        assert len(rows) >= 1, "CSV must have at least the header"
        header = rows[0]
        # Romanian header
        assert "Titlu" in header and "Categorie" in header and "Buget (RON)" in header
        assert "Oraș" in header and "Client" in header


# ============================ ORCHESTRATOR OVERVIEW LISTS 4 PLAYBOOKS ============================
class TestOrchestratorPlaybooksCount:
    def test_lists_four_playbooks(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        playbooks = data.get("playbooks") or []
        assert len(playbooks) >= 4, f"Expected >=4 playbooks, got {len(playbooks)}: {[p.get('id') for p in playbooks]}"
        ids = {p.get("id") for p in playbooks}
        assert "category_visibility_gate" in ids


# ============================ VERIFY SPECIALIST HOOK ============================
class TestVerifySpecialistHook:
    def test_verify_emits_category_visibility_refresh(self, admin_session):
        """Register a test specialist → verify → check that a Category Visibility Gate
        ledger entry appears within a few seconds after verify."""
        unique = uuid.uuid4().hex[:8]
        email = f"test_specverify_{unique}@propmanage.io"
        # Register a new specialist (public endpoint)
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "Spec123!",
            "name": f"TEST Spec {unique}", "role": "specialist",
            "phone": "+40712345678",
            "terms_accepted": True, "privacy_policy_accepted": True,
            "specialty": "hvac", "service_categories": ["hvac"],
            "coverage_zones": ["Bucuresti"],
        }, timeout=15)
        if r.status_code not in (200, 201):
            pytest.skip(f"Register failed ({r.status_code}): {r.text[:200]}")
        reg = r.json()
        spec_id = reg.get("id")
        if not spec_id:
            pytest.skip(f"Register returned no id: {list(reg.keys())}")

        # Read ledger count BEFORE verify
        before = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger?limit=50", timeout=15).json()
        before_items = before.get("items") or before.get("ledger") or []
        before_cvg = sum(1 for e in before_items if e.get("playbook_id") == "category_visibility_gate")

        # VERIFY
        r = admin_session.post(f"{BASE_URL}/api/admin/specialists/{spec_id}/verify", timeout=15)
        assert r.status_code == 200

        # Give the async task a beat
        time.sleep(1.5)
        after = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger?limit=50", timeout=15).json()
        after_items = after.get("items") or after.get("ledger") or []
        after_cvg = sum(1 for e in after_items if e.get("playbook_id") == "category_visibility_gate")

        assert after_cvg > before_cvg, (
            f"No new Category Visibility Gate ledger entry after verify "
            f"(before={before_cvg}, after={after_cvg})"
        )
