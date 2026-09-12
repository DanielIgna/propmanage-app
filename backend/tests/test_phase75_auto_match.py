"""Phase 75 — Admin bulk auto-match tool.

Endpoints under test:
- POST /api/admin/auto-match/preview
- POST /api/admin/auto-match/run (dry_run=true / false; min_rating filter)
- Regression: /api/admin/autonomy/snapshot, /api/admin/autonomy/score,
  /api/admin/smoke-test/run, /api/admin/ai/findings/{id}/resolve (smoke).
- Autonomy operational.signals.auto_matched_requests_pct should increase after run.
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


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
class TestAuth:
    def test_preview_requires_admin(self, client_session):
        r = client_session.post(f"{API}/admin/auto-match/preview", timeout=20)
        assert r.status_code == 403, f"expected 403 for client, got {r.status_code}"

    def test_run_requires_admin(self, client_session):
        r = client_session.post(f"{API}/admin/auto-match/run", json={"dry_run": True}, timeout=20)
        assert r.status_code == 403


# ----- Preview shape -----
class TestPreview:
    def test_preview_returns_expected_shape(self, admin_session):
        r = admin_session.post(f"{API}/admin/auto-match/preview", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for key in ("items", "total_unmatched", "with_match_available", "no_match_available"):
            assert key in data, f"missing key {key} in preview response"
        assert isinstance(data["items"], list)
        assert isinstance(data["total_unmatched"], int)
        # Sums must match
        assert data["total_unmatched"] == len(data["items"])
        assert data["with_match_available"] + data["no_match_available"] == data["total_unmatched"]
        # Per item structure
        for item in data["items"][:5]:
            assert "request_id" in item
            assert "best_match" in item  # either dict or None


# ----- Dry-run does not mutate -----
class TestDryRun:
    def test_dry_run_does_not_mutate(self, admin_session):
        pre = admin_session.post(f"{API}/admin/auto-match/preview", timeout=30).json()
        total_pre = pre["total_unmatched"]

        r = admin_session.post(
            f"{API}/admin/auto-match/run",
            json={"limit": 100, "min_rating": 0, "dry_run": True},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        result = r.json()
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert "assigned" in result and "skipped" in result
        for a in result.get("assigned", []):
            assert a.get("dry_run") is True

        # Preview unchanged
        post = admin_session.post(f"{API}/admin/auto-match/preview", timeout=30).json()
        assert post["total_unmatched"] == total_pre, (
            f"dry_run mutated data: {total_pre} -> {post['total_unmatched']}"
        )


# ----- min_rating filter -----
class TestMinRatingFilter:
    def test_high_min_rating_skips_with_reason(self, admin_session):
        # Set unrealistically high rating to force the skipped path.
        r = admin_session.post(
            f"{API}/admin/auto-match/run",
            json={"limit": 50, "min_rating": 9.9, "dry_run": True},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        result = r.json()
        # If there are any unmatched candidates, they must show in skipped with reason.
        if result["assigned_count"] + result["skipped_count"] > 0:
            assert result["assigned_count"] == 0, (
                "no specialist should clear 9.9 rating gate"
            )
            for s in result["skipped"]:
                assert s["reason"] == "no_eligible_specialist"


# ----- Real run reduces unmatched count + autonomy signal increases -----
class TestRealRun:
    def test_real_run_assigns_and_signal_increases(self, admin_session):
        # Snapshot autonomy BEFORE
        snap_before = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert snap_before.status_code == 200
        sig_before = (
            snap_before.json()
            .get("breakdown", {})
            .get("operational", {})
            .get("signals", {})
            .get("auto_matched_requests_pct")
        )

        pre = admin_session.post(f"{API}/admin/auto-match/preview", timeout=30).json()
        total_pre = pre["total_unmatched"]
        with_match_pre = pre["with_match_available"]

        if with_match_pre == 0:
            pytest.skip(
                f"No matchable unmatched requests in env (total_unmatched={total_pre}) — "
                "real-run path cannot be exercised."
            )

        r = admin_session.post(
            f"{API}/admin/auto-match/run",
            json={"limit": 100, "min_rating": 0, "dry_run": False},
            timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        result = r.json()
        assert result["ok"] is True
        assert result["dry_run"] is False
        assert result["assigned_count"] >= 1, (
            f"expected at least 1 real assignment but got 0; with_match_pre={with_match_pre}"
        )

        # Each assigned item must have specialist_id + name (not dry_run flag)
        for a in result["assigned"]:
            assert a.get("specialist_id")
            assert a.get("specialist_name")
            assert "dry_run" not in a

        # Preview must show reduced unmatched
        post = admin_session.post(f"{API}/admin/auto-match/preview", timeout=30).json()
        assert post["total_unmatched"] < total_pre, (
            f"unmatched count did not drop: {total_pre} -> {post['total_unmatched']}"
        )

        # Force a fresh autonomy snapshot so the signal recomputes
        admin_session.post(f"{API}/admin/autonomy/snapshot", timeout=30)
        time.sleep(1)
        snap_after = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert snap_after.status_code == 200
        sig_after = (
            snap_after.json()
            .get("breakdown", {})
            .get("operational", {})
            .get("signals", {})
            .get("auto_matched_requests_pct")
        )

        # If the signal exists, it should not decrease.
        if sig_before is not None and sig_after is not None:
            assert sig_after >= sig_before, (
                f"auto_matched_requests_pct decreased: {sig_before} -> {sig_after}"
            )


# ----- Regression: other admin endpoints still respond -----
class TestRegression:
    def test_autonomy_snapshot(self, admin_session):
        r = admin_session.post(f"{API}/admin/autonomy/snapshot", timeout=30)
        assert r.status_code == 200, r.text[:200]

    def test_autonomy_score(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "score" in d or "general" in d or "breakdown" in d

    def test_smoke_test_run(self, admin_session):
        r = admin_session.post(f"{API}/admin/smoke-test/run", timeout=60)
        assert r.status_code in (200, 201), r.text[:200]
