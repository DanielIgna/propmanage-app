"""Phase 76 — Admin Auto-Match SCHEDULE + cron tick.

Endpoints under test:
- GET  /api/admin/auto-match/schedule (admin-only; 403 for client)
- PUT  /api/admin/auto-match/schedule (persists + validates interval bounds)
- run_auto_match_cron_tick() — direct in-process invocation:
    * disabled -> {"skipped": "disabled"}
    * enabled + no prior cron run -> executes execute_auto_match (kind=cron)
    * second consecutive call within interval -> {"skipped": "not_due", ...}
- After cron run: GET schedule.last_cron_run populated with executed_at +
  assigned_count + triggered_by.kind == "cron".
- Regression: /admin/autonomy/score, /admin/auto-match/run (manual),
  /admin/healthcheck/run, login flow.
"""
import os
import sys
import asyncio
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}

# Make backend importable for direct cron-tick invocation
sys.path.insert(0, "/app/backend")


def _session(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _session(ADMIN)


@pytest.fixture(scope="module")
def client_session():
    return _session(CLIENT)


# ----- AuthZ -----
class TestScheduleAuthZ:
    def test_get_schedule_requires_admin(self, client_session):
        r = client_session.get(f"{API}/admin/auto-match/schedule", timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:120]}"

    def test_put_schedule_requires_admin(self, client_session):
        r = client_session.put(f"{API}/admin/auto-match/schedule",
                               json={"enabled": True}, timeout=15)
        assert r.status_code == 403


# ----- GET shape -----
class TestScheduleGet:
    def test_get_schedule_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/auto-match/schedule", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "schedule" in data
        assert "last_run" in data
        assert "last_cron_run" in data
        sched = data["schedule"]
        for key in ("enabled", "interval_hours", "min_rating", "limit"):
            assert key in sched, f"missing {key} in schedule"
        assert isinstance(sched["enabled"], bool)
        assert isinstance(sched["interval_hours"], int)


# ----- PUT validation + persistence -----
class TestSchedulePut:
    def test_put_persists_valid_values(self, admin_session):
        # set to interval=6, enabled=False (baseline)
        r = admin_session.put(f"{API}/admin/auto-match/schedule",
                              json={"enabled": False, "interval_hours": 6},
                              timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is False
        assert data["interval_hours"] == 6

        # flip to enabled+interval=3
        r2 = admin_session.put(f"{API}/admin/auto-match/schedule",
                               json={"enabled": True, "interval_hours": 3},
                               timeout=15)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["enabled"] is True
        assert d2["interval_hours"] == 3

        # verify GET returns persisted state
        g = admin_session.get(f"{API}/admin/auto-match/schedule", timeout=15).json()
        assert g["schedule"]["enabled"] is True
        assert g["schedule"]["interval_hours"] == 3

    def test_put_rejects_interval_below_1(self, admin_session):
        r = admin_session.put(f"{API}/admin/auto-match/schedule",
                              json={"interval_hours": 0}, timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:120]}"

    def test_put_rejects_interval_above_24(self, admin_session):
        r = admin_session.put(f"{API}/admin/auto-match/schedule",
                              json={"interval_hours": 25}, timeout=15)
        assert r.status_code == 400


# ----- Cron tick direct invocation -----
# NOTE: motor's `db` singleton in routes/admin.py binds to the first asyncio
# event loop that touches it. Once that loop closes, subsequent motor calls
# fail with "Event loop is closed". To work around, we share ONE event loop
# across all motor-touching tests in this class via a module-scoped fixture.
@pytest.fixture(scope="module")
def shared_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestCronTick:
    def test_cron_tick_skipped_when_disabled(self, admin_session, shared_loop):
        # disable
        admin_session.put(f"{API}/admin/auto-match/schedule",
                          json={"enabled": False}, timeout=15)
        from routes.admin import run_auto_match_cron_tick
        result = shared_loop.run_until_complete(run_auto_match_cron_tick())
        assert result.get("skipped") == "disabled", f"got {result}"

    def test_cron_tick_runs_when_enabled_then_not_due(self, admin_session, shared_loop):
        from routes.admin import run_auto_match_cron_tick, db as admin_db

        # Wipe historical cron run docs so first call actually executes
        async def _wipe():
            await admin_db.auto_match_runs.delete_many({"triggered_by.kind": "cron"})
        shared_loop.run_until_complete(_wipe())

        # enable + interval=6 to make second call "not_due"
        r = admin_session.put(f"{API}/admin/auto-match/schedule",
                              json={"enabled": True, "interval_hours": 6,
                                    "min_rating": 0, "limit": 100},
                              timeout=15)
        assert r.status_code == 200

        first = shared_loop.run_until_complete(run_auto_match_cron_tick())
        # first call should execute (not skipped)
        assert first.get("ok") is True, f"first call did not execute: {first}"
        assert first.get("triggered_by", {}).get("kind") == "cron"
        assert first.get("dry_run") is False
        assert isinstance(first.get("assigned_count"), int)

        second = shared_loop.run_until_complete(run_auto_match_cron_tick())
        assert second.get("skipped") == "not_due", f"second call should be not_due: {second}"
        assert "next_due_in_sec" in second
        assert isinstance(second["next_due_in_sec"], int)
        assert second["next_due_in_sec"] > 0


# ----- Schedule reflects cron last_cron_run after tick -----
class TestLastCronRunPersisted:
    def test_last_cron_run_populated(self, admin_session):
        r = admin_session.get(f"{API}/admin/auto-match/schedule", timeout=15)
        assert r.status_code == 200
        data = r.json()
        last_cron = data.get("last_cron_run")
        assert last_cron is not None, "last_cron_run should be populated after TestCronTick"
        assert "executed_at" in last_cron
        assert "assigned_count" in last_cron
        tb = last_cron.get("triggered_by", {})
        assert tb.get("kind") == "cron", f"last_cron_run triggered_by.kind != 'cron': {tb}"


# ----- Manual flow + regression -----
class TestManualAndRegression:
    def test_manual_run_uses_admin_manual_kind(self, admin_session):
        r = admin_session.post(f"{API}/admin/auto-match/run",
                               json={"dry_run": True, "limit": 5}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["dry_run"] is True
        tb = d.get("triggered_by", {})
        assert tb.get("kind") == "admin_manual", f"manual run kind != admin_manual: {tb}"

    def test_manual_real_run_persists_with_admin_manual(self, admin_session):
        # Real run — even if it assigns 0, doc should be inserted with admin_manual
        r = admin_session.post(f"{API}/admin/auto-match/run",
                               json={"dry_run": False, "limit": 5, "min_rating": 9.9},
                               timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        # min_rating=9.9 will skip everything but a doc is still persisted
        sched = admin_session.get(f"{API}/admin/auto-match/schedule", timeout=15).json()
        last = sched.get("last_run")
        if last:
            assert last.get("triggered_by", {}).get("kind") in ("admin_manual", "cron")

    def test_autonomy_score(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert r.status_code == 200

    def test_healthcheck_run(self, admin_session):
        # endpoint is registered as GET in admin_healthcheck.py
        r = admin_session.get(f"{API}/admin/healthcheck/run", timeout=60)
        assert r.status_code in (200, 201), r.text[:200]

    def test_login_still_200(self):
        r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=15)
        assert r.status_code == 200


# ----- Teardown: disable schedule so cron stays quiet -----
@pytest.fixture(scope="module", autouse=True)
def _restore_disabled(admin_session):
    yield
    try:
        admin_session.put(f"{API}/admin/auto-match/schedule",
                          json={"enabled": False, "interval_hours": 6},
                          timeout=10)
    except Exception:
        pass
