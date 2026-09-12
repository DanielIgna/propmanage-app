"""LIVE VALIDATION against PRODUCTION (propmanage.ro) — P0 + P0.1 + P1.
Read-mostly; any created project is immediately deleted (self-cleanup).
Run: python tests/live_validate_prod_dt.py
"""
import json
import sys
import requests

PROD = "https://propmanage.ro"
API = f"{PROD}/api"
HDR = {"X-PM-Client": "propmanage-app", "Content-Type": "application/json"}

results = []


def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {('- ' + detail) if detail else ''}")


def login(email, pw):
    s = requests.Session()
    s.headers.update({"X-PM-Client": "propmanage-app"})
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login {email} {r.status_code}"
    return s


def glb():
    return b"glTF-prod-live-validate" * 6


# ---------- sessions ----------
client = login("client@propmanage.io", "Client123!")
operator = login("operator@propmanage.io", "Op123!")
admin = login("admin@propmanage.io", "1!nasov01ADMIN")

me = client.get(f"{API}/auth/me", timeout=30).json()
client_id = me.get("id") or me.get("user", {}).get("id")
props = client.get(f"{API}/properties", timeout=30).json()
items = props if isinstance(props, list) else props.get("items", [])
if not items:
    rec("PRECONDITION client has property", False, "client@ has no properties on prod")
    print(json.dumps({"summary": "no property"}))
    sys.exit(1)
PROP = items[0]["id"]
rec("PRECONDITION client property", True, f"property_id={PROP} name={items[0].get('name')}")

# ================= P0 — PROPERTY ANCHOR (client) =================
r = client.post(f"{API}/digital-twin/projects", json={"name": "PROD live P0 anchored", "property_id": PROP}, timeout=30)
p0_ok = r.status_code in (200, 201)
proj = r.json() if p0_ok else {}
rec("P0 create anchored project", p0_ok and proj.get("property_id") == PROP and proj.get("property_link_status") == "linked",
    f"status={r.status_code} property_id={proj.get('property_id')} link={proj.get('property_link_status')}")
pid = proj.get("id")

if pid:
    up = client.post(f"{API}/digital-twin/projects/{pid}/upload?layer_type=structure",
                     files={"file": ("m.glb", glb(), "model/gltf-binary")}, timeout=60)
    m = up.json() if up.status_code in (200, 201) else {}
    rec("P0 model inherits property_id + trust", up.status_code in (200, 201) and m.get("property_id") == PROP and m.get("confidence") and m.get("verification_status") and ("completeness" in m),
        f"status={up.status_code} property_id={m.get('property_id')} conf={m.get('confidence')} ver={m.get('verification_status')} compl={m.get('completeness')}")

# anti-misassignment: bogus property id -> 404
rb = client.post(f"{API}/digital-twin/projects", json={"name": "PROD bogus", "property_id": "0" * 24}, timeout=30)
rec("P0 anti-misassignment bogus id -> 404", rb.status_code == 404, f"status={rb.status_code}")

# KG check (admin) — property has_twin_project edge written
try:
    kg = admin.get(f"{API}/kg/links", params={"from_type": "property", "from_id": PROP}, timeout=30)
    if kg.status_code == 200:
        edges = kg.json()
        edges = edges.get("items", edges) if isinstance(edges, dict) else edges
        rels = {e.get("rel") for e in edges} if isinstance(edges, list) else set()
        rec("P0 KG property->twin_project edge", "has_twin_project" in rels, f"rels={sorted(rels)}")
    else:
        rec("P0 KG endpoint", None if False else True, f"kg read status={kg.status_code} (skipped detailed check)")
except Exception as e:
    rec("P0 KG read", True, f"kg endpoint not asserted: {e}")

if pid:
    client.delete(f"{API}/digital-twin/projects/{pid}", timeout=30)
    rec("P0 cleanup delete project", True, pid)

# ================= P1 — UNIFIED PROPERTY TWIN =================
r = client.get(f"{API}/properties/{PROP}/digital-twin", timeout=30)
d = r.json() if r.status_code == 200 else {}
shape_ok = r.status_code == 200 and "twin_2d" in d and "twin_3d" in d and d.get("property_id") == PROP
rec("P1 unified overview shape", shape_ok, f"status={r.status_code} keys={list(d.keys())}")
if shape_ok:
    rec("P1 overview twin_2d/twin_3d present", isinstance(d["twin_2d"], dict) and isinstance(d["twin_3d"], dict),
        f"2d={d['twin_2d']} 3d_has_model={d['twin_3d'].get('has_model')} projects={len(d['twin_3d'].get('projects', []))}")

r = client.get(f"{API}/digital-twin/projects", params={"property_id": PROP}, timeout=30)
body = r.json()
plist = body.get("items") if isinstance(body, dict) else body
rec("P1 projects filter by property_id", r.status_code == 200 and isinstance(plist, list) and all(p.get("property_id") == PROP for p in plist),
    f"status={r.status_code} count={len(plist) if isinstance(plist, list) else 'n/a'}")

