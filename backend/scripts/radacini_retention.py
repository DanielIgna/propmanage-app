"""Retenția datelor Rădăcini, după `docs/radacini/POLITICA_RETENTIE.md` (durate propuse, încă neavizate de jurist).

Implicit face **doar raport** (numără ce ar expira). Cu --apply șterge sau anonimizează regulile marcate „apply”.
Regulile marcate „raport” (minori care au împlinit 18 ani, conturi inactive) nu modifică nimic niciodată: cer
întâi o notificare a persoanei, care nu e implementată încă.

Nu e înregistrat în scheduler. Raportul afișează doar numere și ID-uri interne, fără nume sau emailuri.

Utilizare (local):
  cd backend && ./venv/bin/python -m scripts.radacini_retention
  cd backend && ./venv/bin/python -m scripts.radacini_retention --apply
"""
import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import db  # noqa: E402

DAY = timedelta(days=1)
LIMIT = 5000  # documente per regulă și rulare; restul la rularea următoare
REQUEST_ACTIVE = ("sent", "viewed", "negotiating")
LISTING_DONE = ("closed", "expired", "cancelled")
NOTIFICATION_PREFIX = "/radacini"
ADULT_AGE = 18


def cutoff(now: datetime, days: int) -> str:
    return (now - days * DAY).isoformat()


def adult_minors(households: list[dict], year: int) -> list[dict]:
    """Gospodăriile cu minori care împlinesc 18 ani anul acesta sau mai devreme: [{household_id, count}]."""
    out = []
    for h in households:
        n = sum(1 for m in h.get("members") or []
                if m.get("is_minor") and isinstance(m.get("birth_year"), int) and year - m["birth_year"] >= ADULT_AGE)
        if n:
            out.append({"household_id": str(h["_id"]), "count": n})
    return out


def inactive_users(members: list[dict], last_seen: dict, limit_iso: str) -> list[str]:
    """Membrii al căror cont nu s-a mai autentificat de la `limit_iso`. Fără `last_seen` cunoscut: nu-i raportăm."""
    return [m["user_id"] for m in members if (last_seen.get(m.get("user_id")) or "9999") < limit_iso]


def radacini_notifications(docs: list[dict]) -> list:
    return [d["_id"] for d in docs if str(d.get("link") or "").startswith(NOTIFICATION_PREFIX)]


async def _ids(coll: str, flt: dict) -> list:
    return [d["_id"] for d in await db[coll].find(flt, {"_id": 1}).to_list(LIMIT)]


