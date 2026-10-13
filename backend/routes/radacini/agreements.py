"""Acorduri Rădăcini: termeni versionați, propunere spre semnare, semnare și anulare."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, check_price, now_iso, oid_or_404, safe_notify
from .projects import create_project_for_agreement
from .requests import (
    ACTIVE_STATUSES,
    ASSIGNED_ELSEWHERE_REASON,
    ReasonIn,
    check_terms,
    clean_crops,
    get_parcel_doc,
    load_parcels,
    _staff_can_read,
)

router = APIRouter(route_class=RadaciniRoute)

EDITABLE = ("draft", "proposed")
ASSIGNED_AGREEMENT_REASON = "Terenul a fost atribuit altui acord."
CLAIMABLE_STATUSES = ("published", "paused")  # un teren editat între timp (draft/rejected) trebuie reverificat


class TermsPatch(BaseModel):
    """Termeni parțiali: doar câmpurile trimise se schimbă."""

    area_m2: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    price_ron_per_year: Optional[float] = None
    harvest_share_percent: Optional[int] = None
    crops: Optional[list[str]] = None
    custom_clauses: Optional[str] = None

    @field_validator("price_ron_per_year")
    @classmethod
    def _price(cls, v: Optional[float]) -> Optional[float]:
        return check_price(v)

    @field_validator("crops")
    @classmethod
    def _crops(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return None if v is None else clean_crops(v)

    @field_validator("custom_clauses")
    @classmethod
    def _clauses(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("Clauzele au cel mult 5000 de caractere.")
        return v or None


class AgreementPatch(BaseModel):
    terms: TermsPatch


class SignIn(BaseModel):
    version: int


def _is_party(doc: dict, user: dict) -> bool:
    return any(p.get("user_id") == str(user["id"]) for p in doc.get("parties", []))


async def _load(agreement_id: str, user: dict) -> tuple[dict, str]:
    """(acord, 'party'|'staff'); 404 dacă userul nu are voie să-l vadă."""
    doc = await db.radacini_agreements.find_one({"_id": oid_or_404(agreement_id)})
    if not doc:
        raise HTTPException(404, "Acordul nu există.")
    if _is_party(doc, user):
        return doc, "party"
    if await _staff_can_read(user, await get_parcel_doc(doc.get("parcel_id"))):
        return doc, "staff"
    raise HTTPException(404, "Acordul nu există.")


def _party_only(access: str) -> None:
    if access != "party":
        raise HTTPException(403, "Doar părțile pot acționa în acest acord.")


def _other_user(doc: dict, user: dict) -> str:
    return next(p["user_id"] for p in doc["parties"] if p["user_id"] != str(user["id"]))


def _link(doc: dict) -> str:
    return f"/radacini/acorduri/{doc['_id']}"


def _name(user: dict) -> str:
    return user.get("name") or "Cealaltă parte"


@router.get("/agreements")
async def list_agreements(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    docs = await db.radacini_agreements.find({"party_ids": uid}).sort("updated_at", -1).to_list(200)
    docs = [d for d in docs if _is_party(d, user)]
    parcels = await load_parcels(d.get("parcel_id") for d in docs)
    items = []
    for d in docs:
        item = serialize_doc(d)
        parcel = parcels.get(str(d.get("parcel_id")), {})
        item["parcel_title"] = parcel.get("title") or d["terms"].get("parcel_snapshot", {}).get("title", "")
        item["parcel_locality"] = parcel.get("locality") or d["terms"].get("parcel_snapshot", {}).get("locality", "")
        item["counterpart_name"] = next((p.get("name", "") for p in d["parties"] if p["user_id"] != uid), "")
        items.append(item)
    return {"items": items}


@router.get("/agreements/{agreement_id}")
async def get_agreement(agreement_id: str, user: dict = Depends(get_current_user)):
    doc, _ = await _load(agreement_id, user)
    out = serialize_doc(doc)
    parcel = (await load_parcels([doc.get("parcel_id")])).get(str(doc.get("parcel_id")), {})
    snap = doc["terms"].get("parcel_snapshot", {})
    out["parcel_title"] = parcel.get("title") or snap.get("title", "")
    out["parcel_locality"] = parcel.get("locality") or snap.get("locality", "")
    return {"agreement": out}


@router.patch("/agreements/{agreement_id}")
async def patch_agreement(agreement_id: str, body: AgreementPatch, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "modificarea acordului")
    doc, access = await _load(agreement_id, user)
    _party_only(access)
    if doc["status"] not in EDITABLE:
        raise HTTPException(409, "Acordul nu mai poate fi modificat.")
    changes = body.terms.model_dump(mode="json", exclude_unset=True)
    for key in ("area_m2", "start_date", "end_date", "crops"):
        if key in changes and changes[key] is None:
            raise HTTPException(400, f"Câmpul {key} nu poate fi gol.")
    old_terms = doc["terms"]
    merged = {**old_terms, **changes}
    for key in ("price_ron_per_year", "harvest_share_percent", "custom_clauses"):
        if merged.get(key) is None:
            merged[key] = None
    parcel = await get_parcel_doc(doc["parcel_id"])
    parcel_area = (parcel or {}).get("area_m2") or old_terms.get("parcel_snapshot", {}).get("area_m2")
    # „Începe azi sau mai târziu” se cere doar dacă data de început chiar se schimbă (un acord rămas în
    # negociere după data inițială poate fi totuși ajustat în alte privințe).
    start_changed = "start_date" in changes and changes["start_date"] != old_terms.get("start_date")
    check_terms(
        merged,
        model=doc["model"],
        parcel_area=parcel_area,
        require_future_start=start_changed,
    )
    if merged == old_terms:
        return {"agreement": serialize_doc(doc)}

    now = now_iso()
    res = await db.radacini_agreements.update_one(
        {"_id": doc["_id"], "status": doc["status"], "version": doc["version"]},
        {
            "$set": {
                "terms": merged,
                "version": doc["version"] + 1,
                "signatures": [],
                "status": "draft",
                "terms_by_user_id": str(user["id"]),
                "terms_at": now,
                "updated_at": now,
            },
            "$push": {
                "versions_history": {
                    "version": doc["version"],
                    "terms": old_terms,
                    "by_user_id": doc.get("terms_by_user_id") or doc["parties"][0]["user_id"],
                    "at": doc.get("terms_at") or doc.get("created_at"),
                }
            },
        },
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Acordul a fost modificat între timp. Reîncarcă pagina.")
    await safe_notify(
        _other_user(doc, user),
        "Acord modificat",
        f"{_name(user)} a modificat termenii acordului (versiunea {doc['version'] + 1}).",
        link=_link(doc),
        type_="agreement",
    )
    await emit(
        "radacini.agreement_edited",
        actor=user,
        payload={"agreement_id": str(doc["_id"]), "version": doc["version"] + 1},
    )
    fresh = await db.radacini_agreements.find_one({"_id": doc["_id"]})
    return {"agreement": serialize_doc(fresh)}


@router.post("/agreements/{agreement_id}/propose")
async def propose_agreement(agreement_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "trimiterea acordului spre semnare")
    doc, access = await _load(agreement_id, user)
    _party_only(access)
    if doc["status"] != "draft":
        raise HTTPException(409, "Doar un acord în ciornă poate fi trimis spre semnare.")
    now = now_iso()
    res = await db.radacini_agreements.update_one(
        {"_id": doc["_id"], "status": "draft", "version": doc["version"]},
        {"$set": {"status": "proposed", "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Acordul a fost modificat între timp. Reîncarcă pagina.")
    await safe_notify(
        _other_user(doc, user),
        "Acord trimis spre semnare",
        f"{_name(user)} ți-a trimis acordul (versiunea {doc['version']}) spre semnare.",
        link=_link(doc),
        type_="agreement",
    )
    await emit(
        "radacini.agreement_proposed",
        actor=user,
        payload={"agreement_id": str(doc["_id"]), "version": doc["version"]},
    )
    return {"agreement": serialize_doc({**doc, "status": "proposed", "updated_at": now})}


async def _decline_competing_requests(agreement: dict, user: dict) -> None:
    """Celelalte cereri active pe teren sunt refuzate (terenul a fost atribuit)."""
    others = await db.radacini_land_requests.find(
        {"parcel_id": agreement["parcel_id"], "status": {"$in": list(ACTIVE_STATUSES)}}
    ).to_list(500)
    now = now_iso()
    for other in others:
        if str(other["_id"]) == agreement["request_id"]:
            continue
        res = await db.radacini_land_requests.update_one(
            {"_id": other["_id"], "status": {"$in": list(ACTIVE_STATUSES)}},
            {
                "$set": {
                    "status": "declined",
                    "decline_reason": ASSIGNED_ELSEWHERE_REASON,
                    "decided_at": now,
                    "last_activity_at": now,
                    "updated_at": now,
                }
            },
        )
        if res.modified_count == 1:
            await safe_notify(
                other["requester_user_id"],
                "Cerere refuzată",
                ASSIGNED_ELSEWHERE_REASON,
                link=f"/radacini/cereri/{other['_id']}",
                type_="request",
            )
            await emit(
                "radacini.request_declined",
                actor=user,
                payload={"request_id": str(other["_id"]), "reason": "assigned_elsewhere"},
            )


async def _cancel_competing_agreements(agreement: dict, user: dict) -> None:
    """Celelalte acorduri nesemnate (draft/proposed) de pe același teren sunt anulate: terenul a fost atribuit."""
    others = await db.radacini_agreements.find(
        {"parcel_id": agreement["parcel_id"], "status": {"$in": list(EDITABLE)}}, {"party_ids": 1}
    ).to_list(200)
    now = now_iso()
    for other in others:
        if other["_id"] == agreement["_id"]:
            continue
        res = await db.radacini_agreements.update_one(
            {"_id": other["_id"], "status": {"$in": list(EDITABLE)}},
            {"$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "cancel_reason": ASSIGNED_AGREEMENT_REASON,
                "updated_at": now,
            }},
        )
        if res.modified_count != 1:
            continue
        for party_id in other.get("party_ids") or []:
            if party_id != str(user["id"]):
                await safe_notify(
                    party_id,
                    "Acord anulat",
                    ASSIGNED_AGREEMENT_REASON,
                    link=f"/radacini/acorduri/{other['_id']}",
                    type_="agreement",
                )
        await emit(
            "radacini.agreement_cancelled",
            actor=user,
            payload={"agreement_id": str(other["_id"]), "reason": "assigned_elsewhere"},
        )


@router.post("/agreements/{agreement_id}/sign")
async def sign_agreement(agreement_id: str, body: SignIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "semnarea acordului")
    uid = str(user["id"])
    doc, access = await _load(agreement_id, user)
    _party_only(access)
    if doc["status"] != "proposed":
        raise HTTPException(409, "Acordul nu este trimis spre semnare.")
    if body.version != doc["version"]:
        raise HTTPException(409, "Versiunea acordului s-a schimbat. Citește din nou termenii.")
    parcel = await get_parcel_doc(doc["parcel_id"])
    if not parcel or parcel.get("archived_at"):
        raise HTTPException(409, "Terenul nu mai există.")
    if parcel.get("active_agreement_id") and parcel["active_agreement_id"] != str(doc["_id"]):
        raise HTTPException(409, "Terenul are deja un acord activ.")
    if parcel.get("status") not in CLAIMABLE_STATUSES:
        raise HTTPException(409, "Terenul nu mai este disponibil.")  # ex.: editat între timp, deci de reverificat

    now = now_iso()
    res = await db.radacini_agreements.update_one(
        {
            "_id": doc["_id"],
            "status": "proposed",
            "version": doc["version"],
            "signatures.user_id": {"$ne": uid},
        },
        {
            "$push": {"signatures": {"user_id": uid, "version": doc["version"], "signed_at": now}},
            "$set": {"updated_at": now},
        },
    )
    if res.modified_count != 1:
        fresh = await db.radacini_agreements.find_one({"_id": doc["_id"]}) or doc
        if any(s.get("user_id") == uid and s.get("version") == fresh.get("version") for s in fresh.get("signatures", [])):
            raise HTTPException(409, "Ai semnat deja această versiune.")
        raise HTTPException(409, "Acordul a fost modificat între timp. Reîncarcă pagina.")

    await emit(
        "radacini.agreement_signed",
        actor=user,
        payload={"agreement_id": str(doc["_id"]), "version": doc["version"]},
    )
    doc = await db.radacini_agreements.find_one({"_id": doc["_id"]}) or doc
    signed_by = {s["user_id"] for s in doc.get("signatures", []) if s.get("version") == doc["version"]}
    if not all(p["user_id"] in signed_by for p in doc["parties"]):
        await safe_notify(
            _other_user(doc, user),
            "Acordul a fost semnat de cealaltă parte",
            f"{_name(user)} a semnat versiunea {doc['version']}. Aștepți semnătura ta.",
            link=_link(doc),
            type_="agreement",
        )
        return {"agreement": serialize_doc(doc)}

    # Toate părțile au semnat: mai întâi terenul (revendicare condiționată), apoi acordul.
    agreement_key = str(doc["_id"])
    claim = await db.radacini_parcels.update_one(
        {
            "_id": parcel["_id"],
            "archived_at": {"$exists": False},
            "status": {"$in": list(CLAIMABLE_STATUSES)},
            "$or": [
                {"active_agreement_id": {"$exists": False}},
                {"active_agreement_id": agreement_key},
            ],
        },
        {"$set": {"active_agreement_id": agreement_key, "status": "paused", "updated_at": now}},
    )
    if claim.matched_count != 1:
        current = await get_parcel_doc(doc["parcel_id"]) or {}
        if current.get("active_agreement_id") and current["active_agreement_id"] != agreement_key:
            raise HTTPException(409, "Terenul are deja un acord activ.")
        raise HTTPException(409, "Terenul nu mai este disponibil.")
    res = await db.radacini_agreements.update_one(
        {"_id": doc["_id"], "status": "proposed", "version": doc["version"]},
        {"$set": {"status": "signed", "signed_at": now, "updated_at": now}},
    )
    fresh = await db.radacini_agreements.find_one({"_id": doc["_id"]}) or doc
    if res.modified_count != 1:
        if fresh.get("status") == "signed":
            # Cealaltă parte a finalizat semnarea simultan: terenul e legit al acestui acord, nu îl eliberăm.
            return {"agreement": serialize_doc(fresh)}
        # Acordul a fost anulat/modificat între timp: eliberăm terenul revendicat și restaurăm starea anterioară.
        await db.radacini_parcels.update_one(
            {"_id": parcel["_id"], "active_agreement_id": agreement_key},
            {"$unset": {"active_agreement_id": ""}, "$set": {"status": parcel.get("status"), "updated_at": now_iso()}},
        )
        raise HTTPException(409, "Acordul a fost modificat între timp. Reîncarcă pagina.")
    doc = fresh
    await _decline_competing_requests(doc, user)
    await _cancel_competing_agreements(doc, user)
    await create_project_for_agreement(doc, user)  # idempotent; erorile se loghează
    await safe_notify(
        _other_user(doc, user),
        "Acord semnat",
        f"Acordul pentru „{parcel.get('title')}” a fost semnat de ambele părți.",
        link=_link(doc),
        type_="agreement",
    )
    await emit(
        "radacini.agreement_completed",
        actor=user,
        payload={"agreement_id": str(doc["_id"]), "parcel_id": doc["parcel_id"]},
    )
    return {"agreement": serialize_doc(doc)}


@router.post("/agreements/{agreement_id}/cancel")
async def cancel_agreement(agreement_id: str, body: ReasonIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "anularea acordului")
    doc, access = await _load(agreement_id, user)
    _party_only(access)
    if doc["status"] not in EDITABLE:
        raise HTTPException(409, "Acordul nu mai poate fi anulat.")
    now = now_iso()
    changes = {"status": "cancelled", "cancelled_at": now, "updated_at": now}
    if body.reason:
        changes["cancel_reason"] = body.reason
    res = await db.radacini_agreements.update_one(
        {"_id": doc["_id"], "status": {"$in": list(EDITABLE)}}, {"$set": changes}
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Acordul nu mai poate fi anulat.")
    message = f"{_name(user)} a anulat acordul."
    if body.reason:
        message += f" Motiv: {body.reason}"
    await safe_notify(_other_user(doc, user), "Acord anulat", message, link=_link(doc), type_="agreement")
    await emit("radacini.agreement_cancelled", actor=user, payload={"agreement_id": str(doc["_id"])})
    return {"agreement": serialize_doc({**doc, **changes})}
