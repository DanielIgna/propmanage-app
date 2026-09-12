"""
Iter200 — Digital Twin P1 consolidation regression + robustness.

Covers:
  * FREE user can create/upload/list/serve OWN model (ingest gate relaxed)
  * FREE user still blocked (402) from ADVANCED (pin create)
  * PREMIUM client full flow: version PATCH with supersedes marks old as
    superseded (non-destructive), visibility validation (public/internal ok,
    'world' -> 400)
  * GET /api/properties/{id}/spaces canonical rooms from 2D twin
  * Document upload with related_model_id/related_room_id persists (verify via GET)
  * 2D plan PDF upload + serve (object-storage restore-aware)
  * Operator twin approve does NOT force structure_health=95; twin_unlocked=true
  * Regression: PREMIUM pin CRUD & comment
"""
import io
import os
import struct
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PW = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PW = "1!nasov01ADMIN"
OP_EMAIL = "operator@propmanage.io"
OP_PW = "Op123!"

HEADERS = {"X-PM-Client": "propmanage-app"}


# ---------------- helpers ----------------
def _login(session: requests.Session, email: str, pw: str):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": email, "password": pw},
                     headers=HEADERS, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return r.json()


def _register_free(session: requests.Session):
    ts = int(time.time())
    email = f"free{ts}{uuid.uuid4().hex[:6]}@example.com"
    r = session.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": email, "password": "FreePass123!",
            "name": "Free Test", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True,
        }, headers=HEADERS, timeout=30,
    )
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:200]}"
    return email


def _min_glb_bytes():
    """Build a minimal valid GLB (JSON chunk only) — enough for upload path."""
    j = b'{"asset":{"version":"2.0"},"scenes":[{"nodes":[]}],"scene":0}'
    # pad JSON chunk to 4-byte alignment with spaces
    pad = (-len(j)) % 4
    j += b" " * pad
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j))
    json_chunk = struct.pack("<II", len(j), 0x4E4F534A) + j
    return header + json_chunk


def _min_pdf_bytes():
    return (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000053 00000 n \n0000000098 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>startxref\n150\n%%EOF\n"
    )


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PW)
    s.headers.update(HEADERS)
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PW)
    s.headers.update(HEADERS)
    return s


@pytest.fixture(scope="module")
def operator_session():
    s = requests.Session()
    _login(s, OP_EMAIL, OP_PW)
    s.headers.update(HEADERS)
    return s


@pytest.fixture(scope="module")
def free_session():
    s = requests.Session()
    email = _register_free(s)
    # register auto-logs-in? Try login just in case
    _login(s, email, "FreePass123!")
    s.headers.update(HEADERS)
    s._email = email
    return s


@pytest.fixture(scope="module")
def free_project(free_session):
    """Create a DT project for the FREE user (should succeed — ingest gate relaxed)."""
    r = free_session.post(
        f"{BASE_URL}/api/digital-twin/projects",
        json={"name": "FREE user project"},
        timeout=30,
    )
    assert r.status_code == 200, f"FREE create project failed: {r.status_code} {r.text[:300]}"
    proj = r.json()
    assert proj.get("id")
    assert proj.get("owner_id")
    return proj


@pytest.fixture(scope="module")
def premium_project(client_session):
    r = client_session.post(
        f"{BASE_URL}/api/digital-twin/projects",
        json={"name": "PREMIUM iter200 project"},
        timeout=30,
    )
    assert r.status_code == 200, f"PREMIUM create project failed: {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="module")
def demo_property_with_spaces(client_session):
    """Return a property_id owned by client that has a 2D twin with rooms."""
    r = client_session.get(f"{BASE_URL}/api/properties", timeout=30)
    assert r.status_code == 200
    props = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    # Try to find one that returns >0 spaces
    for p in props:
        pid = p.get("id") or p.get("_id")
        if not pid:
            continue
        s = client_session.get(f"{BASE_URL}/api/properties/{pid}/spaces", timeout=30)
        if s.status_code == 200 and (s.json().get("count") or 0) > 0:
            return pid, s.json()
    # Fallback: return the first property + last spaces response
    pid = (props[0].get("id") or props[0].get("_id")) if props else None
    return pid, None


