"""Iter 132 — Enterprise Knowledge Center EO-002 refinements R1-R8.
Tests: /access, /tree, /doc, /search, /registry, /review, /inspector, /architecture,
lifecycle logic (Draft/Review/Active/Archived), quality gate, path traversal, 403/401.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
FOUNDER = ("danieligna1@gmail.com", "Founder2026!kc")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def founder():
    return _login(*FOUNDER)


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


# -------- /access --------
def test_access_founder(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/access", timeout=15)
    assert r.status_code == 200
    assert r.json()["is_founder"] is True


def test_access_admin_not_founder(admin):
    r = admin.get(f"{BASE_URL}/api/founder/knowledge/access", timeout=15)
    assert r.status_code == 200
    assert r.json()["is_founder"] is False


# -------- /tree --------
def test_tree_founder(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/tree", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 150, f"expected >150 docs, got {d['total']}"
    assert set(d["status_counts"].keys()).issubset({"Active", "Review", "Draft", "Archived"})
    assert len(d["categories"]) > 0
    # each doc has required fields
    sample_docs = [doc for cat in d["categories"] for doc in cat["docs"]][:20]
    for doc in sample_docs:
        assert "health" in doc and "score" in doc["health"]
        assert 0 <= doc["health"]["score"] <= 100
        assert "quality" in doc and 0 <= doc["quality"] <= 100
        assert doc["status"] in ("Active", "Review", "Draft", "Archived")
        assert "version" in doc and "author" in doc


def test_tree_admin_403(admin):
    r = admin.get(f"{BASE_URL}/api/founder/knowledge/tree", timeout=15)
    assert r.status_code == 403


def test_tree_unauth_401():
    r = requests.get(f"{BASE_URL}/api/founder/knowledge/tree", timeout=15)
    assert r.status_code == 401


# -------- /doc --------
def test_doc_system_zero(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/doc",
                    params={"path": "memory/prompts/SYSTEM_ZERO.md"}, timeout=15)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    m = d["meta"]
    assert m["status"] == "Active", f"SYSTEM_ZERO expected Active, got {m['status']}"
    h = m["health"]
    for k in ("score", "referenced", "implementation", "evidence", "completeness"):
        assert k in h
    g = d["gate"]
    for k in ("naming_consistency", "versioning", "referenced_by_code",
              "duplicate_detection", "not_pending", "truth_engine_validation"):
        assert k in g["checks"]
    assert "quality_score" in g and "passed" in g
    assert isinstance(d["content"], str) and len(d["content"]) > 0
    rels = d["relationships"]
    assert "depends_on" in rels and "used_by" in rels


def test_doc_path_traversal_blocked(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/doc",
                    params={"path": "memory/../../etc/passwd"}, timeout=15)
    assert r.status_code in (400, 404)
    # Must not contain passwd content
    assert "root:" not in r.text


def test_doc_admin_403(admin):
    r = admin.get(f"{BASE_URL}/api/founder/knowledge/doc",
                  params={"path": "memory/prompts/SYSTEM_ZERO.md"}, timeout=15)
    assert r.status_code == 403


# -------- /search --------
def test_search(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/search", params={"q": "truth"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "documents" in d and "registry_nodes" in d
    if d["documents"]:
        doc = d["documents"][0]
        for k in ("snippet", "occurrences", "status", "path"):
            assert k in doc


# -------- /registry --------
def test_registry(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/registry", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "nodes" in d and "edges" in d and "stats" in d
    assert d["stats"]["nodes"] >= 40  # ~46
    assert d["stats"]["edges"] >= 40  # ~44
    assert "edges_by_status" in d["stats"] and "nodes_by_type" in d["stats"]


def test_registry_admin_403(admin):
    r = admin.get(f"{BASE_URL}/api/founder/knowledge/registry", timeout=15)
    assert r.status_code == 403


# -------- /review --------
def test_review(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/review", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("pending_verbatim", "drafts", "needs_review", "duplicates",
              "broken_relations", "activation_suggestions", "cleanup_suggestions", "top_priorities"):
        assert k in d and isinstance(d[k], list)


def test_review_grand_strategy_draft(founder):
    """R3: documente cu DRAFT_TOKENS nereferite ar trebui să fie Draft."""
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/review", timeout=30)
    d = r.json()
    draft_paths = " ".join(x["path"].upper() for x in d["drafts"])
    # cel puțin unul dintre tokens ar trebui să apară
    assert any(t in draft_paths for t in ("GRAND_STRATEGY", "EVOLUTION_ENGINE", "EXPONENTIAL", "SCALING")), \
        f"Expected DRAFT_TOKENS in drafts, got: {draft_paths[:500]}"


# -------- /inspector --------
def test_inspector_ceo_status(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/inspector/ceo.enterprise_status", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "engine" in d and "api" in d and "prompt" in d
    assert "dependencies" in d
    for dep in d["dependencies"][:5]:
        assert "source_name" in dep and "target_name" in dep


def test_inspector_unknown_404(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/inspector/nonexistent.widget", timeout=15)
    assert r.status_code == 404


# -------- /architecture --------
def test_architecture(founder):
    r = founder.get(f"{BASE_URL}/api/founder/knowledge/architecture", timeout=15)
    assert r.status_code == 200
    d = r.json()
    # arch blocks
    assert isinstance(d, dict) and len(d) > 0


def test_architecture_admin_403(admin):
    r = admin.get(f"{BASE_URL}/api/founder/knowledge/architecture", timeout=15)
    assert r.status_code == 403
