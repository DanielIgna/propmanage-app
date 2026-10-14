"""Rădăcini runda 2 (partea A2) — teste: export GDPR, cerere de ștergere, rate limit public, notificări, audit.

Run against a live backend (RADACINI_ENABLED=true):
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_r2.py -q --noconftest

Roles: client = parcel owner, specialist = requester (și cel care cere ștergerea), admin = super-admin.
Everything carries a unique TEST-RAD-<hex> tag; the published parcel is archived at teardown. Deletion
requests left behind (they are is_demo when the server runs with RADACINI_MARK_DEMO=true) are removed by
`backend/scripts/radacini_purge_demo.py --tests-only --apply`.

Rate-limit test: it uses its own X-Forwarded-For address (the server takes the LAST element, added by the proxy),
so it does not exhaust the bucket of the other tests. It assumes the server's default limit
(RADACINI_PUBLIC_RATE_LIMIT_PER_MIN, default 60); set the same variable for the test process if you changed it.
It is skipped when RADACINI_RATE_LIMIT_PROXY_HOPS != 1 (it could not isolate its bucket).
"""
import asyncio
import os
import random
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests

# Independent of tests/test_config.py (its isolation gate targets the legacy Mongo suite).
# Run with --noconftest.
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT_EMAIL, CLIENT_PASSWORD = "client@propmanage.io", "Client123!"
SPECIALIST_EMAIL, SPECIALIST_PASSWORD = "specialist@propmanage.io", "Spec123!"

BACKEND_DIR = Path(__file__).resolve().parents[1]
R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20
FLORESTI = "Florești"
LAT, LNG = 46.7712, 23.6236

S = {}
_created_ids = []


# ── helpers ──────────────────────────────────────────────────────────────────

def _accept_terms(s):
    """Termenii Rădăcini (S8) sunt obligatorii pentru acțiuni: contul de test îi acceptă pe cei curenți."""
    docs = s.get(f"{API}/radacini/legal/documents", timeout=TIMEOUT).json().get("items", [])
    for d in docs:
        s.post(f"{API}/radacini/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)


def _login(email, passwords):
    s = requests.Session()
    last = None
    for pwd in passwords:
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT)
        last = r.status_code
        if r.status_code == 200:
            _accept_terms(s)
            return s
    pytest.skip(f"Login failed for {email} (last={last})")


def _unwrap(data, key):
    if isinstance(data, dict) and isinstance(data.get(key), dict):
        return data[key]
    return data


def _err(r, code):
    assert r.status_code == code, f"expected {code}, got {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json().get("detail"), str), r.text[:300]


def _d(days):
    return (datetime.now(ZoneInfo("Europe/Bucharest")).date() + timedelta(days=days)).isoformat()


