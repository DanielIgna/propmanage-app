"""Phase 26: Stripe Checkout topup (DEMO), Tutorial flag, Milestone renegotiation."""
import os
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


def _login(session: requests.Session, creds: dict) -> dict:
    r = session.post(f"{BASE_URL}/api/auth/login", json=creds, headers={"Origin": BASE_URL})
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def client_sess():
    s = requests.Session()
    _login(s, CLIENT)
    return s


@pytest.fixture(scope="module")
def spec_sess():
    s = requests.Session()
    _login(s, SPEC)
    return s


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    _login(s, ADMIN)
    return s


# ============= TUTORIAL FLAG (P2b) =============
class TestTutorialFlag:
    def test_reset_then_me_returns_false(self, client_sess):
        r = client_sess.post(f"{BASE_URL}/api/auth/tutorial-reset")
        assert r.status_code == 200
        assert r.json().get("ok") is True
        me = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        assert me.get("tutorial_seen") is False

    def test_mark_seen_then_me_returns_true(self, client_sess):
        r = client_sess.post(f"{BASE_URL}/api/auth/tutorial-seen")
        assert r.status_code == 200
        assert r.json().get("ok") is True
        me = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        assert me.get("tutorial_seen") is True

    def test_reset_idempotent(self, client_sess):
        client_sess.post(f"{BASE_URL}/api/auth/tutorial-reset")
        me = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        assert me.get("tutorial_seen") is False
        # Reset again — should still be 200 and false
        r = client_sess.post(f"{BASE_URL}/api/auth/tutorial-reset")
        assert r.status_code == 200


