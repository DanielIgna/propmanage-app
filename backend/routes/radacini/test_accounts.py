"""Conturi de test Rădăcini pentru super-admin (fără parolă: se intră doar prin impersonare PropManage)."""
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from .bridge import db, get_current_user, is_super_admin
from .common import RadaciniRoute, audit_staff, now_iso, today_bucharest
from .constants import COUNTY, LEGAL_NOTICE
from .harvests import owner_share
from .market import product_key, product_tokens

log = logging.getLogger(__name__)

router = APIRouter(route_class=RadaciniRoute)

EMAIL_DOMAIN = "test.radacini.ro"

PERSONAS = [
    {"key": "proprietar", "name": "Ion Pop", "label": "Proprietar de teren", "locality": "Florești",
     "interests": ["land"], "staff": None,
     "description": "Adaugă un teren, trimite-l la verificare, primește cereri și negociază acorduri."},
    {"key": "familie", "name": "Maria Ionescu", "label": "Familie care vrea să cultive", "locality": "Cluj-Napoca",
     "interests": ["grow", "consume", "community"], "staff": None,
     "description": "Caută terenuri, trimite cereri, face parte din proiecte și rezervă produse locale."},
    {"key": "producator", "name": "Elena Mureșan", "label": "Producător local", "locality": "Gilău",
     "interests": ["grow", "sell", "exchange"], "staff": None,
     "description": "Publică anunțuri în piață, gestionează rezervări și recolte."},
    {"key": "consumator", "name": "Andrei Rusu", "label": "Consumator", "locality": "Apahida",
     "interests": ["consume"], "staff": None,
     "description": "Răsfoiește piața locală, rezervă produse și le evaluează."},
    {"key": "operator", "name": "Vasile Crișan", "label": "Operator (Florești, Gilău)", "locality": "Florești",
     "interests": ["community"], "staff": {"role": "operator", "areas": ["Florești", "Gilău"]},
     "description": "Verifică terenurile din zona sa în coada de verificare."},
    {"key": "manager", "name": "Ana Pavel", "label": "Manager", "locality": "Cluj-Napoca",
     "interests": ["community"], "staff": {"role": "manager", "areas": []},
     "description": "Gestionează personalul și verifică terenuri din toate localitățile."},
]


def _email(key: str) -> str:
    return f"{key}@{EMAIL_DOMAIN}"


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if not is_super_admin(user):
        raise HTTPException(403, "Acces doar pentru super-admin.")
    return user


@router.get("/test-accounts")
async def list_test_accounts(user: dict = Depends(require_super_admin)):
    items = []
    for p in PERSONAS:
        u = await db.users.find_one({"email": _email(p["key"])})
        is_persona = bool(u and u.get("radacini_test_persona") == p["key"])
        uid = str(u["_id"]) if is_persona else None
        member = await db.radacini_members.find_one({"user_id": uid}) if uid else None
        staff = await db.radacini_staff.find_one({"user_id": uid}) if uid and p["staff"] else None
        items.append({
            "key": p["key"], "name": p["name"], "label": p["label"], "locality": p["locality"],
            "description": p["description"], "email": _email(p["key"]),
            "staff_role": (p["staff"] or {}).get("role"),
            "user_id": uid, "conflict": bool(u and not is_persona),
            "has_member": bool(member), "has_staff": bool(staff) if p["staff"] else None,
        })
    return {"items": items}


