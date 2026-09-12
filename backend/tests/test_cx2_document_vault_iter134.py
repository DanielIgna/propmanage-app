"""Sprint CX-2 — Property DNA & Document Vault (iter 134)."""
import os
import time

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PWD = "Client123!"


def _login_session(email, pwd):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def owner():
    ts = int(time.time())
    email = f"cx2.iter134.{ts}@test.io"
    pwd = "CxTest2026!"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pwd, "name": "CX2 Iter134", "role": "client",
        "terms_accepted": True, "privacy_policy_accepted": True,
    }, timeout=20)
    assert r.status_code in (200, 201), r.text
    s = _login_session(email, pwd)
    r = s.post(f"{API}/properties", json={
        "name": "Test Casa CX2", "address": "Str. Test 1", "type": "apartament",
        "surface": 65, "rooms": 3,
    }, timeout=20)
    assert r.status_code in (200, 201), r.text
    j = r.json()
    prop_id = j.get("id") or j.get("_id") or (j.get("property") or {}).get("id")
    if not prop_id:
        pl = s.get(f"{API}/properties", timeout=20).json()
        props = pl if isinstance(pl, list) else pl.get("properties") or pl.get("items") or []
        prop_id = props[0]["id"]
    return {"s": s, "prop_id": prop_id, "state": {}}


PDF_BYTES = (b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<< /Type /Catalog >>endobj\n"
             b"trailer<< /Root 1 0 R >>\n%%EOF\n")


def _upload(s, prop_id, **extra):
    files = {"file": ("factura_test.pdf", PDF_BYTES, "application/pdf")}
    data = {"title": "Factură test", "category": "factura", "company": "Enel SA",
            "warranty_end": "2027-06-01"}
    data.update(extra)
    return s.post(f"{API}/properties/{prop_id}/documents", files=files, data=data, timeout=60)


def test_upload_first_document(owner):
    r = _upload(owner["s"], owner["prop_id"])
    assert r.status_code == 200, r.text
    j = r.json()
    doc = j["document"]
    assert j["first_upload"] is True
    assert doc["provenance"] == "declared"
    assert doc["source"] == "owner_upload"
    assert doc["verification_status"] == "unverified"
    assert doc["version"] == 1
    assert doc["company"] == "Enel SA"
    assert doc["warranty_end"] == "2027-06-01"
    assert j["completeness"]["score"] > 0
    owner["state"]["doc_id"] = doc["id"]


def test_upload_invalid_category(owner):
    s = owner["s"]
    files = {"file": ("f.pdf", PDF_BYTES, "application/pdf")}
    r = s.post(f"{API}/properties/{owner['prop_id']}/documents",
               files=files, data={"title": "x", "category": "wrong_cat"}, timeout=30)
    assert r.status_code == 400


