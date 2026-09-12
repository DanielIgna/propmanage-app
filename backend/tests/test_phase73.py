"""Phase 73 backend tests — App Settings Snapshots + Service Contracts."""
import os
import time
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

def _read_backend_url():
    url = os.environ.get('REACT_APP_BACKEND_URL')
    if url:
        return url.rstrip('/')
    try:
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().rstrip('/')
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _read_backend_url()

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text[:300]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist_session():
    return _login(SPECIALIST)


# ---------- SNAPSHOTS ----------
class TestSnapshots:
    def test_create_manual_snapshot(self, admin_session):
        label = f"TEST_snap_{uuid.uuid4().hex[:6]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/app-settings/snapshots", json={"label": label}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["kind"] == "manual"
        assert d["label"] == label
        assert "id" in d and "ts" in d and "settings" in d
        pytest.snap_id = d["id"]
        pytest.snap_label = label

    def test_list_snapshots_excludes_settings(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
        ids = [i["id"] for i in d["items"]]
        assert pytest.snap_id in ids
        # settings should NOT be returned in list
        for item in d["items"]:
            assert "settings" not in item
        # Sorted newest first
        ts_list = [i["ts"] for i in d["items"]]
        assert ts_list == sorted(ts_list, reverse=True)

    def test_get_single_snapshot_has_settings(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots/{pytest.snap_id}", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == pytest.snap_id
        assert "settings" in d

    def test_restore_creates_pre_restore(self, admin_session):
        before = admin_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots?limit=100", timeout=10).json()
        before_ids = {i["id"] for i in before["items"]}
        r = admin_session.post(f"{BASE_URL}/api/admin/app-settings/snapshots/{pytest.snap_id}/restore", timeout=20)
        assert r.status_code == 200, r.text
        assert r.json().get("restored") is True
        time.sleep(0.5)
        after = admin_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots?limit=100", timeout=10).json()
        new_items = [i for i in after["items"] if i["id"] not in before_ids]
        assert any(i.get("kind") == "pre_restore" for i in new_items), f"no pre_restore snapshot created: {new_items}"

    def test_non_admin_forbidden(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots", timeout=10)
        assert r.status_code in (401, 403)
        r2 = client_session.post(f"{BASE_URL}/api/admin/app-settings/snapshots", json={"label": "x"}, timeout=10)
        assert r2.status_code in (401, 403)

    def test_snapshot_404_on_unknown(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/app-settings/snapshots/{uuid.uuid4().hex}", timeout=10)
        assert r.status_code == 404


# ---------- CONTRACTS ----------
@pytest.fixture(scope="module")
def existing_request_id(client_session, admin_session):
    """Find an existing request with a specialist assigned, or create one."""
    # Try admin all requests endpoint or client requests
    for path in ["/api/requests/my", "/api/requests", "/api/admin/requests"]:
        try:
            r = client_session.get(f"{BASE_URL}{path}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get("items") or data.get("requests") or []
                for it in items:
                    if it.get("specialist_id") and it.get("client_id"):
                        return it["id"]
        except Exception:
            continue
    # Create a request as client
    payload = {
        "title": "TEST_phase73_contract_request",
        "description": "Test request for contract generation",
        "category": "plumbing",
        "priority": "normal",
        "city": "Bucuresti",
    }
    r = client_session.post(f"{BASE_URL}/api/requests", json=payload, timeout=15)
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create request for contract testing: {r.status_code} {r.text[:200]}")
    rid = r.json().get("id")
    return rid


class TestContracts:
    def test_generate_404_unknown_request(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/contracts/generate", json={"request_id": "doesnotexist_xyz"}, timeout=15)
        assert r.status_code == 404

    def test_generate_contract(self, admin_session, existing_request_id):
        r = admin_session.post(f"{BASE_URL}/api/contracts/generate", json={"request_id": existing_request_id}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d
        assert d["status"] in ("draft", "active", "mediated")  # may already exist
        assert "body_html" in d and "CONTRACT" in d["body_html"].upper()
        # No raw placeholders left (unsubstituted {{x}} should not appear)
        assert "{{" not in d["body_html"]
        pytest.contract_id = d["id"]
        pytest.contract_doc = d

    def test_generate_idempotent(self, admin_session, existing_request_id):
        r = admin_session.post(f"{BASE_URL}/api/contracts/generate", json={"request_id": existing_request_id}, timeout=20)
        assert r.status_code == 200
        assert r.json()["id"] == pytest.contract_id

    def test_get_contract_as_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/contracts/{pytest.contract_id}", timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == pytest.contract_id

    def test_by_request_returns_contract(self, admin_session, existing_request_id):
        r = admin_session.get(f"{BASE_URL}/api/contracts/by-request/{existing_request_id}", timeout=10)
        assert r.status_code == 200
        assert r.json().get("contract") is not None
        assert r.json()["contract"]["id"] == pytest.contract_id

    def test_by_request_null_when_missing(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/contracts/by-request/nonexistent_{uuid.uuid4().hex}", timeout=10)
        assert r.status_code == 200
        assert r.json().get("contract") is None

    def test_non_party_cannot_read(self, specialist_session):
        # If the existing request was not assigned to this specialist
        c = pytest.contract_doc
        # Login as a different client via register
        s = requests.Session()
        unique = f"test_nonparty_{uuid.uuid4().hex[:8]}@example.com"
        reg = s.post(f"{BASE_URL}/api/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": unique, "password": "Pass123!", "name": "NonParty", "role": "client"
        }, timeout=15)
        if reg.status_code not in (200, 201):
            pytest.skip(f"register failed: {reg.status_code}")
        r = s.get(f"{BASE_URL}/api/contracts/{pytest.contract_id}", timeout=10)
        assert r.status_code == 403, f"expected 403 for non-party, got {r.status_code}"

    def test_sign_as_client(self, client_session):
        # Verify client is party
        c = pytest.contract_doc
        me = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        if str(me.get("id")) != str(c.get("client_id")):
            pytest.skip("Test client is not the party of the existing request — cannot sign")
        r = client_session.post(f"{BASE_URL}/api/contracts/{pytest.contract_id}/sign",
                                json={"signature_name": "Ion Popescu"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["signed_by_client"] is True

    def test_sign_as_specialist_and_active(self, specialist_session):
        c = pytest.contract_doc
        me = specialist_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        if str(me.get("id")) != str(c.get("specialist_id")):
            pytest.skip("Test specialist is not party — skipping specialist sign")
        r = specialist_session.post(f"{BASE_URL}/api/contracts/{pytest.contract_id}/sign",
                                    json={"signature_name": "Vasile Tehnician"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["signed_by_specialist"] is True
        if d.get("signed_by_client"):
            assert d["status"] == "active"

    def test_operator_resolve_as_admin(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/contracts/{pytest.contract_id}/operator-resolve",
                               json={"resolution": "Rezoluție de test: ambele părți de acord cu medierea."},
                               timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "mediated"
        assert d["operator_resolution"]