async def _ensure(admin: dict) -> list:
    # Verificare prealabilă: nu atingem niciun utilizator existent care nu e persona de test.
    for p in PERSONAS:
        u = await db.users.find_one({"email": _email(p["key"])})
        if u and u.get("radacini_test_persona") != p["key"]:
            raise HTTPException(409, f"Emailul {_email(p['key'])} aparține unui cont existent care nu e de test.")

    now = now_iso()
    created = []
    for p in PERSONAS:
        email = _email(p["key"])
        u = await db.users.find_one({"email": email})
        if not u:
            res = await db.users.insert_one({
                "email": email, "name": p["name"], "role": "client", "tier": None,
                "phone": "+40 712 000 000",
                # parolă aleatoare, necomunicată: contul se folosește doar prin impersonare
                "password_hash": bcrypt.hashpw(secrets.token_urlsafe(24).encode(), bcrypt.gensalt()).decode(),
                "email_verified": True, "is_active": True, "is_demo_account": True,
                "radacini_test_persona": p["key"], "created_at": now, "updated_at": now,
            })
            uid = str(res.inserted_id)
            created.append(p["key"])
        else:
            uid = str(u["_id"])
        await db.radacini_members.update_one(
            {"user_id": uid},
            {"$setOnInsert": {"user_id": uid, "interests": p["interests"], "county": COUNTY,
                              "locality": p["locality"], "bio": None, "created_at": now, "is_demo": True},
             "$set": {"updated_at": now}},
            upsert=True,
        )
        if p["staff"]:
            await db.radacini_staff.update_one(
                {"user_id": uid},
                {"$setOnInsert": {"user_id": uid, "email": email, "name": p["name"], "role": p["staff"]["role"],
                                  "areas": p["staff"]["areas"], "created_at": now,
                                  "created_by": str(admin["id"]), "is_demo": True}},
                upsert=True,
            )
    return created


@router.post("/test-accounts/ensure")
async def ensure_test_accounts(admin: dict = Depends(require_super_admin)):
    created = await _ensure(admin)
    await audit_staff(admin, "test_accounts.ensure", "radacini_test_accounts", None, {"created": created})
    return {"ok": True, "created": created}


# ----------------------------------------------------------------- scenariu demo

COLLECTIONS = [
    "radacini_parcels", "radacini_land_requests", "radacini_request_messages", "radacini_agreements",
    "radacini_projects", "radacini_crop_plans", "radacini_activities", "radacini_contributions",
    "radacini_harvests", "radacini_allocations", "radacini_listings", "radacini_reservations",
    "radacini_seller_stats",
]
SEED_TAG = {"is_demo": True, "demo_seed": True}


def _tag(doc: dict) -> dict:
    return {**doc, **SEED_TAG}


async def _persona_ids() -> dict:
    ids = {}
    for p in PERSONAS:
        u = await db.users.find_one({"email": _email(p["key"])})
        if not u or u.get("radacini_test_persona") != p["key"]:
            raise HTTPException(409, f"Contul de test {_email(p['key'])} lipsește sau nu e cont de test.")
        ids[p["key"]] = str(u["_id"])
    return ids


