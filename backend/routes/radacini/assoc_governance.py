"""Composesorate (S9-B): documente, ședințe, mandate, petiții, cereri de informații.

Prefix efectiv `/assoc/...` (routerul se montează sub `/radacini`). Date fictive în S9; voturile sunt consultative.
"""
import asyncio
import hashlib
import inspect
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

import storage_client

from .assoc_core import (  # noqa: F401
    DEFAULT_RULES, active_members, assoc_access, load_assoc_or_404, merged_rules, require_assoc_roles,
    share_totals, write_audit,
)
from .bridge import block_in_impersonation, db, get_current_user, serialize_doc
from .common import RadaciniRoute, load_owners, mark_demo, now_iso, oid_or_404, safe_notify, today_bucharest
from .legal_terms import require_terms

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

STAFF = {"manager", "operator", "council"}
SEE_ALL = STAFF | {"censor"}
MEMBERISH = SEE_ALL | {"member"}
MAX_DOC_BYTES = 10 * 1024 * 1024
EPS = 1e-9
MEETING_KINDS = ("aga_ordinary", "aga_extraordinary", "council")
NO_QUORUM_LABEL = "ținută fără cvorum (art. 9(2))"


async def _m(x):
    return await x if inspect.isawaitable(x) else x


async def _ctx(assoc_id: str, user: dict):
    assoc = await _m(load_assoc_or_404(assoc_id))
    acc = await _m(assoc_access(user, assoc))
    return assoc, acc


def _aid(assoc: dict) -> str:
    return str(assoc["_id"])


def _need(acc: dict, roles: set, msg: str = "Nu ai dreptul la această acțiune.") -> str:
    role = acc.get("role")
    if role not in roles:
        raise HTTPException(403, msg)
    return role


async def _audit(assoc, user, acc, action, ttype, tid, before=None, after=None):
    await _m(write_audit(_aid(assoc), user, acc.get("role"), action, ttype, str(tid), before, after))


def _parse_date(s, field="data") -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        raise HTTPException(400, f"Dată invalidă: {field} (AAAA-LL-ZZ).") from None


def _active(m: dict) -> bool:
    return m.get("status") in ("confirmed", "active")


def _shares(m: Optional[dict]) -> float:
    try:
        return float((m or {}).get("shares") or 0)
    except (TypeError, ValueError):
        return 0.0


def _mid(m: dict) -> str:
    return str(m["_id"])


async def _member_rows(assoc_id: str) -> dict:
    rows = await db.radacini_assoc_members.find({"association_id": assoc_id}).limit(5000).to_list(5000)
    return {_mid(r): r for r in rows}


def _link(assoc_id: str, tab: str) -> str:
    return f"/radacini/composesorate/{assoc_id}?tab={tab}"


async def _council_user_ids(assoc_id: str) -> List[str]:
    rows = await _m(active_members(assoc_id))
    out = []
    for r in rows:
        if r.get("council_role") and r.get("user_id") and r["user_id"] not in out:
            out.append(r["user_id"])
    return out


def _own_member(acc: dict) -> dict:
    m = acc.get("member")
    if not m or not _active(m):
        raise HTTPException(403, "Doar membrii verificați ai asociației pot face această acțiune.")
    return m


def _out(doc: dict, drop=()) -> dict:
    d = serialize_doc(doc)
    for k in drop:
        d.pop(k, None)
    return d


# =========================================================================================== DOCUMENTE

DOC_EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _sniff_doc(data: bytes) -> Optional[str]:
    if data[:5] == b"%PDF-":
        return "application/pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _doc_view(d: dict) -> dict:
    v = serialize_doc(d)
    v.pop("path", None)
    return v


