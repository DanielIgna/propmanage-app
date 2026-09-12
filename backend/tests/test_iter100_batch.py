"""
Iteration 100 batch tests:
- Legal company data (VINTAGE FURNITURE S.R.L.)
- AI Insights rule + LLM for ai_control and governance
- Marketplace Pulse public endpoint
- Autonomy 2.0 Pattern Hunter (supply_gap + churn_risk)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
    assert r.status_code == 200
    return s


# ============ LEGAL / GDPR COMPANY DATA ============
class TestLegalCompany:
    def test_gdpr_documents_company(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/gdpr/documents/company", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("name") == "VINTAGE FURNITURE S.R.L.", f"unexpected name: {data.get('name')}"
        registry = data.get("registry", "")
        assert "J12/3534/2015" in registry
        assert "35250247" in registry
        addr = data.get("address", "")
        assert "Cluj-Napoca" in addr
        assert "Aleea Negoiu" in addr


# ============ AI INSIGHTS (Rule + LLM) — ai_control, governance ============
class TestAIInsightsModules:
    def test_rule_ai_control(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/rule?module=ai_control", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "bullets" in data and isinstance(data["bullets"], list)
        assert "alerts" in data and isinstance(data["alerts"], list)
        assert "recommendations" in data and isinstance(data["recommendations"], list)
        assert len(data["bullets"]) > 0, "expected at least 1 bullet for ai_control"

    def test_rule_governance(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/rule?module=governance", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "bullets" in data and isinstance(data["bullets"], list)
        assert len(data["bullets"]) > 0
        assert "recommendations" in data

    def test_llm_ai_control_and_cache(self, admin_session):
        # first call — may be slow (LLM)
        r1 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=ai_control", timeout=90)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert "summary" in d1 or "text" in d1 or "bullets" in d1, f"missing content: {list(d1.keys())}"
        # second call — should be cached
        r2 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=ai_control", timeout=30)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("cached") is True, f"expected cached=true on 2nd call, got {d2.get('cached')}"

    def test_llm_governance_and_cache(self, admin_session):
        r1 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=governance", timeout=90)
        assert r1.status_code == 200, r1.text
        r2 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=governance", timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True

    def test_client_forbidden_from_admin_insights(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/insights/rule?module=ai_control", timeout=10)
        assert r.status_code in (401, 403), f"client should not access admin insights, got {r.status_code}"


# ============ MARKETPLACE PULSE (Public) ============
class TestMarketPulse:
    def test_pulse_hvac_public(self):
        # NOTE: no auth cookies
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages/montaj-aer-conditionat/pulse", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("category") == "hvac"
        assert "requests_30d" in data and isinstance(data["requests_30d"], int)
        assert "open_now" in data and isinstance(data["open_now"], int)
        assert "active_specialists" in data and isinstance(data["active_specialists"], int)

    def test_pulse_invalid_slug_404(self):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages/nonexistent-slug-abc-xyz/pulse", timeout=10)
        assert r.status_code == 404


# ============ AUTONOMY 2.0 — Pattern Hunter Detectors ============
class TestPatternHunter:
    def test_simulate_pattern_scan_has_new_detectors(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/orchestrator/simulate/pattern_scan",
            json={},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        ledger = data.get("ledger", {})
        steps = ledger.get("steps", [])
        actions = [s.get("action") for s in steps]
        assert "scan_supply_gap" in actions, f"missing scan_supply_gap in {actions}"
        assert "scan_churn_risk" in actions, f"missing scan_churn_risk in {actions}"
        # verify both ok
        for step in steps:
            if step.get("action") in ("scan_supply_gap", "scan_churn_risk"):
                assert step.get("ok") is True, f"{step.get('action')} not ok: {step}"
        # confirm test mode (no writes)
        assert ledger.get("test") is True