def _build_scenario(U: dict) -> dict:
    """Documentele scenariului demo, pe colecții (id-urile se generează aici, ca referințele să fie consistente)."""
    now = datetime.now(timezone.utc)
    today = today_bucharest()

    def ts(days: float = 0, hours: float = 0) -> str:
        return (now - timedelta(days=days, hours=hours)).isoformat()

    def d(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    name = {p["key"]: p["name"] for p in PERSONAS}
    ion, maria, elena, andrei, vasile = U["proprietar"], U["familie"], U["producator"], U["consumator"], U["operator"]
    oid = ObjectId
    P1, P2, P3, P4, P5 = (oid() for _ in range(5))
    A1, A2, PR1 = oid(), oid(), oid()
    R1, R2, R3, R4, R5 = (oid() for _ in range(5))
    C_ROS, C_CAS, C_FAS = oid(), oid(), oid()
    ACT_DONE, ACT_WORK, ACT_IRR = oid(), oid(), oid()
    H1, H2 = oid(), oid()
    L1, L2, L3, L4, L5 = (oid() for _ in range(5))
    sid = str

    def verification(at):
        return {"by": vasile, "at": at, "decision": "approve", "note": "Teren verificat pe teren, date corecte."}

    parcels = [
        {"_id": P1, "owner_user_id": ion, "title": "Grădină lângă Florești, 0,5 ha", "county": COUNTY,
         "locality": "Florești", "lat": 46.7425, "lng": 23.488, "area_m2": 5000,
         "access": "Drum asfaltat până la poartă, loc de parcare la intrare.",
         "water_sources": ["well", "network"], "current_crops": ["Iarbă de cosit"],
         "description": "Grădină îngrijită, împrejmuită, cu sol lutos-nisipos și fântână în colț. "
                        "Ideală pentru legume de sezon.",
         "availability_from": d(-10), "availability_to": d(365),
         "offer": {"models": ["rent", "harvest_share"], "terms": "Preferăm un contract pe cel puțin un sezon.",
                   "price_ron_per_year": 1500, "harvest_share_percent": 25},
         "status": "published", "verification": verification(ts(25)), "created_at": ts(30), "updated_at": ts(25)},
        {"_id": P2, "owner_user_id": ion, "title": "Teren arabil Gilău, 1 ha", "county": COUNTY,
         "locality": "Gilău", "lat": 46.753, "lng": 23.387, "area_m2": 10000,
         "access": "Drum de pământ, accesibil cu mașina pe vreme uscată.",
         "water_sources": ["river"], "current_crops": ["Grâu"],
         "description": "Teren arabil plat, lângă pârâu, fără construcții.",
         "availability_from": d(15), "availability_to": d(380),
         "offer": {"models": ["rent"], "terms": None, "price_ron_per_year": 2400, "harvest_share_percent": None},
         "status": "pending_verification", "created_at": ts(2), "updated_at": ts(1)},
        {"_id": P3, "owner_user_id": ion, "title": "Livadă bătrână Baciu", "county": COUNTY,
         "locality": "Baciu", "lat": 46.77, "lng": 23.48, "area_m2": 3000,
         "access": "", "water_sources": [], "current_crops": ["Meri", "Pruni"],
         "description": "", "offer": {"models": ["rent"], "terms": None, "price_ron_per_year": 900,
                                       "harvest_share_percent": None},
         "status": "draft", "created_at": ts(1), "updated_at": ts(1)},
        {"_id": P4, "owner_user_id": ion, "title": "Teren familie Florești 2000 m²", "county": COUNTY,
         "locality": "Florești", "lat": 46.739, "lng": 23.495, "area_m2": 2000,
         "access": "Acces pietonal și auto prin curtea proprietarului.",
         "water_sources": ["well"], "current_crops": [],
         "description": "Teren pentru o familie care vrea să cultive legume pentru consum propriu.",
         "availability_from": d(-60), "availability_to": d(300),
         "offer": {"models": ["harvest_share"], "terms": None, "price_ron_per_year": None,
                   "harvest_share_percent": 25},
         "status": "paused", "active_agreement_id": sid(A1), "verification": verification(ts(60)),
         "created_at": ts(65), "updated_at": ts(30)},
        {"_id": P5, "owner_user_id": elena, "title": "Solar Gilău 800 m²", "county": COUNTY,
         "locality": "Gilău", "lat": 46.751, "lng": 23.379, "area_m2": 800,
         "access": "Drum asfaltat, la 200 m de centru.", "water_sources": ["well", "irrigation"],
         "current_crops": ["Roșii"],
         "description": "Solar cu irigare prin picurare, pregătit pentru sezonul următor.",
         "availability_from": d(0), "availability_to": d(200),
         "offer": {"models": ["fixed_fee"], "terms": "Taxa include apa de irigat.",
                   "price_ron_per_year": 400, "harvest_share_percent": None},
         "status": "published", "verification": verification(ts(12)), "created_at": ts(14), "updated_at": ts(12)},
    ]

    def proposal(area, start, end, price=None, share=None, crops=None, note=None):
        return {"area_m2": area, "start_date": start, "end_date": end, "price_ron_per_year": price,
                "harvest_share_percent": share, "crops": crops or [], "note": note}

    pr_maria_p1 = proposal(800, d(10), d(190), price=1200, crops=["Roșii", "Ardei"],
                           note="Căutăm un teren aproape de oraș pentru legume pentru familie.")
    pr_elena_a = proposal(1500, d(10), d(200), share=20, crops=["Roșii", "Castraveți"],
                          note="Aș cultiva legume pentru piața locală.")
    pr_ion_b = proposal(1500, d(10), d(200), share=30, crops=["Roșii", "Castraveți"])
    pr_elena_c = proposal(1200, d(12), d(200), share=25, crops=["Roșii", "Castraveți"],
                          note="Reduc suprafața și accept 25%, conform ofertei.")
    requests = [
        {"_id": R1, "parcel_id": sid(P1), "owner_user_id": ion, "requester_user_id": maria, "model": "rent",
         "proposal": pr_maria_p1, "proposal_by_user_id": maria, "proposal_at": ts(1), "proposals_history": [],
         "status": "sent", "last_activity_at": ts(1), "created_at": ts(1), "updated_at": ts(1)},
        {"_id": R2, "parcel_id": sid(P1), "owner_user_id": ion, "requester_user_id": elena, "model": "harvest_share",
         "proposal": pr_elena_c, "proposal_by_user_id": elena, "proposal_at": ts(0, 5),
         "proposals_history": [
             {"proposal": pr_elena_a, "by_user_id": elena, "at": ts(6)},
             {"proposal": pr_ion_b, "by_user_id": ion, "at": ts(3)},
         ],
         "status": "negotiating", "last_activity_at": ts(0, 4), "created_at": ts(6), "updated_at": ts(0, 4)},
        {"_id": R3, "parcel_id": sid(P5), "owner_user_id": elena, "requester_user_id": andrei, "model": "fixed_fee",
         "proposal": proposal(800, d(-20), d(150), price=400, crops=["Salată"]),
         "proposal_by_user_id": andrei, "proposal_at": ts(22), "proposals_history": [],
         "status": "declined", "decline_reason": "Solarul e rezervat pentru răsaduri în prima parte a sezonului.",
         "decided_at": ts(20), "last_activity_at": ts(20), "created_at": ts(22), "updated_at": ts(20)},
        {"_id": R4, "parcel_id": sid(P4), "owner_user_id": ion, "requester_user_id": maria,
         "model": "harvest_share",
         "proposal": proposal(1500, d(-30), d(150), share=25, crops=["Roșii", "Castraveți", "Fasole"],
                              note="Vrem să cultivăm legume pentru familie și vecini."),
         "proposal_by_user_id": maria, "proposal_at": ts(45), "proposals_history": [],
         "status": "accepted", "agreement_id": sid(A1), "decided_at": ts(40),
         "last_activity_at": ts(40), "created_at": ts(45), "updated_at": ts(40)},
        {"_id": R5, "parcel_id": sid(P5), "owner_user_id": elena, "requester_user_id": andrei, "model": "fixed_fee",
         "proposal": proposal(500, d(7), d(180), price=400, crops=["Salată", "Ridichi"],
                              note="Aș lua doar o parte din solar."),
         "proposal_by_user_id": andrei, "proposal_at": ts(6), "proposals_history": [],
         "status": "accepted", "agreement_id": sid(A2), "decided_at": ts(4),
         "last_activity_at": ts(4), "created_at": ts(6), "updated_at": ts(4)},
    ]
    messages = [
        {"request_id": sid(R2), "sender_user_id": elena, "created_at": ts(6),
         "text": "Bună ziua! Aș vrea să cultiv legume aici și să vând surplusul în piața locală."},
        {"request_id": sid(R2), "sender_user_id": ion, "created_at": ts(3),
         "text": "Bună! Mă interesează, dar aș vrea 30% din recoltă. Ce spuneți?"},
        {"request_id": sid(R2), "sender_user_id": elena, "created_at": ts(0, 5),
         "text": "Pot face 25%, cu suprafață puțin mai mică. Am trimis o contrapropunere."},
    ]

    a1_terms = {"area_m2": 1500, "start_date": d(-30), "end_date": d(150), "price_ron_per_year": None,
                "harvest_share_percent": 25, "crops": ["Roșii", "Castraveți", "Fasole"], "custom_clauses": None,
                "parcel_snapshot": {"title": "Teren familie Florești 2000 m²", "locality": "Florești",
                                    "area_m2": 2000}}
    a2_terms = {"area_m2": 500, "start_date": d(7), "end_date": d(180), "price_ron_per_year": 400,
                "harvest_share_percent": None, "crops": ["Salată", "Ridichi"], "custom_clauses": None,
                "parcel_snapshot": {"title": "Solar Gilău 800 m²", "locality": "Gilău", "area_m2": 800}}
    agreements = [
        {"_id": A1, "request_id": sid(R4), "parcel_id": sid(P4),
         "parties": [{"user_id": ion, "role": "owner", "name": name["proprietar"]},
                     {"user_id": maria, "role": "cultivator", "name": name["familie"]}],
         "party_ids": [ion, maria], "model": "harvest_share", "terms": a1_terms, "version": 1,
         "versions_history": [], "terms_by_user_id": ion, "terms_at": ts(40),
         "signatures": [{"user_id": maria, "version": 1, "signed_at": ts(36)},
                        {"user_id": ion, "version": 1, "signed_at": ts(35)}],
         "status": "signed", "signed_at": ts(35), "legal_notice": LEGAL_NOTICE,
         "created_at": ts(40), "updated_at": ts(35)},
        {"_id": A2, "request_id": sid(R5), "parcel_id": sid(P5),
         "parties": [{"user_id": elena, "role": "owner", "name": name["producator"]},
                     {"user_id": andrei, "role": "cultivator", "name": name["consumator"]}],
         "party_ids": [elena, andrei], "model": "fixed_fee", "terms": a2_terms, "version": 1,
         "versions_history": [], "terms_by_user_id": elena, "terms_at": ts(4),
         "signatures": [{"user_id": elena, "version": 1, "signed_at": ts(3)}],
         "status": "proposed", "legal_notice": LEGAL_NOTICE, "created_at": ts(4), "updated_at": ts(3)},
    ]

    members = [
        {"user_id": ion, "name": name["proprietar"], "role": "owner", "joined_at": ts(35)},
        {"user_id": maria, "name": name["familie"], "role": "coordinator", "joined_at": ts(35)},
        {"user_id": andrei, "name": name["consumator"], "role": "participant", "joined_at": ts(30)},
    ]
    projects = [{
        "_id": PR1, "agreement_id": sid(A1), "parcel_id": sid(P4), "title": "Teren familie Florești 2000 m²",
        "locality": "Florești", "area_m2": 1500, "start_date": d(-30), "end_date": d(150),
        "members": members, "member_ids": [ion, maria, andrei], "status": "active", "rev": 1,
        "created_at": ts(35), "updated_at": ts(30),
    }]
    pr = sid(PR1)

    def crop(_id, label, cid, family, area, sow, harvest, yield_kg, status, notes, created):
        return {"_id": _id, "project_id": pr, "crop": label, "crop_id": cid, "family": family, "area_m2": area,
                "sow_date": sow, "expected_harvest_date": harvest, "expected_yield_kg": yield_kg,
                "notes": notes, "status": status, "created_by": maria, "created_at": created, "updated_at": created}

    crops = [
        crop(C_ROS, "Roșii", "rosii", "solanacee", 600, d(-25), d(45), 900, "growing",
             "Soi timpuriu, legate pe araci.", ts(34)),
        crop(C_CAS, "Castraveți", "castraveti", "cucurbitacee", 300, d(-15), d(30), 250, "growing",
             "Pe spalier, lângă gard.", ts(33)),
        crop(C_FAS, "Fasole", "fasole", "leguminoase", 200, d(10), d(90), 120, "planned",
             "După roșii, pentru îmbogățirea solului.", ts(32)),
    ]
    activities = [
        {"_id": ACT_DONE, "project_id": pr, "type": "planting", "title": "Plantat răsaduri de roșii",
         "date": d(-25), "start_time": "09:00", "duration_h": 5, "slots": None, "crop_plan_id": sid(C_ROS),
         "notes": None, "participants": [maria, ion], "status": "done", "rev": 1, "done_at": ts(25),
         "done_by": maria, "created_by": maria, "created_at": ts(33), "updated_at": ts(25)},
        {"_id": ACT_WORK, "project_id": pr, "type": "work_day", "title": "Zi de lucru: pliviri și legat roșii",
         "date": d(5), "start_time": "08:30", "duration_h": 4, "slots": 4, "crop_plan_id": sid(C_ROS),
         "notes": "Aduceți mănuși și apă. Sculele sunt la fața locului.", "participants": [maria],
         "status": "scheduled", "rev": 1, "created_by": maria, "created_at": ts(3), "updated_at": ts(2)},
        {"_id": ACT_IRR, "project_id": pr, "type": "irrigation", "title": "Irigare castraveți",
         "date": d(2), "start_time": "07:30", "duration_h": 1.5, "slots": None, "crop_plan_id": sid(C_CAS),
         "notes": None, "participants": [], "status": "scheduled", "rev": 0, "created_by": maria,
         "created_at": ts(3), "updated_at": ts(3)},
    ]

    def contrib(member, kind, amount, unit, desc, day, status, created, activity=None, reviewer=None):
        c = {"project_id": pr, "member_user_id": member, "member_name": name[_KEY[member]], "kind": kind,
             "amount": amount, "unit": unit, "description": desc, "activity_id": activity, "date": day,
             "status": status, "corrects_id": None, "created_at": created}
        if reviewer:
            c.update({"reviewed_by": reviewer, "reviewed_at": ts(20)})
        return c

    _KEY = {U[k]: k for k in U}
    contributions = [
        contrib(maria, "labor_hours", 6, "ore", "Plantat și udat răsadurile de roșii", d(-25), "confirmed",
                ts(25), sid(ACT_DONE), reviewer=ion),
        contrib(andrei, "materials", 10, "kg", "Compost adus pentru stratul de castraveți", d(-4), "logged", ts(4)),
        contrib(maria, "money", 120, "RON", "Semințe și răsaduri", d(-28), "confirmed", ts(28), reviewer=ion),
    ]

    harvests = [
        {"_id": H1, "project_id": pr, "crop_plan_id": sid(C_ROS), "crop": "Roșii", "quantity_kg": 80.0,
         "date": d(-3), "note": "Prima cules, roșii coapte bine.", "recorded_by": maria, "status": "confirmed",
         "rev": 3, "created_at": ts(3), "confirmed_by": ion, "confirmed_at": ts(2)},
        {"_id": H2, "project_id": pr, "crop_plan_id": sid(C_CAS), "crop": "Castraveți", "quantity_kg": 15.0,
         "date": d(-1), "note": "Primii castraveți.", "recorded_by": maria, "status": "recorded", "rev": 0,
         "created_at": ts(1)},
    ]
    h1 = sid(H1)
    share = owner_share(80.0, 25)  # 20 kg

    def alloc(member, qty, basis, created_by, created, status="allocated", extra=None):
        a = {"harvest_id": h1, "project_id": pr, "member_user_id": member, "member_name": name[_KEY[member]],
             "quantity_kg": qty, "basis": basis, "status": status, "created_by": created_by, "created_at": created}
        a.update(extra or {})
        return a

    allocations = [
        alloc(ion, share, "agreement_share", ion, ts(2)),
        alloc(maria, 40.0, "manual", maria, ts(2), "received", {"received_at": ts(1)}),
        alloc(andrei, 10.0, "manual", maria, ts(2)),
    ]

    def listing(_id, seller, product, category, unit, total, available, price, mode, exchange_for, locality,
                pickup, until, created):
        return {"_id": _id, "seller_user_id": seller, "seller_name": name[_KEY[seller]], "product": product,
                "product_key": product_key(product), "product_tokens": product_tokens(product),
                "category": category, "unit": unit, "quantity_total": float(total),
                "quantity_available": float(available), "price_ron_per_unit": price, "mode": mode,
                "exchange_for": exchange_for, "locality": locality, "pickup_details": pickup,
                "available_until": until, "project_id": None, "status": "active",
                "created_at": created, "updated_at": created}

    listings = [
        listing(L1, elena, "Roșii", "legume", "kg", 30, 30, 9.0, "sale", None, "Gilău",
                "Roșii de grădină, culese în ziua ridicării. Sâmbăta 9-12, în Gilău.", d(10), ts(5)),
        listing(L2, elena, "Ouă de țară", "ouă", "buc", 60, 50, 1.5, "both", "legume de sezon", "Gilău",
                "De la găini crescute în curte. Ridicare în Gilău, seara după 17:00.", d(14), ts(6)),
        listing(L3, elena, "Miere polifloră", "miere", "borcan", 10, 9, 35.0, "sale", None, "Gilău",
                "Borcane de 500 g. Ridicare în Gilău, cu programare.", d(30), ts(8)),
        listing(L4, maria, "Castraveți", "legume", "kg", 8, 8, None, "exchange", "ouă sau brânză", "Cluj-Napoca",
                "Din proiectul nostru de la Florești. Ridicare în Cluj-Napoca, în weekend.", d(7), ts(1)),
        listing(L5, ion, "Roșii", "legume", "kg", 20, 20, 11.0, "sale", None, "Florești",
                "Roșii din grădina proprie. Ridicare în Florești, în fiecare seară.", d(10), ts(4)),
    ]
    # Cantitățile disponibile: L2 are 10 buc confirmate (60 - 10), L3 are 1 borcan ridicat (10 - 1).

    def reservation(listing_id, seller, buyer, qty, mode, status, created, offer=None, message=None, extra=None):
        r = {"listing_id": sid(listing_id), "seller_user_id": seller, "seller_name": name[_KEY[seller]],
             "buyer_user_id": buyer, "buyer_name": name[_KEY[buyer]], "quantity": float(qty), "mode": mode,
             "exchange_offer": offer, "message": message, "status": status, "created_at": created,
             "updated_at": created}
        r.update(extra or {})
        return r

    reservations = [
        reservation(L1, elena, andrei, 3, "cash_on_pickup", "requested", ts(0, 6),
                    message="Pot trece sâmbătă dimineață?"),
        reservation(L2, elena, andrei, 10, "cash_on_pickup", "confirmed", ts(3), extra={"updated_at": ts(2)}),
        reservation(L3, elena, andrei, 1, "cash_on_pickup", "picked_up", ts(7), extra={
            "updated_at": ts(5), "rating": 5, "rating_comment": "Miere excelentă, vânzătoare foarte amabilă!",
            "rated_at": ts(5)}),
        reservation(L2, elena, maria, 12, "exchange", "requested", ts(0, 3), offer="2 kg castraveți",
                    message="Putem face schimbul în weekend?"),
    ]
    stats = [{"seller_user_id": elena, "rating_sum": 5, "rating_count": 1, "created_at": ts(5), "updated_at": ts(5)}]

    return {
        "radacini_parcels": parcels, "radacini_land_requests": requests, "radacini_request_messages": messages,
        "radacini_agreements": agreements, "radacini_projects": projects, "radacini_crop_plans": crops,
        "radacini_activities": activities, "radacini_contributions": contributions,
        "radacini_harvests": harvests, "radacini_allocations": allocations, "radacini_listings": listings,
        "radacini_reservations": reservations, "radacini_seller_stats": stats,
    }


async def _delete_seed() -> dict:
    """Șterge documentele cu `demo_seed` și dependențele lor create ulterior (fără `demo_seed`)."""
    coll = lambda n: getattr(db, n)  # noqa: E731
    counts = {n: 0 for n in COLLECTIONS}

    def flt(**in_fields) -> dict:
        clauses = [{"demo_seed": True}] + [{f: {"$in": ids}} for f, ids in in_fields.items() if ids]
        return clauses[0] if len(clauses) == 1 else {"$or": clauses}

    async def ids(name: str, f: dict) -> list:
        rows = await coll(name).find(f, {"_id": 1}).to_list(5000)
        return [str(r["_id"]) for r in rows]

    async def delete(name: str, f: dict) -> None:
        res = await coll(name).delete_many(f)
        counts[name] += res.deleted_count

    parcel_ids = await ids("radacini_parcels", {"demo_seed": True})
    listing_ids = await ids("radacini_listings", {"demo_seed": True})
    req_ids = await ids("radacini_land_requests", flt(parcel_id=parcel_ids))
    agr_ids = await ids("radacini_agreements", flt(parcel_id=parcel_ids, request_id=req_ids))
    proj_ids = await ids("radacini_projects", flt(parcel_id=parcel_ids, agreement_id=agr_ids))
    harv_ids = await ids("radacini_harvests", flt(project_id=proj_ids))
    res_flt = flt(listing_id=listing_ids)
    sellers = sorted({r["seller_user_id"] for r in await coll("radacini_reservations").find(
        res_flt, {"seller_user_id": 1}).to_list(5000)})

    if req_ids:
        await delete("radacini_request_messages", {"request_id": {"$in": req_ids}})
    await delete("radacini_request_messages", {"demo_seed": True})
    await delete("radacini_allocations", flt(harvest_id=harv_ids, project_id=proj_ids))
    await delete("radacini_harvests", flt(project_id=proj_ids))
    for n in ("radacini_contributions", "radacini_activities", "radacini_crop_plans"):
        await delete(n, flt(project_id=proj_ids))
    if proj_ids:  # anunțurile rămase nu mai trebuie să trimită la proiecte șterse
        await coll("radacini_listings").update_many({"project_id": {"$in": proj_ids}}, {"$set": {"project_id": None}})
    await delete("radacini_projects", flt(parcel_id=parcel_ids, agreement_id=agr_ids))
    await delete("radacini_agreements", flt(parcel_id=parcel_ids, request_id=req_ids))
    await delete("radacini_land_requests", flt(parcel_id=parcel_ids))
    await delete("radacini_reservations", res_flt)
    await delete("radacini_listings", {"demo_seed": True})
    await delete("radacini_parcels", {"demo_seed": True})
    # Ratingul se recalculează leneș din rezervările rămase, deci statisticile vânzătorilor afectați se șterg.
    await delete("radacini_seller_stats", flt(seller_user_id=sellers))
    return counts


@router.post("/test-accounts/seed")
async def seed_demo_scenario(admin: dict = Depends(require_super_admin)):
    await _ensure(admin)
    for name in COLLECTIONS:
        if await getattr(db, name).find_one({"demo_seed": True}, {"_id": 1}):
            raise HTTPException(409, "Datele demo există deja. Resetează-le întâi.")
    scenario = _build_scenario(await _persona_ids())
    counts: dict = {}
    try:
        for name, docs in scenario.items():
            if docs:
                await getattr(db, name).insert_many([_tag(x) for x in docs])
            counts[name] = len(docs)
    except Exception:
        log.exception("radacini: scenariul demo nu a putut fi creat; se curăță documentele inserate")
        await _delete_seed()
        raise HTTPException(500, "Scenariul demo nu a putut fi creat. Nu s-a păstrat nimic.")
    await audit_staff(admin, "test_accounts.seed", "radacini_test_accounts", None, {"counts": counts, "total": sum(counts.values())})
    return {"ok": True, "counts": counts, "total": sum(counts.values())}


@router.post("/test-accounts/reset")
async def reset_demo_scenario(admin: dict = Depends(require_super_admin)):
    counts = await _delete_seed()
    await audit_staff(admin, "test_accounts.reset", "radacini_test_accounts", None, {"counts": counts, "total": sum(counts.values())})
    return {"ok": True, "counts": counts, "total": sum(counts.values())}