@router.post("/assoc/{assoc_id}/documents", status_code=201, dependencies=[Depends(require_terms)])
async def upload_document(
    assoc_id: str,
    type: str = Form(...),
    title: str = Form(...),
    date_: str = Form(..., alias="date"),
    visibility: str = Form("members"),
    replaces_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    assoc, acc = await _ctx(assoc_id, user)
    role = _need(acc, STAFF, "Doar CA sau operatorul pot încărca documente.")
    aid = _aid(assoc)
    if not re.fullmatch(r"[a-z_]{2,40}", type or ""):
        raise HTTPException(400, "Tip de document invalid.")
    title = (title or "").strip()
    if not 2 <= len(title) <= 200:
        raise HTTPException(400, "Titlul trebuie să aibă între 2 și 200 de caractere.")
    if visibility not in ("members", "council"):
        raise HTTPException(400, "Vizibilitate invalidă.")
    ddate = _parse_date(date_).isoformat()
    data = await file.read(MAX_DOC_BYTES + 1)
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(400, "Fișierul depășește 10 MB.")
    ct = _sniff_doc(data) if data else None
    if not ct:
        raise HTTPException(400, "Fișier invalid. Sunt acceptate PDF, JPEG, PNG sau WebP.")
    version = 1
    if replaces_id:
        old = await db.radacini_assoc_documents.find_one({"_id": oid_or_404(replaces_id), "association_id": aid})
        if not old:
            raise HTTPException(404, "Documentul înlocuit nu există.")
        if await db.radacini_assoc_documents.find_one({"association_id": aid, "replaces_id": replaces_id}, {"_id": 1}):
            raise HTTPException(409, "Documentul are deja o versiune mai nouă.")
        version = int(old.get("version") or 1) + 1
    sha = hashlib.sha256(data).hexdigest()
    path = f"radacini/assoc/{aid}/docs/{uuid.uuid4().hex}.{DOC_EXT[ct]}"
    try:
        await asyncio.to_thread(storage_client.put_object, path, data, ct)
    except Exception:
        log.exception("radacini: încărcarea documentului a eșuat")
        raise HTTPException(502, "Documentul nu a putut fi salvat. Încearcă din nou.") from None
    doc = mark_demo({
        "association_id": aid, "type": type, "title": title, "date": ddate, "visibility": visibility,
        "replaces_id": replaces_id or None, "version": version, "path": path, "content_type": ct,
        "size": len(data), "sha256": sha, "uploaded_by": user["id"], "uploaded_role": role, "created_at": now_iso(),
    })
    await db.radacini_assoc_documents.insert_one(doc)
    await _audit(assoc, user, acc, "document.upload", "document", doc["_id"],
                 after={"title": title, "sha256": sha, "visibility": visibility, "replaces_id": replaces_id})
    return {"document": _doc_view(doc)}


@router.get("/assoc/{assoc_id}/documents")
async def list_documents(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc, acc = await _ctx(assoc_id, user)
    role = acc.get("role")
    if role not in MEMBERISH:
        raise HTTPException(403, "Documentele sunt vizibile doar membrilor asociației.")
    q = {"association_id": _aid(assoc)}
    if role == "member":
        q["visibility"] = "members"
    rows = await db.radacini_assoc_documents.find(q).sort("created_at", -1).limit(500).to_list(500)
    replaced = {r.get("replaces_id") for r in rows if r.get("replaces_id")}
    items = []
    for r in rows:
        v = _doc_view(r)
        v["superseded"] = str(r["_id"]) in replaced
        items.append(v)
    return {"items": items}


async def _load_doc(did: str, user: dict):
    doc = await db.radacini_assoc_documents.find_one({"_id": oid_or_404(did)})
    if not doc:
        raise HTTPException(404, "Documentul nu există.")
    assoc, acc = await _ctx(doc["association_id"], user)
    return doc, assoc, acc


@router.get("/assoc/documents/{did}/file")
async def document_file(did: str, user: dict = Depends(get_current_user)):
    doc, assoc, acc = await _load_doc(did, user)
    role = acc.get("role")
    if role not in MEMBERISH or (doc.get("visibility") == "council" and role not in SEE_ALL):
        raise HTTPException(404, "Documentul nu există.")
    try:
        data, _ct = await asyncio.to_thread(storage_client.get_object, doc["path"])
    except Exception:
        log.exception("radacini: citirea documentului a eșuat")
        raise HTTPException(404, "Documentul nu este disponibil.") from None
    await db.radacini_assoc_doc_access.insert_one(mark_demo({
        "document_id": str(doc["_id"]), "association_id": _aid(assoc), "user_id": user["id"], "role": role, "at": now_iso()}))
    ext = DOC_EXT.get(doc.get("content_type"), "bin")
    return Response(content=data, media_type=doc.get("content_type") or "application/octet-stream", headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'inline; filename="document-{str(doc["_id"])[-8:]}.{ext}"'})


@router.get("/assoc/documents/{did}/access-log")
async def document_access_log(did: str, user: dict = Depends(get_current_user)):
    doc, _assoc, acc = await _load_doc(did, user)
    _need(acc, SEE_ALL, "Jurnalul de acces e vizibil doar CA, cenzorilor și administratorilor.")
    rows = await db.radacini_assoc_doc_access.find({"document_id": str(doc["_id"])}).sort("at", -1).limit(500).to_list(500)
    owners = await load_owners({r.get("user_id") for r in rows})
    items = [{"user_id": r["user_id"], "name": owners.get(r["user_id"], {}).get("name", ""), "role": r.get("role"), "at": r.get("at")}
             for r in rows]
    return {"items": items}


# =========================================================================================== ȘEDINȚE

class AgendaItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    details: str = Field("", max_length=2000)


class MeetingIn(BaseModel):
    kind: str
    date: str
    place: str = Field(min_length=1, max_length=200)
    agenda: List[AgendaItem] = Field(default_factory=list, max_length=30)
    material_ids: List[str] = Field(default_factory=list, max_length=20)
    first_convocation_date: Optional[str] = None


async def _check_docs(aid: str, ids: List[str]) -> List[str]:
    out = []
    for i in dict.fromkeys(ids):
        if not await db.radacini_assoc_documents.find_one({"_id": oid_or_404(i), "association_id": aid}, {"_id": 1}):
            raise HTTPException(400, "Document inexistent în această asociație.")
        out.append(i)
    return out


async def _load_meeting(mid: str, user: dict):
    m = await db.radacini_assoc_meetings.find_one({"_id": oid_or_404(mid)})
    if not m:
        raise HTTPException(404, "Ședința nu există.")
    assoc, acc = await _ctx(m["association_id"], user)
    return m, assoc, acc


def _meeting_view(m: dict, acc: dict, rules: dict) -> dict:
    v = serialize_doc(m)
    role = acc.get("role")
    convs = v.get("convocations") or []
    if role not in SEE_ALL:
        me = (acc.get("member") or {}).get("_id")
        v["convocations"] = [c for c in convs if me and c.get("member_id") == str(me)]
        v["convocations_total"] = len(convs)
        att = v.get("attendance")
        if att:
            v["attendance"] = {k: att.get(k) for k in ("represented_shares", "total_shares", "quorum_met", "recorded_at")}
        v.pop("registered_mail_evidence_document_id", None)
    else:
        v["acks"] = sum(1 for c in convs if c.get("read_at"))
    v["held_without_quorum_label"] = NO_QUORUM_LABEL if m.get("held_without_quorum") else None
    return v


@router.post("/assoc/{assoc_id}/meetings", status_code=201, dependencies=[Depends(require_terms)])
async def create_meeting(assoc_id: str, body: MeetingIn, user: dict = Depends(get_current_user)):
    assoc, acc = await _ctx(assoc_id, user)
    _need(acc, STAFF)
    if body.kind not in MEETING_KINDS:
        raise HTTPException(400, "Tip de ședință invalid.")
    rules = merged_rules(assoc)
    rules = await _m(rules)
    d = _parse_date(body.date)
    second = False
    first = None
    if body.first_convocation_date:
        fd = _parse_date(body.first_convocation_date, "first_convocation_date")
        if d <= fd:
            raise HTTPException(400, "A doua convocare trebuie să fie după prima.")
        first = fd.isoformat()
        second = body.kind != "council" and d >= fd + timedelta(days=int(rules.get("second_convocation_day", 7)))
    aid = _aid(assoc)
    mats = await _check_docs(aid, body.material_ids)
    doc = mark_demo({
        "association_id": aid, "kind": body.kind, "date": d.isoformat(), "place": body.place.strip(),
        "agenda": [a.model_dump() for a in body.agenda], "material_ids": mats, "status": "draft",
        "first_convocation_date": first, "second_convocation": second, "convocations": [],
        "registered_mail_evidence_document_id": None, "attendance": None, "decisions": [],
        "minutes_document_id": None, "contest_until": None, "held_without_quorum": False,
        "created_by": user["id"], "created_at": now_iso(),
    })
    await db.radacini_assoc_meetings.insert_one(doc)
    await _audit(assoc, user, acc, "meeting.create", "meeting", doc["_id"], after={"kind": body.kind, "date": doc["date"]})
    return {"meeting": _out(doc)}


@router.get("/assoc/{assoc_id}/meetings")
async def list_meetings(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc, acc = await _ctx(assoc_id, user)
    if acc.get("role") not in MEMBERISH:
        raise HTTPException(403, "Ședințele sunt vizibile doar membrilor asociației.")
    rows = await db.radacini_assoc_meetings.find({"association_id": _aid(assoc)}).sort("date", -1).limit(300).to_list(300)
    return {"items": [_meeting_view(r, acc, {}) for r in rows]}


@router.get("/assoc/meetings/{mid}")
async def get_meeting(mid: str, user: dict = Depends(get_current_user)):
    m, assoc, acc = await _load_meeting(mid, user)
    if acc.get("role") not in MEMBERISH:
        raise HTTPException(403, "Ședințele sunt vizibile doar membrilor asociației.")
    v = _meeting_view(m, acc, {})
    mand = await db.radacini_assoc_mandates.find({"meeting_id": mid, "status": "active"}).limit(2000).to_list(2000)
    me = str((acc.get("member") or {}).get("_id") or "")
    v["mandates_count"] = len(mand)
    v["my_mandate"] = next(({"id": str(x["_id"]), "representative_member_id": x["representative_member_id"]}
                            for x in mand if x["mandator_member_id"] == me), None) if me else None
    return {"meeting": v}


class ConveneIn(BaseModel):
    registered_mail_evidence_document_id: Optional[str] = None


@router.post("/assoc/meetings/{mid}/convene")
async def convene_meeting(mid: str, body: Optional[ConveneIn] = None, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "convocarea ședinței")
    m, assoc, acc = await _load_meeting(mid, user)
    _need(acc, STAFF)
    aid = _aid(assoc)
    if m.get("status") == "held":
        raise HTTPException(409, "Ședința s-a ținut deja.")
    today = today_bucharest()
    d = _parse_date(m["date"])
    if d < today:
        raise HTTPException(409, "Data ședinței a trecut.")
    rules = await _m(merged_rules(assoc))
    conv_days = int(rules.get("convocation_days", 15))
    warning = None
    if (d - today).days < conv_days and m["kind"] != "council":
        warning = f"Convocarea are mai puțin de {conv_days} zile înainte de ședință (statut)."
    changes: dict = {}
    ev = body.registered_mail_evidence_document_id if body else None
    if ev:
        await _check_docs(aid, [ev])
        changes["registered_mail_evidence_document_id"] = ev
    existing = {c.get("member_id") for c in m.get("convocations") or []}
    members = await _m(active_members(aid))
    now = now_iso()
    new = []
    for r in members:
        if _mid(r) in existing:
            continue
        new.append({"member_id": _mid(r), "user_id": r.get("user_id"), "channel": "app/email", "sent_at": now,
                    "delivered": None, "read_at": None})
    convs = list(m.get("convocations") or []) + new
    changes.update({"convocations": convs, "status": "convened", "convened_at": m.get("convened_at") or now,
                    "convene_warning": warning})
    res = await db.radacini_assoc_meetings.update_one({"_id": m["_id"], "status": m.get("status")}, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, "Ședința a fost modificată între timp.")
    title = "Convocare: " + ("ședință CA" if m["kind"] == "council" else "adunare generală")
    msg = f"Ședință la {m['place']}, data {m['date']}. Confirmă primirea în aplicație."
    for c in new:
        if c.get("user_id"):
            await safe_notify(c["user_id"], title, msg, _link(aid, "sedinte"), "info")
    await _audit(assoc, user, acc, "meeting.convene", "meeting", m["_id"], after={"notified": len(new), "warning": warning})
    ev_id = changes.get("registered_mail_evidence_document_id") or m.get("registered_mail_evidence_document_id")
    return {"ok": True, "notified": len(new), "convocations_total": len(convs), "warning": warning,
            "registered_mail_missing": not ev_id,
            "registered_mail_note": None if ev_id else "Consemnează și trimiterea prin recomandată, cu dovadă încărcată."}


@router.post("/assoc/meetings/{mid}/registered-mail")
async def set_registered_mail(mid: str, body: ConveneIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "consemnarea dovezii")
    m, assoc, acc = await _load_meeting(mid, user)
    _need(acc, STAFF)
    if not body.registered_mail_evidence_document_id:
        raise HTTPException(400, "Indică documentul-dovadă.")
    await _check_docs(_aid(assoc), [body.registered_mail_evidence_document_id])
    await db.radacini_assoc_meetings.update_one(
        {"_id": m["_id"]}, {"$set": {"registered_mail_evidence_document_id": body.registered_mail_evidence_document_id}})
    await _audit(assoc, user, acc, "meeting.registered_mail", "meeting", m["_id"],
                 after={"document_id": body.registered_mail_evidence_document_id})
    return {"ok": True}


@router.post("/assoc/meetings/{mid}/ack")
async def ack_meeting(mid: str, user: dict = Depends(get_current_user)):
    m, assoc, acc = await _load_meeting(mid, user)
    me = _own_member(acc)
    convs = list(m.get("convocations") or [])
    mine = next((c for c in convs if c.get("member_id") == _mid(me)), None)
    if not mine:
        raise HTTPException(404, "Nu ai fost convocat la această ședință.")
    if not mine.get("read_at"):
        fresh = await db.radacini_assoc_meetings.find_one({"_id": m["_id"]})
        convs = list((fresh or m).get("convocations") or [])
        for c in convs:
            if c.get("member_id") == _mid(me) and not c.get("read_at"):
                c["read_at"] = now_iso()
                mine = c
        await db.radacini_assoc_meetings.update_one({"_id": m["_id"]}, {"$set": {"convocations": convs}})
    return {"ok": True, "read_at": mine["read_at"]}


class AttendanceIn(BaseModel):
    present_member_ids: List[str] = Field(default_factory=list, max_length=5000)
    mandates_ids: List[str] = Field(default_factory=list, max_length=2000)


def _need_held_date(m: dict) -> None:
    if _parse_date(m["date"]) > today_bucharest():
        raise HTTPException(409, "Operația se poate face doar în ziua ședinței sau după.")


@router.post("/assoc/meetings/{mid}/attendance")
async def record_attendance(mid: str, body: AttendanceIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "consemnarea prezenței")
    m, assoc, acc = await _load_meeting(mid, user)
    _need(acc, STAFF)
    if not str(m.get("kind", "")).startswith("aga"):
        raise HTTPException(400, "Cvorumul se calculează doar pentru adunările generale.")
    if m.get("status") not in ("convened",):
        raise HTTPException(409, "Ședința trebuie să fie convocată și neîncheiată.")
    _need_held_date(m)
    aid = _aid(assoc)
    rows = await _member_rows(aid)
    present = list(dict.fromkeys(body.present_member_ids))
    for p in present:
        if p not in rows or not _active(rows[p]):
            raise HTTPException(400, "Un membru prezent nu e activ în registru.")
    present_set = set(present)
    mand_rows = await db.radacini_assoc_mandates.find({"meeting_id": mid, "status": "active"}).limit(2000).to_list(2000)
    by_id = {str(x["_id"]): x for x in mand_rows}
    mandated = 0.0
    used = []
    for i in dict.fromkeys(body.mandates_ids):
        x = by_id.get(i)
        if not x:
            raise HTTPException(400, "Mandat inexistent sau revocat.")
        if x["representative_member_id"] not in present_set:
            raise HTTPException(400, "Reprezentantul mandatului nu este prezent.")
        if x["mandator_member_id"] in present_set:
            raise HTTPException(400, "Mandantul este prezent personal; mandatul nu se poate folosi.")
        mandated += _shares(rows.get(x["mandator_member_id"]))
        used.append(i)
    present_shares = sum(_shares(rows[p]) for p in present)
    represented = present_shares + mandated
    totals = await _m(share_totals(aid))
    total = float(totals.get("total_shares") or 0)
    quorum_met = total > 0 and represented > total / 2 + EPS
    second = bool(m.get("second_convocation"))
    att = {"present_member_ids": present, "mandate_ids": used, "present_shares": present_shares,
           "mandated_shares": mandated, "represented_shares": represented, "total_shares": total,
           "quorum_met": quorum_met, "recorded_at": now_iso(), "recorded_by": user["id"]}
    changes = {"attendance": att, "held_without_quorum": bool(second and not quorum_met)}
    res = await db.radacini_assoc_meetings.update_one({"_id": m["_id"], "status": "convened"}, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, "Ședința a fost modificată între timp.")
    await _audit(assoc, user, acc, "meeting.attendance", "meeting", m["_id"],
                 after={"represented_shares": represented, "quorum_met": quorum_met, "second_convocation": second})
    return {"attendance": att, "quorum_met": quorum_met, "second_convocation": second,
            "held_without_quorum": changes["held_without_quorum"],
            "label": NO_QUORUM_LABEL if changes["held_without_quorum"] else None}


class DecisionIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    result_text: str = Field(min_length=1, max_length=2000)
    votes_for: Optional[float] = Field(None, ge=0)
    votes_against: Optional[float] = Field(None, ge=0)
    abstentions: Optional[float] = Field(None, ge=0)


class DecisionsIn(BaseModel):
    decisions: List[DecisionIn] = Field(min_length=1, max_length=50)
    minutes_document_id: Optional[str] = None


@router.post("/assoc/meetings/{mid}/decisions")
async def record_decisions(mid: str, body: DecisionsIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "consemnarea hotărârilor")
    m, assoc, acc = await _load_meeting(mid, user)
    _need(acc, STAFF)
    if m.get("status") != "convened":
        raise HTTPException(409, "Hotărârile se consemnează o singură dată, pentru o ședință convocată.")
    _need_held_date(m)
    is_aga = str(m.get("kind", "")).startswith("aga")
    if is_aga:
        att = m.get("attendance")
        if not att:
            raise HTTPException(409, "Consemnează întâi prezența.")
        if not att.get("quorum_met") and not m.get("second_convocation"):
            raise HTTPException(409, "Fără cvorum la prima convocare nu se pot consemna hotărâri.")
    aid = _aid(assoc)
    if body.minutes_document_id:
        await _check_docs(aid, [body.minutes_document_id])
    rules = await _m(merged_rules(assoc))
    contest = (_parse_date(m["date"]) + timedelta(days=int(rules.get("contest_days", 15)))).isoformat()
    decisions = [d.model_dump() for d in body.decisions]
    changes = {"decisions": decisions, "minutes_document_id": body.minutes_document_id, "contest_until": contest,
               "status": "held", "decisions_at": now_iso()}
    res = await db.radacini_assoc_meetings.update_one({"_id": m["_id"], "status": "convened"}, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, "Ședința a fost modificată între timp.")
    await _audit(assoc, user, acc, "meeting.decisions", "meeting", m["_id"],
                 after={"count": len(decisions), "contest_until": contest, "minutes_document_id": body.minutes_document_id})
    return {"ok": True, "contest_until": contest, "decisions": decisions}


# =========================================================================================== MANDATE

class MandateIn(BaseModel):
    # Membrii nu văd registrul: reprezentantul se poate indica prin codul de membru (ex. „M005”) sau prin id.
    representative_member_id: Optional[str] = None
    representative_member_code: Optional[str] = None
    document_id: Optional[str] = None


@router.post("/assoc/meetings/{mid}/mandates", status_code=201, dependencies=[Depends(require_terms)])
async def create_mandate(mid: str, body: MandateIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "acordarea mandatului")
    m, assoc, acc = await _load_meeting(mid, user)
    me = _own_member(acc)
    aid = _aid(assoc)
    if not str(m.get("kind", "")).startswith("aga"):
        raise HTTPException(400, "Mandatele se dau doar pentru adunările generale.")
    if m.get("status") == "held" or _parse_date(m["date"]) <= today_bucharest():
        raise HTTPException(409, "Mandatul se dă înainte de data ședinței.")
    rep = None
    code = (body.representative_member_code or "").strip()
    raw_id = (body.representative_member_id or "").strip()
    if not code and raw_id and not ObjectId.is_valid(raw_id):
        code = raw_id  # s-a trimis codul în câmpul de id
    if code:
        rep = await db.radacini_assoc_members.find_one({"association_id": aid, "code": code.upper()})
    elif raw_id:
        rep = await db.radacini_assoc_members.find_one({"_id": oid_or_404(raw_id), "association_id": aid})
    else:
        raise HTTPException(400, "Indică reprezentantul prin codul de membru.")
    if rep and _mid(rep) == _mid(me):
        raise HTTPException(400, "Nu te poți mandata pe tine însuți.")
    rep_id = _mid(rep) if rep else None
    if not rep or not _active(rep):
        raise HTTPException(400, "Reprezentantul trebuie să fie membru activ al asociației.")
    if body.document_id:
        await _check_docs(aid, [body.document_id])
    rules = await _m(merged_rules(assoc))
    pl = rules.get("proxy_limits") or {}
    max_n, max_frac = int(pl.get("max_members", 5)), float(pl.get("max_shares_fraction", 0.05))
    totals = await _m(share_totals(aid))
    total = float(totals.get("total_shares") or 0)
    active = await db.radacini_assoc_mandates.find({"meeting_id": mid, "status": "active"}).limit(2000).to_list(2000)
    if any(x["mandator_member_id"] == _mid(me) for x in active):
        raise HTTPException(409, "Ai deja un mandat activ pentru această ședință.")
    if any(x["representative_member_id"] == _mid(me) for x in active):
        raise HTTPException(409, "Ești deja reprezentant al altor membri; nu poți da mandat mai departe.")
    if any(x["mandator_member_id"] == rep_id for x in active):
        raise HTTPException(409, "Reprezentantul și-a dat el însuși mandatul altcuiva.")
    mine_rep = [x for x in active if x["representative_member_id"] == rep_id]
    if len(mine_rep) + 1 > max_n:
        raise HTTPException(409, f"Un reprezentant poate avea cel mult {max_n} mandanți.")
    rows = await _member_rows(aid)
    rep_shares = _shares(rep) + sum(_shares(rows.get(x["mandator_member_id"])) for x in mine_rep) + _shares(me)
    if total > 0 and rep_shares > max_frac * total + EPS:
        raise HTTPException(409, f"Reprezentantul ar depăși {max_frac * 100:g}% din totalul cotelor.")
    doc = mark_demo({"association_id": aid, "meeting_id": mid, "mandator_member_id": _mid(me), "mandator_user_id": user["id"],
                     "representative_member_id": rep_id, "document_id": body.document_id, "status": "active",
                     "created_at": now_iso()})
    await db.radacini_assoc_mandates.insert_one(doc)
    # reverificare după inserare (curse): depășirea anulează mandatul propriu
    after = [x for x in await db.radacini_assoc_mandates.find({"meeting_id": mid, "status": "active"}).limit(2000).to_list(2000)
             if x["representative_member_id"] == rep_id]
    sh = _shares(rep) + sum(_shares(rows.get(x["mandator_member_id"])) if x["mandator_member_id"] in rows else _shares(me)
                            for x in after)
    if len(after) > max_n or (total > 0 and sh > max_frac * total + EPS):
        await db.radacini_assoc_mandates.update_one({"_id": doc["_id"]}, {"$set": {"status": "revoked", "revoked_at": now_iso()}})
        raise HTTPException(409, "Limitele de reprezentare au fost depășite.")
    if rep.get("user_id"):
        await safe_notify(rep["user_id"], "Mandat primit", "Un membru te-a mandatat pentru o adunare generală.",
                          _link(aid, "sedinte"), "info")
    return {"mandate": _out(doc)}


@router.delete("/assoc/mandates/{mandate_id}")
async def revoke_mandate(mandate_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "revocarea mandatului")
    x = await db.radacini_assoc_mandates.find_one({"_id": oid_or_404(mandate_id)})
    if not x or x.get("mandator_user_id") != user["id"]:
        raise HTTPException(404, "Mandatul nu există.")
    if x.get("status") != "active":
        raise HTTPException(409, "Mandatul este deja revocat.")
    m = await db.radacini_assoc_meetings.find_one({"_id": oid_or_404(x["meeting_id"])})
    if not m or m.get("status") == "held" or _parse_date(m["date"]) <= today_bucharest():
        raise HTTPException(409, "Mandatul nu mai poate fi revocat după data ședinței.")
    res = await db.radacini_assoc_mandates.update_one({"_id": x["_id"], "status": "active"},
                                                      {"$set": {"status": "revoked", "revoked_at": now_iso()}})
    if res.modified_count != 1:
        raise HTTPException(409, "Mandatul este deja revocat.")
    return {"ok": True}


@router.get("/assoc/meetings/{mid}/mandates")
async def list_mandates(mid: str, user: dict = Depends(get_current_user)):
    m, assoc, acc = await _load_meeting(mid, user)
    role = acc.get("role")
    if role not in MEMBERISH:
        raise HTTPException(403, "Nu ai acces.")
    rows = await db.radacini_assoc_mandates.find({"meeting_id": mid, "status": "active"}).limit(2000).to_list(2000)
    if role not in SEE_ALL:
        me = str((acc.get("member") or {}).get("_id") or "")
        rows = [r for r in rows if me and me in (r["mandator_member_id"], r["representative_member_id"])]
    return {"items": [_out(r, ("mandator_user_id",)) for r in rows]}


# =========================================================================================== PETIȚII

class PetitionIn(BaseModel):
    kind: str
    title: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=2, max_length=4000)
    meeting_id: Optional[str] = None


def _petition_stats(p: dict, totals: dict, rules: dict) -> dict:
    sigs = p.get("signatures") or []
    n = len(sigs)
    sh = sum(float(s.get("shares") or 0) for s in sigs)
    members_count = int(totals.get("members_count") or 0)
    total = float(totals.get("total_shares") or 0)
    if p["kind"] == "extraordinary_aga":
        cfg = rules.get("extraordinary_petition") or {}
        mf, sf = float(cfg.get("members_fraction", 0.25)), float(cfg.get("shares_fraction", 0.25))
        met = (members_count > 0 and n >= mf * members_count - EPS) or (total > 0 and sh >= sf * total - EPS)
        threshold = {"members_fraction": mf, "shares_fraction": sf, "members_needed": -(-mf * members_count // 1),
                     "shares_needed": sf * total}
    else:
        cfg = rules.get("agenda_petition") or {}
        mf = float(cfg.get("members_fraction", 0.10))
        met = members_count > 0 and n >= mf * members_count - EPS
        threshold = {"members_fraction": mf, "members_needed": -(-mf * members_count // 1)}
    return {"signatures_count": n, "signed_shares": sh, "members_count": members_count, "total_shares": total,
            "threshold": threshold, "threshold_met": bool(met)}


async def _agenda_deadline_check(p_or_meeting: dict, rules: dict) -> None:
    days = int((rules.get("agenda_petition") or {}).get("days_before", 5))
    if today_bucharest() > _parse_date(p_or_meeting["date"]) - timedelta(days=days):
        raise HTTPException(409, f"Punctele pe ordinea de zi se propun cu cel puțin {days} zile înainte de ședință.")


@router.post("/assoc/{assoc_id}/petitions", status_code=201, dependencies=[Depends(require_terms)])
async def create_petition(assoc_id: str, body: PetitionIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "inițierea petiției")
    assoc, acc = await _ctx(assoc_id, user)
    me = _own_member(acc)
    aid = _aid(assoc)
    if body.kind not in ("extraordinary_aga", "agenda_item"):
        raise HTTPException(400, "Tip de petiție invalid.")
    rules = await _m(merged_rules(assoc))
    meeting_id = None
    if body.kind == "agenda_item":
        if not body.meeting_id:
            raise HTTPException(400, "Indică ședința (meeting_id).")
        mt = await db.radacini_assoc_meetings.find_one({"_id": oid_or_404(body.meeting_id), "association_id": aid})
        if not mt or not str(mt.get("kind", "")).startswith("aga"):
            raise HTTPException(404, "Adunarea generală nu există.")
        if mt.get("status") == "held":
            raise HTTPException(409, "Ședința s-a ținut deja.")
        await _agenda_deadline_check(mt, rules)
        meeting_id = body.meeting_id
    p = mark_demo({"association_id": aid, "kind": body.kind, "title": body.title.strip(), "text": body.text.strip(),
                   "meeting_id": meeting_id, "created_by_member_id": _mid(me), "created_by": user["id"],
                   "signatures": [], "status": "open", "rev": 0, "threshold_notified": False, "created_at": now_iso()})
    await db.radacini_assoc_petitions.insert_one(p)
    return {"petition": _out(p, ("signatures",))}


@router.post("/assoc/petitions/{pid}/sign")
async def sign_petition(pid: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "semnarea petiției")
    p = await db.radacini_assoc_petitions.find_one({"_id": oid_or_404(pid)})
    if not p:
        raise HTTPException(404, "Petiția nu există.")
    assoc, acc = await _ctx(p["association_id"], user)
    me = _own_member(acc)
    aid = _aid(assoc)
    rules = await _m(merged_rules(assoc))
    for _ in range(6):
        if p.get("status") != "open":
            raise HTTPException(409, "Petiția nu mai primește semnături.")
        if p["kind"] == "agenda_item":
            mt = await db.radacini_assoc_meetings.find_one({"_id": oid_or_404(p["meeting_id"])})
            if not mt:
                raise HTTPException(404, "Ședința nu există.")
            await _agenda_deadline_check(mt, rules)
        sigs = list(p.get("signatures") or [])
        if any(s.get("member_id") == _mid(me) for s in sigs):
            raise HTTPException(409, "Ai semnat deja această petiție.")
        sigs.append({"member_id": _mid(me), "user_id": user["id"], "shares": _shares(me), "at": now_iso()})
        res = await db.radacini_assoc_petitions.update_one(
            {"_id": p["_id"], "rev": p.get("rev", 0), "status": "open"},
            {"$set": {"signatures": sigs, "rev": p.get("rev", 0) + 1}})
        if res.modified_count == 1:
            p["signatures"], p["rev"] = sigs, p.get("rev", 0) + 1
            break
        p = await db.radacini_assoc_petitions.find_one({"_id": p["_id"]})
    else:
        raise HTTPException(409, "Conflict la semnare. Încearcă din nou.")
    totals = await _m(share_totals(aid))
    stats = _petition_stats(p, totals, rules)
    if stats["threshold_met"]:
        extra = {"threshold_met_at": now_iso()}
        if p["kind"] == "extraordinary_aga":
            extra["respond_by"] = (today_bucharest() + timedelta(days=10)).isoformat()
        res = await db.radacini_assoc_petitions.update_one(
            {"_id": p["_id"], "threshold_notified": False}, {"$set": {"threshold_notified": True, **extra}})
        if res.modified_count == 1:
            for uid in await _council_user_ids(aid):
                await safe_notify(uid, "Petiție cu prag atins", f"Petiția „{p['title']}” a atins pragul de semnături.",
                                  _link(aid, "petitii"), "info")
    return {"ok": True, **stats}


@router.get("/assoc/{assoc_id}/petitions")
async def list_petitions(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc, acc = await _ctx(assoc_id, user)
    role = acc.get("role")
    if role not in MEMBERISH:
        raise HTTPException(403, "Petițiile sunt vizibile doar membrilor asociației.")
    aid = _aid(assoc)
    rules = await _m(merged_rules(assoc))
    totals = await _m(share_totals(aid))
    rows = await db.radacini_assoc_petitions.find({"association_id": aid}).sort("created_at", -1).limit(200).to_list(200)
    me = str((acc.get("member") or {}).get("_id") or "")
    items = []
    for p in rows:
        v = _out(p, ("signatures", "rev"))
        v.update(_petition_stats(p, totals, rules))
        v["signed_by_me"] = bool(me) and any(s.get("member_id") == me for s in p.get("signatures") or [])
        if role in SEE_ALL:
            v["signers"] = [{"member_id": s["member_id"], "shares": s.get("shares"), "at": s.get("at")} for s in p.get("signatures") or []]
        items.append(v)
    return {"items": items}


class RespondIn(BaseModel):
    text: str = Field(min_length=2, max_length=4000)
    decision: Optional[str] = Field(None, max_length=100)


@router.post("/assoc/petitions/{pid}/respond")
async def respond_petition(pid: str, body: RespondIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "răspunsul la petiție")
    p = await db.radacini_assoc_petitions.find_one({"_id": oid_or_404(pid)})
    if not p:
        raise HTTPException(404, "Petiția nu există.")
    assoc, acc = await _ctx(p["association_id"], user)
    _need(acc, STAFF)
    resp = {"text": body.text.strip(), "decision": body.decision, "by": user["id"], "at": now_iso()}
    res = await db.radacini_assoc_petitions.update_one({"_id": p["_id"], "status": "open"},
                                                       {"$set": {"status": "responded", "response": resp}})
    if res.modified_count != 1:
        raise HTTPException(409, "Petiția a primit deja răspuns.")
    await _audit(assoc, user, acc, "petition.respond", "petition", p["_id"], after={"decision": body.decision})
    if p.get("created_by"):
        await safe_notify(p["created_by"], "Răspuns la petiție", f"Petiția „{p['title']}” a primit răspuns.",
                          _link(_aid(assoc), "petitii"), "info")
    return {"ok": True, "response": resp}


# =========================================================================================== CERERI DE INFORMAȚII

class InfoRequestIn(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=2, max_length=4000)


class AnswerIn(BaseModel):
    text: str = Field(min_length=2, max_length=4000)
    document_id: Optional[str] = None


def _req_view(r: dict) -> dict:
    v = serialize_doc(r)
    v["overdue"] = bool(not r.get("answered_at") and r.get("due_at") and r["due_at"] < now_iso())
    return v


@router.post("/assoc/{assoc_id}/requests", status_code=201, dependencies=[Depends(require_terms)])
async def create_request(assoc_id: str, body: InfoRequestIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "trimiterea cererii")
    assoc, acc = await _ctx(assoc_id, user)
    me = _own_member(acc)
    aid = _aid(assoc)
    open_n = await db.radacini_assoc_requests.count_documents(
        {"association_id": aid, "member_id": _mid(me), "status": "open"})
    if open_n >= 20:
        raise HTTPException(429, "Ai prea multe cereri fără răspuns.")
    rules = await _m(merged_rules(assoc))
    due = datetime.now(timezone.utc) + timedelta(days=int(rules.get("info_request_days", 30)))
    doc = mark_demo({"association_id": aid, "member_id": _mid(me), "user_id": user["id"], "subject": body.subject.strip(),
                     "text": body.text.strip(), "due_at": due.isoformat(), "status": "open", "answered_at": None, "answer": None,
                     "created_at": now_iso()})
    await db.radacini_assoc_requests.insert_one(doc)
    for uid in (await _council_user_ids(aid))[:20]:
        await safe_notify(uid, "Cerere de informații", f"Cerere nouă: {body.subject.strip()}", _link(aid, "cereri"), "info")
    return {"request": _req_view(doc)}


@router.get("/assoc/{assoc_id}/requests")
async def list_requests(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc, acc = await _ctx(assoc_id, user)
    role = acc.get("role")
    if role not in MEMBERISH:
        raise HTTPException(403, "Nu ai acces.")
    q = {"association_id": _aid(assoc)}
    if role not in SEE_ALL:
        q["user_id"] = user["id"]
    rows = await db.radacini_assoc_requests.find(q).sort("created_at", -1).limit(500).to_list(500)
    return {"items": [_req_view(r) for r in rows]}


@router.post("/assoc/requests/{rid}/answer")
async def answer_request(rid: str, body: AnswerIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "răspunsul la cerere")
    r = await db.radacini_assoc_requests.find_one({"_id": oid_or_404(rid)})
    if not r:
        raise HTTPException(404, "Cererea nu există.")
    assoc, acc = await _ctx(r["association_id"], user)
    _need(acc, STAFF)
    if body.document_id:
        await _check_docs(_aid(assoc), [body.document_id])
    ans = {"text": body.text.strip(), "document_id": body.document_id, "by": user["id"], "at": now_iso()}
    res = await db.radacini_assoc_requests.update_one({"_id": r["_id"], "status": "open"},
                                                      {"$set": {"status": "answered", "answered_at": ans["at"], "answer": ans}})
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea are deja răspuns.")
    await _audit(assoc, user, acc, "request.answer", "request", r["_id"],
                 after={"late": bool(r.get("due_at") and r["due_at"] < ans["at"])})
    if r.get("user_id"):
        await safe_notify(r["user_id"], "Răspuns la cererea ta", f"Cererea „{r['subject']}” a primit răspuns.",
                          _link(_aid(assoc), "cereri"), "info")
    return {"ok": True, "answer": ans}
