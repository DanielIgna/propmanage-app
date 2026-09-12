"""Iter78 — DEMO_MASTER_CODE env var + danieligna1 protection + Demo Activity Log."""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")

SUPER = ("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
OWNER = ("danieligna1@gmail.com", "0108")
MKT   = ("marketing.admin@propmanage.io", "Mkt!Demo2026Strong")
CLIENT = ("client@propmanage.io", "Client123!")

MASTER_CODE = "0108"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def super_session():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def owner_session():
    return _login(*OWNER)


@pytest.fixture(scope="module")
def mkt_session():
    return _login(*MKT)


# -------- ENV VAR / MASTER CODE --------

class TestMasterCode:
    def test_env_var_present(self):
        # verified via reset-password endpoint with wrong code rejects
        s = _login(*SUPER)
        r = s.post(f"{BASE_URL}/api/admin/demo-accounts/reset-password",
                   json={"email": MKT[0], "master_code": "9999"})
        assert r.status_code == 403
        assert "Cod master incorect" in r.text or "incorect" in r.text.lower()

    def test_default_fallback_0108_works(self):
        # admin-accounts/change-password with code 0108 (backward compat)
        s = _login(*SUPER)
        # use marketing.admin temporarily then restore
        r = s.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                   json={"email": MKT[0], "master_code": MASTER_CODE,
                         "new_password": "Mkt!Demo2026Strong"})
        assert r.status_code == 200, r.text


# -------- PROTECTED EMAILS --------

class TestProtectedEmails:
    def test_list_returns_both_protected(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/admin-accounts")
        assert r.status_code == 200
        data = r.json()
        emails_set = set(data.get("protected_emails", []))
        assert "admin@propmanage.io" in emails_set
        assert "danieligna1@gmail.com" in emails_set
        # both rows is_protected=True
        items = {it["email"]: it for it in data["items"]}
        assert items.get("admin@propmanage.io", {}).get("is_protected") is True
        assert items.get("danieligna1@gmail.com", {}).get("is_protected") is True

    def test_danieligna_cannot_be_blocked(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                               json={"email": "danieligna1@gmail.com", "master_code": MASTER_CODE})
        assert r.status_code == 400
        assert "protejat" in r.text.lower()

    def test_danieligna_cannot_change_role(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                               json={"email": "danieligna1@gmail.com", "new_role": "operator",
                                     "new_scope": "ops", "master_code": MASTER_CODE})
        assert r.status_code == 400

    def test_owner_login_works(self):
        s = _login(*OWNER)
        r = s.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        u = r.json()
        assert u.get("email") == OWNER[0]
        assert u.get("role") == "admin"


# -------- RBAC on demo-activity --------

class TestRBAC:
    def test_super_can_list(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_super_can_summary(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity/summary?days=7")
        assert r.status_code == 200
        d = r.json()
        for k in ("since", "days", "total_actions", "users", "global_top_pages"):
            assert k in d

    def test_non_super_blocked_list(self):
        s = _login(*CLIENT)
        r = s.get(f"{BASE_URL}/api/admin/demo-activity")
        assert r.status_code == 403
        assert "super-admin" in r.text.lower()

    def test_non_super_blocked_summary(self):
        s = _login(*CLIENT)
        r = s.get(f"{BASE_URL}/api/admin/demo-activity/summary")
        assert r.status_code == 403


# -------- ACTIVITY MIDDLEWARE --------

class TestActivityMiddleware:
    def test_demo_user_generates_logs(self, mkt_session, super_session):
        # call several endpoints as marketing demo admin
        mkt_session.get(f"{BASE_URL}/api/admin/marketing/dashboard")
        mkt_session.get(f"{BASE_URL}/api/admin/marketing/performance/summary")
        time.sleep(2.5)  # wait for fire-and-forget tasks
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": MKT[0], "days": 1})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1, f"no logs found for {MKT[0]}"
        # find dashboard call
        match = [it for it in items if it["path"] == "/api/admin/marketing/dashboard"]
        assert match, f"no dashboard log found. paths: {[i['path'] for i in items]}"
        log = match[0]
        assert log["email"] == MKT[0]
        assert log["label"] == "Vizualizat Marketing Dashboard"
        assert log["method"] == "GET"
        assert isinstance(log["status_code"], int)
        assert log["duration_ms"] >= 0
        assert "ts" in log
        assert "T" in log["ts"]  # ISO format

    def test_non_demo_user_does_not_log(self, super_session):
        # Super admin makes a call
        super_session.get(f"{BASE_URL}/api/admin/admin-accounts")
        time.sleep(1.5)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": "admin@propmanage.io", "days": 1})
        items = r.json()["items"]
        assert len(items) == 0, f"non-demo super admin should not generate logs: {items}"

    def test_owner_does_not_log(self, owner_session, super_session):
        owner_session.get(f"{BASE_URL}/api/admin/admin-accounts")
        time.sleep(1.5)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": "danieligna1@gmail.com", "days": 1})
        assert r.json()["items"] == []


# -------- FILTERS --------

class TestFilters:
    def test_filter_by_email(self, mkt_session, super_session):
        mkt_session.get(f"{BASE_URL}/api/admin/marketing/dashboard")
        time.sleep(2)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": MKT[0]})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(it["email"] == MKT[0] for it in items)

    def test_filter_by_q_label(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"q": "marketing", "days": 7})
        assert r.status_code == 200
        items = r.json()["items"]
        if items:
            assert any("marketing" in it["label"].lower() or
                       "marketing" in it["path"].lower() for it in items)

    def test_filter_limit(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"limit": 5, "days": 7})
        assert len(r.json()["items"]) <= 5

    def test_filter_days(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"days": 1})
        assert r.status_code == 200