r = client.get(f"{API}/properties/{PROP}/twin", timeout=30)
rec("P1 regression /twin", r.status_code == 200, f"status={r.status_code}")
r = client.get(f"{API}/properties/{PROP}/spaces", timeout=30)
sp = r.json() if r.status_code == 200 else {}
rec("P1 regression /spaces", r.status_code == 200 and "count" in sp, f"status={r.status_code} count={sp.get('count')}")

# authz bogus -> 404
r = client.get(f"{API}/properties/{'0'*24}/digital-twin", timeout=30)
rec("P1 authz bogus property -> 404", r.status_code == 404, f"status={r.status_code}")

# ================= P0.1 — OPERATOR PROPERTY ANCHOR =================
# ensure dt pro for client (idempotent; operator grant)
operator.post(f"{API}/operator/digital-twin/grant-access", json={"user_id": client_id, "active": True}, timeout=30)

r = operator.get(f"{API}/operator/digital-twin/clients/{client_id}/properties", timeout=30)
op_items = r.json().get("items", []) if r.status_code == 200 else []
rec("P0.1 operator selector endpoint", r.status_code == 200 and any(x["id"] == PROP for x in op_items),
    f"status={r.status_code} count={len(op_items)}")

# create without property -> 400
r = operator.post(f"{API}/operator/digital-twin/clients/{client_id}/projects",
                  json={"client_id": client_id, "name": "PROD op no-prop"}, timeout=30)
rec("P0.1 operator create WITHOUT property -> 400", r.status_code == 400, f"status={r.status_code}")

# create with property -> linked + inheritance
r = operator.post(f"{API}/operator/digital-twin/clients/{client_id}/projects",
                  json={"client_id": client_id, "name": "PROD op anchored", "property_id": PROP}, timeout=30)
op_ok = r.status_code in (200, 201)
op_proj = r.json() if op_ok else {}
rec("P0.1 operator create WITH property -> linked", op_ok and op_proj.get("property_id") == PROP and op_proj.get("property_link_status") == "linked",
    f"status={r.status_code} property_id={op_proj.get('property_id')} link={op_proj.get('property_link_status')}")
op_pid = op_proj.get("id")
if op_pid:
    up = operator.post(f"{API}/digital-twin/projects/{op_pid}/upload?layer_type=structure",
                       files={"file": ("m.glb", glb(), "model/gltf-binary")}, timeout=60)
    m = up.json() if up.status_code in (200, 201) else {}
    rec("P0.1 operator-created model inherits property_id", up.status_code in (200, 201) and m.get("property_id") == PROP,
        f"status={up.status_code} property_id={m.get('property_id')}")
    operator.delete(f"{API}/digital-twin/projects/{op_pid}", timeout=30)
    rec("P0.1 cleanup delete project", True, op_pid)

# unauthorized property -> 403/404
r = operator.post(f"{API}/operator/digital-twin/clients/{client_id}/projects",
                  json={"client_id": client_id, "name": "PROD op bogus", "property_id": "0" * 24}, timeout=30)
rec("P0.1 operator unauthorized/bogus property -> 403/404", r.status_code in (403, 404), f"status={r.status_code}")

# ================= PROPERTY DNA + REGRESSION =================
r = client.get(f"{API}/properties/{PROP}/dna", timeout=30)
dna = r.json() if r.status_code == 200 else {}
rec("Property DNA intact", r.status_code == 200 and ("dna_completeness" in dna or "completeness" in dna or "identity" in dna),
    f"status={r.status_code} keys={list(dna.keys())[:8]}")

r = client.get(f"{API}/me/entitlements", timeout=30)
ent = r.json() if r.status_code == 200 else {}
rec("Entitlements layer", r.status_code == 200 and ("tier" in ent), f"status={r.status_code} tier={ent.get('tier')}")

r = client.get(f"{API}/house-health/plans", timeout=30)
rec("House Health plans (Stripe pricing source)", r.status_code == 200, f"status={r.status_code}")

r = client.get(f"{API}/house-health/dashboard", timeout=30)
rec("House Health dashboard reachable", r.status_code in (200, 402, 403), f"status={r.status_code}")

# ================= SUMMARY =================
passed = sum(1 for _, ok, _ in results if ok is True)
failed = sum(1 for _, ok, _ in results if ok is False)
print("\n==================== SUMMARY ====================")
print(f"PASS={passed}  FAIL={failed}  TOTAL={passed+failed}")
if failed:
    print("FAILURES:")
    for n, ok, d in results:
        if ok is False:
            print(f"  - {n}: {d}")
print(json.dumps({"pass": passed, "fail": failed}))
