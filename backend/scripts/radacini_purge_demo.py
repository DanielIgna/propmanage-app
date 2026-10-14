"""Șterge documentele demo ale modulului Rădăcini (is_demo=true) și tot ce depinde de ele.

Implicit rulează în dry-run (doar numără). Cu --apply șterge efectiv.
Dependentele NON-demo ale documentelor șterse (cereri, mesaje, acorduri, proiecte, culturi, activități,
contribuții, recolte, alocări, rezervări) se șterg și ele, ca să nu rămână documente orfane care indică
spre terenuri / anunțuri / recolte inexistente. Dry-run-ul le listează separat („dependente non-demo”).
Statisticile de rating (`radacini_seller_stats`) ale vânzătorilor ale căror rezervări evaluate se șterg se
elimină și ele; se recalculează automat, din rezervările rămase, la prima citire / evaluare.

Jurnalul de acces la locația exactă (`radacini_location_access_log`) se șterge împreună cu terenurile la care
se referă (câmpul `parcel_id`) sau când e marcat demo. Cererile de ștergere GDPR (`radacini_deletion_requests`)
se șterg doar dacă sunt marcate demo (cele reale nu au `is_demo`).

Cu --tests-only șterge doar datele lăsate de testele HTTP: terenuri demo cu „TEST-RAD-” în titlu și anunțuri
demo cu „TEST-RAD-” în produs, plus tot ce depinde de ele, plus cererile de ștergere marcate demo (testele GDPR
le creează pe conturile de test).

Utilizare (local):
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --apply
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --tests-only --apply
"""
import argparse
import asyncio
import sys
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import db  # noqa: E402

COLLECTIONS = (
    "radacini_members",
    "radacini_parcels",
    "radacini_staff",
    "radacini_land_requests",
    "radacini_request_messages",
    "radacini_agreements",
    "radacini_projects",
    "radacini_crop_plans",
    "radacini_activities",
    "radacini_contributions",
    "radacini_harvests",
    "radacini_allocations",
    "radacini_listings",
    "radacini_reservations",
    "radacini_seller_stats",  # (nu există colecții de lock-uri: rezervarea unică se obține prin upsert)
    "radacini_location_access_log",
    "radacini_deletion_requests",
    # S6/S7
    "radacini_communities",
    "radacini_community_members",
    "radacini_community_posts",
    "radacini_households",
    "radacini_consents",
    "radacini_decisions",
    "radacini_disputes",
    "radacini_photos",
    "radacini_project_needs",
    "radacini_providers",
    "radacini_service_requests",
    # S8 (documentele legale nu sunt demo; acceptările și onboarding-ul conturilor de test sunt is_demo)
    "radacini_legal_acceptances",
    "radacini_onboarding",
)
DEMO_FILTER = {"is_demo": True}
SCAN_LIMIT = 100000
IN_CHUNK = 100  # pgmongo traduce `$in` în SQL doar până la 200 de valori
DELETE_CHUNK = 500

# (colecția-părinte, câmpul din copil care indică spre părinte, copiii). Ordinea e topologică: un copil
# descoperit într-o muchie (ex. proiecte prin acord) își propagă apoi propriii copii în muchiile următoare.
EDGES = (
    (
        "radacini_parcels",
        "parcel_id",
        ("radacini_land_requests", "radacini_agreements", "radacini_projects", "radacini_location_access_log"),
    ),
    ("radacini_land_requests", "request_id", ("radacini_request_messages", "radacini_agreements")),
    ("radacini_agreements", "agreement_id", ("radacini_projects",)),
    (
        "radacini_projects",
        "project_id",
        (
            "radacini_crop_plans",
            "radacini_activities",
            "radacini_contributions",
            "radacini_harvests",
            "radacini_allocations",
        ),
    ),
    ("radacini_harvests", "harvest_id", ("radacini_allocations",)),
    ("radacini_listings", "listing_id", ("radacini_reservations",)),
)


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


async def _ids(name: str, flt: dict) -> set:
    docs = await getattr(db, name).find(flt, {"_id": 1}).limit(SCAN_LIMIT).to_list(SCAN_LIMIT)
    return {str(d["_id"]) for d in docs}


