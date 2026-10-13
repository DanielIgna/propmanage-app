"""Șterge documentele demo ale modulului Rădăcini (is_demo=true).

Implicit rulează în dry-run (doar numără). Cu --apply șterge efectiv.
Cu --tests-only șterge doar datele lăsate de testele HTTP (terenuri cu „TEST-RAD-” în titlu)
și tot ce depinde de ele (cereri, mesaje, acorduri, proiecte, culturi, activități, contribuții).

Utilizare (local):
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --apply
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --tests-only --apply
"""
import argparse
import asyncio
import sys
from pathlib import Path

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
)
DEMO_FILTER = {"is_demo": True}


async def run(apply: bool) -> None:
    mode = "APLICARE" if apply else "DRY-RUN (nimic nu se șterge; folosește --apply)"
    print(f"Rădăcini purge demo — {mode}")
    for name in COLLECTIONS:
        coll = getattr(db, name)
        count = await coll.count_documents(DEMO_FILTER)
        if apply and count:
            await coll.delete_many(DEMO_FILTER)
            print(f"  {name}: șterse {count}")
        else:
            print(f"  {name}: {count} demo")


async def run_tests_only(apply: bool) -> None:
    mode = "APLICARE" if apply else "DRY-RUN (nimic nu se șterge; folosește --apply)"
    print(f"Rădăcini purge date de test (TEST-RAD-) — {mode}")
    parcels = await db.radacini_parcels.find({"is_demo": True}, {"title": 1}).to_list(100000)
    parcel_ids = [str(d["_id"]) for d in parcels if "TEST-RAD-" in (d.get("title") or "")]
    by_parcel = {"parcel_id": {"$in": parcel_ids}}
    request_ids = [str(d["_id"]) for d in await db.radacini_land_requests.find(by_parcel, {"_id": 1}).to_list(100000)]
    project_ids = [str(d["_id"]) for d in await db.radacini_projects.find(by_parcel, {"_id": 1}).to_list(100000)]
    by_project = {"project_id": {"$in": project_ids}}
    plan = [
        ("radacini_contributions", by_project),
        ("radacini_activities", by_project),
        ("radacini_crop_plans", by_project),
        ("radacini_projects", by_parcel),
        ("radacini_agreements", by_parcel),
        ("radacini_request_messages", {"request_id": {"$in": request_ids}}),
        ("radacini_land_requests", by_parcel),
        ("radacini_parcels", {"_id": {"$in": [d["_id"] for d in parcels if str(d["_id"]) in set(parcel_ids)]}}),
    ]
    for name, flt in plan:
        coll = getattr(db, name)
        count = await coll.count_documents(flt)
        if apply and count:
            await coll.delete_many(flt)
            print(f"  {name}: șterse {count}")
        else:
            print(f"  {name}: {count} de test")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="șterge efectiv documentele demo")
    parser.add_argument("--tests-only", action="store_true", help="doar datele lăsate de testele HTTP (TEST-RAD-)")
    args = parser.parse_args()
    asyncio.run(run_tests_only(apply=args.apply) if args.tests_only else run(apply=args.apply))


if __name__ == "__main__":
    main()
