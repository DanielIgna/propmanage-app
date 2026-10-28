"""Rădăcini — vizibilitatea scorului de transparență per asociație (DPIA R6).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_score_visibility.py -q --noconftest

Partea fără server verifică regula direct pe funcții; partea HTTP se sare dacă backend-ul nu e pornit.
Asociația de test are numele „TEST-RAD-…” (o curăță `scripts.radacini_purge_demo --tests-only`).
"""
import os
import uuid

import pytest
import requests

from routes.radacini.assoc_core import DEFAULT_RULES, _check_rules, _public_view, score_visible

API = f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')}/api"
R = f"{API}/radacini"
TIMEOUT = 20
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))


# ---------- fără server ----------
def test_default_is_public():
    assert DEFAULT_RULES["score_visibility"] == "public"
    assoc = {"_id": "a1", "rules": {}, "transparency_cache": {"score": 80}}
    assert score_visible(assoc, None) is True
    assert _public_view(assoc, 3)["transparency_score"] == 80


def test_members_only_hides_score_for_outsiders():
    assoc = {"_id": "a1", "rules": {"score_visibility": "members"}, "transparency_cache": {"score": 80}}
    for role in (None, "claimant"):
        assert score_visible(assoc, role) is False
    for role in ("member", "council", "censor", "operator", "manager"):
        assert score_visible(assoc, role) is True
    view = _public_view(assoc, 3, score_visible(assoc, None))
    assert view["transparency_score"] is None and view["score_visible"] is False


def test_rule_value_validated():
    assert _check_rules({"score_visibility": "members"}) == {"score_visibility": "members"}
    for bad in ("toti", 1, None):
        with pytest.raises(ValueError):
            _check_rules({"score_visibility": bad})


# ---------- HTTP (backend pornit) ----------
def _backend_up() -> bool:
    try:
        return requests.get(f"{API}/health", timeout=3).status_code < 500
    except requests.RequestException:
        return False


def _login(email, passwords):
    s = requests.Session()
    for pwd in passwords:
        if s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT).status_code == 200:
            for d in requests.get(f"{R}/legal/documents", timeout=TIMEOUT).json()["items"]:
                s.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)
            return s
    pytest.skip(f"Login failed for {email}")


@pytest.mark.skipif(not _backend_up(), reason="backend-ul nu e pornit")
def test_http_members_only():
    admin = _login(ADMIN_EMAIL, ADMIN_PASSWORDS)
    client = _login("client@propmanage.io", ["Client123!"])
    r = admin.post(f"{R}/assoc", json={"name": f"TEST-RAD-SCOR {uuid.uuid4().hex[:6]}", "type": "composesorat",
                                       "localities": ["Test"], "description": "test", "legal": {}, "patrimony": []},
                   timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    aid = r.json().get("id") or r.json()["association"]["id"]
    anon = requests.Session()
    # implicit public: oricine vede scorul
    assert anon.get(f"{R}/assoc/{aid}/transparency", timeout=TIMEOUT).status_code == 200
    assert admin.patch(f"{R}/assoc/{aid}", json={"rules": {"score_visibility": "toti"}}, timeout=TIMEOUT).status_code in (400, 422)
    r = admin.patch(f"{R}/assoc/{aid}", json={"rules": {"score_visibility": "members"}}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    # străinii (anonim sau cont fără legătură) nu-l mai văd
    for s in (anon, client):
        assert s.get(f"{R}/assoc/{aid}/transparency", timeout=TIMEOUT).status_code == 403
        a = s.get(f"{R}/assoc/{aid}", timeout=TIMEOUT).json()["association"]
        assert a["transparency_score"] is None and a["score_visible"] is False
    listed = [a for a in anon.get(f"{R}/assoc", timeout=TIMEOUT).json()["items"] if a["id"] == aid]
    assert listed and listed[0]["transparency_score"] is None
    # managerul îl vede în continuare
    assert admin.get(f"{R}/assoc/{aid}/transparency", timeout=TIMEOUT).status_code == 200
    assert admin.get(f"{R}/assoc/{aid}", timeout=TIMEOUT).json()["association"]["score_visible"] is True
