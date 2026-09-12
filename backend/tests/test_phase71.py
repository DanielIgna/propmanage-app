"""Phase 71 mega-sprint backend tests.

Covers:
  A) Urgency: [URGENT] notification prefix + priority filter
  B) QA Copilot code-aware mode (no hallucinated paths)
  C) Digital Twin AI Q&A: auth, 404, graceful empty, disabled
  D) Document Intelligence: upload/list/ask/delete + Romanian stemmer + stats + 403 + 413
"""
import io
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

def _read_url_from_env_file():
    try:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return ""

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_url_from_env_file()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}


def _session(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _session(ADMIN)


@pytest.fixture(scope="module")
def client_s():
    return _session(CLIENT)


@pytest.fixture(scope="module")
def spec_s():
    return _session(SPEC)


@pytest.fixture(scope="module", autouse=True)
def _ensure_ai_enabled(admin_s):
    """Ensure ecosystem is enabled at start and restore at end."""
    admin_s.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": True}, timeout=10)
    yield
    admin_s.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": True}, timeout=10)


# ---------- Etapa A: Urgency ----------
class TestUrgency:
    def test_create_urgent_request_has_urgent_prefix(self, client_s, spec_s):
        # Get an existing property for the client
        pr = client_s.get(f"{BASE_URL}/api/properties", timeout=10)
        assert pr.status_code == 200
        props = pr.json() if isinstance(pr.json(), list) else pr.json().get("items", [])
        if not props:
            pytest.skip("No properties for client")
        property_id = props[0].get("id")

        payload = {
            "property_id": property_id,
            "title": "TEST_phase71 urgent leak",
            "category": "hvac",
            "priority": "urgent",
            "budget_estimate": 500,
            "description": "Urgent leak in bathroom",
        }
        r = client_s.post(f"{BASE_URL}/api/requests", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body.get("priority") == "urgent"
        self._created_id = body.get("id")

        # Check specialist notifications for [URGENT] prefix
        nr = spec_s.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert nr.status_code == 200
        items = nr.json() if isinstance(nr.json(), list) else nr.json().get("items", [])
        urgent_titles = [
            n.get("title", "") for n in items
            if "TEST_phase71 urgent leak" in n.get("title", "")
        ]
        assert any("[URGENT]" in t for t in urgent_titles), f"No [URGENT] prefix found in {urgent_titles}"

    def test_priority_filter_urgent(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/requests?priority=urgent", timeout=10)
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert all((it.get("priority") == "urgent") for it in items), "Found non-urgent in priority=urgent filter"


# ---------- Etapa B: QA Copilot code-aware ----------
class TestQACopilotCodeAware:
    def test_finding_code_aware_validates_paths(self, admin_s):
        # Create session
        r = admin_s.post(
            f"{BASE_URL}/api/admin/qa-copilot/sessions",
            json={"title": "TEST_phase71 code-aware", "area": "marketplace"},
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        sid = r.json().get("id")
        assert sid

        # Add a finding about a marketplace bug
        finding_body = {
            "text": "Pe pagina /specialist, butonul 🔥 Urgent din filter bar nu filtrează lista când este apăsat. Problema apare în SpecialistDashboard cu FilterBar.",
            "role": "qa",
        }
        rf = admin_s.post(
            f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}/findings",
            json=finding_body,
            timeout=45,
        )
        assert rf.status_code in (200, 201), rf.text
        finding = rf.json()
        ai = finding.get("ai_analysis") or {}
        assert ai.get("code_aware") is True, f"code_aware should be True, got {ai}"
        assert "invalid_paths_filtered" in ai, "invalid_paths_filtered must be in response"
        # All suspected_files must actually exist on disk
        for sf in ai.get("suspected_files") or []:
            # Path could be relative under /app
            candidate = sf if sf.startswith("/") else f"/app/{sf}"
            assert os.path.exists(candidate), f"AI suggested non-existent file: {sf}"

        # cleanup
        admin_s.delete(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}", timeout=10)


# ---------- Etapa C: Digital Twin Q&A ----------
class TestDigitalTwinQA:
    def test_history_no_auth_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/digital-twin/qa/history?project_id=anything", timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_history_nonexistent_project_404(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/digital-twin/qa/history?project_id=NONEXISTENT_phase71", timeout=10)
        assert r.status_code == 404

    def test_ask_disabled_ecosystem_returns_graceful(self, admin_s):
        # disable
        admin_s.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": False}, timeout=10)
        try:
            r = admin_s.post(
                f"{BASE_URL}/api/digital-twin/qa/ask",
                json={"project_id": "any-id-ok", "question": "Cat este suprafata?"},
                timeout=15,
            )
            # When disabled, returns 200 with disabled message (graceful)
            assert r.status_code == 200, f"expected 200 graceful, got {r.status_code} {r.text}"
            data = r.json()
            assert "dezactivat" in (data.get("answer") or "").lower()
        finally:
            admin_s.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": True}, timeout=10)


# ---------- Etapa D: Document Intelligence ----------
class TestDocsAI:
    _doc_id = None

    def test_upload_txt(self, client_s):
        text = (
            "Suprafața livingului este 28 m². Tabloul electric este în holul de intrare. "
            "Boilerul electric este în baia mare. Centrala termică este pe gaz natural."
        )
        files = {"file": ("TEST_phase71_apt.txt", io.BytesIO(text.encode("utf-8")), "text/plain")}
        r = client_s.post(f"{BASE_URL}/api/ai-docs/upload", files=files, data={"title": "TEST_phase71 apt"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("id")
        assert data.get("chunk_count", 0) >= 1
        TestDocsAI._doc_id = data["id"]

    def test_list_contains_uploaded(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/ai-docs/list", timeout=10)
        assert r.status_code == 200
        items = r.json().get("items", [])
        ids = [i.get("id") for i in items]
        assert TestDocsAI._doc_id in ids

    def test_ask_living_area(self, client_s):
        r = client_s.post(
            f"{BASE_URL}/api/ai-docs/ask",
            json={"question": "Cat este suprafata livingului?", "top_k": 4},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        sources = data.get("sources") or []
        assert len(sources) >= 1, f"expected sources, got {data}"
        # answer should mention 28
        answer = (data.get("answer") or "").lower()
        assert "28" in answer, f"answer should mention 28, got: {answer}"

    def test_ask_electric_panel(self, client_s):
        r = client_s.post(
            f"{BASE_URL}/api/ai-docs/ask",
            json={"question": "Unde este tabloul electric?", "top_k": 4},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        sources = data.get("sources") or []
        assert len(sources) >= 1
        answer = (data.get("answer") or "").lower()
        assert ("hol" in answer or "intrare" in answer), f"expected 'hol' or 'intrare', got: {answer}"

    def test_stats_admin_only(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/ai-docs/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "total_documents" in data
        assert "by_kind" in data

    def test_stats_client_403(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/ai-docs/stats", timeout=10)
        assert r.status_code == 403

    def test_upload_oversize_413(self, client_s):
        big = b"x" * (11 * 1024 * 1024 + 100)
        files = {"file": ("TEST_phase71_big.txt", io.BytesIO(big), "text/plain")}
        r = client_s.post(f"{BASE_URL}/api/ai-docs/upload", files=files, timeout=60)
        assert r.status_code == 413, f"expected 413, got {r.status_code}"

    def test_delete_doc(self, client_s):
        assert TestDocsAI._doc_id
        r = client_s.delete(f"{BASE_URL}/api/ai-docs/{TestDocsAI._doc_id}", timeout=10)
        assert r.status_code == 200
        # verify gone
        r2 = client_s.get(f"{BASE_URL}/api/ai-docs/list", timeout=10)
        ids = [i.get("id") for i in r2.json().get("items", [])]
        assert TestDocsAI._doc_id not in ids
