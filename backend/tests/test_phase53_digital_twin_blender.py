"""Phase 53 — Digital Twin: Blender headless conversion + Trimble Connect embed.

Tests cover:
- Multi-format upload (.obj, .dae, .fbx, .stl, .ply) → Blender auto-conversion
- Conversion status polling endpoint
- Conversion retry endpoint
- Trimble embed URL validation + persistence (operator/admin only)
- Edge cases: .skp → CloudConvert path, .glb direct (no conversion)
- Permissions: client (no DT access) → 403, specialist → 403 on /trimble
"""
import os
import shutil
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

# Blender conversion requires the blender binary on the host — skip the whole
# module in environments (e.g. preview pods) where it is not installed.
pytestmark = pytest.mark.skipif(
    shutil.which("blender") is None,
    reason="Blender binary not installed in this environment",
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}


TINY_OBJ = b"""v -1 -1 -1
v 1 -1 -1
v 1 1 -1
v -1 1 -1
v -1 -1 1
v 1 -1 1
v 1 1 1
v -1 1 1
f 1 2 3 4
f 5 8 7 6
f 1 5 6 2
f 2 6 7 3
f 3 7 8 4
f 4 8 5 1
"""


def _login(creds):
    """Login and return a requests.Session with auth cookies set."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text}"
    # Auth might be via cookie OR token in body — handle both
    body = r.json()
    tok = body.get("token") or body.get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def _auth(session):
    # Backward-compat shim: pass the session through; callers use session.get/post
    return session


# ---- fixtures ----

@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def operator_token():
    return _login(OPERATOR)


@pytest.fixture(scope="module")
def client_token():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist_token():
    return _login(SPECIALIST)


@pytest.fixture(scope="module")
def admin_project(admin_token):
    """Create a fresh DT project owned by admin for the run."""
    r = requests.post(
        f"{BASE_URL}/api/digital-twin/projects",
        cookies=admin_token.cookies, headers=admin_token.headers,
        json={"name": "TEST_p53_blender_proj", "description": "phase 53 test"},
        timeout=15,
    )
    assert r.status_code == 200, f"create project failed: {r.status_code} {r.text}"
    return r.json()


# ---- helpers ----

def _upload(token, pid, ext, content=TINY_OBJ):
    files = {"file": (f"cube{ext}", content, "application/octet-stream")}
    return requests.post(
        f"{BASE_URL}/api/digital-twin/projects/{pid}/upload",
        cookies=token.cookies, headers=token.headers,
        files=files,
        timeout=30,
    )


def _poll_status(token, model_id, max_sec=45):
    """Poll conversion status; return final response dict."""
    deadline = time.time() + max_sec
    last = None
    while time.time() < deadline:
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/conversions/{model_id}/status",
            cookies=token.cookies, headers=token.headers,
            timeout=10,
        )
        assert r.status_code == 200, f"status {r.status_code}: {r.text}"
        last = r.json()
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(2)
    return last


# ====================== TESTS ======================

# --- OBJ → GLB happy path ---
class TestBlenderObjConversion:
    def test_upload_obj_triggers_blender(self, admin_token, admin_project):
        r = _upload(admin_token, admin_project["id"], ".obj")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ext"] == ".obj"
        assert data["kind"] == "source"
        assert data.get("conversion_status") == "pending"
        assert data.get("conversion_engine") == "blender"
        # Stash for next tests
        admin_project["_obj_model_id"] = data["id"]

    def test_poll_status_until_completed(self, admin_token, admin_project):
        mid = admin_project.get("_obj_model_id")
        assert mid, "previous upload test must have run first"
        final = _poll_status(admin_token, mid, max_sec=60)
        assert final, "no status received"
        assert final.get("status") == "completed", f"conversion did not complete: {final}"
        assert final.get("converted_model_id"), "converted_model_id missing"
        assert final.get("converted_url"), "converted_url missing"
        assert final["converted_url"].endswith(".glb"), final["converted_url"]
        assert "/api/digital-twin/files/" in final["converted_url"]
        admin_project["_obj_converted_url"] = final["converted_url"]

    def test_converted_glb_is_downloadable_and_valid(self, admin_token, admin_project):
        url = admin_project.get("_obj_converted_url")
        assert url
        full = url if url.startswith("http") else f"{BASE_URL}{url}"
        r = requests.get(full, cookies=admin_token.cookies, headers=admin_token.headers, timeout=30)
        assert r.status_code == 200, f"download failed: {r.status_code}"
        # GLB magic bytes = b"glTF"
        assert r.content[:4] == b"glTF", f"GLB magic missing, got {r.content[:8]!r}"
        assert len(r.content) > 100, "GLB suspiciously small"


# --- Retry conversion ---
class TestConversionRetry:
    def test_retry_resets_status_to_pending(self, admin_token, admin_project):
        mid = admin_project.get("_obj_model_id")
        assert mid
        r = requests.post(
            f"{BASE_URL}/api/digital-twin/conversions/{mid}/retry",
            cookies=admin_token.cookies, headers=admin_token.headers,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["status"] == "pending"
        assert data["engine"] == "blender"

    def test_retry_completes_again(self, admin_token, admin_project):
        mid = admin_project.get("_obj_model_id")
        final = _poll_status(admin_token, mid, max_sec=60)
        assert final.get("status") == "completed", f"retry did not complete: {final}"


# --- Multi-format upload (just verify accepted + triggers blender for first chunk) ---
class TestMultiFormatUpload:
    @pytest.mark.parametrize("ext", [".dae", ".fbx", ".stl", ".ply", ".obj"])
    def test_upload_accepted_and_triggers_blender(self, admin_token, admin_project, ext):
        # Re-use the OBJ content (Blender will likely fail to parse for non-obj
        # formats, but we only verify the API accepts the upload & enqueues Blender).
        r = _upload(admin_token, admin_project["id"], ext)
        assert r.status_code == 200, f"{ext} upload failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["ext"] == ext
        assert data["kind"] == "source", f"{ext} kind should be source, got {data.get('kind')}"
        assert data.get("conversion_engine") == "blender"
        assert data.get("conversion_status") == "pending"


# --- Edge cases ---
class TestEdgeCases:
    def test_skp_routes_to_cloudconvert(self, admin_token, admin_project):
        # Tiny fake .skp (CloudConvert will eventually fail since it doesn't
        # support SKP, but the conversion_engine field is what we assert).
        r = _upload(admin_token, admin_project["id"], ".skp", content=b"SketchUp fake header data")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ext"] == ".skp"
        assert data["kind"] == "archive"
        # cloudconvert client may or may not be enabled depending on env
        if data.get("conversion_engine"):
            assert data["conversion_engine"] == "cloudconvert", data

    def test_glb_direct_no_conversion(self, admin_token, admin_project):
        # Minimal valid-ish GLB header
        glb = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 16
        r = _upload(admin_token, admin_project["id"], ".glb", content=glb)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ext"] == ".glb"
        assert data["kind"] == "model"
        # No conversion fields should be set
        assert data.get("conversion_status") in (None, "n/a"), data.get("conversion_status")
        assert data.get("conversion_engine") in (None, ""), data.get("conversion_engine")

    def test_unsupported_extension_rejected(self, admin_token, admin_project):
        r = _upload(admin_token, admin_project["id"], ".txt", content=b"hello")
        assert r.status_code == 400, r.text


# --- Trimble embed URL validation ---
class TestTrimbleEmbed:
    def test_invalid_url_rejected(self, operator_token, admin_project):
        r = requests.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/{admin_project['id']}/trimble",
            cookies=operator_token.cookies, headers=operator_token.headers,
            json={"trimble_embed_url": "https://malicious.com/iframe"},
            timeout=10,
        )
        assert r.status_code == 400, r.text

    def test_valid_url_persists(self, operator_token, admin_token, admin_project):
        good = "https://web.connect.trimble.com/projects/abc/viewer/xyz"
        r = requests.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/{admin_project['id']}/trimble",
            cookies=operator_token.cookies, headers=operator_token.headers,
            json={"trimble_embed_url": good},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("trimble_embed_url") == good

        # Verify GET returns it
        r2 = requests.get(
            f"{BASE_URL}/api/digital-twin/projects/{admin_project['id']}",
            cookies=admin_token.cookies, headers=admin_token.headers,
            timeout=10,
        )
        assert r2.status_code == 200
        assert r2.json().get("trimble_embed_url") == good

    def test_empty_string_clears(self, operator_token, admin_project):
        r = requests.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/{admin_project['id']}/trimble",
            cookies=operator_token.cookies, headers=operator_token.headers,
            json={"trimble_embed_url": ""},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json().get("trimble_embed_url") is None

    def test_specialist_cannot_set_trimble(self, specialist_token, admin_project):
        r = requests.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/{admin_project['id']}/trimble",
            cookies=specialist_token.cookies, headers=specialist_token.headers,
            json={"trimble_embed_url": "https://web.connect.trimble.com/xyz"},
            timeout=10,
        )
        assert r.status_code == 403, r.text

    def test_client_cannot_set_trimble(self, client_token, admin_project):
        r = requests.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/{admin_project['id']}/trimble",
            cookies=client_token.cookies, headers=client_token.headers,
            json={"trimble_embed_url": "https://web.connect.trimble.com/xyz"},
            timeout=10,
        )
        assert r.status_code == 403, r.text


# --- Permissions for upload (DT access) ---
class TestUploadPermissions:
    def test_client_without_dt_pro_cannot_upload(self, client_token, admin_project):
        # client@propmanage.io should NOT have digital_twin_pro by default
        r = _upload(client_token, admin_project["id"], ".obj")
        # 403 (no DT access) OR 404 (no access to admin's project) both valid security responses
        assert r.status_code in (403, 404), f"expected 403/404 got {r.status_code} {r.text}"


# --- Cleanup ---
@pytest.fixture(scope="module", autouse=True)
def cleanup_project(admin_token, admin_project):
    yield
    try:
        requests.delete(
            f"{BASE_URL}/api/digital-twin/projects/{admin_project['id']}",
            cookies=admin_token.cookies, headers=admin_token.headers,
            timeout=10,
        )
    except Exception:
        pass