# ============= WALLET TOPUP STRIPE (P1) =============
class TestWalletTopupCheckout:
    def test_create_demo_session_ok(self, client_sess):
        r = client_sess.post(
            f"{BASE_URL}/api/wallet/topup-checkout-session",
            json={"amount": 500},
            headers={"Origin": BASE_URL},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "checkout_url" in body
        assert "session_id" in body
        assert body.get("demo_mode") is True
        assert "/payment-success" in body["checkout_url"]
        assert body["session_id"].startswith("cs_topup_demo_")

    def test_reject_amount_zero(self, client_sess):
        r = client_sess.post(
            f"{BASE_URL}/api/wallet/topup-checkout-session",
            json={"amount": 0},
            headers={"Origin": BASE_URL},
        )
        assert r.status_code == 422  # pydantic validation gt=0

    def test_reject_amount_too_large(self, client_sess):
        r = client_sess.post(
            f"{BASE_URL}/api/wallet/topup-checkout-session",
            json={"amount": 50001},
            headers={"Origin": BASE_URL},
        )
        assert r.status_code == 422  # pydantic validation le=50000

    def test_topup_status_credits_wallet_idempotently(self, client_sess):
        # Get balance before
        me_before = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        bal_before = float(me_before.get("wallet_balance", 0))

        # Create session
        amount = 123.0
        sess = client_sess.post(
            f"{BASE_URL}/api/wallet/topup-checkout-session",
            json={"amount": amount},
            headers={"Origin": BASE_URL},
        ).json()
        sid = sess["session_id"]

        # First poll → should credit + return paid
        r1 = client_sess.get(f"{BASE_URL}/api/wallet/topup-status/{sid}")
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        assert body1.get("payment_status") == "paid"
        assert body1.get("amount") == amount

        # Verify wallet credited
        me_after = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        bal_after = float(me_after.get("wallet_balance", 0))
        assert abs((bal_after - bal_before) - amount) < 0.5, f"Expected +{amount}, got {bal_after - bal_before}"

        # Second poll → idempotent, already_credited
        r2 = client_sess.get(f"{BASE_URL}/api/wallet/topup-status/{sid}")
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2.get("payment_status") == "paid"
        assert body2.get("already_credited") is True

        me_again = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        assert abs(float(me_again.get("wallet_balance", 0)) - bal_after) < 0.01

    def test_topup_status_404_for_other_users_session(self, client_sess, spec_sess):
        sess = client_sess.post(
            f"{BASE_URL}/api/wallet/topup-checkout-session",
            json={"amount": 50},
            headers={"Origin": BASE_URL},
        ).json()
        sid = sess["session_id"]
        # specialist trying to peek at client's session
        r = spec_sess.get(f"{BASE_URL}/api/wallet/topup-status/{sid}")
        assert r.status_code == 404

    def test_legacy_topup_still_works(self, client_sess):
        me_before = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        bal_before = float(me_before.get("wallet_balance", 0))
        r = client_sess.post(f"{BASE_URL}/api/wallet/topup?amount=50")
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        me_after = client_sess.get(f"{BASE_URL}/api/auth/me").json()
        assert abs(float(me_after.get("wallet_balance", 0)) - bal_before - 50) < 0.5


# ============= MILESTONE RENEGOTIATION (P2a) =============
@pytest.fixture(scope="module")
def renegotiation_project(client_sess, spec_sess):
    """Find or create a project with >=2 pending_funding milestones between client and specialist."""
    spec_me = spec_sess.get(f"{BASE_URL}/api/auth/me").json()
    spec_id = spec_me["id"]
    client_me = client_sess.get(f"{BASE_URL}/api/auth/me").json()
    client_id = client_me["id"]

    # Try to find an existing project visible to both
    lst = client_sess.get(f"{BASE_URL}/api/projects")
    candidates = lst.json() if lst.status_code == 200 and isinstance(lst.json(), list) else []
    for p in candidates:
        if p.get("designer_id") == spec_id and p.get("client_id") == client_id:
            pending = [m for m in (p.get("milestones") or []) if m.get("status") == "pending_funding"]
            if len(pending) >= 2:
                return {"id": p.get("id") or p.get("_id"), "milestones": p["milestones"],
                        "spec_id": spec_id, "pending_count": len(pending)}

    # Otherwise attempt creation
    payload = {
        "name": f"TEST_RenegProj_{uuid.uuid4().hex[:6]}",
        "title": f"TEST_RenegProj_{uuid.uuid4().hex[:6]}",
        "designer_id": spec_id,
        "budget": 12000,
        "description": "Test project for renegotiation",
    }
    r = client_sess.post(f"{BASE_URL}/api/projects", json=payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"No suitable project found and cannot create one ({r.status_code}): {r.text[:200]}")
    proj = r.json()
    pid = proj.get("id") or proj.get("_id")
    init = client_sess.post(f"{BASE_URL}/api/projects/{pid}/milestones/init", json={"total_budget": 12000})
    if init.status_code not in (200, 201):
        init = spec_sess.post(f"{BASE_URL}/api/projects/{pid}/milestones/init", json={"total_budget": 12000})
    p = client_sess.get(f"{BASE_URL}/api/projects/{pid}").json()
    pending = [m for m in (p.get("milestones") or []) if m.get("status") == "pending_funding"]
    if len(pending) < 2:
        pytest.skip(f"Not enough pending_funding milestones (got {len(pending)})")
    return {"id": pid, "milestones": p["milestones"], "spec_id": spec_id, "pending_count": len(pending)}


class TestMilestoneRenegotiate:
    def test_propose_invalid_pcts_sum(self, client_sess, renegotiation_project):
        pid = renegotiation_project["id"]
        n = renegotiation_project["pending_count"]
        bad = [50.0] * n  # sums to 50*n, not 100
        r = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate",
            json={"pcts": bad},
        )
        assert r.status_code == 400

    def test_propose_wrong_length(self, client_sess, renegotiation_project):
        pid = renegotiation_project["id"]
        # Send wrong number of pcts
        r = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate",
            json={"pcts": [100.0]},  # only 1, but we have >=2 unfunded
        )
        # Should fail because length != unfunded count (400 from route or 422 from pydantic min_items)
        assert r.status_code in (400, 422), r.text

    def test_propose_negative_pct(self, client_sess, renegotiation_project):
        pid = renegotiation_project["id"]
        n = renegotiation_project["pending_count"]
        pcts = [120.0] + [(100 - 120) / (n - 1)] * (n - 1)
        r = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate",
            json={"pcts": pcts},
        )
        assert r.status_code == 400

    def test_full_flow_accept(self, client_sess, spec_sess, renegotiation_project):
        pid = renegotiation_project["id"]
        n = renegotiation_project["pending_count"]
        # Equal split, e.g. [50,50] for 2 milestones
        pcts = [round(100.0 / n, 2)] * n
        # Adjust last to make sum exact 100
        pcts[-1] = round(100.0 - sum(pcts[:-1]), 2)

        # Client proposes
        r = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate",
            json={"pcts": pcts, "note": "TEST propose"},
        )
        assert r.status_code == 200, r.text
        proposal = r.json()["proposal"]
        assert proposal["status"] == "pending"
        assert proposal["proposed_by_role"] == "client"
        prop_id = proposal["id"]

        # List proposals
        lst = client_sess.get(f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate")
        assert lst.status_code == 200
        items = lst.json().get("proposals", [])
        assert any(p["id"] == prop_id for p in items)

        # Proposer cannot respond
        r_self = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate/{prop_id}/respond",
            json={"accept": True},
        )
        assert r_self.status_code == 403

        # Counterparty (designer/specialist) accepts
        r_acc = spec_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate/{prop_id}/respond",
            json={"accept": True, "note": "TEST accept"},
        )
        assert r_acc.status_code == 200, r_acc.text
        body = r_acc.json()
        assert body["status"] == "accepted"
        new_ms = body["milestones"]
        # Pending funding milestones should match new pcts at the end
        pending_new = [m for m in new_ms if m.get("status") == "pending_funding"]
        assert len(pending_new) == n
        for m, expected_pct in zip(pending_new, pcts):
            assert abs(m["pct"] - expected_pct) < 0.5

        # Already accepted → cannot respond again
        r_again = spec_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate/{prop_id}/respond",
            json={"accept": True},
        )
        assert r_again.status_code == 400

    def test_propose_and_reject(self, spec_sess, client_sess, renegotiation_project):
        pid = renegotiation_project["id"]
        # Refresh project to get current pending count
        p = client_sess.get(f"{BASE_URL}/api/projects/{pid}").json()
        pending = [m for m in (p.get("milestones") or []) if m.get("status") == "pending_funding"]
        n = len(pending)
        if n < 2:
            pytest.skip("Not enough pending milestones for reject test")
        pcts = [round(100.0 / n, 2)] * n
        pcts[-1] = round(100.0 - sum(pcts[:-1]), 2)

        # Now specialist proposes
        r = spec_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate",
            json={"pcts": pcts, "note": "TEST spec propose"},
        )
        assert r.status_code == 200, r.text
        prop_id = r.json()["proposal"]["id"]
        assert r.json()["proposal"]["proposed_by_role"] == "designer"

        # Client rejects
        r_rej = client_sess.post(
            f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate/{prop_id}/respond",
            json={"accept": False, "note": "TEST reject"},
        )
        assert r_rej.status_code == 200, r_rej.text
        assert r_rej.json()["status"] == "rejected"

        # Verify in listing
        lst = client_sess.get(f"{BASE_URL}/api/projects/{pid}/milestones/renegotiate").json()
        target = next(p for p in lst["proposals"] if p["id"] == prop_id)
        assert target["status"] == "rejected"
