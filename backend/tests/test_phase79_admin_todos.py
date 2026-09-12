"""Phase 79 — AI Assistant inline_context + Admin ToDo Board tests."""
import os
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

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


# ---- ToDos GET / authz ----
def test_list_todos_admin(admin):
    r = admin.get(f"{BASE_URL}/api/admin/todos", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and isinstance(data["items"], list)
    assert "doc_done_ids" in data and isinstance(data["doc_done_ids"], list)


def test_list_todos_client_forbidden(client):
    r = client.get(f"{BASE_URL}/api/admin/todos", timeout=15)
    assert r.status_code == 403


# ---- POST validation ----
def test_create_todo_invalid_priority(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos", json={"text": "TEST_invalid_prio", "priority": "urgent"}, timeout=15)
    assert r.status_code in (400, 422)


def test_create_todo_text_too_short(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos", json={"text": "a", "priority": "medium"}, timeout=15)
    assert r.status_code in (400, 422)


# ---- CRUD ----
@pytest.fixture
def created_todo(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos", json={"text": "TEST_phase79_todo", "priority": "low"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data and data["text"] == "TEST_phase79_todo"
    assert data["priority"] == "low"
    assert data["done"] is False
    assert "created_at" in data
    yield data
    # cleanup
    admin.delete(f"{BASE_URL}/api/admin/todos/{data['id']}", timeout=15)


def test_create_persists(admin, created_todo):
    r = admin.get(f"{BASE_URL}/api/admin/todos", timeout=15)
    ids = [t["id"] for t in r.json()["items"]]
    assert created_todo["id"] in ids


def test_update_done_sets_done_at(admin, created_todo):
    r = admin.put(f"{BASE_URL}/api/admin/todos/{created_todo['id']}", json={"done": True}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["done"] is True
    assert data.get("done_at")


def test_update_priority(admin, created_todo):
    r = admin.put(f"{BASE_URL}/api/admin/todos/{created_todo['id']}", json={"priority": "high"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["priority"] == "high"


def test_update_text(admin, created_todo):
    r = admin.put(f"{BASE_URL}/api/admin/todos/{created_todo['id']}", json={"text": "TEST_phase79_updated"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["text"] == "TEST_phase79_updated"


def test_update_invalid_priority(admin, created_todo):
    r = admin.put(f"{BASE_URL}/api/admin/todos/{created_todo['id']}", json={"priority": "lol"}, timeout=15)
    assert r.status_code == 400


def test_update_not_found(admin):
    r = admin.put(f"{BASE_URL}/api/admin/todos/nope-no-such-id", json={"done": True}, timeout=15)
    assert r.status_code == 404


def test_delete_then_404(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos", json={"text": "TEST_to_delete", "priority": "medium"}, timeout=15)
    tid = r.json()["id"]
    d = admin.delete(f"{BASE_URL}/api/admin/todos/{tid}", timeout=15)
    assert d.status_code == 200 and d.json() == {"deleted": True}
    d2 = admin.delete(f"{BASE_URL}/api/admin/todos/{tid}", timeout=15)
    assert d2.status_code == 404


# ---- doc-done ----
def test_doc_done_mark_and_unmark(admin):
    body = {"id": "doc:autonomy-engine:0", "action": "mark"}
    r = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json=body, timeout=15)
    assert r.status_code == 200
    assert "doc:autonomy-engine:0" in r.json()["doc_done_ids"]
    # idempotent
    r2 = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json=body, timeout=15)
    assert r2.status_code == 200
    ids = r2.json()["doc_done_ids"]
    assert ids.count("doc:autonomy-engine:0") == 1
    # unmark
    r3 = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json={"id": "doc:autonomy-engine:0", "action": "unmark"}, timeout=15)
    assert r3.status_code == 200
    assert "doc:autonomy-engine:0" not in r3.json()["doc_done_ids"]


def test_doc_done_invalid_prefix(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json={"id": "abc:1", "action": "mark"}, timeout=15)
    assert r.status_code == 400


def test_doc_done_invalid_action(admin):
    r = admin.post(f"{BASE_URL}/api/admin/todos/doc-done", json={"id": "doc:x:1", "action": "lol"}, timeout=15)
    assert r.status_code == 400


# ---- inline_context AI ask ----
def test_ask_docs_inline_context(admin):
    ctx = (
        "Autonomy Engine — sistemul AI care evaluează 5 sub-scoruri: Operational, Technical, "
        "Security, Dev și AI. Pe baza scorului general, există patru tier-uri de operare: "
        "Manual, Assisted, Autonomous, Self-driving."
    )
    payload = {
        "question": "Cum funcționează Autonomy Engine?",
        "inline_context": ctx,
        "inline_context_label": "Manual Admin PropManage",
    }
    r = admin.post(f"{BASE_URL}/api/ai-docs/ask", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("mode") == "inline_context"
    sources = data.get("sources") or []
    assert len(sources) == 1
    assert sources[0].get("kind") == "inline_manual"
    answer = (data.get("answer") or "").lower()
    # The LLM should reference at least one of the listed tiers/scores
    assert any(k in answer for k in ["manual", "assisted", "autonomous", "self-driving", "operational", "technical", "security"])


def test_ask_docs_without_inline_context_still_rag(admin):
    # Without inline_context, behavior is RAG over user docs (admin sees all).
    r = admin.post(f"{BASE_URL}/api/ai-docs/ask",
                   json={"question": "ceva intrebare oarecare pentru regresie"}, timeout=60)
    assert r.status_code == 200
    data = r.json()
    # Crucially, NOT inline_context mode
    assert data.get("mode") != "inline_context"
    assert "answer" in data


# ---- Regression ----
def test_autonomy_score(admin):
    r = admin.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=20)
    assert r.status_code == 200


def test_ai_activity(admin):
    r = admin.get(f"{BASE_URL}/api/admin/ai-activity", timeout=20)
    assert r.status_code == 200
