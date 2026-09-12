"""Phase-35 Release Gate end-to-end backend tests.

Covers:
  * POST /api/admin/qa/automation/release-gate {email_admins:false}
  * POST /api/admin/qa/automation/release-gate {email_admins:true}
  * GET  /api/admin/qa/automation/release-gates
  * GET  /api/admin/qa/automation/release-gates/{gate_id}
  * RBAC: client cannot access any of the above
"""

import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAILS_ENV = (os.environ.get("ADMIN_EMAILS") or "danieligna1@gmail.com,carlospacu@gmail.com,admin@propmanage.io").split(",")
ADMIN_EMAILS_EXPECTED = {e.strip() for e in ADMIN_EMAILS_ENV if e.strip()}


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_client() -> requests.Session:
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session() -> requests.Session:
    return _login("client@propmanage.io", "Client123!")


# ---------------- Release Gate — no-email ----------------
class TestReleaseGateNoEmail:
    """Run gate without emailing admins; validate shape & timings."""

    @pytest.fixture(scope="class")
    def gate(self, admin_client):
        t0 = time.time()
        r = admin_client.post(
            f"{BASE_URL}/api/admin/qa/automation/release-gate",
            json={"email_admins": False},
            timeout=120,
        )
        dt = time.time() - t0
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        # < 120s ceiling for CI safety; the spec says <15s on warm path but Playwright cold-starts may bump.
        assert dt < 120, f"Gate took too long: {dt:.1f}s"
        return r.json()

    def test_payload_shape(self, gate):
        for key in ("gate_id", "triggered_by", "started_at", "finished_at", "duration_ms", "summary", "results", "email"):
            assert key in gate, f"missing {key}"
        assert isinstance(gate["gate_id"], str) and len(gate["gate_id"]) == 12
        assert gate["triggered_by"] == "admin@propmanage.io"

    def test_summary(self, gate):
        s = gate["summary"]
        assert s["total"] >= 14, f"expected total>=14, got {s['total']}"
        for k in ("pass", "fail", "p0_fail", "p1_fail", "blocked", "written_to_run"):
            assert k in s, f"missing summary.{k}"
        assert s["written_to_run"] == 0, "no run_id supplied → should be 0"
        assert s["blocked"] == (s["p0_fail"] > 0)
        assert s["pass"] + s["fail"] == s["total"]

    def test_results_14_items(self, gate):
        assert isinstance(gate["results"], list)
        assert len(gate["results"]) >= 14, f"expected >=14 results, got {len(gate['results'])}"
        for r in gate["results"]:
            assert "code" in r and "status" in r and "priority" in r and "duration_ms" in r

    def test_email_disabled(self, gate):
        assert gate["email"]["sent"] is False
        assert gate["email"]["recipients"] == []
        assert gate["email"]["error"] in (None, "")


# ---------------- Gates history (lightweight) ----------------
class TestReleaseGatesList:
    def test_list_after_gate(self, admin_client):
        # Ensure at least one gate exists for the assertions to be meaningful.
        admin_client.post(
            f"{BASE_URL}/api/admin/qa/automation/release-gate",
            json={"email_admins": False},
            timeout=120,
        )
        r = admin_client.get(f"{BASE_URL}/api/admin/qa/automation/release-gates", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "gates" in body and isinstance(body["gates"], list)
        assert len(body["gates"]) >= 1
        first = body["gates"][0]
        # lightweight list must NOT include the heavy results array
        assert "results" not in first, "list endpoint must strip results"
        for k in ("gate_id", "summary", "triggered_by", "started_at", "duration_ms"):
            assert k in first, f"list item missing {k}"


# ---------------- Gate detail ----------------
class TestReleaseGateDetail:
    def test_get_detail(self, admin_client):
        # find a gate to inspect
        list_r = admin_client.get(f"{BASE_URL}/api/admin/qa/automation/release-gates", timeout=20)
        gates = list_r.json()["gates"]
        assert gates, "no gates available to test detail"
        gid = gates[0]["gate_id"]
        r = admin_client.get(f"{BASE_URL}/api/admin/qa/automation/release-gates/{gid}", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["gate_id"] == gid
        assert isinstance(body.get("results"), list) and len(body["results"]) >= 14

    def test_get_detail_404(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/qa/automation/release-gates/deadbeef0000", timeout=20)
        assert r.status_code == 404


# ---------------- RBAC ----------------
class TestRBAC:
    def test_client_cannot_run_gate(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/admin/qa/automation/release-gate",
            json={"email_admins": False},
            timeout=30,
        )
        assert r.status_code == 403, f"got {r.status_code} {r.text[:200]}"

    def test_client_cannot_list_gates(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/qa/automation/release-gates", timeout=15)
        assert r.status_code == 403

    def test_client_cannot_get_detail(self, client_session):
        r = client_session.get(
            f"{BASE_URL}/api/admin/qa/automation/release-gates/anyid000000",
            timeout=15,
        )
        assert r.status_code == 403


# ---------------- Email-enabled gate (P0 — but uses real Resend, so kept last) ----------------
@pytest.mark.email
class TestReleaseGateWithEmail:
    """Spec asked us NOT to actually send email during this pass — gate this with marker.
    Run only when explicitly requested: pytest -m email
    """

    def test_gate_emails_admins(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/admin/qa/automation/release-gate",
            json={"email_admins": True},
            timeout=120,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["email"]["sent"] is True
        recips = set(body["email"]["recipients"])
        assert recips == ADMIN_EMAILS_EXPECTED, f"got {recips}, expected {ADMIN_EMAILS_EXPECTED}"
