"""Raportarea conținutului (mecanism de notificare și acțiune, art. 16–17 DSA): orice membru poate raporta un
anunț, un teren, o comunitate sau un utilizator; personalul analizează raportarea și o închide cu o decizie
motivată, iar raportorul primește confirmarea primirii și decizia. Restricționarea efectivă a conținutului se
face cu uneltele existente (închiderea anunțului, pauza terenului), iar decizia de aici o consemnează."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from .bridge import db, get_current_user
from .common import RadaciniRoute, audit_staff, mark_demo, now_iso, oid_or_404, safe_notify
from .staff import require_staff

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

# tip → (colecție, câmpul cu titlul afișat, câmpul proprietarului)
TARGETS = {
    "listing": ("radacini_listings", "product", "seller_user_id"),
    "parcel": ("radacini_parcels", "title", "owner_user_id"),
    "community": ("radacini_communities", "name", "created_by"),
    "user": ("users", "name", "_id"),
}
REASONS = {
    "illegal": "Conținut ilegal",
    "fraud": "Înșelătorie sau date false",
    "unsafe_food": "Produs alimentar nesigur",
    "abuse": "Hărțuire sau limbaj abuziv",
    "privacy": "Date personale expuse",
    "spam": "Spam sau reclamă",
    "other": "Altceva",
}
DECISIONS = {
    "no_action": "Fără măsuri: conținutul respectă regulile",
    "content_restricted": "Conținutul a fost restricționat",
    "user_warned": "Utilizatorul a fost avertizat",
}
MAX_PER_DAY = 20
REPORTS_LINK = "/radacini/raportari"


class ReportIn(BaseModel):
    target_type: str
    target_id: str
    reason: str
    details: str = ""

    @field_validator("target_type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in TARGETS:
            raise ValueError("Tip de conținut necunoscut.")
        return v

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        if v not in REASONS:
            raise ValueError("Motiv necunoscut.")
        return v

    @field_validator("details")
    @classmethod
    def _details(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) > 1000:
            raise ValueError("Detaliile au cel mult 1000 de caractere.")
        return v


class ResolveIn(BaseModel):
    decision: str
    note: str

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in DECISIONS:
            raise ValueError("Decizie invalidă.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 1000:
            raise ValueError("Motivarea deciziei este obligatorie (3–1000 de caractere).")
        return v


def _out(d: dict, staff: bool = False) -> dict:
    out = {
        "id": str(d["_id"]), "target_type": d.get("target_type"), "target_id": d.get("target_id"),
        "target_title": d.get("target_title"), "reason": d.get("reason"), "reason_label": REASONS.get(d.get("reason")),
        "details": d.get("details"), "status": d.get("status"), "created_at": d.get("created_at"),
        "decision": d.get("decision"), "decision_label": DECISIONS.get(d.get("decision")),
        "decision_note": d.get("decision_note"), "resolved_at": d.get("resolved_at"),
    }
    if staff:
        out.update({"reporter_id": d.get("reporter_id"), "reporter_name": d.get("reporter_name"),
                    "target_owner_id": d.get("target_owner_id"), "resolved_by_name": d.get("resolved_by_name")})
    return out


async def _target(target_type: str, target_id: str) -> dict:
    coll, title_f, owner_f = TARGETS[target_type]
    doc = await db[coll].find_one({"_id": oid_or_404(target_id)})
    if not doc:
        raise HTTPException(404, "Conținutul raportat nu există.")
    owner = doc.get(owner_f)
    return {"title": str(doc.get(title_f) or "")[:120], "owner_id": str(owner) if owner else None}


@router.post("/reports")
async def create_report(body: ReportIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    tgt = await _target(body.target_type, body.target_id)
    if body.target_type == "user" and body.target_id == uid:
        raise HTTPException(400, "Nu te poți raporta pe tine.")
    if await db.radacini_reports.find_one({"reporter_id": uid, "target_type": body.target_type,
                                           "target_id": body.target_id, "status": "open"}, {"_id": 1}):
        raise HTTPException(409, "Ai deja o raportare deschisă pentru acest conținut.")
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    if await db.radacini_reports.count_documents({"reporter_id": uid, "created_at": {"$gte": since}}) >= MAX_PER_DAY:
        raise HTTPException(429, "Ai trimis prea multe raportări azi. Încearcă mâine.")
    now = now_iso()
    doc = mark_demo({
        "target_type": body.target_type, "target_id": body.target_id, "target_title": tgt["title"],
        "target_owner_id": tgt["owner_id"], "reason": body.reason, "details": body.details,
        "reporter_id": uid, "reporter_name": user.get("name") or user.get("email"),
        "status": "open", "created_at": now, "updated_at": now,
    })
    res = await db.radacini_reports.insert_one(doc)
    doc["_id"] = res.inserted_id
    await safe_notify(uid, "Raportare primită",
                      "Am primit raportarea ta. Personalul Rădăcini o analizează și îți comunică decizia.",
                      REPORTS_LINK, type_="moderation")
    return {"report": _out(doc)}


@router.get("/reports/mine")
async def my_reports(user: dict = Depends(get_current_user)):
    docs = await db.radacini_reports.find({"reporter_id": str(user["id"])}).sort("created_at", -1).limit(200).to_list(200)
    return {"items": [_out(d) for d in docs]}


@router.get("/staff/reports")
async def staff_reports(status: Optional[str] = Query(None), ctx: dict = Depends(require_staff())):
    flt = {"status": status} if status in ("open", "resolved") else {}
    docs = await db.radacini_reports.find(flt).sort("created_at", -1).limit(500).to_list(500)
    return {"items": [_out(d, staff=True) for d in docs],
            "open_count": await db.radacini_reports.count_documents({"status": "open"})}


@router.post("/staff/reports/{report_id}/resolve")
async def resolve_report(report_id: str, body: ResolveIn, ctx: dict = Depends(require_staff())):
    user = ctx["user"]
    doc = await db.radacini_reports.find_one({"_id": oid_or_404(report_id)})
    if not doc:
        raise HTTPException(404, "Raportarea nu există.")
    if doc.get("status") != "open":
        raise HTTPException(409, "Raportarea a fost deja închisă.")
    now = now_iso()
    upd = {"status": "resolved", "decision": body.decision, "decision_note": body.note, "resolved_at": now,
           "resolved_by": str(user["id"]), "resolved_by_name": user.get("name") or user.get("email"), "updated_at": now}
    res = await db.radacini_reports.update_one({"_id": doc["_id"], "status": "open"}, {"$set": upd})
    if not res.modified_count:
        raise HTTPException(409, "Raportarea a fost deja închisă.")
    await audit_staff(user, "radacini.report_resolve", "report", report_id,
                      {"decision": body.decision, "target_type": doc.get("target_type"), "target_id": doc.get("target_id")})
    label = DECISIONS[body.decision]
    await safe_notify(doc["reporter_id"], "Decizie la raportarea ta",
                      f"{label}. Motivare: {body.note}", REPORTS_LINK, type_="moderation")
    owner = doc.get("target_owner_id")
    if body.decision != "no_action" and owner and ObjectId.is_valid(str(owner)):
        await safe_notify(owner, "Decizie de moderare",
                          f"{label} („{doc.get('target_title') or ''}”). Motivare: {body.note}. "
                          "Poți contesta decizia prin pagina de contact Rădăcini.",
                          None, type_="moderation")
    return {"report": _out({**doc, **upd}, staff=True)}
