"""Rădăcini S5 — teste de integrare HTTP pentru administrare (contract: docs/radacini/PLAN.md, "S5 — contract").

Run against a live backend (RADACINI_ENABLED=true):
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s5.py -q --noconftest

Roles: admin = super-admin (tratat ca manager), client = vânzător / proprietar / cel care cere ștergerea,
specialist = cumpărător (nu e personal). Everything carries a unique TEST-RAD-<hex> tag (produsul anunțului,
titlul terenului); terenul de test e arhivat și anunțul închis la final. Cererile de ștergere create de test
sunt rezolvate chiar în test (nu rămâne nicio cerere `pending`). Rutele de administrare cer rolul `manager`.
"""
import os
import uuid
from datetime import datetime, timedelta
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

R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20
FLORESTI = "Florești"
LAT, LNG = 46.7712, 23.6236
ZERO_ID = "0" * 24

S = {}


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


def _get(admin, path, **params):
    return admin.get(f"{R}{path}", params=params or None, timeout=TIMEOUT)


def _ids(items):
    return {x["id"] for x in items}


def _listing_body(**over):
    b = {
        "product": f"{TAG} roșii",
        "category": "legume",
        "unit": "kg",
        "quantity_total": 20,
        "price_ron_per_unit": 8,
        "mode": "both",
        "exchange_for": "Ouă de țară sau miere",
        "locality": FLORESTI,
        "pickup_details": "Ridicare de la poartă, după ora 17",
    }
    b.update(over)
    return {k: v for k, v in b.items() if v is not None}


ADMIN_ROUTES = [
    ("GET", "/admin/kpis", None),
    ("GET", "/admin/activity", None),
    ("GET", "/admin/members", None),
    ("GET", "/admin/parcels", None),
    ("GET", "/admin/listings", None),
    ("GET", "/admin/deletion-requests", None),
    ("GET", "/admin/audit", None),
    ("POST", f"/admin/listings/{ZERO_ID}/close", {"reason": "motiv de test"}),
    ("POST", f"/admin/deletion-requests/{ZERO_ID}/resolve", {"decision": "done", "note": "test"}),
]


