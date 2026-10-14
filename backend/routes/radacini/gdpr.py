"""GDPR Rădăcini: exportul datelor utilizatorului (acces / portabilitate) și cererea de ștergere.

- `GET  /api/radacini/me/export`         — toate datele Rădăcini ale utilizatorului curent, JSON descărcabil.
- `POST /api/radacini/me/delete-request` — înregistrează o cerere de ștergere (procesare manuală, nu automată).
- `GET  /api/radacini/me/delete-request` — starea ultimei cereri.
Ștergerea efectivă se face manual, după verificarea obligațiilor legale de păstrare (acorduri semnate,
rezervări în curs); de aceea cererea doar se stochează.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from bson import ObjectId

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, SlidingWindowLimiter, mark_demo, now_iso

router = APIRouter(route_class=RadaciniRoute)

EXPORT_CAP = 5000  # documente per listă; peste această valoare lista e marcată în `truncated`
IN_CHUNK = 100  # pgmongo traduce `$in` în SQL doar până la 200 de valori
EXPORT_LIMIT, EXPORT_WINDOW = 10, 600.0  # cel mult 10 exporturi la 10 minute per utilizator
_EXPORT_LIMITER = SlidingWindowLimiter(window=EXPORT_WINDOW)

NOTES = [
    "Exportul conține datele Rădăcini asociate contului tău. Datele de cont PropManage (parolă, plăți etc.) nu fac parte din el.",
    "Mesajele din cereri includ doar cele scrise de tine; mesajele celeilalte părți aparțin acelei persoane.",
    "La acorduri, semnăturile celeilalte părți sunt reduse la identificator, versiune și dată.",
    "Jurnalul de acces la locația exactă conține accesările făcute de tine și cele asupra terenurilor tale.",
]


async def _fetch(collection: str, flt: dict, label: str, truncated: list) -> list:
    docs = await getattr(db, collection).find(flt).sort("created_at", 1).limit(EXPORT_CAP + 1).to_list(EXPORT_CAP + 1)
    if len(docs) > EXPORT_CAP:
        truncated.append(label)
        docs = docs[:EXPORT_CAP]
    return [serialize_doc(d) for d in docs]


def _only_mine(agreement: dict, uid: str) -> dict:
    """Semnăturile celeilalte părți: doar user_id, version, signed_at (fără date tehnice ale altcuiva)."""
    agreement["signatures"] = [
        s if s.get("user_id") == uid else {k: s.get(k) for k in ("user_id", "version", "signed_at") if k in s}
        for s in agreement.get("signatures") or []
    ]
    return agreement


async def _location_access(uid: str, parcel_ids: list, truncated: list) -> list:
    """Accesările locației exacte: făcute de utilizator, asupra lui (owner) sau asupra terenurilor lui."""
    by_id = {}
    flts = [{"$or": [{"owner_user_id": uid}, {"user_id": uid}]}]
    flts += [{"parcel_id": {"$in": parcel_ids[i:i + IN_CHUNK]}} for i in range(0, len(parcel_ids), IN_CHUNK)]
    for flt in flts:
        for item in await _fetch("radacini_location_access_log", flt, "location_access_log", truncated):
            by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda x: str(x.get("at") or x.get("created_at") or ""))


@router.get("/me/export")
async def export_my_data(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    if not _EXPORT_LIMITER.hit(uid, EXPORT_LIMIT):
        raise HTTPException(429, "Ai cerut deja mai multe exporturi. Încearcă din nou peste câteva minute.")
    truncated: list = []

    def fetch(collection, flt, label):
        return _fetch(collection, flt, label, truncated)

    parcels = await fetch("radacini_parcels", {"owner_user_id": uid}, "parcels")
    projects = await fetch("radacini_projects", {"member_ids": uid}, "projects")
    agreements = [_only_mine(a, uid) for a in await fetch("radacini_agreements", {"party_ids": uid}, "agreements")]
    member = await db.radacini_members.find_one({"user_id": uid})
    staff = await db.radacini_staff.find_one({"user_id": uid})
    stats = await db.radacini_seller_stats.find_one({"seller_user_id": uid})

    data = {
        "format_version": 1,
        "generated_at": now_iso(),
        "notes": NOTES,
        "account": {"id": uid, "email": user.get("email"), "name": user.get("name")},
        "member": serialize_doc(member),
        "staff": serialize_doc(staff),
        "parcels": parcels,
        "requests_sent": await fetch("radacini_land_requests", {"requester_user_id": uid}, "requests_sent"),
        "requests_received": await fetch("radacini_land_requests", {"owner_user_id": uid}, "requests_received"),
        "messages_authored": await fetch("radacini_request_messages", {"sender_user_id": uid}, "messages_authored"),
        "agreements": agreements,
        "projects": projects,
        "crop_plans_created": await fetch("radacini_crop_plans", {"created_by": uid}, "crop_plans_created"),
        "activities": await fetch(
            "radacini_activities", {"$or": [{"created_by": uid}, {"participants": uid}]}, "activities"),
        "contributions": await fetch("radacini_contributions", {"member_user_id": uid}, "contributions"),
        "harvests_recorded": await fetch(
            "radacini_harvests", {"$or": [{"recorded_by": uid}, {"confirmed_by": uid}]}, "harvests_recorded"),
        "allocations": await fetch("radacini_allocations", {"member_user_id": uid}, "allocations"),
        "listings": await fetch("radacini_listings", {"seller_user_id": uid}, "listings"),
        "reservations_as_buyer": await fetch("radacini_reservations", {"buyer_user_id": uid}, "reservations_as_buyer"),
        "reservations_as_seller": await fetch("radacini_reservations", {"seller_user_id": uid}, "reservations_as_seller"),
        "seller_stats": serialize_doc(stats),
        "location_access_log": await _location_access(uid, [p["id"] for p in parcels], truncated),
        "deletion_requests": await fetch("radacini_deletion_requests", {"user_id": uid}, "deletion_requests"),
        "truncated": sorted(set(truncated)),
    }
    return JSONResponse(
        content=jsonable_encoder(data, custom_encoder={ObjectId: str}),
        headers={"Content-Disposition": 'attachment; filename="radacini-datele-mele.json"', "Cache-Control": "no-store"},
    )


@router.post("/me/delete-request")
async def request_deletion(user: dict = Depends(get_current_user)):
    # Un admin care vede contul prin impersonare nu poate cere ștergerea datelor în numele utilizatorului.
    block_in_impersonation(user, "cererea de ștergere a datelor")
    uid = str(user["id"])
    doc = mark_demo({"user_id": uid, "at": now_iso(), "status": "pending"})
    # Upsert serializat de pgmongo: două cereri simultane nu pot crea două cereri „pending”.
    res = await db.radacini_deletion_requests.update_one(
        {"user_id": uid, "status": "pending"}, {"$setOnInsert": doc}, upsert=True
    )
    if res.upserted_id is None:
        raise HTTPException(409, "Ai deja o cerere de ștergere în curs de procesare.")
    doc["_id"] = res.upserted_id
    await emit("radacini.deletion_requested", actor=user, payload={"request_id": str(res.upserted_id)})
    return {"request": serialize_doc(doc)}


@router.get("/me/delete-request")
async def my_deletion_request(user: dict = Depends(get_current_user)):
    docs = await db.radacini_deletion_requests.find({"user_id": str(user["id"])}).sort("at", -1).limit(1).to_list(1)
    return {"request": serialize_doc(docs[0]) if docs else None}