# ============================================================
# 1. FREE user — ingest relaxed, advanced still gated
# ============================================================
class TestFreeIngestRelaxed:
    def test_free_can_create_project(self, free_project):
        assert free_project["id"]
        assert free_project["name"] == "FREE user project"
        assert free_project.get("model_count", 0) == 0

    def test_free_can_upload_glb(self, free_session, free_project):
        pid = free_project["id"]
        glb = _min_glb_bytes()
        files = {"file": ("free_model.glb", glb, "model/gltf-binary")}
        r = free_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/upload",
            files=files,
            params={"change_reason": "initial upload"},
            timeout=60,
        )
        assert r.status_code == 200, f"FREE upload failed: {r.status_code} {r.text[:400]}"
        m = r.json()
        assert m["source"] in ("owner_upload", "specialist", "platform")
        assert m["version"] == 1
        assert m["status"] in ("ready", "processing", "stored")
        assert m["visibility"] == "internal"
        assert m["object_path"]
        assert m["change_reason"] == "initial upload"
        # store id for downstream tests
        free_project["_first_model"] = m

    def test_free_can_list_models(self, free_session, free_project):
        pid = free_project["id"]
        r = free_session.get(f"{BASE_URL}/api/digital-twin/projects/{pid}/models",
                             timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1
        assert any(m["id"] == free_project["_first_model"]["id"] for m in data["items"])

    def test_free_can_serve_uploaded_model(self, free_session, free_project):
        pid = free_project["id"]
        m = free_project["_first_model"]
        r = free_session.get(
            f"{BASE_URL}/api/digital-twin/files/{pid}/{m['stored_as']}",
            timeout=30,
        )
        assert r.status_code == 200, f"serve failed: {r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("model/gltf-binary") \
            or "gltf" in r.headers.get("content-type", "")
        assert len(r.content) > 0

    def test_free_blocked_from_pin_create(self, free_session, free_project):
        pid = free_project["id"]
        r = free_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/pins",
            json={"title": "FREE tries pin",
                  "position": {"x": 0, "y": 0, "z": 0}},
            timeout=30,
        )
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        # FastAPI error envelope: detail={...}
        detail = body.get("detail") or body
        assert detail.get("error") == "entitlement_required"
        assert detail.get("feature") == "digital_twin_advanced"