async def run(apply: bool = False, now: Optional[datetime] = None, scope: Optional[dict] = None) -> dict:
    """Aplică regulile. `scope` se adaugă la toate filtrele (testele îl folosesc ca să atingă doar datele lor)."""
    now = now or datetime.now(timezone.utc)
    scope = scope or {}
    out: dict = {}

    async def delete(name: str, coll: str, ids: list, cascade: Optional[tuple] = None):
        n_casc = 0
        if apply and ids:
            if cascade:
                c_coll, c_field = cascade
                n_casc = (await db[c_coll].delete_many({c_field: {"$in": [str(i) for i in ids]}, **scope})).deleted_count
            await db[coll].delete_many({"_id": {"$in": ids}})
        out[name] = {"action": "delete", "count": len(ids), **({"cascade": n_casc} if cascade else {})}

    # 1. Jurnalul de acces la locația exactă: 12 luni.
    await delete("location_access_log", "radacini_location_access_log",
                 await _ids("radacini_location_access_log", {"at": {"$lt": cutoff(now, 365)}, **scope}))

    # 2. Cereri de teren încheiate fără acord: 24 de luni de la ultima activitate, cu mesajele lor.
    reqs = await db.radacini_land_requests.find(
        {"status": {"$nin": list(REQUEST_ACTIVE)}, "updated_at": {"$lt": cutoff(now, 730)}, **scope},
        {"_id": 1, "agreement_id": 1},
    ).to_list(LIMIT)
    await delete("land_requests", "radacini_land_requests", [r["_id"] for r in reqs if not r.get("agreement_id")],
                 cascade=("radacini_request_messages", "request_id"))

    # 3. Anunțuri închise/expirate: 24 de luni, doar dacă nu au rezervări (acelea se păstrează 3 ani, ca probă).
    listings = await _ids("radacini_listings",
                          {"status": {"$in": list(LISTING_DONE)}, "updated_at": {"$lt": cutoff(now, 730)}, **scope})
    if listings:
        booked = {r["listing_id"] for r in await db.radacini_reservations.find(
            {"listing_id": {"$in": [str(i) for i in listings]}}, {"listing_id": 1}).to_list(LIMIT)}
        listings = [i for i in listings if str(i) not in booked]
    await delete("listings", "radacini_listings", listings)

    # 4. Raportări DSA: după 2 ani de la decizie, fără datele raportorului.
    reports = await _ids("radacini_reports", {"status": "resolved", "resolved_at": {"$lt": cutoff(now, 730)},
                                              "reporter_id": {"$exists": True}, **scope})
    if apply and reports:
        await db.radacini_reports.update_many({"_id": {"$in": reports}},
                                              {"$unset": {"reporter_id": "", "reporter_name": ""}})
    out["reports"] = {"action": "anonymize", "count": len(reports)}

    # 5. Notificări Rădăcini în aplicație: 12 luni. Colecția e comună cu PropManage și mare: citim doar notificările
    # membrilor Rădăcini și le păstrăm pe cele fără link Rădăcini.
    members = await db.radacini_members.find(scope, {"user_id": 1}).to_list(LIMIT)
    member_ids = [m["user_id"] for m in members if m.get("user_id")]
    notes = []
    for i in range(0, len(member_ids), 500):
        notes += radacini_notifications(await db.notifications.find(
            {"user_id": {"$in": member_ids[i:i + 500]}, "created_at": {"$lt": cutoff(now, 365)}, **scope},
            {"_id": 1, "link": 1}).to_list(LIMIT))
    await delete("notifications", "notifications", notes)

    # 6. Minori care au împlinit 18 ani: doar raport (întâi invitația pentru cont propriu).
    households = await db.radacini_households.find({"members.is_minor": True, **scope},
                                                   {"_id": 1, "members": 1}).to_list(LIMIT)
    adults = adult_minors(households, now.year)
    out["adult_minors"] = {"action": "report", "count": sum(a["count"] for a in adults),
                           "households": [a["household_id"] for a in adults]}

    # 7. Conturi inactive de 24 de luni: doar raport (întâi notificarea, apoi anonimizare după 30 de zile).
    seen: dict = {}
    if members:
        from bson import ObjectId
        oids = [ObjectId(m["user_id"]) for m in members if ObjectId.is_valid(str(m.get("user_id")))]
        for u in await db.users.find({"_id": {"$in": oids}}, {"_id": 1, "last_seen": 1}).to_list(LIMIT):
            seen[str(u["_id"])] = u.get("last_seen")
    out["inactive_accounts"] = {"action": "report",
                                "count": len(inactive_users(members, seen, cutoff(now, 730)))}

    if apply and not scope:
        from routes.radacini.common import audit_staff
        await audit_staff({"id": "system", "email": "radacini_retention"}, "retention_run", "system", None,
                          {k: v["count"] for k, v in out.items()})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="șterge/anonimizează (implicit doar raport)")
    args = ap.parse_args()
    res = asyncio.run(run(apply=args.apply))
    print("APLICAT" if args.apply else "DOAR RAPORT (folosește --apply ca să modifici)")
    for name, r in res.items():
        extra = f", în cascadă {r['cascade']}" if "cascade" in r else ""
        print(f"  {name:22} {r['action']:9} {r['count']}{extra}")


if __name__ == "__main__":
    main()