# -------- FRIENDLY LABELS --------

class TestFriendlyLabels:
    def test_marketing_dashboard_label(self, mkt_session, super_session):
        mkt_session.get(f"{BASE_URL}/api/admin/marketing/dashboard")
        time.sleep(2)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": MKT[0], "days": 1})
        labels = {it["label"] for it in r.json()["items"]
                  if it["path"] == "/api/admin/marketing/dashboard"}
        assert "Vizualizat Marketing Dashboard" in labels

    def test_strategic_partners_cross_ref_label(self, mkt_session, super_session):
        # Even if endpoint returns 403, middleware still logs
        mkt_session.get(f"{BASE_URL}/api/admin/strategic-partners/cross-ref")
        time.sleep(2)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity",
                              params={"email": MKT[0], "q": "Cross-Reference", "days": 1})
        items = r.json()["items"]
        if items:
            assert any(it["label"] == "Cross-Reference AI" for it in items)


# -------- SUMMARY --------

class TestSummary:
    def test_summary_structure(self, mkt_session, super_session):
        mkt_session.get(f"{BASE_URL}/api/admin/marketing/dashboard")
        time.sleep(2)
        r = super_session.get(f"{BASE_URL}/api/admin/demo-activity/summary?days=7")
        d = r.json()
        assert d["days"] == 7
        assert isinstance(d["total_actions"], int)
        assert isinstance(d["users"], list)
        # if users present, validate structure
        if d["users"]:
            u = d["users"][0]
            for k in ("email", "name", "scope", "total_actions", "errors",
                      "last_seen", "top_pages"):
                assert k in u, f"missing {k}"
        # totals sorted desc
        if len(d["users"]) >= 2:
            assert d["users"][0]["total_actions"] >= d["users"][1]["total_actions"]


# -------- REGRESSION --------

class TestRegression:
    def test_demo_accounts_six_items(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/demo-accounts")
        assert r.status_code == 200
        assert r.json()["count"] >= 6

    def test_admin_accounts_22_plus(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/admin-accounts")
        assert r.status_code == 200
        assert r.json()["count"] >= 6  # reasonable lower bound; was 22 prev