async def _ids_by_field(name: str, field: str, values: set) -> set:
    out: set = set()
    for chunk in _chunks(sorted(values), IN_CHUNK):
        out |= await _ids(name, {field: {"$in": chunk}})
    return out


async def collect(roots: dict) -> tuple[dict, dict]:
    """(ids de șters per colecție, ids rădăcină per colecție). Închiderea dependențelor urmează EDGES."""
    ids = {name: set(roots.get(name, ())) for name in COLLECTIONS}
    for parent, field, children in EDGES:
        if not ids[parent]:
            continue
        for child in children:
            ids[child] |= await _ids_by_field(child, field, ids[parent])
    # Statistici de rating: vânzătorii ale căror rezervări evaluate dispar.
    sellers: set = set()
    res_ids = sorted(ids["radacini_reservations"])
    for chunk in _chunks(res_ids, IN_CHUNK):
        rows = await db.radacini_reservations.find(
            {"_id": {"$in": [ObjectId(i) for i in chunk]}, "rating": {"$exists": True}}, {"seller_user_id": 1}
        ).limit(len(chunk)).to_list(len(chunk))
        sellers |= {r["seller_user_id"] for r in rows if r.get("seller_user_id")}
    if sellers:
        ids["radacini_seller_stats"] |= await _ids_by_field("radacini_seller_stats", "seller_user_id", sellers)
    return ids, {name: set(roots.get(name, ())) for name in COLLECTIONS}


async def _delete_ids(name: str, ids: set) -> None:
    coll = getattr(db, name)
    for chunk in _chunks(sorted(ids), DELETE_CHUNK):
        await coll.delete_many({"_id": {"$in": [ObjectId(i) for i in chunk]}})


async def _report_and_delete(ids: dict, roots: dict, apply: bool, label: str) -> None:
    for name in COLLECTIONS:
        total = ids[name]
        if not total:
            print(f"  {name}: 0 {label}")
            continue
        dependents = len(total - roots[name])
        detail = f"{len(roots[name])} {label}" + (f" + {dependents} dependente non-demo" if dependents else "")
        if apply:
            await _delete_ids(name, total)
            print(f"  {name}: șterse {len(total)} ({detail})")
        else:
            print(f"  {name}: {detail}")


async def run(apply: bool) -> None:
    mode = "APLICARE" if apply else "DRY-RUN (nimic nu se șterge; folosește --apply)"
    print(f"Rădăcini purge demo — {mode}")
    roots = {name: await _ids(name, DEMO_FILTER) for name in COLLECTIONS}
    ids, roots = await collect(roots)
    await _report_and_delete(ids, roots, apply, "demo")


async def run_tests_only(apply: bool) -> None:
    mode = "APLICARE" if apply else "DRY-RUN (nimic nu se șterge; folosește --apply)"
    print(f"Rădăcini purge date de test (TEST-RAD-) — {mode}")
    parcels = await db.radacini_parcels.find(DEMO_FILTER, {"title": 1}).limit(SCAN_LIMIT).to_list(SCAN_LIMIT)
    listings = await db.radacini_listings.find(DEMO_FILTER, {"product": 1}).limit(SCAN_LIMIT).to_list(SCAN_LIMIT)
    roots = {
        "radacini_parcels": {str(d["_id"]) for d in parcels if "TEST-RAD-" in (d.get("title") or "")},
        "radacini_listings": {str(d["_id"]) for d in listings if "TEST-RAD-" in (d.get("product") or "")},
        "radacini_deletion_requests": await _ids("radacini_deletion_requests", DEMO_FILTER),
    }
    ids, roots = await collect(roots)
    await _report_and_delete(ids, roots, apply, "de test")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="șterge efectiv documentele demo")
    parser.add_argument("--tests-only", action="store_true", help="doar datele lăsate de testele HTTP (TEST-RAD-)")
    args = parser.parse_args()
    asyncio.run(run_tests_only(apply=args.apply) if args.tests_only else run(apply=args.apply))


if __name__ == "__main__":
    main()