# ============================================================
# 2. PREMIUM — versioning + supersedes + visibility validation
# ============================================================
class TestPremiumVersioning:
    def test_premium_upload_two_models_and_supersede(self, client_session, premium_project):
        pid = premium_project["id"]
        # upload model v1
        r1 = client_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/upload",
            files={"file": ("v1.glb", _min_glb_bytes(), "model/gltf-binary")},
            params={"change_reason": "v1"}, timeout=60,
        )
        assert r1.status_code == 200, r1.text[:200]
        m1 = r1.json()
        # upload model v2
        r2 = client_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/upload",
            files={"file": ("v2.glb", _min_glb_bytes(), "model/gltf-binary")},
            params={"change_reason": "v2 refined"}, timeout=60,
        )
        assert r2.status_code == 200, r2.text[:200]
        m2 = r2.json()

        # PATCH v2 with version=2, version_label, supersedes=m1
        patch = client_session.patch(
            f"{BASE_URL}/api/digital-twin/models/{m2['id']}",
            json={"version": 2, "version_label": "v2 final",
                  "supersedes": m1["id"]},
            timeout=30,
        )
        assert patch.status_code == 200, f"patch supersedes failed: {patch.text[:300]}"
        pdata = patch.json()
        assert pdata["version"] == 2
        assert pdata["version_label"] == "v2 final"
        assert pdata["supersedes"] == m1["id"]

        # Verify m1 marked as superseded (NON-DESTRUCTIVE — still listed)
        lst = client_session.get(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/models", timeout=30)
        assert lst.status_code == 200
        items = lst.json()["items"]
        found_old = next((m for m in items if m["id"] == m1["id"]), None)
        assert found_old, "OLD model must remain in list (non-destructive)"
        assert found_old["status"] == "superseded"
        assert found_old.get("superseded_by") == m2["id"]
        # stash for later
        premium_project["_m1"] = m1
        premium_project["_m2"] = m2

    def test_visibility_valid_transitions(self, client_session, premium_project):
        mid = premium_project["_m2"]["id"]
        for v in ("public", "internal"):
            r = client_session.patch(
                f"{BASE_URL}/api/digital-twin/models/{mid}",
                json={"visibility": v}, timeout=30,
            )
            assert r.status_code == 200, f"visibility={v} failed: {r.text[:200]}"
            assert r.json()["visibility"] == v

    def test_visibility_invalid_world_rejected(self, client_session, premium_project):
        mid = premium_project["_m2"]["id"]
        r = client_session.patch(
            f"{BASE_URL}/api/digital-twin/models/{mid}",
            json={"visibility": "world"}, timeout=30,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"


# ============================================================
# 3. /spaces canonical rooms
# ============================================================
class TestSpacesEndpoint:
    def test_spaces_from_twin_2d(self, demo_property_with_spaces):
        pid, spaces = demo_property_with_spaces
        if not spaces or spaces.get("count", 0) == 0:
            pytest.skip("No property with 2D twin rooms found for client")
        assert spaces["count"] >= 1
        s0 = spaces["spaces"][0]
        assert s0["space_id"]
        assert "name" in s0
        assert s0["source"] == "twin_2d"


# ============================================================
# 4. Document upload with related_model_id + related_room_id
# ============================================================
class TestDocumentRelations:
    def test_document_persists_related_ids(self, client_session, premium_project,
                                            demo_property_with_spaces):
        prop_id, spaces = demo_property_with_spaces
        if not prop_id:
            pytest.skip("No property available")
        model_id = premium_project["_m2"]["id"]
        room_id = None
        if spaces and spaces.get("count"):
            room_id = spaces["spaces"][0]["space_id"]

        files = {"file": ("test_doc.pdf", _min_pdf_bytes(), "application/pdf")}
        data = {
            "title": "TEST_related_ids",
            "category": "altele",
            "related_model_id": model_id,
            "related_room_id": room_id or "",
        }
        r = client_session.post(
            f"{BASE_URL}/api/properties/{prop_id}/documents",
            files=files, data=data, timeout=60,
        )
        assert r.status_code == 200, f"doc upload failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        doc = body.get("document") or body
        assert doc.get("related_model_id") == model_id
        if room_id:
            assert doc.get("related_room_id") == room_id
        doc_id = doc.get("id") or doc.get("_id")
        assert doc_id
        # GET-verify persistence
        g = client_session.get(f"{BASE_URL}/api/documents/{doc_id}", timeout=30)
        assert g.status_code == 200, f"GET doc failed: {g.text[:200]}"
        gbody = g.json()
        gdoc = gbody.get("document") or gbody
        assert gdoc.get("related_model_id") == model_id
        if room_id:
            assert gdoc.get("related_room_id") == room_id


# ============================================================
# 5. 2D plan PDF upload + serve
# ============================================================
class TestPlanUploadServe:
    def test_upload_and_serve_plan(self, client_session, premium_project):
        pid = premium_project["id"]
        files = {"file": ("plan.pdf", _min_pdf_bytes(), "application/pdf")}
        r = client_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/plans",
            files=files,
            params={"title": "TEST plan iter200", "plan_type": "floorplan"},
            timeout=60,
        )
        assert r.status_code == 200, f"plan upload: {r.status_code} {r.text[:300]}"
        plan = r.json()
        assert plan["stored_as"]
        # Serve
        g = client_session.get(
            f"{BASE_URL}/api/digital-twin/plans/{pid}/{plan['stored_as']}",
            timeout=30,
        )
        assert g.status_code == 200, f"serve plan: {g.status_code} {g.text[:200]}"
        assert g.headers.get("content-type", "").startswith("application/pdf")
        assert g.content.startswith(b"%PDF")


# ============================================================
# 6. Operator approve — no structure_health=95 override
# ============================================================
class TestOperatorApproveNoHealthOverride:
    def test_approve_preserves_structure_health(self, client_session, operator_session):
        # Find a property with a twin that can be approved
        r = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=30)
        assert r.status_code == 200
        twins = r.json()
        # Skip if none available
        candidates = [t for t in twins if t.get("property_id") and t.get("status") in
                      ("draft", "pending_validation", "approved", "needs_revision")]
        if not candidates:
            pytest.skip("No twin candidates in operator queue")

        # Prefer one that is NOT the demo property with 5 real rooms (avoid mutating)
        DO_NOT_TOUCH = "6a11d70e600be19667009c93"
        preferred = [t for t in candidates if t["property_id"] != DO_NOT_TOUCH]
        target = (preferred or candidates)[0]
        prop_id = target["property_id"]

        # Read current property structure_health (as admin)
        # Use operator session to fetch property via GET /api/properties/{id} if allowed
        p_before = operator_session.get(f"{BASE_URL}/api/properties/{prop_id}",
                                        timeout=30)
        prev_health = None
        if p_before.status_code == 200:
            pb = p_before.json()
            prev_health = pb.get("structure_health")

        # Approve
        r2 = operator_session.post(
            f"{BASE_URL}/api/operator/twins/{prop_id}/validate",
            json={"action": "approve", "notes": "iter200 test"},
            timeout=30,
        )
        assert r2.status_code == 200, f"approve failed: {r2.status_code} {r2.text[:300]}"
        assert r2.json().get("status") == "approved"

        # Read property again
        p_after = operator_session.get(f"{BASE_URL}/api/properties/{prop_id}",
                                       timeout=30)
        if p_after.status_code == 200:
            pa = p_after.json()
            # twin_unlocked must be true
            assert pa.get("twin_unlocked") is True, \
                f"twin_unlocked should be True after approve: {pa.get('twin_unlocked')}"
            # structure_health must NOT be forced to 95
            after_health = pa.get("structure_health")
            if prev_health is None:
                # No previous value — should remain absent or unchanged, but definitely NOT 95
                # (unless it happened to be 95 already, which is fine — assert idempotent)
                assert after_health != 95 or prev_health == 95, \
                    f"structure_health forced to 95 (was {prev_health})"
            else:
                assert after_health == prev_health, \
                    f"structure_health changed on approve: {prev_health} -> {after_health}"


# ============================================================
# 7. Regression — PREMIUM pin CRUD + comment
# ============================================================
class TestPremiumPinRegression:
    def test_pin_create_list_comment_delete(self, client_session, premium_project):
        pid = premium_project["id"]
        r = client_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/pins",
            json={"title": "regression pin",
                  "position": {"x": 1, "y": 2, "z": 3},
                  "priority": "normal", "category": "general"},
            timeout=30,
        )
        assert r.status_code == 200, f"pin create: {r.status_code} {r.text[:200]}"
        pin = r.json()
        pin_id = pin["id"]

        lst = client_session.get(
            f"{BASE_URL}/api/digital-twin/projects/{pid}/pins", timeout=30)
        assert lst.status_code == 200
        assert any(p["id"] == pin_id for p in lst.json()["items"])

        # Comment on the pin (schema: message)
        c = client_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/comments",
            json={"message": "regression comment iter200"}, timeout=30,
        )
        assert c.status_code in (200, 201), \
            f"comment failed: {c.status_code} {c.text[:200]}"

        # Cleanup pin
        d = client_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}", timeout=30)
        assert d.status_code == 200
