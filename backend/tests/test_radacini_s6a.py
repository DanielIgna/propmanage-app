"""Rădăcini S6-A/B/C — teste HTTP: comunități, gospodării + consimțământ, decizii.

Run (backend pornit cu RADACINI_ENABLED=true și routerele S6 incluse):
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s6a.py -q --noconftest
client = coordonator / titular, specialist = membru / invitat, admin = membru terț (nu e în comunitate).
Totul poartă eticheta TEST-RAD-<hex>; comunitatea și gospodăria de test sunt șterse la final.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT = ("client@propmanage.io", ["Client123!"])
SPECIALIST = ("specialist@propmanage.io", ["Spec123!"])
SPECIALIST_EMAIL = SPECIALIST[0]

R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20
ZERO_ID = "0" * 24
S = {}


def _login(email, passwords):
    s = requests.Session()
    last = None
    for pwd in passwords:
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT)
        last = r.status_code
        if r.status_code == 200:
            return s
    pytest.skip(f"Login failed for {email} (last={last})")


def _err(r, code):
    assert r.status_code == code, f"expected {code}, got {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json().get("detail"), str), r.text[:300]


def _uid(session):
    r = session.get(f"{R}/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _future(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(scope="module")
def client():
    return _login(*CLIENT)


@pytest.fixture(scope="module")
def specialist():
    return _login(*SPECIALIST)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, specialist, admin):
    yield
    cid = S.get("closed_id")
    if cid:
        specialist.post(f"{R}/communities/{cid}/leave", timeout=TIMEOUT)
        client.delete(f"{R}/communities/{cid}", timeout=TIMEOUT)
    oid = S.get("open_id")
    if oid:
        for s in (specialist, admin):
            s.post(f"{R}/communities/{oid}/leave", timeout=TIMEOUT)
        client.delete(f"{R}/communities/{oid}", timeout=TIMEOUT)
    hid = S.get("household_id")
    if hid:
        client.delete(f"{R}/households/{hid}", timeout=TIMEOUT)


def _community_body(**over):
    b = {"name": f"{TAG} comunitate", "locality": "Florești", "description": "test", "visibility": "open"}
    b.update(over)
    return b


# ── A. comunități ────────────────────────────────────────────────────────────

class TestCommunities:
    def test_anonymous_401(self):
        assert requests.get(f"{R}/communities", timeout=TIMEOUT).status_code == 401

    def test_validation_400(self, client):
        _err(client.post(f"{R}/communities", json=_community_body(name="ab"), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/communities", json=_community_body(locality="Paris"), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/communities", json=_community_body(visibility="x"), timeout=TIMEOUT), 400)

    def test_create_open_and_closed(self, client):
        r = client.post(f"{R}/communities", json=_community_body(), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        c = r.json()["community"]
        assert c["my_role"] == "coordinator" and c["members_count"] == 1
        S["open_id"] = c["id"]
        r = client.post(f"{R}/communities", json=_community_body(name=f"{TAG} închisă", visibility="closed"), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        S["closed_id"] = r.json()["community"]["id"]

    def test_list_filter(self, specialist):
        r = specialist.get(f"{R}/communities", params={"q": TAG}, timeout=TIMEOUT)
        assert r.status_code == 200
        ids = {c["id"]: c for c in r.json()["items"]}
        assert S["open_id"] in ids and ids[S["open_id"]]["my_role"] is None

    def test_join_open_active(self, specialist):
        r = specialist.post(f"{R}/communities/{S['open_id']}/join", timeout=TIMEOUT)
        assert r.status_code == 200 and r.json()["status"] == "active"
        _err(specialist.post(f"{R}/communities/{S['open_id']}/join", timeout=TIMEOUT), 409)
        c = specialist.get(f"{R}/communities/{S['open_id']}", timeout=TIMEOUT).json()["community"]
        assert c["members_count"] == 2 and c["my_role"] == "member"

    def test_closed_pending_approve(self, client, specialist):
        cid = S["closed_id"]
        r = specialist.post(f"{R}/communities/{cid}/join", timeout=TIMEOUT)
        assert r.status_code == 200 and r.json()["status"] == "pending"
        _err(specialist.get(f"{R}/communities/{cid}/posts", timeout=TIMEOUT), 403)
        uid = _uid(specialist)
        _err(specialist.post(f"{R}/communities/{cid}/members/{uid}/approve", timeout=TIMEOUT), 403)
        d = client.get(f"{R}/communities/{cid}", timeout=TIMEOUT).json()
        assert [p["user_id"] for p in d["pending"]] == [uid]
        assert client.post(f"{R}/communities/{cid}/members/{uid}/approve", timeout=TIMEOUT).status_code == 200
        _err(client.post(f"{R}/communities/{cid}/members/{uid}/approve", timeout=TIMEOUT), 409)
        c = client.get(f"{R}/communities/{cid}", timeout=TIMEOUT).json()["community"]
        assert c["members_count"] == 2
        assert specialist.get(f"{R}/communities/{cid}/posts", timeout=TIMEOUT).status_code == 200

    def test_reject_pending(self, client, admin):
        cid = S["closed_id"]
        assert admin.post(f"{R}/communities/{cid}/join", timeout=TIMEOUT).json()["status"] == "pending"
        uid = _uid(admin)
        assert client.post(f"{R}/communities/{cid}/members/{uid}/reject", timeout=TIMEOUT).status_code == 200
        _err(client.post(f"{R}/communities/{cid}/members/{uid}/reject", timeout=TIMEOUT), 404)

    def test_leave_last_coordinator_409(self, client):
        _err(client.post(f"{R}/communities/{S['open_id']}/leave", timeout=TIMEOUT), 409)

    def test_promote_then_leave(self, client, specialist):
        cid = S["closed_id"]
        uid = _uid(specialist)
        _err(specialist.post(f"{R}/communities/{cid}/members/{uid}/promote", timeout=TIMEOUT), 403)
        assert client.post(f"{R}/communities/{cid}/members/{uid}/promote", timeout=TIMEOUT).status_code == 200
        _err(client.post(f"{R}/communities/{cid}/members/{uid}/promote", timeout=TIMEOUT), 409)
        assert client.post(f"{R}/communities/{cid}/leave", timeout=TIMEOUT).status_code == 200
        assert client.post(f"{R}/communities/{cid}/join", timeout=TIMEOUT).status_code == 200  # re-intră (pending)
        assert specialist.post(f"{R}/communities/{cid}/members/{_uid(client)}/approve", timeout=TIMEOUT).status_code == 200
        # revenim: specialistul pleacă (acum client e doar membru → clientul rămâne fără coordonator, deci readucem)
        assert specialist.post(f"{R}/communities/{cid}/members/{_uid(client)}/promote", timeout=TIMEOUT).status_code == 200
        assert specialist.post(f"{R}/communities/{cid}/leave", timeout=TIMEOUT).status_code == 200
        c = client.get(f"{R}/communities/{cid}", timeout=TIMEOUT).json()["community"]
        assert c["members_count"] == 1 and c["my_role"] == "coordinator"
        S["closed_specialist_left"] = True

    def test_posts(self, client, specialist, admin):
        oid = S["open_id"]
        _err(admin.get(f"{R}/communities/{oid}/posts", timeout=TIMEOUT), 403)
        _err(admin.post(f"{R}/communities/{oid}/posts", json={"text": "x"}, timeout=TIMEOUT), 403)
        _err(specialist.post(f"{R}/communities/{oid}/posts", json={"text": ""}, timeout=TIMEOUT), 400)
        _err(specialist.post(f"{R}/communities/{oid}/posts", json={"text": "fix", "pinned": True}, timeout=TIMEOUT), 403)
        p1 = specialist.post(f"{R}/communities/{oid}/posts", json={"text": f"{TAG} unu"}, timeout=TIMEOUT).json()["post"]
        p2 = client.post(f"{R}/communities/{oid}/posts", json={"text": f"{TAG} doi", "pinned": True}, timeout=TIMEOUT).json()["post"]
        assert p2["pinned"] is True
        # fixarea altuia mută pinul (max 1)
        assert client.post(f"{R}/posts/{p1['id']}/pin", json={"pinned": True}, timeout=TIMEOUT).status_code == 200
        items = specialist.get(f"{R}/communities/{oid}/posts", timeout=TIMEOUT).json()["items"]
        assert items[0]["id"] == p1["id"] and sum(1 for i in items if i["pinned"]) == 1
        _err(specialist.delete(f"{R}/posts/{p2['id']}", timeout=TIMEOUT), 403)
        assert client.delete(f"{R}/posts/{p1['id']}", timeout=TIMEOUT).status_code == 200  # coordonator
        assert specialist.delete(f"{R}/posts/{p2['id']}", timeout=TIMEOUT).status_code == 403
        assert client.delete(f"{R}/posts/{p2['id']}", timeout=TIMEOUT).status_code == 200


# ── B. gospodării ────────────────────────────────────────────────────────────

class TestHouseholds:
    def test_create(self, client):
        mine = client.get(f"{R}/households/mine", timeout=TIMEOUT).json()
        if mine["household"]:
            if not mine["household"]["name"].startswith("TEST-RAD"):
                pytest.skip("Contul client are o gospodărie reală; testul nu o atinge.")
            client.delete(f"{R}/households/{mine['household']['id']}", timeout=TIMEOUT)
        _err(client.post(f"{R}/households", json={"name": "x"}, timeout=TIMEOUT), 400)
        r = client.post(f"{R}/households", json={"name": f"{TAG} familie"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        S["household_id"] = r.json()["household"]["id"]
        _err(client.post(f"{R}/households", json={"name": f"{TAG} alta"}, timeout=TIMEOUT), 409)

    def test_minor_needs_consent(self, client):
        hid = S["household_id"]
        body = {"relation": "fiu", "first_name": "Andrei", "birth_year": 2015}
        _err(client.post(f"{R}/households/{hid}/members", json=body, timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/households/{hid}/members", json={**body, "parental_consent": False}, timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/households/{hid}/members", json={**body, "parental_consent": True, "birth_year": 1850}, timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/households/{hid}/members", json={**body, "parental_consent": True, "first_name": "Ana Maria"}, timeout=TIMEOUT), 400)

    def test_minor_with_consent(self, client):
        hid = S["household_id"]
        r = client.post(f"{R}/households/{hid}/members",
                        json={"relation": "fiu", "first_name": "Andrei", "birth_year": 2015, "parental_consent": True},
                        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        minors = [m for m in r.json()["household"]["members"] if m["is_minor"]]
        assert len(minors) == 1 and minors[0]["birth_year"] == 2015 and "user_id" not in minors[0]
        exp = client.get(f"{R}/me/export", timeout=TIMEOUT).json()
        consents = [c for c in exp["consents"] if c.get("household_id") == hid]
        assert consents and consents[0]["kind"] == "minor_data" and consents[0]["version"] == "2026-10"
        assert consents[0]["subject_name"] == "Andrei" and consents[0]["ip"] and len(consents[0]["user_agent"]) <= 300
        assert any(h["id"] == hid for h in exp["households"])

    def test_remove_minor_by_index(self, client):
        hid = S["household_id"]
        h = client.get(f"{R}/households/mine", timeout=TIMEOUT).json()["household"]
        idx = next(i for i, m in enumerate(h["members"]) if m["is_minor"])
        r = client.delete(f"{R}/households/{hid}/members/{idx}", timeout=TIMEOUT)
        assert r.status_code == 200 and not any(m["is_minor"] for m in r.json()["household"]["members"])
        _err(client.delete(f"{R}/households/{hid}/members/0", timeout=TIMEOUT), 409)  # titularul

    def test_adult_invite_accept(self, client, specialist):
        hid = S["household_id"]
        _err(client.post(f"{R}/households/{hid}/members", json={"relation": "x", "email": "nimeni-test@example.invalid"}, timeout=TIMEOUT), 404)
        _err(specialist.post(f"{R}/households/{hid}/members", json={"relation": "x", "email": SPECIALIST_EMAIL}, timeout=TIMEOUT), 403)
        r = client.post(f"{R}/households/{hid}/members", json={"relation": "partener", "email": SPECIALIST_EMAIL}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert [m["status"] for m in r.json()["household"]["members"] if m.get("user_id")][-1] == "pending"
        _err(client.post(f"{R}/households/{hid}/members", json={"relation": "partener", "email": SPECIALIST_EMAIL}, timeout=TIMEOUT), 409)
        inv = specialist.get(f"{R}/households/mine", timeout=TIMEOUT).json()
        assert any(i["household_id"] == hid for i in inv["invitations"])
        _err(client.post(f"{R}/households/{hid}/accept", timeout=TIMEOUT), 404)  # titularul nu are invitație
        r = specialist.post(f"{R}/households/{hid}/accept", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        mine = specialist.get(f"{R}/households/mine", timeout=TIMEOUT).json()
        assert mine["household"]["id"] == hid and not mine["invitations"]
        _err(specialist.post(f"{R}/households/{hid}/accept", timeout=TIMEOUT), 404)
        # ieșire proprie
        uid = _uid(specialist)
        assert specialist.delete(f"{R}/households/{hid}/members/{uid}", timeout=TIMEOUT).status_code == 200


# ── C. decizii ───────────────────────────────────────────────────────────────

class TestDecisions:
    def _body(self, **over):
        b = {"scope": "community", "scope_id": S["open_id"], "question": f"{TAG} ce plantăm?",
             "options": ["Roșii", "Castraveți"], "closes_at": _future()}
        b.update(over)
        return b

    def test_create_validation_and_perms(self, client, specialist):
        _err(specialist.post(f"{R}/decisions", json=self._body(), timeout=TIMEOUT), 403)
        _err(client.post(f"{R}/decisions", json=self._body(options=["unu"]), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/decisions", json=self._body(options=["a", "a"]), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/decisions", json=self._body(question="abc"), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/decisions", json=self._body(closes_at=_future(-1)), timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/decisions", json=self._body(scope="project", scope_id=ZERO_ID), timeout=TIMEOUT), 403)
        r = client.post(f"{R}/decisions", json=self._body(), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()["decision"]
        assert d["status"] == "open" and d["results"] is None and "votes" not in d
        S["decision_id"] = d["id"]

    def test_vote_flow(self, client, specialist, admin):
        did = S["decision_id"]
        r = specialist.get(f"{R}/decisions", params={"scope": "community", "scope_id": S["open_id"]}, timeout=TIMEOUT)
        d = next(x for x in r.json()["items"] if x["id"] == did)
        assert d["results"] is None and d["my_vote"] is None  # rezultate ascunse înainte de vot
        _err(admin.get(f"{R}/decisions", params={"scope": "community", "scope_id": S["open_id"]}, timeout=TIMEOUT), 403)
        _err(admin.post(f"{R}/decisions/{did}/vote", json={"option_index": 0}, timeout=TIMEOUT), 403)
        _err(specialist.post(f"{R}/decisions/{did}/vote", json={"option_index": 5}, timeout=TIMEOUT), 400)
        r = specialist.post(f"{R}/decisions/{did}/vote", json={"option_index": 1}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()["decision"]
        assert d["my_vote"] == 1 and d["results"] == [0, 1]
        _err(specialist.post(f"{R}/decisions/{did}/vote", json={"option_index": 0}, timeout=TIMEOUT), 409)

    def test_close_only_creator(self, client, specialist):
        did = S["decision_id"]
        _err(specialist.post(f"{R}/decisions/{did}/close", timeout=TIMEOUT), 403)
        r = client.post(f"{R}/decisions/{did}/close", timeout=TIMEOUT)
        assert r.status_code == 200 and r.json()["decision"]["results"] == [0, 1]
        _err(client.post(f"{R}/decisions/{did}/close", timeout=TIMEOUT), 409)
        _err(client.post(f"{R}/decisions/{did}/vote", json={"option_index": 0}, timeout=TIMEOUT), 409)
