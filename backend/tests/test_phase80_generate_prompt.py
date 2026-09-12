"""Phase 80 — Per-task Emergent prompt generation tests.

Tests POST /api/admin/todos/generate-prompt and verifies no regression on
existing admin todos endpoints, ai-docs/ask (with and without inline_context),
and autonomy score endpoint.
"""
import os
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="session")
def client():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


# ---- generate-prompt: happy path ----
def test_generate_prompt_admin_success(admin):
    payload = {
        "text": "Refă imaginile din galeria principală — sunt placeholders generice acum",
        "topic_title": "Image Generation",
        "priority": "high",
    }
    r = admin.post(f"{BASE_URL}/api/admin/todos/generate-prompt", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "prompt" in data and isinstance(data["prompt"], str)
    assert len(data["prompt"]) > 50, f"prompt too short: {data['prompt']!r}"
    # 5 Romanian markdown sections must be present
    prompt = data["prompt"]
    required_sections = ["Obiectiv", "Fișiere suspecte", "Pași concreți", "Criterii de validare", "Risc"]
    missing = [s for s in required_sections if s not in prompt]
    assert not missing, f"Missing sections in prompt: {missing}\nPrompt:\n{prompt}"
    assert "model" in data
    assert "provider" in data


def test_generate_prompt_minimal_payload(admin):
    """Only text — no topic_title, no priority — should still work."""
    r = admin.post(
        f"{BASE_URL}/api/admin/todos/generate-prompt",
        json={"text": "Adaugă filtru de prioritate la lista de cereri"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("prompt")
    assert len(data["prompt"]) > 30


# ---- generate-prompt: validation ----
def test_generate_prompt_empty_text(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos/generate-prompt", json={"text": ""}, timeout=15)
    assert r.status_code in (400, 422)


def test_generate_prompt_short_text(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos/generate-prompt", json={"text": "ab"}, timeout=15)
    assert r.status_code in (400, 422)


def test_generate_prompt_missing_text(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos/generate-prompt", json={}, timeout=15)
    assert r.status_code in (400, 422)


# ---- generate-prompt: authz ----
def test_generate_prompt_client_forbidden(client):
    r = client.post(
        f"{BASE_URL}/api/admin/todos/generate-prompt",
        json={"text": "anything reasonable here for testing"},
        timeout=15,
    )
    assert r.status_code == 403


def test_generate_prompt_unauthenticated():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/admin/todos/generate-prompt",
        json={"text": "anything reasonable here for testing"},
        timeout=15,
    )
    assert r.status_code in (401, 403)


# ---- Fallback prompt code path exists (verify by reading file) ----
def test_fallback_prompt_code_exists():
    """Verify the deterministic fallback exists in admin_todos.py for empty LLM response."""
    p = "/app/backend/routes/admin_todos.py"
    with open(p) as f:
        src = f.read()
    # Verify the fallback path exists
    assert "if not prompt:" in src
    assert "## Obiectiv" in src
    assert "## Fișiere suspecte" in src
    assert "## Pași concreți" in src
    assert "## Criterii de validare" in src
    assert "## Risc" in src


# ---- Regression: existing endpoints still work ----
def test_regression_list_todos(admin):
    r = admin.get(f"{BASE_URL}/api/admin/todos", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "doc_done_ids" in data


def test_regression_crud_round_trip(admin):
    # CREATE
    r = admin.post(f"{BASE_URL}/api/admin/todos", json={"text": "TEST_phase80_rt", "priority": "low"}, timeout=15)
    assert r.status_code == 200
    tid = r.json()["id"]
    try:
        # UPDATE
        u = admin.put(f"{BASE_URL}/api/admin/todos/{tid}", json={"done": True}, timeout=15)
        assert u.status_code == 200 and u.json()["done"] is True and u.json().get("done_at")
        # VERIFY persistence via GET list
        lst = admin.get(f"{BASE_URL}/api/admin/todos", timeout=15).json()["items"]
        match = [t for t in lst if t["id"] == tid]
        assert match and match[0]["done"] is True
    finally:
        # DELETE
        d = admin.delete(f"{BASE_URL}/api/admin/todos/{tid}", timeout=15)
        assert d.status_code == 200


def test_regression_doc_done_mark_unmark(admin):
    body = {"id": "doc:phase80-test:0", "action": "mark"}
    r = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json=body, timeout=15)
    assert r.status_code == 200
    assert "doc:phase80-test:0" in r.json()["doc_done_ids"]
    # cleanup
    r2 = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json={"id": "doc:phase80-test:0", "action": "unmark"}, timeout=15)
    assert r2.status_code == 200
    assert "doc:phase80-test:0" not in r2.json()["doc_done_ids"]


def test_regression_ai_docs_ask_inline_context(admin):
    payload = {
        "question": "Cum funcționează modulul?",
        "inline_context": "Modulul X face Y. Are 3 sub-componente: A, B, C.",
        "inline_context_label": "Test Manual",
    }
    r = admin.post(f"{BASE_URL}/api/ai-docs/ask", json=payload, timeout=60)
    assert r.status_code == 200
    data = r.json()
    assert data.get("mode") == "inline_context"


def test_regression_ai_docs_ask_rag(admin):
    r = admin.post(f"{BASE_URL}/api/ai-docs/ask", json={"question": "ceva regresie"}, timeout=60)
    assert r.status_code == 200
    data = r.json()
    assert data.get("mode") != "inline_context"
    assert "answer" in data


def test_regression_autonomy_score(admin):
    r = admin.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=20)
    assert r.status_code == 200
