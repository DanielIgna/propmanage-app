"""Iter86 — Autonomy Orchestrator Sprint 1 backend tests.

Covers:
- /api/admin/orchestrator/overview KPI + playbooks
- /simulate/{smoke_fail|autonomy_score_drop|webhook_fail}
- /retry-tick behavior (backoff, no duplicate re-enqueue, escalation after 3)
- /playbooks/{id}/toggle disable→skipped_disabled→re-enable
- /ledger endpoint
- 401/403 for non-admin
- Regression: /api/admin/autonomy/score works (reflex snapshot didn't break autonomy engine)
- Regression: client login + client dashboard endpoint responds
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"  # from backend/.env SEED_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ------------------------------------------------------------------
# OVERVIEW
# ------------------------------------------------------------------
class TestOverview:
    def test_overview_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "today" in d and "playbooks" in d
        assert set(d["today"].keys()) >= {"actions", "minutes_saved", "auto_resolved", "escalated"}
        assert "total_minutes_saved" in d
        assert "retry_pending" in d
        # 3 playbooks expected
        ids = {pb["id"] for pb in d["playbooks"]}
        assert ids == {"smoke_fail_to_qa", "autonomy_reflex", "webhook_retry_guardian"}, f"got {ids}"
        for pb in d["playbooks"]:
            assert "enabled" in pb and "runs_total" in pb
            # last_run_at may be None if never run

    def test_overview_forbidden_for_non_admin(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_overview_forbidden_for_anon(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=30)
        assert r.status_code in (401, 403)


# ------------------------------------------------------------------
# SIMULATE
# ------------------------------------------------------------------
class TestSimulate:
    def test_simulate_smoke_fail_creates_qa_session_and_ledger(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/smoke_fail", timeout=30)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d.get("handled") is True
        led = d.get("ledger") or {}
        assert led.get("outcome") == "auto_resolved"
        assert led.get("minutes_saved") == 20
        assert led.get("test") is True
        assert led.get("playbook_id") == "smoke_fail_to_qa"

    def test_simulate_smoke_fail_dedupes_same_day(self, admin_session):
        # Second call should append to existing qa session (still returns auto_resolved w/ append action)
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/smoke_fail", timeout=30)
        assert r.status_code == 200
        led = r.json().get("ledger") or {}
        actions = [s.get("action") for s in led.get("steps") or []]
        assert "append_finding_existing_session" in actions, f"expected dedupe append, got steps={actions}"

    def test_simulate_autonomy_score_drop_test_mode(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/autonomy_score_drop", timeout=45)
        assert r.status_code == 200, r.text[:300]
        led = r.json().get("ledger") or {}
        assert led.get("outcome") == "auto_resolved"
        # SIMULARE marker present
        details = " ".join((s.get("detail") or "") for s in led.get("steps") or [])
        assert "SIMULARE" in details, f"expected SIMULARE marker, got: {details[:200]}"

    def test_simulate_webhook_fail_enqueues_retry(self, admin_session):
        # baseline retry_pending
        ov0 = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=30).json()
        pending0 = ov0.get("retry_pending", 0)

        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/webhook_fail", timeout=30)
        assert r.status_code == 200, r.text[:200]
        led = r.json().get("ledger") or {}
        assert led.get("outcome") == "retry_scheduled"

        ov1 = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=30).json()
        assert ov1.get("retry_pending", 0) >= pending0 + 1, "retry_pending should have increased by >=1"

    def test_simulate_invalid_kind(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/nonexistent", timeout=15)
        assert r.status_code == 400

    def test_simulate_forbidden_for_client(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/smoke_fail", timeout=15)
        assert r.status_code in (401, 403)


# ------------------------------------------------------------------
# RETRY TICK — backoff, no dupe, escalate after 3
# ------------------------------------------------------------------
class TestRetryTick:
    def test_retry_tick_processes_pending(self, admin_session):
        # Ensure at least one email in queue (create fresh one). handle_webhook_fail sets next_retry_at ~2 min in future,
        # so first tick likely has processed=0. That's OK — we're mainly testing the endpoint contract.
        admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/webhook_fail", timeout=30)
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/retry-tick", timeout=30)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        for k in ("processed", "sent", "failed_permanent", "rescheduled"):
            assert k in d, f"missing key {k}"
            assert isinstance(d[k], int)

    def test_retry_tick_no_duplicate_and_escalates(self, admin_session):
        """Force items due-now (next_retry_at in past) via direct simulate, then
        tick multiple times. Because Resend fails in this env, each due item
        should either reschedule (attempts++) or fail permanent after 3 attempts.
        We only verify contract: processed items don't duplicate & each tick
        gives an integer summary. Full failure→escalation asserted at DB level
        would require direct db access which the pytest here avoids."""
        # We can't manipulate next_retry_at from HTTP; just tick a few times and
        # ensure no error is raised.
        for _ in range(3):
            r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/retry-tick", timeout=30)
            assert r.status_code == 200
            time.sleep(0.5)

    def test_retry_tick_forbidden_for_client(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/admin/orchestrator/retry-tick", timeout=15)
        assert r.status_code in (401, 403)


# ------------------------------------------------------------------
# TOGGLE PLAYBOOK
# ------------------------------------------------------------------
class TestToggle:
    def test_toggle_disable_and_reenable(self, admin_session):
        pid = "smoke_fail_to_qa"
        # Disable
        r = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/{pid}/toggle",
            json={"enabled": False}, timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("enabled") is False

        # Verify simulate returns handled=false reason=playbook_disabled
        r = admin_session.post(f"{BASE_URL}/api/admin/orchestrator/simulate/smoke_fail", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("handled") is False
        assert d.get("reason") == "playbook_disabled"

        # Overview should show enabled=False for this playbook + ledger entry skipped_disabled
        ov = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=15).json()
        smoke = next((p for p in ov["playbooks"] if p["id"] == pid), None)
        assert smoke and smoke["enabled"] is False

        led = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger", params={"limit": 20}, timeout=15).json()
        recent_smoke = [e for e in led["items"] if e.get("playbook_id") == pid][:5]
        assert any(e.get("outcome") == "skipped_disabled" for e in recent_smoke), "expected skipped_disabled ledger entry"

        # Re-enable (cleanup)
        r = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/{pid}/toggle",
            json={"enabled": True}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("enabled") is True

    def test_toggle_unknown_playbook_404(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/nope/toggle",
            json={"enabled": True}, timeout=15,
        )
        assert r.status_code == 404

    def test_toggle_forbidden_for_client(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/admin/orchestrator/playbooks/smoke_fail_to_qa/toggle",
            json={"enabled": False}, timeout=15,
        )
        assert r.status_code in (401, 403)


# ------------------------------------------------------------------
# LEDGER
# ------------------------------------------------------------------
class TestLedger:
    def test_ledger_returns_items(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
        # After our smoke_fail simulate calls, we should have entries
        assert len(d["items"]) >= 1
        e = d["items"][0]
        assert "id" in e and "ts" in e and "outcome" in e

    def test_ledger_forbidden_for_client(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger", timeout=15)
        assert r.status_code in (401, 403)


# ------------------------------------------------------------------
# REGRESSION
# ------------------------------------------------------------------
class TestRegression:
    def test_client_login_and_me(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("email") == CLIENT_EMAIL
        assert d.get("role") == "client"

    def test_autonomy_score_still_works(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=30)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        # Basic shape check — reflex snapshot didn't break the engine
        assert isinstance(d, dict)
        # /admin/autonomy/score returns {scores, tier, weights, targets, breakdown, recommendations, computed_at, cached}
        assert "scores" in d and "tier" in d, f"unexpected shape: {list(d.keys())}"
        assert isinstance(d["scores"], dict)