def _ensure_member(session, interests, locality):
    r = session.put(
        f"{R}/members/me",
        json={"interests": interests, "county": "Cluj", "locality": locality},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text


def _my_user_id(session):
    r = session.get(f"{R}/members/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["member"]["user_id"]


def _export(session):
    r = session.get(f"{R}/me/export", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r


def _ids(items):
    return {x["id"] for x in items}


def _impersonate(target_uid):
    s = _login(ADMIN_EMAIL, ADMIN_PASSWORDS)
    r = s.post(
        f"{API}/admin/impersonate",
        json={"user_id": target_uid, "reason": "test Radacini: GDPR in impersonare"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip(f"impersonation unavailable in this environment ({r.status_code})")
    return s


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def anon():
    return requests.Session()


@pytest.fixture(scope="module")
def client():
    return _login(CLIENT_EMAIL, [CLIENT_PASSWORD])


@pytest.fixture(scope="module")
def specialist():
    return _login(SPECIALIST_EMAIL, [SPECIALIST_PASSWORD])


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module")
def _members(client, specialist):
    _ensure_member(client, ["land", "consume"], FLORESTI)
    _ensure_member(specialist, ["grow", "sell"], FLORESTI)
    S["client_uid"] = _my_user_id(client)
    S["specialist_uid"] = _my_user_id(specialist)


@pytest.fixture(scope="module")
def _cleanup(client, admin, _members):
    yield
    for pid in _created_ids:
        try:
            client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass


# ── 1. export GDPR ───────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestExportSetup:
    def test_publish_parcel_request_and_message(self, client, specialist, admin):
        payload = {
            "title": f"{TAG} teren R2",
            "county": "Cluj",
            "locality": FLORESTI,
            "lat": LAT,
            "lng": LNG,
            "area_m2": 5000,
            "access": "Drum de pământ, acces auto",
            "water_sources": ["well"],
            "current_crops": ["porumb"],
            "description": "Teren de test pentru GDPR.",
            "offer": {"models": ["rent"], "terms": "Termeni de test", "price_ron_per_year": 1200},
        }
        r = client.post(f"{R}/parcels", json=payload, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["pid"] = _unwrap(r.json(), "parcel")["id"]
        _created_ids.append(S["pid"])
        assert client.post(f"{R}/parcels/{S['pid']}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{S['pid']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text

        body = {
            "model": "rent", "area_m2": 1000, "start_date": _d(10), "end_date": _d(375),
            "price_ron_per_year": 1000, "crops": ["porumb"], "note": f"{TAG} cerere",
        }
        r = specialist.post(f"{R}/parcels/{S['pid']}/requests", json=body, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["rid"] = _unwrap(r.json(), "request")["id"]
        S["msg"] = f"{TAG} mesaj"
        r = specialist.post(f"{R}/requests/{S['rid']}/messages", json={"text": S["msg"]}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text


@pytest.mark.usefixtures("_members", "_cleanup")
class TestExport:
    def test_requires_auth(self, anon):
        _err(anon.get(f"{R}/me/export", timeout=TIMEOUT), 401)

    def test_owner_export(self, client):
        r = _export(client)
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.headers.get("cache-control") == "no-store"
        d = r.json()
        assert d["account"]["id"] == S["client_uid"]
        assert d["member"]["user_id"] == S["client_uid"]
        assert S["pid"] in _ids(d["parcels"])
        assert S["rid"] in _ids(d["requests_received"])
        assert S["rid"] not in _ids(d["requests_sent"])
        # mesajul e scris de cealaltă parte: nu intră în exportul proprietarului
        assert all(m.get("sender_user_id") == S["client_uid"] for m in d["messages_authored"])
        assert S["msg"] not in {m.get("text") for m in d["messages_authored"]}
        assert d["truncated"] == []
        for key in ("agreements", "projects", "contributions", "allocations", "listings",
                    "reservations_as_buyer", "reservations_as_seller", "location_access_log",
                    "deletion_requests", "notes"):
            assert isinstance(d[key], list), key

    def test_requester_export(self, specialist):
        d = _export(specialist).json()
        assert d["account"]["id"] == S["specialist_uid"]
        assert S["rid"] in _ids(d["requests_sent"])
        assert S["pid"] not in _ids(d["parcels"]), "terenul altcuiva nu apare în export"
        assert S["rid"] not in _ids(d["requests_received"])
        mine = [m for m in d["messages_authored"] if m["request_id"] == S["rid"]]
        assert [m["text"] for m in mine] == [S["msg"]]
        assert all(m["sender_user_id"] == S["specialist_uid"] for m in d["messages_authored"])

    def test_no_secrets_in_export(self, specialist):
        text = _export(specialist).text.lower()
        assert "password" not in text

    def test_export_allowed_in_impersonation(self):
        s = _impersonate(S["client_uid"])
        try:
            d = _export(s).json()
            assert d["account"]["id"] == S["client_uid"]
            assert S["pid"] in _ids(d["parcels"])
        finally:
            s.post(f"{API}/admin/stop-impersonation", timeout=TIMEOUT)


# ── 2. cerere de ștergere ────────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestDeleteRequest:
    def test_requires_auth(self, anon):
        _err(anon.post(f"{R}/me/delete-request", timeout=TIMEOUT), 401)
        _err(anon.get(f"{R}/me/delete-request", timeout=TIMEOUT), 401)

    def test_blocked_in_impersonation(self):
        s = _impersonate(S["specialist_uid"])
        try:
            r = s.post(f"{R}/me/delete-request", timeout=TIMEOUT)
            _err(r, 403)
            assert "impersonare" in r.json()["detail"]
        finally:
            s.post(f"{API}/admin/stop-impersonation", timeout=TIMEOUT)

    def test_create_then_duplicate_409(self, specialist):
        before = specialist.get(f"{R}/me/delete-request", timeout=TIMEOUT)
        assert before.status_code == 200, before.text
        already = (before.json().get("request") or {}).get("status") == "pending"  # rămas dintr-o rulare anterioară
        first = specialist.post(f"{R}/me/delete-request", timeout=TIMEOUT)
        if already:
            _err(first, 409)
        else:
            assert first.status_code == 200, first.text
            req = first.json()["request"]
            assert req["status"] == "pending" and req["user_id"] == S["specialist_uid"] and req["at"]
        _err(specialist.post(f"{R}/me/delete-request", timeout=TIMEOUT), 409)

    def test_status_and_export_show_request(self, specialist):
        cur = specialist.get(f"{R}/me/delete-request", timeout=TIMEOUT).json()["request"]
        assert cur["status"] == "pending" and cur["user_id"] == S["specialist_uid"]
        d = _export(specialist).json()
        assert cur["id"] in _ids(d["deletion_requests"])


# ── 3. rate limit public ─────────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestPublicRateLimit:
    def test_anonymous_meta_returns_429_after_limit(self, client):
        if os.environ.get("RADACINI_RATE_LIMIT_PROXY_HOPS", "1") != "1":
            pytest.skip("test izolat prin X-Forwarded-For; cere RADACINI_RATE_LIMIT_PROXY_HOPS=1")
        limit = int(os.environ.get("RADACINI_PUBLIC_RATE_LIMIT_PER_MIN", "60"))
        if limit <= 0 or limit > 300:
            pytest.skip("limita publică e dezactivată sau prea mare pentru un test rapid")
        ip = f"198.51.100.{random.randint(1, 254)}"
        headers = {"X-Forwarded-For": f"203.0.113.77, {ip}"}  # stânga e ignorat, contează ultimul element
        s = requests.Session()
        codes = [s.get(f"{R}/meta", headers=headers, timeout=TIMEOUT).status_code for _ in range(limit + 3)]
        assert codes[:limit] == [200] * limit, codes
        assert codes[limit:] == [429] * 3, codes
        r = s.get(f"{R}/meta", headers=headers, timeout=TIMEOUT)
        _err(r, 429)
        assert r.headers.get("retry-after") == "60"
        # aceeași limită pentru lista publică de terenuri (același coș); IP-ul din stânga nu ocolește limita
        spoof = {"X-Forwarded-For": f"8.8.8.8, {ip}"}
        assert s.get(f"{R}/parcels", headers=spoof, timeout=TIMEOUT).status_code == 429
        # alt IP: neafectat
        other = {"X-Forwarded-For": f"198.51.100.{(int(ip.rsplit('.', 1)[1]) % 254) + 1}"}
        assert s.get(f"{R}/meta", headers=other, timeout=TIMEOUT).status_code == 200
        # un utilizator autentificat de la același IP are coș separat și nu e blocat
        assert client.get(f"{R}/meta", headers=headers, timeout=TIMEOUT).status_code == 200


# ── 4. flag implicit oprit ───────────────────────────────────────────────────

class TestFlagDefaultOff:
    def test_default_is_disabled(self):
        env = {k: v for k, v in os.environ.items() if k != "RADACINI_ENABLED"}
        code = "import routes.radacini.api as a; print('ENABLED=' + str(a.RADACINI_ENABLED))"
        out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True,
                             text=True, timeout=120)
        assert "ENABLED=False" in out.stdout, out.stdout[-300:] + out.stderr[-300:]
        env["RADACINI_ENABLED"] = "true"
        out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True,
                             text=True, timeout=120)
        assert "ENABLED=True" in out.stdout, out.stdout[-300:] + out.stderr[-300:]


# ── 5. notificări și audit (unitare, fără server) ────────────────────────────

@pytest.fixture
def modules():
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from routes.radacini import common, notifications
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"modulele backend nu se pot importa aici: {exc}")
    return common, notifications


class _FakeColl:
    def __init__(self, doc=None):
        self.doc, self.inserted, self.projection = doc, [], None

    async def insert_one(self, doc):
        self.inserted.append(doc)

    async def find_one(self, flt, projection=None):
        self.projection = projection
        return self.doc


class _FakeDb:
    def __init__(self, user):
        self.notifications, self.users = _FakeColl(), _FakeColl(user)


UID = "a" * 24


class TestNotifications:
    def test_email_is_branded_escaped_and_absolute(self, modules, monkeypatch):
        _, notif = modules
        monkeypatch.setenv("RADACINI_PUBLIC_URL", "https://radacini.example.test/")
        sent, pushed = [], []
        fake = _FakeDb({"email": "x@example.test"})

        async def fake_send(to, subject, html, plain=None, **kw):
            sent.append((to, subject, html, plain))

        async def fake_push(*a):
            pushed.append(a)

        monkeypatch.setattr(notif, "db", fake)
        monkeypatch.setattr(notif, "send_email", fake_send)
        monkeypatch.setattr(notif, "send_web_push", fake_push)

        async def run():
            await notif.radacini_notify(UID, "Teren <b>nou</b>", "Salut & <script>x</script>", "/radacini/terenurile-mele")
            await asyncio.sleep(0)  # lasă task-ul de push să ruleze

        asyncio.run(run())
        n = fake.notifications.inserted[0]
        assert n["user_id"] == UID and n["read"] is False and n["link"] == "/radacini/terenurile-mele"
        assert {"title", "message", "type", "created_at"} <= set(n)
        assert fake.users.projection == {"email": 1, "is_demo_account": 1}
        (to, subject, html, plain), = sent
        assert to == "x@example.test" and subject == "Rădăcini: Teren <b>nou</b>"
        assert "&lt;b&gt;nou&lt;/b&gt;" in html and "<script>" not in html and "&amp;" in html
        assert 'href="https://radacini.example.test/radacini/terenurile-mele"' in html
        assert "https://radacini.example.test/radacini/terenurile-mele" in plain
        assert "PropManage" not in subject and "PropManage" not in html
        assert pushed and pushed[0][0] == UID and pushed[0][1].startswith("Rădăcini: ")

    def test_no_base_url_omits_link_and_rejects_external_links(self, modules, monkeypatch):
        _, notif = modules
        for var in ("RADACINI_PUBLIC_URL", "APP_PUBLIC_URL", "FRONTEND_PUBLIC_URL", "FRONTEND_URL"):
            monkeypatch.delenv(var, raising=False)
        html, _ = notif.build_email("T", "M", "/radacini/x")
        assert "href" not in html
        monkeypatch.setenv("RADACINI_PUBLIC_URL", "https://radacini.example.test")
        for bad in ("https://evil.example", "//evil.example", 'javascript:alert(1)', '/x" onclick="y', None):
            assert "href" not in notif.build_email("T", "M", bad)[0], bad

    def test_demo_accounts_get_no_email(self, modules, monkeypatch):
        _, notif = modules
        sent = []
        fake = _FakeDb({"email": "p@test.radacini.ro", "is_demo_account": True})

        async def fake_send(*a, **kw):
            sent.append(a)

        async def fake_push(*a):
            pass

        monkeypatch.setattr(notif, "db", fake)
        monkeypatch.setattr(notif, "send_email", fake_send)
        monkeypatch.setattr(notif, "send_web_push", fake_push)
        asyncio.run(notif.radacini_notify(UID, "T", "M", None))
        assert fake.notifications.inserted and not sent

    def test_safe_notify_goes_through_radacini_notify(self, modules, monkeypatch):
        common, _ = modules
        calls = []

        async def fake_notify(user_id, title, message, link=None, type_="info"):
            calls.append((user_id, title, message, link, type_))

        monkeypatch.setattr(common, "radacini_notify", fake_notify)

        async def run():
            await common.safe_notify(UID, "  Titlu <i>lung</i>\n", "Mesaj <b>x</b>", "/radacini/a", type_="verification")
            await asyncio.gather(*list(common._BG_TASKS))

        asyncio.run(run())
        assert calls == [(UID, "Titlu ‹i›lung‹/i›", "Mesaj ‹b›x‹/b›", "/radacini/a", "verification")]


class TestAudit:
    def test_audit_staff_calls_admin_audit_and_never_raises(self, modules, monkeypatch):
        common, _ = modules
        seen = []

        async def ok(action, actor, target=None, before=None, after=None, note=None):
            seen.append((action, actor["id"], target, after, note))

        monkeypatch.setattr(common, "admin_audit", ok)
        user = {"id": "u1", "email": "m@example.test", "name": "M"}
        asyncio.run(common.audit_staff(user, "parcel.approve", "radacini_parcel", "p1", {"note": "ok"}))
        asyncio.run(common.audit_staff(
            {**user, "impersonation": {"admin_id": "adm", "admin_email": "a@example.test", "log_id": "l"}},
            "radacini.staff.add", "radacini_staff", None))
        assert seen[0] == ("radacini.parcel.approve", "u1", {"type": "radacini_parcel", "id": "p1"}, {"note": "ok"}, None)
        assert seen[1][0] == "radacini.staff.add" and seen[1][2]["id"] is None
        assert seen[1][3]["impersonated_by"]["admin_id"] == "adm" and seen[1][4]

        async def boom(*a, **kw):
            raise RuntimeError("db down")

        monkeypatch.setattr(common, "admin_audit", boom)
        asyncio.run(common.audit_staff(user, "x", "t", "1"))  # nu aruncă