ROUTE_IDS = [f"{m} {p.replace(ZERO_ID, '<id>')}" for m, p, _ in ADMIN_ROUTES]


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
    _ensure_member(client, ["land", "sell"], FLORESTI)
    _ensure_member(specialist, ["grow", "consume"], FLORESTI)
    S["client_uid"] = _my_user_id(client)
    S["specialist_uid"] = _my_user_id(specialist)
    r = client.get(f"{R}/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    S["client_name"] = r.json().get("name") or ""


@pytest.fixture(scope="module")
def _cleanup(client, admin, _members):
    yield
    for pid in S.get("parcel_ids", []):
        try:
            client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass
    if S.get("lid"):
        try:  # dacă testul a eșuat înainte de moderare, închidem anunțul (vânzătorul)
            client.post(f"{R}/listings/{S['lid']}/close", timeout=TIMEOUT)
        except Exception:
            pass


# ── 1. acces: doar managerul ─────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestAccess:
    @pytest.mark.parametrize("method,path,body", ADMIN_ROUTES, ids=ROUTE_IDS)
    def test_anonymous_401(self, anon, method, path, body):
        r = anon.request(method, f"{R}{path}", json=body, timeout=TIMEOUT)
        _err(r, 401)

    @pytest.mark.parametrize("method,path,body", ADMIN_ROUTES, ids=ROUTE_IDS)
    def test_non_staff_403(self, specialist, method, path, body):
        r = specialist.request(method, f"{R}{path}", json=body, timeout=TIMEOUT)
        _err(r, 403)

    def test_operator_is_not_manager_403(self, admin, client):
        """Un operator (personal, dar nu manager) nu are acces la administrare."""
        me = client.get(f"{R}/staff/me", timeout=TIMEOUT).json()
        if me.get("is_staff"):
            pytest.skip("contul client este deja personal; nu-i schimbăm rolul")
        r = admin.post(f"{R}/staff", json={"email": CLIENT_EMAIL, "role": "operator", "areas": []}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        try:
            for method, path, body in ADMIN_ROUTES:
                resp = client.request(method, f"{R}{path}", json=body, timeout=TIMEOUT)
                _err(resp, 403)
        finally:
            admin.delete(f"{R}/staff/{S['client_uid']}", timeout=TIMEOUT)
        assert client.get(f"{R}/staff/me", timeout=TIMEOUT).json()["is_staff"] is False

    def test_admin_allowed(self, admin):
        for method, path, body in ADMIN_ROUTES:
            if method == "GET":
                r = admin.get(f"{R}{path}", timeout=TIMEOUT)
                assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"


# ── 2. KPI ───────────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestKpis:
    def test_keys_and_shape(self, admin):
        r = _get(admin, "/admin/kpis")
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ("members", "members_by_interest", "parcels_by_status", "requests_by_status", "agreements_signed",
                    "projects_active", "harvest_kg_confirmed", "listings_active", "reservations_by_status",
                    "pending_verification", "open_deletion_requests", "generated_at"):
            assert key in d, key
        assert set(d["members_by_interest"]) == {"grow", "consume", "land", "sell", "exchange", "community"}
        assert set(d["parcels_by_status"]) == {"draft", "pending_verification", "published", "rejected", "paused"}
        assert set(d["requests_by_status"]) == {
            "sent", "viewed", "negotiating", "accepted", "declined", "withdrawn", "expired"}
        assert set(d["reservations_by_status"]) == {
            "requested", "confirmed", "picked_up", "cancelled", "no_show", "declined"}
        for key in ("members", "agreements_signed", "projects_active", "listings_active",
                    "pending_verification", "open_deletion_requests"):
            assert isinstance(d[key], int) and d[key] >= 0, key
        assert isinstance(d["harvest_kg_confirmed"], (int, float)) and d["harvest_kg_confirmed"] >= 0
        assert d["members"] >= 2  # client + specialist (fixture)
        assert d["pending_verification"] == d["parcels_by_status"]["pending_verification"]
        assert all(isinstance(v, int) and v >= 0 for grp in (
            d["members_by_interest"], d["parcels_by_status"], d["requests_by_status"], d["reservations_by_status"]
        ) for v in grp.values())

    def test_cache_returns_same_snapshot(self, admin):
        first = _get(admin, "/admin/kpis").json()
        second = _get(admin, "/admin/kpis").json()
        assert second["generated_at"] == first["generated_at"]
        assert second["cached"] is True


# ── 3. membri ────────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestMembers:
    def test_list_shape_without_email(self, admin):
        r = _get(admin, "/admin/members", limit=50)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["items"], list) and isinstance(d["total"], int) and d["total"] >= 2
        mine = [m for m in d["items"] if m["user_id"] == S["client_uid"]]
        assert mine, "clientul trebuie să apară în prima pagină"
        m = mine[0]
        assert {"id", "user_id", "name", "county", "locality", "interests", "created_at", "counts"} <= set(m)
        assert set(m["counts"]) == {"parcels", "projects", "listings"}
        assert all(isinstance(v, int) for v in m["counts"].values())
        text = r.text
        assert CLIENT_EMAIL not in text and SPECIALIST_EMAIL not in text and "email" not in text.lower()
        assert "bio" not in m

    def test_filter_interest_and_locality(self, admin):
        d = _get(admin, "/admin/members", interest="land", locality=FLORESTI, limit=50).json()
        assert S["client_uid"] in {m["user_id"] for m in d["items"]}
        assert all("land" in m["interests"] and m["locality"] == FLORESTI for m in d["items"])
        none = _get(admin, "/admin/members", interest="community", locality="Mociu", limit=50).json()
        assert all("community" in m["interests"] and m["locality"] == "Mociu" for m in none["items"])

    def test_search_by_name(self, admin):
        name = S["client_name"].strip()
        if not name:
            pytest.skip("contul client nu are nume")
        needle = name.split()[0][:4].upper()
        d = _get(admin, "/admin/members", q=needle, limit=50).json()
        assert S["client_uid"] in {m["user_id"] for m in d["items"]}, d
        nobody = _get(admin, "/admin/members", q=f"zzz-{uuid.uuid4().hex}").json()
        assert nobody["items"] == [] and nobody["total"] == 0

    def test_skip_past_end_is_empty(self, admin):
        d = _get(admin, "/admin/members", skip=100000, limit=5).json()
        assert d["items"] == []

    def test_invalid_params_400(self, admin):
        _err(_get(admin, "/admin/members", interest="nu-exista"), 400)
        _err(_get(admin, "/admin/members", locality="Atlantida"), 400)
        _err(_get(admin, "/admin/members", limit=51), 400)
        _err(_get(admin, "/admin/members", limit=0), 400)
        _err(_get(admin, "/admin/members", skip=-1), 400)


# ── 4. terenuri (vedere de moderare) ─────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestParcels:
    def test_create_draft_parcel(self, client):
        payload = {
            "title": f"{TAG} teren admin",
            "county": "Cluj",
            "locality": FLORESTI,
            "lat": LAT,
            "lng": LNG,
            "area_m2": 4000,
            "access": "Drum de pământ, acces auto",
            "water_sources": ["well"],
            "current_crops": ["porumb"],
            "description": "Descriere de test care nu apare în lista de moderare.",
            "offer": {"models": ["rent"], "terms": "Termeni de test", "price_ron_per_year": 900},
        }
        r = client.post(f"{R}/parcels", json=payload, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["pid"] = _unwrap(r.json(), "parcel")["id"]
        S.setdefault("parcel_ids", []).append(S["pid"])

    def test_list_rounds_location_and_hides_private_fields(self, admin):
        r = _get(admin, "/admin/parcels", status="draft", locality=FLORESTI, limit=50)
        assert r.status_code == 200, r.text
        d = r.json()
        mine = [p for p in d["items"] if p["id"] == S["pid"]]
        assert mine, "terenul proaspăt creat trebuie să fie în pagina cea mai nouă"
        p = mine[0]
        assert p["status"] == "draft" and p["locality"] == FLORESTI and p["owner_user_id"] == S["client_uid"]
        assert p["lat"] == round(LAT, 2) and p["lng"] == round(LNG, 2) and p["exact_location"] is False
        assert p["owner_name"]
        assert "owner_email" not in p and "description" not in p and "access" not in p
        assert p["offer_models"] == ["rent"]
        assert isinstance(d["total"], int) and d["total"] >= 1
        assert CLIENT_EMAIL not in r.text

    def test_status_filter_excludes_other_states(self, admin):
        d = _get(admin, "/admin/parcels", status="published", limit=50).json()
        assert S["pid"] not in _ids(d["items"])
        assert all(p["status"] == "published" for p in d["items"])

    def test_invalid_params_400(self, admin):
        _err(_get(admin, "/admin/parcels", status="nu-exista"), 400)
        _err(_get(admin, "/admin/parcels", locality="Atlantida"), 400)
        _err(_get(admin, "/admin/parcels", limit=51), 400)


# ── 5. moderarea anunțurilor ─────────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestListingModeration:
    def test_setup_listing_and_reservation(self, client, specialist):
        r = client.post(f"{R}/listings", json=_listing_body(), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["lid"] = _unwrap(r.json(), "listing")["id"]
        r = specialist.post(
            f"{R}/listings/{S['lid']}/reservations",
            json={"quantity": 2, "mode": "cash_on_pickup"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        res = _unwrap(r.json(), "reservation")
        assert res["status"] == "requested"
        S["rid"] = res["id"]

    def test_admin_lists_active_with_pending_count(self, admin):
        r = _get(admin, "/admin/listings", status="active", limit=50)
        assert r.status_code == 200, r.text
        d = r.json()
        mine = [x for x in d["items"] if x["id"] == S["lid"]]
        assert mine, "anunțul proaspăt creat trebuie să fie în pagina cea mai nouă"
        assert mine[0]["status"] == "active" and mine[0]["pending_reservations"] == 1
        assert "product_tokens" not in mine[0]
        assert isinstance(d["total"], int)

    def test_invalid_status_400(self, admin):
        _err(_get(admin, "/admin/listings", status="nu-exista"), 400)
        _err(_get(admin, "/admin/listings", limit=51), 400)

    def test_close_validation_and_missing(self, admin):
        url = f"{R}/admin/listings/{S['lid']}/close"
        _err(admin.post(url, json={"reason": "ab"}, timeout=TIMEOUT), 400)
        _err(admin.post(url, json={"reason": "   "}, timeout=TIMEOUT), 400)
        _err(admin.post(url, json={"reason": "x" * 301}, timeout=TIMEOUT), 400)
        _err(admin.post(url, json={}, timeout=TIMEOUT), 400)
        _err(admin.post(f"{R}/admin/listings/{ZERO_ID}/close", json={"reason": "motiv valid"}, timeout=TIMEOUT), 404)
        _err(admin.post(f"{R}/admin/listings/nu-e-id/close", json={"reason": "motiv valid"}, timeout=TIMEOUT), 404)
        # încercările respinse n-au închis anunțul
        d = _get(admin, "/admin/listings", status="active", limit=50).json()
        assert S["lid"] in _ids(d["items"])

    def test_close_by_admin(self, admin):
        r = admin.post(
            f"{R}/admin/listings/{S['lid']}/close",
            json={"reason": f"{TAG} anunț retras la moderare"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["listing"]["status"] == "closed" and d["listing"]["id"] == S["lid"]
        assert d["listing"]["moderated_at"]
        assert d["reason"] == f"{TAG} anunț retras la moderare"
        assert d["cancelled_reservations"] == 1

    def test_second_close_409(self, admin):
        r = admin.post(f"{R}/admin/listings/{S['lid']}/close", json={"reason": "a doua oară"}, timeout=TIMEOUT)
        _err(r, 409)

    def test_seller_and_buyer_see_the_result(self, client, specialist):
        r = client.get(f"{R}/listings/{S['lid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        listing = _unwrap(r.json(), "listing")
        assert listing["status"] == "closed" and listing["moderated_at"]
        assert "moderation_reason" not in listing, "motivul nu se salvează pe anunț (îl pot citi și cumpărătorii)"
        r = specialist.get(f"{R}/reservations/mine", params={"role": "buyer"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        mine = [x for x in r.json()["items"] if x["id"] == S["rid"]]
        assert mine and mine[0]["status"] == "cancelled"

    def test_closed_listing_listed_as_closed(self, admin):
        d = _get(admin, "/admin/listings", status="closed", limit=50).json()
        row = [x for x in d["items"] if x["id"] == S["lid"]]
        assert row and row[0]["pending_reservations"] == 0

    def test_seller_cannot_reopen_or_close_again(self, client):
        _err(client.post(f"{R}/listings/{S['lid']}/close", timeout=TIMEOUT), 409)


# ── 6. cereri de ștergere (GDPR) ─────────────────────────────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestDeletionRequests:
    def test_create_request_and_list_pending(self, client, admin):
        r = client.post(f"{R}/me/delete-request", timeout=TIMEOUT)
        assert r.status_code in (200, 409), r.text  # 409 = o cerere rămasă dintr-o rulare anterioară
        d = _get(admin, "/admin/deletion-requests", status="pending", limit=100).json()
        mine = [x for x in d["items"] if x["user_id"] == S["client_uid"]]
        assert mine, d
        S["did"] = mine[0]["id"]
        assert mine[0]["status"] == "pending" and mine[0]["user_email"] == CLIENT_EMAIL
        assert "user_name" in mine[0]
        assert isinstance(d["total"], int) and d["total"] >= 1

    def test_invalid_filter_400(self, admin):
        _err(_get(admin, "/admin/deletion-requests", status="nu-exista"), 400)
        _err(_get(admin, "/admin/deletion-requests", limit=101), 400)

    def test_resolve_validation(self, admin, client):
        url = f"{R}/admin/deletion-requests/{S['did']}/resolve"
        _err(admin.post(url, json={"decision": "foo"}, timeout=TIMEOUT), 400)
        _err(admin.post(url, json={"decision": "rejected"}, timeout=TIMEOUT), 400)  # respingerea cere motiv
        _err(admin.post(url, json={"decision": "rejected", "note": "ab"}, timeout=TIMEOUT), 400)
        _err(admin.post(url, json={"note": "fără decizie"}, timeout=TIMEOUT), 400)
        _err(admin.post(f"{R}/admin/deletion-requests/{ZERO_ID}/resolve", json={"decision": "done"}, timeout=TIMEOUT), 404)
        _err(client.post(url, json={"decision": "done"}, timeout=TIMEOUT), 403)  # nici proprietarul cererii nu o rezolvă
        # nimic din cele de mai sus n-a modificat cererea
        d = _get(admin, "/admin/deletion-requests", status="pending", limit=100).json()
        assert S["did"] in _ids(d["items"])

    def test_resolve_done_then_409(self, admin, client):
        url = f"{R}/admin/deletion-requests/{S['did']}/resolve"
        r = admin.post(url, json={"decision": "done", "note": f"{TAG} date șterse manual"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        req = r.json()["request"]
        assert req["status"] == "done" and req["resolved_at"] and req["resolution_note"]
        _err(admin.post(url, json={"decision": "done"}, timeout=TIMEOUT), 409)
        _err(admin.post(url, json={"decision": "rejected", "note": "alt motiv"}, timeout=TIMEOUT), 409)
        mine = client.get(f"{R}/me/delete-request", timeout=TIMEOUT).json()["request"]
        assert mine["id"] == S["did"] and mine["status"] == "done"

    def test_lists_reflect_resolution(self, admin):
        done = _get(admin, "/admin/deletion-requests", status="done", limit=100).json()
        assert S["did"] in _ids(done["items"])
        pending = _get(admin, "/admin/deletion-requests", status="pending", limit=100).json()
        assert S["did"] not in _ids(pending["items"])

    def test_resolve_rejected_with_note(self, client, admin):
        r = client.post(f"{R}/me/delete-request", timeout=TIMEOUT)
        assert r.status_code == 200, r.text  # după „done”, o cerere nouă e permisă
        rid = r.json()["request"]["id"]
        S["did2"] = rid
        r = admin.post(
            f"{R}/admin/deletion-requests/{rid}/resolve",
            json={"decision": "rejected", "note": f"{TAG} există obligații legale de păstrare"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        assert r.json()["request"]["status"] == "rejected"
        mine = client.get(f"{R}/me/delete-request", timeout=TIMEOUT).json()["request"]
        assert mine["id"] == rid and mine["status"] == "rejected"
        _err(admin.post(f"{R}/admin/deletion-requests/{rid}/resolve", json={"decision": "done"}, timeout=TIMEOUT), 409)


# ── 7. activitate și audit (după acțiunile de mai sus) ───────────────────────

@pytest.mark.usefixtures("_members", "_cleanup")
class TestActivity:
    def test_shape_and_privacy(self, admin):
        r = _get(admin, "/admin/activity", limit=100)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["items"], list) and d["items"]
        assert len(d["items"]) <= 100
        for it in d["items"]:
            assert it["type"].startswith("radacini.")
            assert {"id", "type", "actor_id", "actor_name", "actor_role", "payload", "created_at"} <= set(it)
            assert " " not in (it["actor_name"] or ""), "doar prenumele"
        stamps = [it["created_at"] for it in d["items"]]
        assert stamps == sorted(stamps, reverse=True), "cele mai noi primele"
        text = r.text
        assert ADMIN_EMAIL not in text and CLIENT_EMAIL not in text and SPECIALIST_EMAIL not in text

    def test_contains_recent_events(self, admin):
        d = _get(admin, "/admin/activity", limit=100).json()
        by_type = {}
        for it in d["items"]:
            by_type.setdefault(it["type"], []).append(it)
        created = [i for i in by_type.get("radacini.listing_created", []) if i["payload"].get("listing_id") == S["lid"]]
        closed = [i for i in by_type.get("radacini.listing_closed", []) if i["payload"].get("listing_id") == S["lid"]]
        assert created and closed
        assert closed[0]["payload"].get("moderated") is True
        assert any(i["payload"].get("request_id") == S["did"] for i in by_type.get("radacini.deletion_resolved", []))

    def test_pagination_with_before(self, admin):
        first = _get(admin, "/admin/activity", limit=2).json()
        assert len(first["items"]) == 2 and first["next_before"] == first["items"][-1]["created_at"]
        older = _get(admin, "/admin/activity", limit=5, before=first["next_before"]).json()
        assert all(i["created_at"] < first["next_before"] for i in older["items"])
        assert not _ids(older["items"]) & _ids(first["items"])

    def test_invalid_params_400(self, admin):
        _err(_get(admin, "/admin/activity", limit=101), 400)
        _err(_get(admin, "/admin/activity", limit=0), 400)
        _err(_get(admin, "/admin/activity", before="ieri"), 400)


@pytest.mark.usefixtures("_members", "_cleanup")
class TestAudit:
    def test_moderation_and_resolution_are_audited(self, admin):
        r = _get(admin, "/admin/audit", limit=100)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["items"] and all(i["action"].startswith("radacini.") for i in d["items"])
        stamps = [i["created_at"] for i in d["items"]]
        assert stamps == sorted(stamps, reverse=True)
        assert "actor_email" not in r.text
        closes = [i for i in d["items"] if i["action"] == "radacini.listing.close" and i["target_id"] == S["lid"]]
        assert closes and closes[0]["details"]["cancelled_reservations"] == 1
        assert closes[0]["details"]["reason"].startswith(TAG)
        resolved = {i["target_id"]: i for i in d["items"] if i["action"] == "radacini.deletion.resolve"}
        assert resolved[S["did"]]["details"]["decision"] == "done"
        assert resolved[S["did2"]]["details"]["decision"] == "rejected"

    def test_invalid_params_400(self, admin):
        _err(_get(admin, "/admin/audit", limit=101), 400)
        _err(_get(admin, "/admin/audit", before="ieri"), 400)
