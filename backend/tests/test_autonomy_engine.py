"""Tests for the Autonomy Engine (Phase A1+A2).

Covers:
- GET /api/admin/autonomy/score   (admin only, returns full report)
- GET /api/admin/autonomy/history (admin only, returns items/days/count)
- POST /api/admin/autonomy/snapshot (creates snapshot doc)
- GET/PUT /api/admin/autonomy/targets (config CRUD + cache invalidation)
- 403 on non-admin role
- Smoke check: /api/admin/ai-control/overview & /api/admin/healthcheck still respond
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend env file
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT)


# ---------------------------------------------------------------------------
# /score
# ---------------------------------------------------------------------------
class TestAutonomyScore:
    def test_score_admin_ok(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # Required keys
        for k in ("scores", "tier", "weights", "targets", "breakdown", "recommendations", "computed_at"):
            assert k in data, f"missing key {k}"
        # Sub-scores
        scores = data["scores"]
        for k in ("general", "operational", "technical", "security", "dev", "ai"):
            assert k in scores, f"missing score {k}"
            assert isinstance(scores[k], (int, float))
            assert 0 <= scores[k] <= 100
        # Tier
        assert data["tier"] in ("self-driving", "autonomous", "assisted", "manual")
        # Weights = 6 keys (5 sub-scores) - note: weights are 5 (sub-scores), targets are 6 incl general
        assert set(data["weights"].keys()) >= {"operational", "technical", "security", "dev", "ai"}
        assert set(data["targets"].keys()) >= {"general", "operational", "technical", "security", "dev", "ai"}
        # Breakdown sanity
        for k in ("operational", "technical", "security", "dev", "ai"):
            assert "score" in data["breakdown"][k]
            assert "signals" in data["breakdown"][k]
        # Recommendations is a list (may be empty)
        assert isinstance(data["recommendations"], list)
        # No ObjectId leakage
        assert "_id" not in str(data)

    def test_score_non_admin_403(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_score_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=30)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /snapshot + /history
# ---------------------------------------------------------------------------
class TestAutonomySnapshotHistory:
    def test_snapshot_then_history_count_increases(self, admin_client):
        # baseline count
        r0 = admin_client.get(f"{BASE_URL}/api/admin/autonomy/history?days=30", timeout=30)
        assert r0.status_code == 200, r0.text
        base = r0.json()
        assert "items" in base and "days" in base and "count" in base
        assert base["days"] == 30
        baseline_count = base["count"]

        # take snapshot
        r1 = admin_client.post(f"{BASE_URL}/api/admin/autonomy/snapshot", timeout=60)
        assert r1.status_code == 200, r1.text
        snap = r1.json()
        # Either error key absent, or full doc returned
        assert "error" not in snap, f"snapshot returned error: {snap}"
        # No ObjectId leak
        assert "_id" not in snap
        for k in ("snap_id", "timestamp", "scores", "tier"):
            assert k in snap, f"snapshot missing {k}"

        # history must now have at least one more item
        r2 = admin_client.get(f"{BASE_URL}/api/admin/autonomy/history?days=30", timeout=30)
        assert r2.status_code == 200
        after = r2.json()
        assert after["count"] >= baseline_count + 1, (
            f"count did not increase: before={baseline_count} after={after['count']}"
        )
        assert len(after["items"]) > 0

    def test_history_non_admin_403(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/autonomy/history?days=7", timeout=30)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /targets GET + PUT
# ---------------------------------------------------------------------------
class TestAutonomyTargets:
    def test_get_targets(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/autonomy/targets", timeout=30)
        assert r.status_code == 200, r.text
        cfg = r.json()
        assert "weights" in cfg and "targets" in cfg
        # 5 weights (sub-scores), 6 targets (incl general)
        assert len(cfg["weights"]) == 5
        assert len(cfg["targets"]) == 6

    def test_put_targets_normalize_and_persist(self, admin_client):
        # Read original config
        original = admin_client.get(f"{BASE_URL}/api/admin/autonomy/targets", timeout=30).json()

        # Update weights and targets
        new_weights = {
            "operational": 2,
            "technical": 2,
            "security": 2,
            "dev": 2,
            "ai": 2,
        }  # sum=10 -> normalized 0.2 each
        new_targets = {
            "general": 92,
            "operational": 96,
            "technical": 86,
            "security": 91,
            "dev": 76,
            "ai": 81,
        }
        r = admin_client.put(
            f"{BASE_URL}/api/admin/autonomy/targets",
            json={"weights": new_weights, "targets": new_targets},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        cfg = r.json()
        # Weights normalized
        for k, v in cfg["weights"].items():
            assert abs(v - 0.2) < 1e-6, f"weight {k}={v} not normalized to 0.2"
        # Targets persisted exactly
        for k, v in new_targets.items():
            assert cfg["targets"][k] == v

        # GET again -> still persisted
        r2 = admin_client.get(f"{BASE_URL}/api/admin/autonomy/targets", timeout=30).json()
        for k, v in new_targets.items():
            assert r2["targets"][k] == v

        # /score should reflect new weights/targets (cache invalidated)
        r3 = admin_client.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=60).json()
        for k in new_weights:
            assert abs(r3["weights"][k] - 0.2) < 1e-6
        for k, v in new_targets.items():
            assert r3["targets"][k] == v

        # Restore originals
        admin_client.put(
            f"{BASE_URL}/api/admin/autonomy/targets",
            json={"weights": original["weights"], "targets": original["targets"]},
            timeout=30,
        )

    def test_put_targets_zero_weights_rejected(self, admin_client):
        r = admin_client.put(
            f"{BASE_URL}/api/admin/autonomy/targets",
            json={"weights": {"operational": 0, "technical": 0, "security": 0, "dev": 0, "ai": 0}},
            timeout=30,
        )
        assert r.status_code == 400

    def test_targets_non_admin_403(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/autonomy/targets", timeout=30)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Smoke: existing AI endpoints still work (no regression)
# ---------------------------------------------------------------------------
class TestNoRegression:
    def test_ai_control_overview(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/ai-control/overview", timeout=30)
        assert r.status_code == 200, r.text

    def test_admin_healthcheck(self, admin_client):
        # actual endpoint exposed by admin_healthcheck router
        r = admin_client.get(f"{BASE_URL}/api/admin/healthcheck/run", timeout=60)
        assert r.status_code == 200, r.text
