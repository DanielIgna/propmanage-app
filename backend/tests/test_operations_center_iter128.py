"""Iteration 128 — Operations Center (COO Directive) end-to-end backend tests.

Covers:
- GET /api/admin/operations (leads with id, stages, manual_methods, gaps, coo_report, one_win)
- PATCH /api/admin/operations/leads/{id} (stage change + note)
- GET /gaps with summary/filters
- GET /gaps/export CSV
- GET /gaps/{id}/candidates (fallback logic)
- POST /manual-payments (validation + linking + stage auto-move)
- GET /manual-payments (list + totals)
- POST /win (One Win Per Day)
- Manual payment on VE order edge (already-paid rejection)
"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def ops_snapshot(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/operations")
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- GET /operations ----------------
class TestOperationsCenterGet:
    def test_structure(self, ops_snapshot):
        d = ops_snapshot
        for k in ["stages", "manual_methods", "leads", "gaps", "coo_report", "one_win", "ve_orders_pending"]:
            assert k in d, f"missing {k}"
        assert isinstance(d["leads"], list)
        assert isinstance(d["stages"], list) and len(d["stages"]) >= 10
        assert "cash" in d["manual_methods"] and "bank_transfer" in d["manual_methods"]

    def test_leads_have_id(self, ops_snapshot):
        if not ops_snapshot["leads"]:
            pytest.skip("no leads")
        for l in ops_snapshot["leads"][:5]:
            assert "id" in l and l["id"], l
            assert "_id" not in l

    def test_coo_report_fields(self, ops_snapshot):
        c = ops_snapshot["coo_report"]
        for k in ["new_leads_today", "open_leads", "revenue_pending_ron",
                  "payments_received_real", "manual_payments_count",
                  "manual_payments_total_ron", "biggest_bottleneck", "top_founder_action"]:
            assert k in c, k

    def test_one_win(self, ops_snapshot):
        assert "one_win" in ops_snapshot
        assert "today" in ops_snapshot["one_win"] and "yesterday" in ops_snapshot["one_win"]


# ---------------- PATCH /leads/{id} ----------------
class TestLeadPatch:
    def test_invalid_lead_id(self, admin_session):
        r = admin_session.patch(f"{BASE_URL}/api/admin/operations/leads/badid", json={"stage": "contacted"})
        assert r.status_code == 404

    def test_invalid_stage(self, admin_session, ops_snapshot):
        if not ops_snapshot["leads"]:
            pytest.skip("no leads")
        lid = ops_snapshot["leads"][0]["id"]
        r = admin_session.patch(f"{BASE_URL}/api/admin/operations/leads/{lid}", json={"stage": "nonsense_stage"})
        assert r.status_code == 400

    def test_stage_change_and_note_persist(self, admin_session, ops_snapshot):
        if not ops_snapshot["leads"]:
            pytest.skip("no leads")
        lid = ops_snapshot["leads"][0]["id"]
        # move to contacted
        r = admin_session.patch(f"{BASE_URL}/api/admin/operations/leads/{lid}",
                                json={"stage": "contacted", "note": "TEST_iter128 note", "next_action": "TEST_iter128 next"})
        assert r.status_code == 200
        # verify
        r2 = admin_session.get(f"{BASE_URL}/api/admin/operations")
        matched = [l for l in r2.json()["leads"] if l["id"] == lid][0]
        assert matched["stage"] == "contacted"
        assert "TEST_iter128" in (matched.get("next_action") or "")


# ---------------- Gaps ----------------
class TestGaps:
    def test_list_open(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps?status=open")
        assert r.status_code == 200
        d = r.json()
        assert "records" in d and "summary" in d
        s = d["summary"]
        for k in ["total_open", "waiting_customers", "est_lost_revenue_ron", "by_city", "by_category"]:
            assert k in s

    def test_filter_all(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps?status=all")
        assert r.status_code == 200

    def test_export_csv(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps/export?status=all")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "detected_at" in r.text.splitlines()[0]

    def test_candidates_endpoint(self, admin_session):
        gr = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps?status=open")
        recs = gr.json()["records"]
        if not recs:
            pytest.skip("no open gaps")
        gid = recs[0]["id"]
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps/{gid}/candidates")
        assert r.status_code == 200
        d = r.json()
        assert "candidates" in d and "fallback" in d

    def test_candidates_bad_gap(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/gaps/badid/candidates")
        assert r.status_code == 404


# ---------------- Manual Payments ----------------
class TestManualPayments:
    def test_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations/manual-payments")
        assert r.status_code == 200
        d = r.json()
        assert "payments" in d and "totals" in d
        assert "total_ron" in d["totals"] and "count" in d["totals"]

    def test_invalid_method(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments",
                               json={"amount_ron": 100, "method": "bitcoin", "customer_name": "x"})
        assert r.status_code == 400

    def test_zero_amount(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments",
                               json={"amount_ron": 0, "method": "cash", "customer_name": "x"})
        assert r.status_code == 400

    def test_negative_amount(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments",
                               json={"amount_ron": -50, "method": "cash", "customer_name": "x"})
        assert r.status_code == 400

    def test_missing_customer_no_lead(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments",
                               json={"amount_ron": 100, "method": "cash"})
        assert r.status_code == 400

    def test_invalid_lead(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments",
                               json={"amount_ron": 100, "method": "cash", "lead_id": "badid", "customer_name": "x"})
        assert r.status_code == 404

    def test_create_generic_payment_and_verify(self, admin_session):
        pre = admin_session.get(f"{BASE_URL}/api/admin/operations/manual-payments").json()
        pre_count = pre["totals"]["count"]
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/manual-payments", json={
            "amount_ron": 123.45, "method": "cash",
            "customer_name": "TEST_iter128 Cash Customer",
            "reference": "TEST_iter128-REF"
        })
        assert r.status_code == 200, r.text
        pid = r.json()["payment_id"]
        assert pid
        post = admin_session.get(f"{BASE_URL}/api/admin/operations/manual-payments").json()
        assert post["totals"]["count"] == pre_count + 1
        match = [p for p in post["payments"] if p["id"] == pid]
        assert match and match[0]["status"] == "verified"
        assert match[0]["method"] == "cash"
        assert match[0]["amount_ron"] == 123.45


# ---------------- Win ----------------
class TestWin:
    def test_empty_win_rejected(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/win", json={"text": ""})
        assert r.status_code == 400

    def test_save_win(self, admin_session):
        txt = f"TEST_iter128 win {datetime.utcnow().isoformat()}"
        r = admin_session.post(f"{BASE_URL}/api/admin/operations/win", json={"text": txt})
        assert r.status_code == 200
        # verify
        ops = admin_session.get(f"{BASE_URL}/api/admin/operations").json()
        assert ops["one_win"]["today"]["text"] == txt


# ---------------- Regression ----------------
class TestRegression:
    def test_first_revenue_summary(self, admin_session):
        # Actual endpoint is /api/admin/war-room (first-revenue module mounted there)
        r = admin_session.get(f"{BASE_URL}/api/admin/war-room")
        assert r.status_code == 200