def test_upload_exe_rejected(owner):
    s = owner["s"]
    files = {"file": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")}
    r = s.post(f"{API}/properties/{owner['prop_id']}/documents",
               files=files, data={"title": "x", "category": "factura"}, timeout=30)
    assert r.status_code == 400


def test_upload_empty_file(owner):
    s = owner["s"]
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    r = s.post(f"{API}/properties/{owner['prop_id']}/documents",
               files=files, data={"title": "x", "category": "factura"}, timeout=30)
    assert r.status_code == 400


def test_list_facets_and_filters(owner):
    s = owner["s"]
    r = s.get(f"{API}/properties/{owner['prop_id']}/documents", timeout=20)
    assert r.status_code == 200
    j = r.json()
    assert j["total"] >= 1
    cats = [f["category"] for f in j["facets"]]
    assert "factura" in cats

    r2 = s.get(f"{API}/properties/{owner['prop_id']}/documents",
               params={"category": "factura"}, timeout=20)
    assert r2.status_code == 200
    assert all(d["category"] == "factura" for d in r2.json()["documents"])

    r3 = s.get(f"{API}/properties/{owner['prop_id']}/documents",
               params={"q": "Enel"}, timeout=20)
    assert r3.status_code == 200 and len(r3.json()["documents"]) >= 1

    r4 = s.get(f"{API}/properties/{owner['prop_id']}/documents",
               params={"warranty": "active"}, timeout=20)
    assert r4.status_code == 200 and len(r4.json()["documents"]) >= 1


def test_document_detail_and_file(owner):
    s = owner["s"]
    did = owner["state"]["doc_id"]
    r = s.get(f"{API}/documents/{did}", timeout=20)
    assert r.status_code == 200
    assert r.json()["document"]["id"] == did
    assert "previous_versions" in r.json()

    r2 = s.get(f"{API}/documents/{did}/file", timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/pdf")
    assert len(r2.content) > 0

    r3 = s.get(f"{API}/documents/{did}/file", params={"download": 1}, timeout=30)
    assert r3.status_code == 200
    assert "attachment" in r3.headers.get("content-disposition", "").lower()


def test_patch_appends_history(owner):
    s = owner["s"]
    did = owner["state"]["doc_id"]
    r = s.patch(f"{API}/documents/{did}",
                json={"room": "Bucătărie", "title": "Factură centrală"}, timeout=20)
    assert r.status_code == 200
    r2 = s.get(f"{API}/documents/{did}", timeout=20)
    d = r2.json()["document"]
    assert d["title"] == "Factură centrală"
    assert d["room"] == "Bucătărie"
    edits = [h for h in (d.get("history") or []) if h.get("event") == "edit"]
    assert edits, "no edit history entry"
    assert "changes" in edits[-1] and "title" in edits[-1]["changes"]


def test_new_version_supersedes(owner):
    s = owner["s"]
    did = owner["state"]["doc_id"]
    files = {"file": ("factura_v2.pdf", PDF_BYTES + b"v2", "application/pdf")}
    r = s.post(f"{API}/documents/{did}/version", files=files, timeout=60)
    assert r.status_code == 200, r.text
    new_doc = r.json()["document"]
    assert new_doc["version"] == 2
    assert new_doc["prev_version_id"] == did
    owner["state"]["v2_id"] = new_doc["id"]

    r2 = s.get(f"{API}/properties/{owner['prop_id']}/documents", timeout=20)
    ids = [d["id"] for d in r2.json()["documents"]]
    assert did not in ids
    assert new_doc["id"] in ids

    r3 = s.get(f"{API}/documents/{new_doc['id']}", timeout=20)
    prev = r3.json()["previous_versions"]
    assert any(p["id"] == did for p in prev)


def test_soft_delete(owner):
    s = owner["s"]
    files = {"file": ("todel.pdf", PDF_BYTES, "application/pdf")}
    r = s.post(f"{API}/properties/{owner['prop_id']}/documents",
               files=files, data={"title": "To Delete", "category": "altele"}, timeout=30)
    assert r.status_code == 200
    del_id = r.json()["document"]["id"]

    r2 = s.delete(f"{API}/documents/{del_id}", timeout=20)
    assert r2.status_code == 200
    r3 = s.get(f"{API}/properties/{owner['prop_id']}/documents", timeout=20)
    ids = [d["id"] for d in r3.json()["documents"]]
    assert del_id not in ids


def test_completeness_structure(owner):
    s = owner["s"]
    r = s.get(f"{API}/properties/{owner['prop_id']}/completeness", timeout=20)
    assert r.status_code == 200
    j = r.json()
    assert 0 <= j["score"] <= 100
    assert j["max"] == 100
    assert isinstance(j["items"], list) and len(j["items"]) > 0
    it = j["items"][0]
    for k in ("earned", "max", "done", "label"):
        assert k in it
    assert "missing" in j and "next_step" in j
    if j["next_step"]:
        assert "expected_gain" in j["next_step"]
    assert "docs_count" in j


def test_security_other_client_and_anonymous(owner):
    other = _login_session(CLIENT_EMAIL, CLIENT_PWD)
    r = other.get(f"{API}/properties/{owner['prop_id']}/documents", timeout=20)
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"

    v2 = owner["state"].get("v2_id")
    if v2:
        r2 = other.get(f"{API}/documents/{v2}/file", timeout=20)
        assert r2.status_code in (403, 404)

    r3 = requests.get(f"{API}/properties/{owner['prop_id']}/documents", timeout=20)
    assert r3.status_code == 401


def test_dna_and_timeline_events(owner):
    s = owner["s"]
    r = s.get(f"{API}/properties/{owner['prop_id']}/dna", timeout=20)
    assert r.status_code == 200
    dna = r.json()
    caps = dna.get("capabilities") or {}
    docs_cap = caps.get("documents") or {}
    docs_data = docs_cap.get("data") or docs_cap
    assert docs_cap.get("populated") is True
    assert (docs_data.get("count") or 0) >= 1
    assert docs_data.get("by_category")

    r2 = s.get(f"{API}/properties/{owner['prop_id']}/timeline", timeout=20)
    assert r2.status_code == 200
    tl = r2.json()
    events = tl if isinstance(tl, list) else tl.get("events") or tl.get("items") or []
    kinds = [str(e.get("kind") or e.get("type") or e.get("event") or "") for e in events]
    assert any("document_uploaded" in k for k in kinds), f"no document_uploaded in {kinds[:20]}"
    assert any("warranty_registered" in k for k in kinds), f"no warranty_registered in {kinds[:20]}"
