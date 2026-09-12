"""Iter95 — Sprint D Autonomy Sprint 3 (Pattern Hunter, Finance Reconciler, Roadmap Advisor).

Tests the 3 new orchestrator playbooks via admin cookie session.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
# Main agent asserts admin password is "1!nasov01ADMIN"; test_credentials.md still lists "Admin123!" (stale).
ADMIN_PASSWORDS = ["1!nasov01ADMIN", "Admin123!"]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    last_err = None
    for pw in ADMIN_PASSWORDS:
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": pw}, timeout=15)
        if r.status_code == 200:
            print(f"[admin_session] Login OK with password variant: {'primary' if pw == ADMIN_PASSWORDS[0] else 'fallback'}")
            return s
        last_err = f"{r.status_code} {r.text[:200]}"
    pytest.skip(f"Cannot login as admin: {last_err}")


# ---------------------------------------------------------------------------
# 1. Overview: all 10 playbooks
# ---------------------------------------------------------------------------
class TestOverview:
    def test_overview_lists_10_playbooks_including_sprint3(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "playbooks" in data
        pbs = data["playbooks"]
        assert len(pbs) == 10, f"Expected 10 playbooks, got {len(pbs)}: {[p['name'] for p in pbs]}"

        by_name = {p["name"]: p for p in pbs}
        for expected in ("Pattern Hunter", "Finance Reconciler", "Roadmap Advisor"):
            assert expected in by_name, f"Missing playbook: {expected}"
            assert by_name[expected].get("description"), f"{expected} missing description"

        # ids
        ids = {p["id"] for p in pbs}
        for pid in ("pattern_hunter", "finance_reconciler", "roadmap_advisor"):
            assert pid in ids


# ---------------------------------------------------------------------------
# 2. Simulate pattern_scan
# ---------------------------------------------------------------------------
class TestSimulatePatternScan:
    def test_simulate_pattern_scan_auto_resolved_4_steps(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/pattern_scan", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Result comes back nested under emit_signal shape: {simulated, handled, ledger:{...}}
        assert data.get("simulated") == "pattern_scan"
        assert data.get("handled") is True, f"Expected handled=True, got: {data}"

        ledger = data.get("ledger") or {}
        outcome = ledger.get("outcome")
        steps = ledger.get("steps") or []
        print(f"[pattern_scan] outcome={outcome} steps={len(steps)}")
        assert outcome == "auto_resolved", f"Expected auto_resolved got {outcome}: {data}"
        assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}: {steps}"
        action_names = [s.get("action") for s in steps]
        for expected_action in ("scan_demand_surge", "scan_dispute_hotspots", "scan_stale_demand", "report_findings"):
            assert expected_action in action_names, f"Missing step {expected_action}, got: {action_names}"

        # report_findings should include SIMULARE marker in test mode
        report_step = next(s for s in steps if s.get("action") == "report_findings")
        detail = report_step.get("detail", "")
        assert "SIMULARE" in detail, f"Expected 'SIMULARE' in report_findings detail, got: {detail}"


# ---------------------------------------------------------------------------
# 3. Simulate finance_reconcile
# ---------------------------------------------------------------------------
class TestSimulateFinanceReconcile:
    def test_simulate_finance_reconcile_4_steps(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/finance_reconcile", timeout=45)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("simulated") == "finance_reconcile"
        assert data.get("handled") is True

        ledger = data.get("ledger") or {}
        steps = ledger.get("steps") or []
        outcome = ledger.get("outcome")
        escalated = ledger.get("escalated")
        print(f"[finance_reconcile] outcome={outcome} escalated={escalated} steps={len(steps)}")
        assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}: {steps}"
        action_names = [s.get("action") for s in steps]
        for expected_action in (
            "check_negative_balances",
            "check_orphan_transactions",
            "check_confirmed_without_tx",
            "reconciliation_verdict",
        ):
            assert expected_action in action_names, f"Missing step {expected_action}, got: {action_names}"


# ---------------------------------------------------------------------------
# 4. Simulate roadmap_advise (test mode → NO Claude call)
# ---------------------------------------------------------------------------
class TestSimulateRoadmapAdvise:
    def test_simulate_roadmap_advise_skips_claude(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/roadmap_advise", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("simulated") == "roadmap_advise"
        assert data.get("handled") is True

        ledger = data.get("ledger") or {}
        outcome = ledger.get("outcome")
        steps = ledger.get("steps") or []
        print(f"[roadmap_advise] outcome={outcome} steps={len(steps)}")
        assert outcome == "auto_resolved", f"Expected auto_resolved got {outcome}"

        llm_step = next((s for s in steps if s.get("action") == "llm_advise"), None)
        assert llm_step is not None, f"Missing llm_advise step, got: {steps}"
        detail = llm_step.get("detail", "")
        assert "SIMULARE" in detail and "sărit" in detail, f"Expected SIMULARE skip message, got: {detail}"


# ---------------------------------------------------------------------------
# 5. Simulate invalid kind → 400 listing all 10 kinds
# ---------------------------------------------------------------------------
class TestSimulateInvalidKind:
    def test_invalid_kind_returns_400_with_all_kinds(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/invalid_kind", timeout=15)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        for kind in (
            "smoke_fail",
            "autonomy_score_drop",
            "webhook_fail",
            "category_visibility_refresh",
            "dispute_opened",
            "kyc_prevalidated",
            "marketplace_medic_scan",
            "pattern_scan",
            "finance_reconcile",
            "roadmap_advise",
        ):
            assert kind in detail, f"Missing kind '{kind}' in 400 detail: {detail}"


# ---------------------------------------------------------------------------
# 6. Playbook toggle: disable + verify skip, re-enable + verify runs.
#    IMPORTANT: leave enabled=true at the end.
# ---------------------------------------------------------------------------
class TestPlaybookToggle:
    def test_pattern_hunter_toggle_skip_then_enable(self, admin_session):
        # Disable
        r = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/pattern_hunter/toggle",
            json={"enabled": False}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("enabled") is False

        # Simulate — expect handled=false with reason=playbook_disabled
        r2 = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/pattern_scan", timeout=15)
        assert r2.status_code == 200
        d2 = r2.json()
        print(f"[toggle disabled] data={d2}")
        assert d2.get("handled") is False, f"Expected handled=False when disabled, got: {d2}"
        assert d2.get("reason") == "playbook_disabled", f"Expected reason=playbook_disabled, got: {d2.get('reason')}"

        # Re-enable
        r3 = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/pattern_hunter/toggle",
            json={"enabled": True}, timeout=15,
        )
        assert r3.status_code == 200
        assert r3.json().get("enabled") is True

        # Simulate again — expect auto_resolved
        r4 = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/pattern_scan", timeout=30)
        assert r4.status_code == 200
        d4 = r4.json()
        assert d4.get("handled") is True
        outcome_enabled = (d4.get("ledger") or {}).get("outcome")
        assert outcome_enabled == "auto_resolved", f"Expected auto_resolved after re-enable, got {outcome_enabled}"

    def test_ensure_all_sprint3_enabled_at_end(self, admin_session):
        """Safety net: verify all 3 new playbooks are enabled=true after tests."""
        for pid in ("pattern_hunter", "finance_reconciler", "roadmap_advisor"):
            r = admin_session.post(
                f"{BASE_URL}/api/admin/orchestrator/playbooks/{pid}/toggle",
                json={"enabled": True}, timeout=15,
            )
            assert r.status_code == 200, f"Failed to re-enable {pid}"
            assert r.json().get("enabled") is True


# ---------------------------------------------------------------------------
# 8. Ledger shows recent entries for the 3 new playbooks
# ---------------------------------------------------------------------------
class TestLedger:
    def test_ledger_shows_sprint3_entries(self, admin_session):
        # Give the async writes a moment
        time.sleep(1)
        r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger?limit=200", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        pb_ids_present = {i.get("playbook_id") for i in items}
        print(f"[ledger] {len(items)} items, playbook_ids sample={list(pb_ids_present)[:10]}")
        for pid in ("pattern_hunter", "finance_reconciler", "roadmap_advisor"):
            assert pid in pb_ids_present, f"Ledger missing entry for {pid}. Got ids: {pb_ids_present}"
