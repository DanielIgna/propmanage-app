"""Rădăcini S9-B — documente, ședințe, mandate, petiții, cereri (HTTP, backend pornit, necesită partea A).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s9b.py -q --noconftest
"""
import hashlib
import os
import uuid
from datetime import date, timedelta

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
R = f"{API}/radacini"
A = f"{R}/assoc"
TIMEOUT = 30
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + uuid.uuid4().hex.encode()


def _login(email, passwords):
    s = requests.Session()
    for pwd in passwords:
        if s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT).status_code == 200:
            docs = requests.get(f"{R}/legal/documents", timeout=TIMEOUT).json()["items"]
            for d in docs:
                s.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)
            return s
    pytest.skip(f"Login failed for {email}")


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module")
def spec():
    return _login("specialist@propmanage.io", ["Spec123!"])


@pytest.fixture(scope="module")
def outsider():
    return _login("client@propmanage.io", ["Client123!"])


def _make_assoc(admin, spec, n):
    r = admin.post(A, json={"name": f"TEST-RAD-S9B {uuid.uuid4().hex[:6]}", "type": "composesorat", "localities": ["Test"],
                            "description": "test", "legal": {}, "patrimony": []}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    aid = (body.get("association") or body).get("id")
    ids = {}
    for i in range(1, n + 1):
        code = f"M{i:03d}"
        r = admin.post(f"{A}/{aid}/members", json={"code": code, "name": f"Membru {i}", "shares": 1, "sources": [f"Nr {i}"],
                                                    "status": "confirmed"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        row = r.json().get("member") or r.json()
        ids[code] = row.get("id")
    r = spec.post(f"{A}/{aid}/claims", json={"kind": "self", "member_code": "M002", "note": "test", "document_ids": []}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    cid = (r.json().get("claim") or r.json()).get("id")
    r = admin.post(f"{A}/claims/{cid}/decide", json={"decision": "approve", "note": "ok"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return aid, ids


@pytest.fixture(scope="module")
def big(admin, spec):
    return _make_assoc(admin, spec, 8)


@pytest.fixture(scope="module")
def small(admin, spec):
    return _make_assoc(admin, spec, 4)


def _upload(s, aid, **kw):
    data = kw.pop("data", PDF)
    form = {"type": "statute", "title": "Statut test", "date": date.today().isoformat(), "visibility": "members", **kw}
    return s.post(f"{A}/{aid}/documents", data=form, files={"file": ("a.pdf", data, "application/pdf")}, timeout=TIMEOUT)


def test_documents(admin, spec, outsider, big):
    aid, _ = big
    r = _upload(admin, aid)
    assert r.status_code == 201, r.text
    doc = r.json()["document"]
    assert doc["sha256"] == hashlib.sha256(PDF).hexdigest() and "path" not in doc
    assert _upload(spec, aid).status_code == 403  # membru simplu nu încarcă
    assert _upload(admin, aid, data=b"not a pdf at all").status_code == 400
    assert _upload(admin, aid, visibility="council", title="Intern").status_code == 201
    v2 = _upload(admin, aid, replaces_id=doc["id"], data=PDF + b"x")
    assert v2.status_code == 201 and v2.json()["document"]["version"] == 2
    assert _upload(admin, aid, replaces_id=doc["id"]).status_code == 409
    items = spec.get(f"{A}/{aid}/documents", timeout=TIMEOUT).json()["items"]
    assert items and all(i["visibility"] == "members" for i in items)  # membrul nu vede documentele CA
    assert outsider.get(f"{A}/{aid}/documents", timeout=TIMEOUT).status_code in (403, 404)
    f = spec.get(f"{A}/documents/{doc['id']}/file", timeout=TIMEOUT)
    assert f.status_code == 200 and f.content == PDF
    log = admin.get(f"{A}/documents/{doc['id']}/access-log", timeout=TIMEOUT)
    assert log.status_code == 200 and log.json()["items"]
    assert spec.get(f"{A}/documents/{doc['id']}/access-log", timeout=TIMEOUT).status_code == 403
    assert outsider.get(f"{A}/documents/{doc['id']}/file", timeout=TIMEOUT).status_code in (403, 404)


def _meeting(admin, aid, d, **kw):
    r = admin.post(f"{A}/{aid}/meetings", json={"kind": "aga_ordinary", "date": d.isoformat(), "place": "Căminul",
                                                 "agenda": [{"title": "Bilanț", "details": ""}], **kw}, timeout=TIMEOUT)
    assert r.status_code == 201, r.text
    return r.json()["meeting"]["id"]


def test_meeting_flow_and_quorum(admin, spec, outsider, big):
    aid, ids = big
    today = date.today()
    assert spec.post(f"{A}/{aid}/meetings", json={"kind": "aga_ordinary", "date": today.isoformat(), "place": "x"},
                     timeout=TIMEOUT).status_code == 403
    mid = _meeting(admin, aid, today)
    r = admin.post(f"{A}/meetings/{mid}/convene", json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    assert r.json()["warning"] and r.json()["registered_mail_missing"] and r.json()["notified"] >= 1
    assert spec.post(f"{A}/meetings/{mid}/convene", json={}, timeout=TIMEOUT).status_code == 403
    assert spec.post(f"{A}/meetings/{mid}/ack", timeout=TIMEOUT).status_code == 200
    assert outsider.post(f"{A}/meetings/{mid}/ack", timeout=TIMEOUT).status_code in (403, 404)
    att = admin.post(f"{A}/meetings/{mid}/attendance", json={"present_member_ids": [ids["M002"]]}, timeout=TIMEOUT)
    assert att.status_code == 200, att.text
    assert att.json()["quorum_met"] is False and att.json()["held_without_quorum"] is False
    dec = {"decisions": [{"title": "t", "result_text": "adoptat"}]}
    assert admin.post(f"{A}/meetings/{mid}/decisions", json=dec, timeout=TIMEOUT).status_code == 409
    assert spec.get(f"{A}/meetings/{mid}", timeout=TIMEOUT).json()["meeting"]["id"] == mid
    mid2 = _meeting(admin, aid, today, first_convocation_date=(today - timedelta(days=8)).isoformat())
    assert admin.post(f"{A}/meetings/{mid2}/convene", json={}, timeout=TIMEOUT).status_code == 200
    att2 = admin.post(f"{A}/meetings/{mid2}/attendance", json={"present_member_ids": [ids["M002"]]}, timeout=TIMEOUT).json()
    assert att2["held_without_quorum"] is True and "9(2)" in att2["label"]
    d = admin.post(f"{A}/meetings/{mid2}/decisions", json=dec, timeout=TIMEOUT)
    assert d.status_code == 200, d.text
    assert d.json()["contest_until"] == (today + timedelta(days=15)).isoformat()


def test_mandate_limits(admin, spec, big):
    aid, ids = big
    mid = _meeting(admin, aid, date.today() + timedelta(days=30))
    assert spec.post(f"{A}/meetings/{mid}/mandates", json={"representative_member_id": ids["M002"]}, timeout=TIMEOUT).status_code == 400
    r = spec.post(f"{A}/meetings/{mid}/mandates", json={"representative_member_id": ids["M003"]}, timeout=TIMEOUT)
    assert r.status_code == 409, r.text  # 2 din 8 cote > 5%
    assert spec.post(f"{A}/meetings/{mid}/mandates", json={"representative_member_id": "0" * 24}, timeout=TIMEOUT).status_code in (400, 404)


def test_petitions(admin, spec, big, small):
    aid, _ = big
    p = spec.post(f"{A}/{aid}/petitions", json={"kind": "extraordinary_aga", "title": "AGA", "text": "Cerem AGA"}, timeout=TIMEOUT)
    assert p.status_code == 201, p.text
    pid = p.json()["petition"]["id"]
    s = spec.post(f"{A}/petitions/{pid}/sign", timeout=TIMEOUT)
    assert s.status_code == 200 and s.json()["signatures_count"] == 1 and s.json()["threshold_met"] is False
    assert spec.post(f"{A}/petitions/{pid}/sign", timeout=TIMEOUT).status_code == 409
    assert spec.post(f"{A}/petitions/{pid}/respond", json={"text": "ok"}, timeout=TIMEOUT).status_code == 403
    aid2, _ = small
    p2 = spec.post(f"{A}/{aid2}/petitions", json={"kind": "extraordinary_aga", "title": "AGA", "text": "Cerem AGA"},
                   timeout=TIMEOUT).json()["petition"]["id"]
    assert spec.post(f"{A}/petitions/{p2}/sign", timeout=TIMEOUT).json()["threshold_met"] is True  # 1/4 = 25%
    lst = spec.get(f"{A}/{aid2}/petitions", timeout=TIMEOUT).json()["items"]
    assert lst[0]["threshold_met"] and lst[0]["signed_by_me"]
    r = admin.post(f"{A}/petitions/{p2}/respond", json={"text": "Convocăm AGA"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text


def test_info_requests(admin, spec, outsider, big):
    aid, _ = big
    r = spec.post(f"{A}/{aid}/requests", json={"subject": "Bilanț", "text": "Doresc bilanțul."}, timeout=TIMEOUT)
    assert r.status_code == 201, r.text
    req = r.json()["request"]
    assert req["overdue"] is False and req["due_at"]
    assert outsider.post(f"{A}/{aid}/requests", json={"subject": "xx", "text": "yy"}, timeout=TIMEOUT).status_code in (403, 404)
    assert spec.post(f"{A}/requests/{req['id']}/answer", json={"text": "da"}, timeout=TIMEOUT).status_code == 403
    a = admin.post(f"{A}/requests/{req['id']}/answer", json={"text": "Atașat."}, timeout=TIMEOUT)
    assert a.status_code == 200, a.text
    assert admin.post(f"{A}/requests/{req['id']}/answer", json={"text": "din nou"}, timeout=TIMEOUT).status_code == 409
    mine = spec.get(f"{A}/{aid}/requests", timeout=TIMEOUT).json()["items"]
    assert any(x["id"] == req["id"] and x["answer"] for x in mine)
