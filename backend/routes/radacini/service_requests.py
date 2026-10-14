"""Prestatori și cereri de lucrări mecanizate. Fără plăți în platformă: prețul e orientativ, plata se face direct."""
import logging
import math
from datetime import date as _Date  # câmpurile `window_*` folosesc tipul; evităm umbrirea
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .legal_terms import require_terms
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify
from .constants import LOCALITIES
from .projects import ensure_active, load_project, need_coordinator, project_link, today_str

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

SERVICE_TYPES = [
    {"id": "arat", "label": "Arat"},
    {"id": "discuit", "label": "Discuit"},
    {"id": "frezat", "label": "Frezat"},
    {"id": "semanat_mecanizat", "label": "Semănat mecanizat"},
    {"id": "irigatii", "label": "Irigații"},
    {"id": "transport", "label": "Transport"},
    {"id": "consultanta_agronomica", "label": "Consultanță agronomică"},
    {"id": "tratamente", "label": "Tratamente"},
]
SERVICE_TYPE_IDS = {s["id"] for s in SERVICE_TYPES}
MAX_NOTIFIED = 50
MAX_PRICE = 1_000_000
_CAS_TRIES = 6


# ----------------------------------------------------------------- scheme

class ProviderIn(BaseModel):
    services: list[str]
    localities: list[str]
    note: Optional[str] = None
    active: bool = True

    @field_validator("services")
    @classmethod
    def _services(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))
        if not v:
            raise ValueError("Alege cel puțin un serviciu.")
        if any(s not in SERVICE_TYPE_IDS for s in v):
            raise ValueError("Serviciu necunoscut.")
        return v

    @field_validator("localities")
    @classmethod
    def _localities(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))
        if not 1 <= len(v) <= 20:
            raise ValueError("Alege între 1 și 20 de localități.")
        if any(loc not in LOCALITIES for loc in v):
            raise ValueError("Localitate necunoscută.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Nota are cel mult 500 de caractere.")
        return v or None


