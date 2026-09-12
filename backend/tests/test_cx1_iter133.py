"""Sprint CX-1 iter133 — funnel conversion + phone optional for clients."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")


def _uniq_email(prefix="cx.test"):
    return f"{prefix}.{int(time.time()*1000)}.{os.getpid()}@test.io"


@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- REGISTER ----------

def test_register_client_no_phone_ok(s):
    email = _uniq_email("cx.nophone")
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Testing123!", "name": "CX NoPhone",
        "role": "client", "terms_accepted": True, "privacy_policy_accepted": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("email") == email
    assert data.get("phone", "") in ("", None)


def test_register_client_with_phone_ok(s):
    email = _uniq_email("cx.phone")
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Testing123!", "name": "CX Phone",
        "role": "client", "phone": "0722111222",
        "terms_accepted": True, "privacy_policy_accepted": True,
    })
    assert r.status_code == 200, r.text
    lr = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "Testing123!"})
    token = lr.json().get("access_token") or lr.json().get("token")
    me = s.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"} if token else {})
    assert me.status_code == 200
    phone = me.json().get("phone", "")
    assert "0722111222" in phone or phone.endswith("0722111222")


def test_register_specialist_no_phone_400(s):
    email = _uniq_email("cx.spec.nophone")
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Testing123!", "name": "CX Spec",
        "role": "specialist",
        "terms_accepted": True, "privacy_policy_accepted": True,
    })
    assert r.status_code == 400
    assert "specialist" in r.text.lower() or "obligatoriu" in r.text.lower()


def test_register_client_invalid_phone_400(s):
    email = _uniq_email("cx.badphone")
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Testing123!", "name": "CX Bad",
        "role": "client", "phone": "abc",
        "terms_accepted": True, "privacy_policy_accepted": True,
    })
    assert r.status_code == 400
    assert "invalid" in r.text.lower() or "format" in r.text.lower()


# ---------- CMS PUBLIC ----------

def test_cms_public_new_copy(s):
    r = s.get(f"{BASE_URL}/api/cms/public")
    assert r.status_code == 200
    payload = r.json()
    # Might be nested or flat — flatten
    import json as _j
    txt = _j.dumps(payload, ensure_ascii=False)
    assert "Cartea de service" in txt, "hero.title1 lipsa 'Cartea de service'"
    assert "Creează contul gratuit" in txt, "hero.cta1 lipsa 'Creează contul gratuit'"
    assert "12,842" not in txt and "12.842" not in txt, "cifra fabricată încă prezentă"
    # 14 zile should not be in cta.footer — allow it elsewhere but check cta section if exists
    cta = payload.get("cta") if isinstance(payload, dict) else None
    if cta and isinstance(cta, dict):
        footer = str(cta.get("footer", ""))
        assert "14 zile" not in footer


# ---------- REGRESSION LOGIN ----------

@pytest.mark.parametrize("email,password", [
    ("admin@propmanage.io", "1!nasov01ADMIN"),
    ("client@propmanage.io", "Client123!"),
    ("specialist@propmanage.io", "Spec123!"),
])
def test_login_regression(s, email, password):
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"{email} => {r.status_code} {r.text[:200]}"
