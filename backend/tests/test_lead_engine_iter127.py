"""Growth OS G1 — Lead Engine backend tests (iter 127)."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
if not BASE_URL.startswith("http"):
    BASE_URL = "http://localhost:8001"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ---------- Lead magnet capture ----------

def _payload_health(email):
    return {
        "magnet": "health_score",
        "name": "QA G1",
        "email": email,
        "consent": True,
        "score": 65,
        "risks": ["Instalatie veche", "Umiditate"],
        "answers": {"an": "1990 – 2010", "electric": "Nu"},
    }


def test_lead_magnet_health_score_ok():
    email = f"qa-g1-hs-{int(time.time())}@test.ro"
    r = requests.post(f"{BASE_URL}/api/public/lead-magnet", json=_payload_health(email), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data.get("deduped") is False


def test_lead_magnet_dedupe_same_day():
    email = f"qa-g1-dedup-{int(time.time())}@test.ro"
    r1 = requests.post(f"{BASE_URL}/api/public/lead-magnet", json=_payload_health(email), timeout=15)
    assert r1.status_code == 200
    assert r1.json().get("deduped") is False
    r2 = requests.post(f"{BASE_URL}/api/public/lead-magnet", json=_payload_health(email), timeout=15)
    assert r2.status_code == 200
    assert r2.json().get("deduped") is True


def test_lead_magnet_buying_checklist_ok():
    email = f"qa-g1-bc-{int(time.time())}@test.ro"
    r = requests.post(f"{BASE_URL}/api/public/lead-magnet", json={
        "magnet": "buying_checklist", "name": "QA G1 BC", "email": email, "consent": True,
    }, timeout=15)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_lead_magnet_consent_false_400():
    r = requests.post(f"{BASE_URL}/api/public/lead-magnet", json={
        "magnet": "health_score", "name": "X", "email": "x@test.ro",
        "consent": False, "score": 50,
    }, timeout=15)
    assert r.status_code == 400


def test_lead_magnet_invalid_magnet_400():
    r = requests.post(f"{BASE_URL}/api/public/lead-magnet", json={
        "magnet": "nope", "name": "X", "email": "x@test.ro", "consent": True,
    }, timeout=15)
    assert r.status_code == 400


def test_lead_magnet_invalid_email_400():
    r = requests.post(f"{BASE_URL}/api/public/lead-magnet", json={
        "magnet": "health_score", "name": "X", "email": "not-an-email",
        "consent": True, "score": 50,
    }, timeout=15)
    assert r.status_code == 400


# ---------- Growth funnel ----------

def test_growth_funnel_contains_lead_magnet(admin_session):
    # ensure at least one lead exists in current window
    email = f"qa-g1-funnel-{int(time.time())}@test.ro"
    requests.post(f"{BASE_URL}/api/public/lead-magnet", json=_payload_health(email), timeout=15)

    r = admin_session.get(f"{BASE_URL}/api/admin/growth/funnel?days=30", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "leads_by_source" in data
    assert "lead_magnet" in data["leads_by_source"], f"leads_by_source={data['leads_by_source']}"
    assert data["leads_by_source"]["lead_magnet"] >= 1
    assert "visitors" in data
    assert "ve_orders" in data


# ---------- Sitemap ----------

def test_sitemap_contains_new_slugs():
    r = requests.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=15)
    assert r.status_code == 200
    body = r.text
    for slug in [
        "/scorul-casei",
        "/checklist-cumparare",
        "/ghiduri/audit-tehnic-apartament-pret",
        "/ghiduri/verificare-apartament-inainte-de-cumparare",
        "/ghiduri/ce-este-digital-twin-locuinta",
        "/ghiduri/imobile-verificate-cum-functioneaza",
    ]:
        assert slug in body, f"Missing slug in sitemap: {slug}"


# ---------- Regression ----------

def test_admin_war_room_still_works(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/war-room", timeout=15)
    assert r.status_code == 200, r.text
