"""Șterge documentele demo ale modulului Rădăcini (is_demo=true).

Implicit rulează în dry-run (doar numără). Cu --apply șterge efectiv.

Utilizare (local):
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo
  cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --apply
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="șterge efectiv documentele demo")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
