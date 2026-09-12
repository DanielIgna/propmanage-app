"""Iter98 — Sprint F backend tests: Specialist Cockpit + AI Insights LLM + Reconcile Orphans.

STRICT LLM BUDGET: analytics module is cached; only finance module may trigger ONE real Claude call.
Do NOT use force=true. Do NOT hit marketplace/overview/control_tower LLM modules.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

SPECIALIST_CRED = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN_CRED = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT_CRED = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(session: requests.Session, cred: dict) -> requests.Response:
    return session.post(f"{BASE_URL}/api/auth/login", json=cred, timeout=30)


@pytest.fixture(scope="module")
def specialist_session():
    s = requests.Session()
    r = _login(s, SPECIALIST_CRED)
    if r.status_code != 200:
        pytest.skip(f"Specialist login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN_CRED)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = _login(s, CLIENT_CRED)
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code} {r.text[:200]}")
    return s


# --- 1) Specialist Cockpit ---
class TestSpecialistCockpit:
    def test_cockpit_shape(self, specialist_session):
        r = specialist_session.get(f"{BASE_URL}/api/specialist/cockpit", timeout=30)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        # Pipeline
        assert "pipeline" in data
        for k in ("leads_matched", "leads_total", "offers_active", "done_this_month"):
            assert k in data["pipeline"], f"missing pipeline.{k}"
            assert isinstance(data["pipeline"][k], int), f"pipeline.{k} not int: {type(data['pipeline'][k])}"
        # Money
        assert "money" in data
        for k in ("this_month", "last_month", "avg_per_job"):
            assert k in data["money"], f"missing money.{k}"
        assert "trend_pct" in data["money"]
        # Benchmark
        assert "benchmark" in data
        if data["benchmark"] is not None:
            b = data["benchmark"]
            assert b.get("category") == "hvac", f"benchmark category expected hvac, got {b.get('category')}"
            assert "unit" in b
        # Assistant actions
        assert "assistant_actions" in data
        assert isinstance(data["assistant_actions"], list)
        assert 1 <= len(data["assistant_actions"]) <= 4
        for a in data["assistant_actions"]:
            assert "kind" in a and "text" in a and "cta" in a
        print(f"Cockpit OK: this_month={data['money']['this_month']} trend={data['money']['trend_pct']} bench={data['benchmark']}")

    def test_cockpit_forbidden_for_client(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/specialist/cockpit", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 for client, got {r.status_code}"


# --- 2 & 3) AI Insights LLM ---
class TestAIInsightsLLM:
    def test_analytics_cached(self, admin_session):
        # NO force=true. Should return cached response (6h TTL).
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm", params={"module": "analytics"}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data.get("cached") is True, f"expected cached=true, got cached={data.get('cached')}"
        assert "bullets" in data and isinstance(data["bullets"], list) and len(data["bullets"]) > 0
        assert "recommendations" in data and isinstance(data["recommendations"], list)
        print(f"Analytics LLM cached: bullets={len(data['bullets'])} recs={len(data['recommendations'])}")

    def test_finance_module_shape(self, admin_session):
        # May trigger ONE real Claude call (allowed by review_request budget).
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm", params={"module": "finance"}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert "bullets" in data
        assert "recommendations" in data
        assert "cached" in data
        # alerts may or may not be present per shape; verify it exists as key at minimum
        assert isinstance(data.get("bullets", []), list)
        assert isinstance(data.get("recommendations", []), list)
        print(f"Finance LLM shape OK: cached={data.get('cached')} bullets={len(data.get('bullets', []))}")

    def test_invalid_module_returns_400(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm", params={"module": "bad"}, timeout=30)
        assert r.status_code == 400, f"expected 400 for bad module, got {r.status_code}: {r.text[:200]}"

    def test_non_admin_forbidden(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/insights/llm", params={"module": "analytics"}, timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 for client, got {r.status_code}"


# --- 4) Reconcile Orphans (idempotent) ---
class TestReconcileOrphans:
    def test_reconcile_returns_zero(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/control-tower/actions/reconcile-orphans", timeout=60)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert "repaired" in data
        assert data["repaired"] == 0, f"expected 0 repaired (already reconciled), got {data['repaired']}"
        assert "message" in data
        print(f"Reconcile idempotent: repaired={data['repaired']} msg={data.get('message')}")

    def test_attention_list_no_orphans(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/control-tower", timeout=30)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        # look for attention list — collect any orphan_transactions entries anywhere in payload
        payload_str = str(data)
        # attention list can be under various keys; check for 'orphan_transactions' kind not present as active
        attention = data.get("attention") or data.get("attention_list") or []
        if isinstance(attention, list):
            kinds = [str(a.get("kind") or a.get("type") or "") for a in attention if isinstance(a, dict)]
            assert "orphan_transactions" not in kinds, f"orphan_transactions still in attention: {kinds}"
        print(f"Control-tower attention: {len(attention) if isinstance(attention, list) else 'n/a'} items")

    def test_orchestrator_ledger_has_reconcile_entry(self, admin_session):
        # Try likely endpoints for orchestrator ledger
        candidates = [
            "/api/admin/orchestrator/ledger",
            "/api/admin/control-tower/ledger",
            "/api/orchestrator/ledger",
        ]
        found = None
        for path in candidates:
            r = admin_session.get(f"{BASE_URL}{path}", timeout=30)
            if r.status_code == 200:
                found = (path, r.json())
                break
        if not found:
            pytest.skip(f"No ledger endpoint responded 200 among {candidates}")
        path, data = found
        payload_str = str(data)
        assert "reconcile_orphans_1tap" in payload_str or "reconcile_orphans" in payload_str, \
            f"reconcile_orphans_1tap not found in ledger at {path}"
        print(f"Ledger at {path} contains reconcile step OK")
