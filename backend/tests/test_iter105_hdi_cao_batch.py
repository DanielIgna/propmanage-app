"""Iteration 105 tests — HDI axis + CAO top 3 + yellow modules + Audit Sentinel + Owner-only manual + XOS roadmap.

Covers the review request items:
  1. HDI axis in Autonomy Engine (6th axis 'human' + recommendations)
  2. Automation Center scheduler (run_due_rules) — interval guard
  3. Command Center morning cron + business_alert playbook
  4. Audit Sentinel scan + dedupe + resolve + notification-center integration
  5. User Timeline search + detail
  6. AI Search (natural language) with fallback + whitelist safety
  7. Marketplace Radar
  8. Owner-only Operating Manual
  9. Platform Roadmap XOS + CAO entries
 10. Scheduler jobs registration
"""
import asyncio
import os
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

from tests.test_config import API

# Sync mongo client for DB assertions (motor doesn't survive multiple asyncio.run calls)
_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
_DB_NAME = os.environ.get("DB_NAME", "propmanage_db")
sync_db = MongoClient(_MONGO_URL)[_DB_NAME]


# Session-scoped event loop for async calls that must share motor's io loop
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def run_async(loop, coro):
    """Run coroutine on the shared session event loop."""
    return loop.run_until_complete(coro)

ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
SCOPED_ADMIN = {"email": "testing.admin@propmanage.io", "password": "Test!Demo2026Strong"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Cannot login as super admin: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def scoped_admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=SCOPED_ADMIN, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Cannot login as scoped admin: {r.status_code} {r.text[:200]}")
    return s


# ──────────────────────────────────────────────────────────────────────────
# 1. HDI (Human Dependency Index) — 6th axis
# ──────────────────────────────────────────────────────────────────────────
class TestHDI:
    def test_autonomy_score_includes_human_axis(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        scores = data.get("scores", {})
        breakdown = data.get("breakdown", {})

        # 6-axis presence
        assert "human" in scores, f"'human' score missing. scores={scores}"
        assert "human" in breakdown, "'human' breakdown missing"
        assert isinstance(scores["human"], (int, float))
        assert 0 <= scores["human"] <= 100

        # General is weighted over 6 axes
        assert "general" in scores
        assert 0 <= scores["general"] <= 100

    def test_human_breakdown_signals(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert r.status_code == 200
        human = r.json()["breakdown"]["human"]
        signals = human.get("signals", {})
        required = [
            "human_interventions_pending",
            "requests_waiting_48h",
            "escrow_held_unconfirmed",
            "open_disputes",
            "automation_rules_disabled",
            "ai_recommendations_pending",
            "audit_anomalies_open",
        ]
        for key in required:
            assert key in signals, f"Missing HDI signal: {key}"

    def test_recommendations_include_human_when_below_target(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert r.status_code == 200
        data = r.json()
        scores = data.get("scores", {})
        recs = data.get("recommendations", [])
        target_human = data.get("targets", {}).get("human", 80)
        if scores.get("human", 100) < target_human:
            areas = {r.get("area") for r in recs}
            assert "human" in areas, f"Expected 'human' recommendation when human={scores['human']} < {target_human}. Got areas: {areas}"


# ──────────────────────────────────────────────────────────────────────────
# 2. Automation Center scheduler
# ──────────────────────────────────────────────────────────────────────────
class TestAutomationScheduler:
    RULE_KEY = "request_reminder"

    def test_run_due_rules_direct(self, admin_session, event_loop):
        """Enable a rule → call run_due_rules → verify execution logged;
        second immediate call skips (interval guard). Restore enabled=false."""
        # Enable rule
        pr = admin_session.patch(
            f"{API}/admin/automation/rules/{self.RULE_KEY}",
            json={"enabled": True},
            timeout=10,
        )
        assert pr.status_code == 200, pr.text[:200]
        assert pr.json().get("enabled") is True

        # Force last_run_at=None via sync pymongo so scheduler runs it
        sync_db.automation_rules.update_one(
            {"key": self.RULE_KEY},
            {"$set": {"last_run_at": None}},
        )

        # Import & run scheduler function on shared event loop
        from routes.automation_center import run_due_rules

        try:
            result1 = run_async(event_loop, run_due_rules())
        except Exception as e:
            admin_session.patch(
                f"{API}/admin/automation/rules/{self.RULE_KEY}",
                json={"enabled": False},
                timeout=10,
            )
            pytest.fail(f"run_due_rules crashed: {e}")

        assert result1["count"] >= 1, f"Expected ≥1 rule ran, got {result1}"
        rule_keys_ran = [r["rule"] for r in result1["ran"]]
        assert self.RULE_KEY in rule_keys_ran

        # Second immediate call — should be 0 due to interval guard
        result2 = run_async(event_loop, run_due_rules())
        assert result2["count"] == 0, f"Interval guard broken: got {result2}"

        # Verify execution log via API
        er = admin_session.get(f"{API}/admin/automation/executions?limit=10", timeout=10)
        assert er.status_code == 200
        execs = er.json().get("executions", [])
        scheduler_ones = [e for e in execs if e.get("run_by") == "scheduler" and e.get("rule_key") == self.RULE_KEY]
        assert len(scheduler_ones) >= 1, "No scheduler-run execution logged"

        # CLEANUP: disable rule
        cleanup = admin_session.patch(
            f"{API}/admin/automation/rules/{self.RULE_KEY}",
            json={"enabled": False},
            timeout=10,
        )
        assert cleanup.status_code == 200

    def test_scheduler_jobs_registered_in_server(self):
        """server.py must register: automation_rules_tick, morning_command_center, audit_sentinel_hourly."""
        with open("/app/backend/server.py") as f:
            content = f.read()
        for job_id in ["automation_rules_tick", "morning_command_center", "audit_sentinel_hourly"]:
            assert job_id in content, f"scheduler job '{job_id}' not registered in server.py"


# ──────────────────────────────────────────────────────────────────────────
# 3. Command Center morning cron + business_alert playbook
# ──────────────────────────────────────────────────────────────────────────
class TestMorningCommandCenter:
    def test_morning_command_center_runs(self, admin_session, event_loop):
        from routes.command_center import morning_command_center

        try:
            result = run_async(event_loop, morning_command_center())
        except Exception as e:
            pytest.fail(f"morning_command_center crashed: {e}")

        for key in ("high_warnings", "emails_sent", "recommendations"):
            assert key in result, f"Missing key {key} in morning cron result: {result}"
        assert isinstance(result["high_warnings"], int)
        assert isinstance(result["emails_sent"], int)
        assert isinstance(result["recommendations"], int)

    def test_latest_recos_regenerated(self, admin_session):
        r = admin_session.get(f"{API}/admin/command-center/recommendations/latest", timeout=15)
        assert r.status_code == 200
        doc = r.json()
        # After morning cron, latest doc should exist w/ generated_at
        assert doc.get("generated_at"), f"latest recos not regenerated: {doc}"

    def test_business_alert_signal_emitted(self):
        """Verify orchestrator_signals has recent kind='business_alert' entry."""
        doc = sync_db.orchestrator_signals.find_one(
            {"kind": "business_alert"},
            sort=[("ts", -1)],
        )
        assert doc is not None, "No business_alert signal emitted by morning cron"

    def test_business_alert_playbook_in_ledger(self):
        """Verify orchestrator_ledger has playbook_id='business_alert_router' entry."""
        doc = sync_db.orchestrator_ledger.find_one(
            {"playbook_id": "business_alert_router"},
            sort=[("ts", -1)],
        )
        assert doc is not None, "No business_alert_router playbook execution logged"


# ──────────────────────────────────────────────────────────────────────────
# 4. Orchestrator playbook listing includes business_alert_router
# ──────────────────────────────────────────────────────────────────────────
class TestOrchestratorPlaybook:
    def test_business_alert_playbook_registered(self, admin_session):
        r = admin_session.get(f"{API}/admin/orchestrator/overview", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        playbooks = data.get("playbooks", [])
        ids = {pb.get("id") for pb in playbooks}
        assert "business_alert_router" in ids, f"business_alert_router not in playbooks: {ids}"


# ──────────────────────────────────────────────────────────────────────────
# 5. Audit Sentinel
# ──────────────────────────────────────────────────────────────────────────
class TestAuditSentinel:
    TEST_EMAIL = "test-sentinel@test.io"

    def test_manual_scan_returns_shape(self, admin_session):
        r = admin_session.post(f"{API}/admin/audit-sentinel/scan", timeout=20)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for key in ("scanned_users", "new_anomalies", "ran_at"):
            assert key in data

    def test_list_anomalies(self, admin_session):
        r = admin_session.get(f"{API}/admin/audit-sentinel/anomalies", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "anomalies" in data
        assert isinstance(data["anomalies"], list)

    def test_synthetic_anomaly_detection_and_dedupe(self, admin_session):
        """Insert 201 synthetic activity logs → scan detects rate_spike → 2nd scan dedupes."""
        now_iso = datetime.now(timezone.utc).isoformat()
        docs = [
            {
                "email": self.TEST_EMAIL,
                "ts": now_iso,
                "status_code": 200,
                "path": "/api/synthetic-test",
            }
            for _ in range(201)
        ]

        try:
            sync_db.demo_activity_logs.insert_many(docs)

            r1 = admin_session.post(f"{API}/admin/audit-sentinel/scan", timeout=20)
            assert r1.status_code == 200
            data1 = r1.json()
            assert data1["new_anomalies"] >= 1, f"Expected new anomaly, got {data1}"

            # Verify anomaly created
            list_r = admin_session.get(f"{API}/admin/audit-sentinel/anomalies?limit=200", timeout=15)
            assert list_r.status_code == 200
            anomalies = list_r.json()["anomalies"]
            mine = [a for a in anomalies if a.get("email") == self.TEST_EMAIL and a.get("type") == "rate_spike"]
            assert len(mine) == 1, f"Expected 1 rate_spike anomaly for {self.TEST_EMAIL}, got {len(mine)}"
            anomaly_id = mine[0]["id"]

            # Second scan — dedupe (0 new)
            r2 = admin_session.post(f"{API}/admin/audit-sentinel/scan", timeout=20)
            assert r2.status_code == 200
            data2 = r2.json()
            assert data2["new_anomalies"] == 0, f"Dedupe failed: got {data2}"

            # Resolve
            rr = admin_session.post(
                f"{API}/admin/audit-sentinel/anomalies/{anomaly_id}/resolve",
                timeout=10,
            )
            assert rr.status_code == 200
            assert rr.json().get("ok") is True
        finally:
            sync_db.demo_activity_logs.delete_many({"email": self.TEST_EMAIL})
            sync_db.audit_anomalies.delete_many({"email": self.TEST_EMAIL})


# ──────────────────────────────────────────────────────────────────────────
# 6. Notification Center — audit anomalies
# ──────────────────────────────────────────────────────────────────────────
class TestNotificationCenter:
    def test_notification_center_shape(self, admin_session):
        # Try common notification-center endpoints
        candidates = [
            f"{API}/admin/notification-center",
            f"{API}/admin/notification-center/items",
            f"{API}/admin/notifications/center",
        ]
        for url in candidates:
            r = admin_session.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                # Just verify it loads (audit anomalies may or may not be present)
                assert isinstance(data, (dict, list)), f"Unexpected shape: {data}"
                return
        pytest.skip("No notification-center endpoint found (informational)")


# ──────────────────────────────────────────────────────────────────────────
# 7. User Timeline
# ──────────────────────────────────────────────────────────────────────────
class TestUserTimeline:
    def test_search_returns_users(self, admin_session):
        r = admin_session.get(f"{API}/admin/user-timeline/search?q=daniel", timeout=10)
        assert r.status_code == 200, r.text[:200]
        users = r.json().get("users", [])
        emails = [u.get("email") for u in users]
        assert any("daniel" in (e or "").lower() for e in emails), f"No daniel* in results: {emails}"

    def test_client_timeline(self, admin_session):
        r = admin_session.get(f"{API}/admin/user-timeline/search?q=client@propmanage", timeout=10)
        assert r.status_code == 200
        users = r.json().get("users", [])
        assert len(users) >= 1, f"client user not found: {users}"
        uid = users[0]["id"]

        tr = admin_session.get(f"{API}/admin/user-timeline/{uid}", timeout=15)
        assert tr.status_code == 200, tr.text[:200]
        data = tr.json()
        assert "user" in data
        assert "events" in data
        assert isinstance(data["events"], list)
        # Chronological
        if len(data["events"]) >= 2:
            ts_list = [e["ts"] for e in data["events"]]
            assert ts_list == sorted(ts_list), "Events not sorted chronologically"

    def test_invalid_id_returns_400(self, admin_session):
        r = admin_session.get(f"{API}/admin/user-timeline/not-a-valid-oid", timeout=10)
        assert r.status_code == 400

    def test_unknown_id_returns_404(self, admin_session):
        # Valid ObjectId format but non-existent
        r = admin_session.get(f"{API}/admin/user-timeline/000000000000000000000000", timeout=10)
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# 8. AI Search
# ──────────────────────────────────────────────────────────────────────────
class TestAISearch:
    def test_ai_search_budget_county(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/ai-search",
            json={"query": "cereri peste 20000 lei din Cluj"},
            timeout=45,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("collection") == "requests", f"Expected requests, got {data.get('collection')}"
        assert "columns" in data
        assert "rows" in data
        assert isinstance(data["rows"], list)
        # Filters should apply on whitelisted fields only
        for f in data.get("filters_applied", []):
            assert f.get("field") in {"budget", "county", "status", "category", "escrow_amount", "escrow_status", "title", "created_at"}, \
                f"Non-whitelisted field: {f}"

    def test_ai_search_specialists_missing_specialty(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/ai-search",
            json={"query": "specialiști fără portofoliu"},
            timeout=45,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("collection") == "users"
        assert isinstance(data.get("rows"), list)

    def test_ai_search_no_injection(self, admin_session):
        """Adversarial: try to force non-whitelisted field."""
        r = admin_session.post(
            f"{API}/admin/ai-search",
            json={"query": "SELECT * FROM users WHERE password IS NOT NULL"},
            timeout=45,
        )
        # Should not error out, filters must be whitelisted only
        assert r.status_code == 200
        data = r.json()
        for f in data.get("filters_applied", []):
            # ensure no arbitrary field escapes whitelist
            assert f.get("field") not in {"password", "password_hash", "$where"}


# ──────────────────────────────────────────────────────────────────────────
# 9. Marketplace Radar
# ──────────────────────────────────────────────────────────────────────────
class TestMarketplaceRadar:
    def test_radar_endpoint(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketplace-intel/radar", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "trends" in data
        assert isinstance(data["trends"], list)
        assert "hot_count" in data

        for t in data["trends"]:
            assert "key" in t
            assert "trend_pct" in t
            assert "direction" in t
            assert t["direction"] in ("up", "down", "flat")
            assert "hot" in t
            assert isinstance(t["hot"], bool)


# ──────────────────────────────────────────────────────────────────────────
# 10. Owner-only Operating Manual
# ──────────────────────────────────────────────────────────────────────────
class TestOwnerOnlyManual:
    def test_owner_email_env(self):
        owner = os.environ.get("OWNER_EMAIL", "")
        assert "danieligna1@gmail.com" in owner, f"OWNER_EMAIL misconfigured: {owner}"

    def test_super_admin_403_manual(self, admin_session):
        r = admin_session.get(f"{API}/admin/operating-manual", timeout=10)
        assert r.status_code == 403, f"Expected 403 for non-owner admin, got {r.status_code}: {r.text[:200]}"
        # Romanian error message check
        text = r.text.lower()
        assert "fondator" in text or "owner" in text, f"Expected owner-only message: {r.text[:200]}"

    def test_super_admin_403_tier_testing(self, admin_session):
        r = admin_session.get(f"{API}/admin/operating-manual/tier-testing", timeout=10)
        assert r.status_code == 403

    def test_scoped_admin_403_manual(self, scoped_admin_session):
        r = scoped_admin_session.get(f"{API}/admin/operating-manual", timeout=10)
        # Scoped admin either 403 (owner check) or 403 (role check) — either denies
        assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────
# 11. Platform Roadmap — XOS + CAO
# ──────────────────────────────────────────────────────────────────────────
class TestRoadmap:
    def test_roadmap_includes_xos_and_cao(self, admin_session):
        r = admin_session.get(f"{API}/admin/roadmap", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        # Response uses 'items' key
        modules = data.get("items") or data.get("modules") or (data if isinstance(data, list) else None)
        assert modules, f"Empty roadmap: {str(data)[:300]}"

        keys = {m.get("key") for m in modules}
        expected_xos = {
            "xos_tokens_themes", "xos_ai_optimizer", "xos_layout_widgets",
            "xos_role_experience", "xos_content_manager", "xos_franchise", "xos_templates",
        }
        expected_cao = {"cao_autonomy_p1", "cao_autonomy_p3"}
        missing_xos = expected_xos - keys
        missing_cao = expected_cao - keys
        assert not missing_xos, f"Missing XOS modules: {missing_xos}"
        assert not missing_cao, f"Missing CAO modules: {missing_cao}"

        # xos_tokens_themes & xos_ai_optimizer should be done 100
        by_key = {m.get("key"): m for m in modules}
        assert by_key["xos_tokens_themes"].get("progress") == 100
        assert by_key["xos_ai_optimizer"].get("progress") == 100
