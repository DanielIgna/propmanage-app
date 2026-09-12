"""Iter102 — Design Intelligence Engine (P1a/b/c) + Platform Roadmap.
Coverage:
  · /api/admin/design-intelligence/{targets,layout/analyze,components/analyze,proposals,summary,proposals/{id}/{advance,rollback},delete}
  · /api/admin/roadmap /analyze /analysis/latest /{key} (PATCH)
  · RBAC 403 for client role
  · Apply→Rollback with token snapshot restoration (leave tokens as original)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_role_client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"client login failed: {r.status_code} {r.text[:200]}")
    return s


# ── Design Intelligence — targets & summary ─────────────────────────────────
class TestTargetsAndSummary:
    def test_targets_pages_and_components(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-intelligence/targets", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "pages" in data and "components" in data
        assert len(data["pages"]) == 13, f"expected 13 pages, got {len(data['pages'])}"
        assert len(data["components"]) == 17, f"expected 17 components, got {len(data['components'])}"
        # Sanity: pages have key/label/zone/path
        p0 = data["pages"][0]
        for k in ("key", "label", "zone", "path"):
            assert k in p0
        c0 = data["components"][0]
        for k in ("key", "label", "category"):
            assert k in c0

    def test_summary_has_counts_and_top_pending(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/design-intelligence/summary", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "counts" in data
        assert "total" in data
        assert "top_pending" in data
        # counts should have all valid statuses
        for s in ("proposed", "testing", "approved", "applied", "rejected"):
            assert s in data["counts"]
        # top_pending is sorted desc by impact score
        top = data["top_pending"]
        if len(top) >= 2:
            scores = [(p.get("impact") or {}).get("score", 0) for p in top]
            assert scores == sorted(scores, reverse=True), f"top_pending not sorted desc: {scores}"


# ── Component Optimizer (P1b) — reuse ds_button (already has proposals) ─────
class TestComponentOptimizer:
    def test_analyze_kpi_card_returns_proposals_with_impact(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/components/analyze",
            json={"component_key": "kpi_card"}, timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        proposals = data.get("proposals", [])
        assert len(proposals) >= 1, "expected at least 1 proposal"
        for p in proposals:
            assert p["source"] == "component_optimizer"
            assert p["target"] == "kpi_card"
            imp = p.get("impact") or {}
            for k in ("score", "ux_benefit", "users_reach", "effort", "risk", "tier"):
                assert k in imp, f"impact missing {k}: {imp}"
            assert 0 <= imp["score"] <= 100
            assert imp["tier"] in ("high", "medium", "low")
            assert p["status"] == "proposed"

    def test_analyze_unknown_component_returns_404(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/components/analyze",
            json={"component_key": "does_not_exist_xyz"}, timeout=15,
        )
        assert r.status_code == 404


# ── Layout Optimizer (P1a) ──────────────────────────────────────────────────
class TestLayoutOptimizer:
    def test_analyze_landing_returns_proposals(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/layout/analyze",
            json={"page_key": "landing"}, timeout=90,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        proposals = data.get("proposals", [])
        assert 1 <= len(proposals) <= 6, f"expected 1-6 proposals, got {len(proposals)}"
        for p in proposals:
            assert p["source"] == "layout_optimizer"
            assert p["target"] == "landing"
            imp = p.get("impact") or {}
            assert 0 <= imp.get("score", -1) <= 100
        # verify persistence via list endpoint
        r2 = admin_client.get(f"{BASE_URL}/api/admin/design-intelligence/proposals?source=layout_optimizer", timeout=15)
        assert r2.status_code == 200
        found_ids = {p["id"] for p in r2.json()["proposals"]}
        for p in proposals:
            assert p["id"] in found_ids, f"proposal {p['id']} not persisted"

    def test_analyze_unknown_page_returns_404(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/layout/analyze",
            json={"page_key": "nonexistent_page_zzz"}, timeout=15,
        )
        assert r.status_code == 404


# ── Evolution Engine (P1c) ──────────────────────────────────────────────────
def _make_proposal_no_tokens(admin_client) -> str:
    """Return a proposed proposal id. Prefer non-token, fall back to any proposed."""
    def _first_proposed(prefer_no_token=True):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/design-intelligence/proposals?status=proposed", timeout=15,
        )
        proposals = r.json().get("proposals", [])
        if prefer_no_token:
            for p in proposals:
                if not p.get("token_patch"):
                    return p["id"]
        return proposals[0]["id"] if proposals else None

    pid = _first_proposed(prefer_no_token=True)
    if pid:
        return pid
    # trigger analyze to generate fresh proposals
    admin_client.post(
        f"{BASE_URL}/api/admin/design-intelligence/components/analyze",
        json={"component_key": "kpi_card"}, timeout=60,
    )
    pid = _first_proposed(prefer_no_token=True) or _first_proposed(prefer_no_token=False)
    if pid:
        return pid
    pytest.skip("no proposed proposal available")


def _make_proposal_with_tokens(admin_client) -> dict:
    """Return a proposal dict having a token_patch (for apply/rollback test)."""
    r = admin_client.get(
        f"{BASE_URL}/api/admin/design-intelligence/proposals?status=proposed", timeout=15,
    )
    for p in r.json().get("proposals", []):
        if p.get("token_patch"):
            return p
    # analyze ds_button to force a token proposal (LLM often produces token_patch on components)
    r2 = admin_client.post(
        f"{BASE_URL}/api/admin/design-intelligence/components/analyze",
        json={"component_key": "ds_button"}, timeout=60,
    )
    for p in r2.json().get("proposals", []):
        if p.get("token_patch"):
            return p
    pytest.skip("no token-patch proposal available")


class TestEvolutionPipeline:
    def test_full_pipeline_transitions(self, admin_client):
        pid = _make_proposal_no_tokens(admin_client)
        # proposed → start_test → testing
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "start_test"}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["proposal"]["status"] == "testing"

        # testing → approve → approved
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "approve"}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["proposal"]["status"] == "approved"

        # approved → apply → applied
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "apply"}, timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["proposal"]["status"] == "applied"
        # If it applied tokens live, MUST rollback to keep environment clean
        if data["applied"].get("tokens_applied"):
            rb = admin_client.post(
                f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/rollback", timeout=15,
            )
            assert rb.status_code == 200
            assert rb.json()["tokens_restored"] is True

    def test_invalid_transition_returns_400(self, admin_client):
        pid = _make_proposal_no_tokens(admin_client)
        # can't apply directly from proposed
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "apply"}, timeout=15,
        )
        assert r.status_code == 400

    def test_unknown_action_returns_400(self, admin_client):
        pid = _make_proposal_no_tokens(admin_client)
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "banana"}, timeout=15,
        )
        assert r.status_code == 400

    def test_reject_from_proposed(self, admin_client):
        pid = _make_proposal_no_tokens(admin_client)
        r = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "reject"}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["proposal"]["status"] == "rejected"

    def test_delete_only_for_proposed_or_rejected(self, admin_client):
        # rejected → delete allowed
        pid = _make_proposal_no_tokens(admin_client)
        admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
            json={"action": "reject"}, timeout=15,
        )
        r = admin_client.delete(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}", timeout=15,
        )
        assert r.status_code == 200

        # applied → delete forbidden — reuse the pipeline test outcome by creating a fresh chain
        pid2 = _make_proposal_no_tokens(admin_client)
        for act in ("start_test", "approve", "apply"):
            admin_client.post(
                f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid2}/advance",
                json={"action": act}, timeout=15,
            )
        r2 = admin_client.delete(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid2}", timeout=15,
        )
        assert r2.status_code == 400


# ── CRITICAL: Apply→Rollback with token patch (must restore tokens) ─────────
class TestApplyRollbackTokens:
    def test_apply_merges_patch_and_rollback_restores(self, admin_client):
        proposal = _make_proposal_with_tokens(admin_client)
        pid = proposal["id"]
        patch = proposal["token_patch"]

        # Capture original tokens
        r0 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=15)
        assert r0.status_code == 200
        original_tokens = r0.json()["tokens"]

        # Advance proposed → approved → applied
        for act in ("start_test", "approve", "apply"):
            r = admin_client.post(
                f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/advance",
                json={"action": act}, timeout=15,
            )
            assert r.status_code == 200, f"{act} failed: {r.text[:200]}"

        apply_resp = r.json()
        assert apply_resp["proposal"]["status"] == "applied"
        assert apply_resp["applied"]["tokens_applied"] is True

        # Verify tokens reflect the patch
        r1 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=15)
        applied_tokens = r1.json()["tokens"]
        for group_key, group in patch.items():
            for token_key, token_val in group.items():
                assert applied_tokens.get(group_key, {}).get(token_key) == token_val, (
                    f"patch not applied to {group_key}.{token_key}: expected {token_val}, "
                    f"got {applied_tokens.get(group_key, {}).get(token_key)}"
                )

        # Rollback
        r2 = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/rollback", timeout=15,
        )
        assert r2.status_code == 200
        assert r2.json()["tokens_restored"] is True
        assert r2.json()["proposal"]["status"] == "approved"

        # Verify tokens restored
        r3 = admin_client.get(f"{BASE_URL}/api/admin/design-studio/tokens", timeout=15)
        restored_tokens = r3.json()["tokens"]
        for group_key, group in patch.items():
            for token_key in group:
                assert restored_tokens.get(group_key, {}).get(token_key) == original_tokens.get(group_key, {}).get(token_key), (
                    f"rollback did not restore {group_key}.{token_key}"
                )

        # Rollback on non-applied returns 400
        r4 = admin_client.post(
            f"{BASE_URL}/api/admin/design-intelligence/proposals/{pid}/rollback", timeout=15,
        )
        assert r4.status_code == 400


# ── Platform Roadmap ────────────────────────────────────────────────────────
class TestRoadmap:
    def test_seed_and_counts(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 21, f"expected 21 modules, got {data['total']}"
        counts = data["counts"]
        for k in ("urgent", "priority", "improvement", "done", "in_progress", "planned"):
            assert k in counts
        assert isinstance(data["overall_progress"], (int, float))

    def test_seed_is_idempotent(self, admin_client):
        r1 = admin_client.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        r2 = admin_client.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        assert r1.json()["total"] == r2.json()["total"] == 21

    def test_patch_updates_and_persists(self, admin_client):
        # PATCH a module — pick 'resend_dns' (least critical)
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/roadmap/resend_dns",
            json={"progress": 55, "notes": "TEST_iter102_note"}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["progress"] == 55
        assert r.json()["notes"] == "TEST_iter102_note"

        # Re-GET — value must survive re-seed
        r2 = admin_client.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        m = next((x for x in r2.json()["items"] if x["key"] == "resend_dns"), None)
        assert m is not None
        assert m["progress"] == 55
        assert m["notes"] == "TEST_iter102_note"

    def test_patch_invalid_priority_returns_400(self, admin_client):
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/roadmap/resend_dns",
            json={"priority": "banana"}, timeout=15,
        )
        assert r.status_code == 400

    def test_patch_unknown_key_returns_404(self, admin_client):
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/roadmap/does_not_exist_xyz",
            json={"progress": 10}, timeout=15,
        )
        assert r.status_code == 404

    def test_analyze_and_latest(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/admin/roadmap/analyze", timeout=90)
        assert r.status_code == 200
        data = r.json()
        for k in ("verdict", "top_priorities", "quick_wins", "risks", "overlaps", "suggested_order", "ai_generated"):
            assert k in data
        assert isinstance(data["top_priorities"], list)

        # cached fetch
        r2 = admin_client.get(f"{BASE_URL}/api/admin/roadmap/analysis/latest", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["result"] is not None


# ── RBAC — client should get 403 on all /admin/design-intelligence + /admin/roadmap
class TestRBAC:
    @pytest.mark.parametrize("path", [
        "/api/admin/design-intelligence/targets",
        "/api/admin/design-intelligence/summary",
        "/api/admin/design-intelligence/proposals",
        "/api/admin/roadmap",
    ])
    def test_client_gets_403_on_admin_get(self, client_role_client, path):
        r = client_role_client.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 403, f"{path}: {r.status_code}"

    @pytest.mark.parametrize("path,payload", [
        ("/api/admin/design-intelligence/layout/analyze", {"page_key": "landing"}),
        ("/api/admin/design-intelligence/components/analyze", {"component_key": "kpi_card"}),
        ("/api/admin/roadmap/analyze", {}),
    ])
    def test_client_gets_403_on_admin_post(self, client_role_client, path, payload):
        r = client_role_client.post(f"{BASE_URL}{path}", json=payload, timeout=15)
        assert r.status_code == 403, f"{path}: {r.status_code}"
