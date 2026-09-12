"""Enterprise Health Engine (D122) + Formula Registry (D151) — iter 129 tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"

DOMAIN_KEYS = {
    "product", "ux", "operations", "growth", "marketplace", "customer_trust",
    "knowledge", "revenue", "automation", "technical_debt", "ai_learning",
}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ------------------------ Enterprise Health summary ------------------------

class TestEnterpriseHealthSummary:
    def test_get_summary(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # overall
        assert "overall" in d and "domains" in d and "alerts" in d
        assert "history" in d and "generated_at" in d
        o = d["overall"]
        assert set(["score", "band", "previous", "trend_30d"]).issubset(o.keys())
        assert 0 <= o["score"] <= 100
        assert "label" in o["band"] and "key" in o["band"]

        # 11 domains
        assert len(d["domains"]) == 11
        keys = {dm["key"] for dm in d["domains"]}
        assert keys == DOMAIN_KEYS

        # sorted ascending by score
        scores = [dm["score"] for dm in d["domains"]]
        assert scores == sorted(scores), f"domains not sorted asc: {scores}"

        for dm in d["domains"]:
            for f in ("key", "label", "score", "band", "confidence",
                      "warning_threshold", "top_findings", "version"):
                assert f in dm, f"missing {f} in domain {dm.get('key')}"
            assert dm["confidence"] in ("high", "medium", "low")

        # alerts correctness
        for a in d["alerts"]:
            assert a["domain"] in DOMAIN_KEYS
            assert a["score"] < 80
            expected_sev = "critical" if a["score"] < 60 else "warning"
            assert a["severity"] == expected_sev
            assert a["cause"] and a["business_impact"]
            assert 1 <= len(a["top_actions"]) <= 3
            for act in a["top_actions"]:
                assert "action" in act and "estimated_gain_pts" in act
            assert isinstance(a["estimated_effect"], str) and a["estimated_effect"]

        # every domain <80 must be in alerts
        under = {dm["key"] for dm in d["domains"] if dm["score"] < 80}
        alerted = {a["domain"] for a in d["alerts"]}
        assert under == alerted, f"mismatch under={under} alerted={alerted}"

    def test_history_snapshot_exists(self, admin_session):
        # After GET above, today's snapshot must exist. We can't hit mongo directly,
        # but summary returns history[] which includes today's date.
        r = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health", timeout=60)
        assert r.status_code == 200
        hist = r.json().get("history", [])
        assert isinstance(hist, list) and len(hist) >= 1
        assert "date" in hist[-1] and "overall" in hist[-1]


# ------------------------ Formula Registry ------------------------

class TestFormulaRegistry:
    def test_list_formulas(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas", timeout=30)
        assert r.status_code == 200
        fs = r.json()["formulas"]
        assert len(fs) == 11
        keys = {f["key"] for f in fs}
        assert keys == DOMAIN_KEYS
        for f in fs:
            assert f.get("version", 0) >= 1
            assert f.get("status") == "active"
            assert isinstance(f.get("inputs"), list) and len(f["inputs"]) >= 1
            assert "_id" not in f  # ObjectId excluded

    def test_explain_revenue(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas/revenue/explain", timeout=30)
        assert r.status_code == 200
        e = r.json()
        for f in ("key", "label", "formula", "version", "calculation_steps",
                  "positive_contributors", "negative_contributors", "confidence",
                  "warning_threshold", "critical_threshold"):
            assert f in e, f"missing {f} in explain"
        assert e["key"] == "revenue"
        assert len(e["calculation_steps"]) >= 1
        for s in e["calculation_steps"]:
            for k in ("value", "subscore", "weight", "contribution_pts", "metric", "label"):
                assert k in s

    def test_explain_unknown_key_404(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas/nonexistent_xyz/explain", timeout=30)
        assert r.status_code == 404


# ------------------ PATCH validations + edit/rollback flow ------------------

class TestFormulaPatchValidation:
    """Use domain 'knowledge' as test target — patch + rollback to keep clean."""

    KEY = "knowledge"

    def _get_formula(self, s):
        r = s.get(f"{BASE_URL}/api/admin/enterprise-health/formulas", timeout=30)
        assert r.status_code == 200
        return next(f for f in r.json()["formulas"] if f["key"] == self.KEY)

    def test_patch_missing_reason_400(self, admin_session):
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"weights": {"ai_documents": 0.5}},
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_patch_unknown_metric_400(self, admin_session):
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"weights": {"totally_fake_metric": 0.5}, "reason": "test"},
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_patch_negative_weight_400(self, admin_session):
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"weights": {"ai_documents": -0.2}, "reason": "test"},
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_patch_warn_leq_critical_400(self, admin_session):
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"warning_threshold": 50, "critical_threshold": 60, "reason": "test"},
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_patch_zero_sum_weights_400(self, admin_session):
        f = self._get_formula(admin_session)
        zeros = {i["metric"]: 0 for i in f["inputs"]}
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"weights": zeros, "reason": "test"},
            timeout=30,
        )
        assert r.status_code == 400, r.text


class TestFormulaEditRollback:
    """End-to-end: read original → PATCH → verify version bump + audit → rollback → verify."""
    KEY = "knowledge"

    def test_edit_and_rollback(self, admin_session):
        # baseline
        r0 = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas", timeout=30)
        f0 = next(f for f in r0.json()["formulas"] if f["key"] == self.KEY)
        v0 = f0["version"]
        original_weights = {i["metric"]: i["weight"] for i in f0["inputs"]}

        # PATCH — tweak one weight
        new_weights = dict(original_weights)
        first_metric = list(new_weights.keys())[0]
        new_weights[first_metric] = round(original_weights[first_metric] + 0.05, 3)
        r1 = admin_session.patch(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}",
            json={"weights": new_weights, "reason": "iter129 regression test"},
            timeout=30,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["version"] == v0 + 1

        # verify persistence
        r2 = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas", timeout=30)
        f1 = next(f for f in r2.json()["formulas"] if f["key"] == self.KEY)
        assert f1["version"] == v0 + 1
        got = {i["metric"]: i["weight"] for i in f1["inputs"]}
        assert abs(got[first_metric] - new_weights[first_metric]) < 1e-6

        # audit trail
        ra = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}/audit", timeout=30)
        assert ra.status_code == 200
        entries = ra.json()["audit"]
        assert entries and entries[0]["new_version"] == v0 + 1
        assert entries[0]["reason"] == "iter129 regression test"
        assert entries[0].get("by")

        # ROLLBACK — MUST always run to keep registry clean
        rb = admin_session.post(
            f"{BASE_URL}/api/admin/enterprise-health/formulas/{self.KEY}/rollback",
            json={"reason": "iter129 cleanup"},
            timeout=30,
        )
        assert rb.status_code == 200, rb.text

        # verify weights restored
        r3 = admin_session.get(f"{BASE_URL}/api/admin/enterprise-health/formulas", timeout=30)
        f2 = next(f for f in r3.json()["formulas"] if f["key"] == self.KEY)
        got2 = {i["metric"]: i["weight"] for i in f2["inputs"]}
        for m, w in original_weights.items():
            assert abs(got2[m] - w) < 1e-6, f"weight not restored for {m}: {got2[m]} vs {w}"


# ------------------------ Regression: Operations Center + Business Health ------------------------

class TestRegression:
    def test_operations_still_loads(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/operations", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # leads with id
        leads = d.get("leads") or d.get("lead_list") or []
        # tolerate different shapes — just check keys
        assert isinstance(d, dict)
        if isinstance(leads, list) and leads:
            assert "id" in leads[0]

    def test_business_health_still_works(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/business-health", timeout=30)
        assert r.status_code == 200, r.text