class ServiceRequestIn(BaseModel):
    service_type: str
    description: str
    area_m2: Optional[float] = None
    window_from: _Date
    window_to: _Date
    locality: str

    @field_validator("service_type")
    @classmethod
    def _service(cls, v: str) -> str:
        if v not in SERVICE_TYPE_IDS:
            raise ValueError("Serviciu necunoscut.")
        return v

    @field_validator("description")
    @classmethod
    def _description(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 1000:
            raise ValueError("Descrierea trebuie să aibă între 3 și 1000 de caractere.")
        return v

    @field_validator("area_m2")
    @classmethod
    def _area(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if not math.isfinite(v) or not 0 < v <= 100_000_000:
            raise ValueError("Suprafața trebuie să fie un număr pozitiv.")
        return v

    @field_validator("locality")
    @classmethod
    def _locality(cls, v: str) -> str:
        if v not in LOCALITIES:
            raise ValueError("Localitate necunoscută.")
        return v


class OfferIn(BaseModel):
    price_ron_indicative: Optional[float] = None
    message: str = ""

    @field_validator("price_ron_indicative")
    @classmethod
    def _price(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if not math.isfinite(v) or not 0 <= v <= MAX_PRICE:
            raise ValueError("Prețul orientativ trebuie să fie între 0 și 1 000 000 RON.")
        return round(v, 2)

    @field_validator("message")
    @classmethod
    def _message(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Mesajul are cel mult 500 de caractere.")
        return v


class AssignIn(BaseModel):
    provider_user_id: str


class DoneIn(BaseModel):
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def _rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Evaluarea trebuie să fie între 1 și 5.")
        return v

    @field_validator("comment")
    @classmethod
    def _comment(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Comentariul are cel mult 500 de caractere.")
        return v or None


# ----------------------------------------------------------------- helperi

def _rating_view(doc: dict) -> dict:
    count = int(doc.get("rating_count") or 0)
    total = doc.get("rating_sum") or 0
    return {"rating_count": count, "rating_avg": round(total / count, 2) if count else None}


def _provider_public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "services": doc.get("services", []),
        "localities": doc.get("localities", []),
        "note": doc.get("note"),
        **_rating_view(doc),
    }


def _provider_me(doc: dict) -> dict:
    return {**_provider_public(doc), "user_id": doc["user_id"], "active": bool(doc.get("active", True))}


async def _provider(user_id: str) -> Optional[dict]:
    return await db.radacini_providers.find_one({"user_id": str(user_id)})


def _request_view(doc: dict, uid: str, *, coordinator: bool, project: Optional[dict] = None) -> dict:
    out = serialize_doc(doc)
    out.pop("rev", None)
    offers = doc.get("offers", [])
    if not coordinator:  # prestatorul vede doar oferta proprie
        offers = [o for o in offers if o.get("provider_user_id") == uid]
    out["offers"] = offers
    out["offers_count"] = len(doc.get("offers", []))
    if project is not None:
        out["project_title"] = project.get("title")
    return out


async def _load_request(request_id: str, user: dict) -> tuple[dict, dict, str, Optional[str]]:
    req = await db.radacini_service_requests.find_one({"_id": oid_or_404(request_id)})
    if not req:
        raise HTTPException(404, "Cererea nu există.")
    project, access, role = await load_project(req["project_id"], user)
    return req, project, access, role


async def _cas(req: dict, fields: dict, status_in: tuple) -> bool:
    rev = req.get("rev", 0)
    res = await db.radacini_service_requests.update_one(
        {"_id": req["_id"], "rev": rev, "status": {"$in": list(status_in)}},
        {"$set": {**fields, "rev": rev + 1, "updated_at": now_iso()}},
    )
    return res.modified_count == 1


async def _reload(req: dict) -> dict:
    fresh = await db.radacini_service_requests.find_one({"_id": req["_id"]})
    if not fresh:
        raise HTTPException(404, "Cererea nu există.")
    return fresh


def _label(service_type: str) -> str:
    return next((s["label"] for s in SERVICE_TYPES if s["id"] == service_type), service_type)


# ----------------------------------------------------------------- rute: catalog și prestatori

@router.get("/service-types")
async def service_types(user: dict = Depends(get_current_user)):
    return {"items": SERVICE_TYPES}


@router.get("/providers/me")
async def get_my_provider(user: dict = Depends(get_current_user)):
    doc = await _provider(user["id"])
    if not doc:
        return {"exists": False}
    return {"exists": True, "provider": _provider_me(doc)}


@router.put("/providers/me")
async def put_my_provider(body: ProviderIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "profilul de prestator")
    uid = str(user["id"])
    now = now_iso()
    # Upsert pe user_id (serializat de pgmongo); evaluările se păstrează între salvări.
    await db.radacini_providers.update_one(
        {"user_id": uid},
        {
            "$set": {
                "name": user.get("name") or "Prestator",
                "services": body.services,
                "localities": body.localities,
                "note": body.note,
                "active": body.active,
                "updated_at": now,
            },
            "$setOnInsert": mark_demo({"user_id": uid, "rating_sum": 0, "rating_count": 0, "created_at": now}),
        },
        upsert=True,
    )
    doc = await _provider(uid)
    await emit("radacini.provider_updated", actor=user, payload={"services": body.services, "active": body.active})
    return {"provider": _provider_me(doc)}


@router.get("/providers")
async def list_providers(service: Optional[str] = None, locality: Optional[str] = None,
                         user: dict = Depends(get_current_user)):
    if service is not None and service not in SERVICE_TYPE_IDS:
        raise HTTPException(400, "Serviciu necunoscut.")
    if locality is not None and locality not in LOCALITIES:
        raise HTTPException(400, "Localitate necunoscută.")
    flt: dict = {"active": True}
    if service:
        flt["services"] = service
    if locality:
        flt["localities"] = locality
    docs = await db.radacini_providers.find(flt).to_list(200)
    return {"items": [_provider_public(d) for d in docs]}


# ----------------------------------------------------------------- rute: cereri de lucrări

@router.get("/projects/{project_id}/service-requests")
async def list_service_requests(project_id: str, user: dict = Depends(get_current_user)):
    project, access, role = await load_project(project_id, user)
    docs = await db.radacini_service_requests.find({"project_id": str(project["_id"])}).to_list(500)
    docs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    uid = str(user["id"])
    coord = role == "coordinator" or access == "staff"
    return {"items": [_request_view(d, uid, coordinator=coord) for d in docs]}


@router.post("/projects/{project_id}/service-requests")
async def create_service_request(project_id: str, body: ServiceRequestIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "cererea de lucrare")
    project, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    if body.window_to < body.window_from:
        raise HTTPException(400, "Sfârșitul intervalului nu poate fi înaintea începutului.")
    if body.window_to.isoformat() < today_str():
        raise HTTPException(400, "Intervalul dorit nu poate fi în trecut.")
    pid = str(project["_id"])
    if await db.radacini_service_requests.count_documents({"project_id": pid, "status": {"$in": ["open", "assigned"]}}) >= 50:
        raise HTTPException(409, "Ai prea multe cereri deschise în acest proiect.")
    now = now_iso()
    doc = mark_demo({
        "project_id": pid,
        "service_type": body.service_type,
        "description": body.description,
        "area_m2": body.area_m2,
        "window_from": body.window_from.isoformat(),
        "window_to": body.window_to.isoformat(),
        "locality": body.locality,
        "status": "open",
        "offers": [],
        "created_by": str(user["id"]),
        "rev": 0,
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_service_requests.insert_one(doc)
    rid = str(doc["_id"])
    member_ids = {m["user_id"] for m in project.get("members", [])}
    providers = await db.radacini_providers.find(
        {"active": True, "services": body.service_type, "localities": body.locality}
    ).to_list(MAX_NOTIFIED + len(member_ids))
    notified = 0
    for p in providers:
        if p["user_id"] in member_ids:
            continue
        if notified >= MAX_NOTIFIED:
            break
        notified += 1
        await safe_notify(
            p["user_id"], "Cerere nouă de lucrare",
            f"{_label(body.service_type)} în {body.locality}, între {doc['window_from']} și {doc['window_to']}.",
            link="/radacini/prestator", type_="project",
        )
    await emit(
        "radacini.service_request_created", actor=user,
        payload={"project_id": pid, "request_id": rid, "service_type": body.service_type, "notified": notified},
    )
    return {"request": _request_view(doc, str(user["id"]), coordinator=True), "notified": notified}


@router.get("/service-requests/open")
async def open_service_requests(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    prov = await _provider(uid)
    if not prov or not prov.get("active", True):
        return {"items": []}
    docs = await db.radacini_service_requests.find({
        "status": "open",
        "service_type": {"$in": prov.get("services", [])},
        "locality": {"$in": prov.get("localities", [])},
    }).sort("created_at", -1).to_list(50)
    docs = [d for d in docs if uid != d.get("created_by")]
    titles: dict = {}
    for pid in {d["project_id"] for d in docs}:
        p = await db.radacini_projects.find_one({"_id": oid_or_404(pid)}, {"title": 1, "member_ids": 1})
        titles[pid] = p
    items = []
    for d in docs:
        p = titles.get(d["project_id"]) or {}
        if uid in (p.get("member_ids") or []):
            continue
        v = _request_view(d, uid, coordinator=False, project=p)
        v["my_offer"] = v["offers"][0] if v["offers"] else None
        items.append(v)
    return {"items": items}


@router.post("/service-requests/{request_id}/offers", dependencies=[Depends(require_terms)])
async def make_offer(request_id: str, body: OfferIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "oferta de lucrare")
    uid = str(user["id"])
    req, project, _, _ = await _load_request_for_provider(request_id, user)
    prov = await _provider(uid)
    if not prov or not prov.get("active", True):
        raise HTTPException(403, "Ai nevoie de un profil de prestator activ.")
    if req["service_type"] not in prov.get("services", []) or req["locality"] not in prov.get("localities", []):
        raise HTTPException(403, "Cererea nu se potrivește serviciilor sau localităților tale.")
    if uid in {m["user_id"] for m in project.get("members", [])}:
        raise HTTPException(403, "Nu poți oferta pentru propriul proiect.")
    ensure_active(project)
    for _ in range(_CAS_TRIES):
        if req.get("status") != "open":
            raise HTTPException(409, "Cererea nu mai primește oferte.")
        if any(o.get("provider_user_id") == uid for o in req.get("offers", [])):
            raise HTTPException(409, "Ai trimis deja o ofertă pentru această cerere.")
        if len(req.get("offers", [])) >= 100:
            raise HTTPException(409, "Cererea a primit numărul maxim de oferte.")
        offer = {
            "provider_user_id": uid,
            "name": prov.get("name") or user.get("name") or "",
            "price_ron_indicative": body.price_ron_indicative,
            "message": body.message,
            "at": now_iso(),
        }
        if await _cas(req, {"offers": [*req.get("offers", []), offer]}, ("open",)):
            break
        req = await _reload(req)
    else:
        raise HTTPException(409, "Cererea a fost modificată între timp. Reîncearcă.")
    for m in project.get("members", []):
        if m.get("role") == "coordinator":
            await safe_notify(
                m["user_id"], "Ofertă nouă pentru o lucrare",
                f"{offer['name']} a trimis o ofertă pentru {_label(req['service_type'])} în „{project['title']}”.",
                link=project_link(project["_id"]), type_="project",
            )
    await emit("radacini.service_offer_made", actor=user, payload={"request_id": request_id, "project_id": req["project_id"]})
    return {"request": _request_view(await _reload(req), uid, coordinator=False, project=project)}


async def _load_request_for_provider(request_id: str, user: dict):
    """Prestatorul nu e membru al proiectului: încărcăm cererea și proiectul fără verificarea de acces."""
    req = await db.radacini_service_requests.find_one({"_id": oid_or_404(request_id)})
    if not req:
        raise HTTPException(404, "Cererea nu există.")
    project = await db.radacini_projects.find_one({"_id": oid_or_404(req["project_id"])})
    if not project:
        raise HTTPException(404, "Cererea nu există.")
    return req, project, None, None


@router.post("/service-requests/{request_id}/assign")
async def assign_request(request_id: str, body: AssignIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "alegerea prestatorului")
    req, project, access, role = await _load_request(request_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    offer = next((o for o in req.get("offers", []) if o.get("provider_user_id") == body.provider_user_id), None)
    if not offer:
        raise HTTPException(400, "Prestatorul ales nu a trimis ofertă.")
    # Condiționat open → assigned: două alegeri simultane nu pot reuși amândouă.
    res = await db.radacini_service_requests.update_one(
        {"_id": req["_id"], "status": "open"},
        {"$set": {"status": "assigned", "assigned_provider_user_id": body.provider_user_id,
                  "assigned_at": now_iso(), "updated_at": now_iso()}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea nu mai este deschisă.")
    await safe_notify(
        body.provider_user_id, "Ofertă acceptată",
        f"Oferta ta pentru {_label(req['service_type'])} în „{project['title']}” a fost aleasă.",
        link="/radacini/prestator", type_="project",
    )
    await emit("radacini.service_assigned", actor=user,
               payload={"request_id": request_id, "provider_user_id": body.provider_user_id})
    return {"request": _request_view(await _reload(req), str(user["id"]), coordinator=True, project=project)}


@router.post("/service-requests/{request_id}/done")
async def done_request(request_id: str, body: DoneIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "finalizarea lucrării")
    req, project, access, role = await _load_request(request_id, user)
    need_coordinator(access, role)
    provider_id = req.get("assigned_provider_user_id")
    now = now_iso()
    res = await db.radacini_service_requests.update_one(
        {"_id": req["_id"], "status": "assigned"},
        {"$set": {"status": "done", "rating": body.rating, "rating_comment": body.comment,
                  "done_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Lucrarea nu este în starea „atribuită”.")
    # Agregat pe prestator (o singură dată: tranziția assigned → done a reușit o singură dată).
    prov_res = await db.radacini_providers.update_one(
        {"user_id": provider_id}, {"$inc": {"rating_sum": body.rating, "rating_count": 1}}
    )
    if prov_res.modified_count != 1:
        log.warning("radacini: prestatorul %s nu a putut fi evaluat pentru cererea %s", provider_id, request_id)
    await safe_notify(
        provider_id, "Lucrare finalizată",
        f"Lucrarea {_label(req['service_type'])} din „{project['title']}” a fost marcată finalizată.",
        link="/radacini/prestator", type_="project",
    )
    await emit("radacini.service_done", actor=user,
               payload={"request_id": request_id, "provider_user_id": provider_id, "rating": body.rating})
    return {"request": _request_view(await _reload(req), str(user["id"]), coordinator=True, project=project)}


@router.post("/service-requests/{request_id}/cancel")
async def cancel_request(request_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "anularea cererii")
    req, project, access, role = await _load_request(request_id, user)
    need_coordinator(access, role)
    now = now_iso()
    res = await db.radacini_service_requests.update_one(
        {"_id": req["_id"], "status": {"$in": ["open", "assigned"]}},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea nu mai poate fi anulată.")
    provider_id = req.get("assigned_provider_user_id")
    if provider_id:
        await safe_notify(
            provider_id, "Lucrare anulată",
            f"Cererea {_label(req['service_type'])} din „{project['title']}” a fost anulată.",
            link="/radacini/prestator", type_="project",
        )
    await emit("radacini.service_cancelled", actor=user, payload={"request_id": request_id})
    return {"request": _request_view(await _reload(req), str(user["id"]), coordinator=True, project=project)}
