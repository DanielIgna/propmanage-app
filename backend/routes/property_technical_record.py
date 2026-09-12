"""Property Technical Record (v1) — dosarul tehnic viu al unei proprietăți.

Scop: layer de agregare NON-DESTRUCTIV peste infrastructura existentă. Reutilizează
`properties`, `property_documents`, `property_assets`, `twins`, `requests`,
`activity_events`, `buildings`. Adaugă:
  * câmpuri de context OPȚIONALE pe `buildings` (Domain B — Building Context)
  * colecție nouă `property_diagnostics` (Domain C — Regulatory Diagnostics)

Reguli critice (v1):
  * Domain A / B / C rămân distincte semantic — orice diagnostic nou pornește
    întotdeauna UNVERIFIED și niciodată nu devine VERIFIED automat.
  * jurisdiction este obligatoriu pentru orice diagnostic (FR/RO/OTHER etc.).
  * Nu se codifică reguli juridice — sunt doar categorii de date.
  * HartaBlocuri este o posibilă sursă externă (source_type=external_reference),
    fără scraping și fără import automat.
  * Transaction Readiness returnează doar statusuri (COMPLETE/PARTIAL/MISSING/
    NOT_VERIFIED) — NU un scor juridic sau numeric.

Endpoints:
  GET    /api/properties/{prop_id}/technical-record
  GET    /api/properties/{prop_id}/building-context
  POST   /api/properties/{prop_id}/building-context        (create+attach dacă lipsește)
  PATCH  /api/buildings/{building_id}/context               (update non-destructiv)
  GET    /api/properties/{prop_id}/diagnostics
  POST   /api/properties/{prop_id}/diagnostics
  PATCH  /api/diagnostics/{diag_id}
  DELETE /api/diagnostics/{diag_id}
  GET    /api/properties/{prop_id}/transaction-readiness
  GET    /api/technical-record/vocabulary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from routes.property_dna import _load_property_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["property_technical_record"])


# =============================================================================
# VOCABULARY (extensibil) — categorii de date, NU obligații legale
# =============================================================================
DIAGNOSTIC_TYPES = {
    "energy_performance": "Performanță energetică",
    "electrical": "Instalație electrică",
    "gas": "Instalație gaz",
    "asbestos": "Azbest",
    "lead": "Plumb",
    "sanitation": "Salubritate / apă",
    "risks_natural_technological": "Riscuri naturale / tehnologice",
    "structural": "Structură",
    "termite": "Termite / dăunători lemn",
    "noise": "Zgomot",
    "accessibility": "Accesibilitate",
    "thermal": "Termic (izolație)",
    "other": "Alt diagnostic",
}

JURISDICTIONS = {
    "FR": "Franța",
    "RO": "România",
    "EU": "Uniunea Europeană",
    "OTHER": "Altă jurisdicție",
}

BUILDING_TYPES = {
    "block": "Bloc de locuințe",
    "individual_house": "Casă individuală",
    "duplex": "Duplex / cuplat",
    "commercial": "Clădire comercială",
    "mixed": "Clădire mixtă",
    "other": "Altă tipologie",
}

VERIFICATION_LEVELS = {
    "unverified": "Neverificat",
    "declared": "Declarat",
    "documented": "Documentat",
    "verified": "Verificat",
}

SOURCE_TYPES = {
    "manual": "Introdus manual",
    "external_reference": "Referință externă",
    "public_registry": "Registru public",
    "professional_document": "Document profesional",
}


@router.get("/technical-record/vocabulary")
async def get_vocabulary(_user: dict = Depends(get_current_user)):
    """Categorii de date pentru UI (dropdown-uri) — extensibile fără refactor."""
    return {
        "diagnostic_types": [{"id": k, "label": v} for k, v in DIAGNOSTIC_TYPES.items()],
        "jurisdictions": [{"id": k, "label": v} for k, v in JURISDICTIONS.items()],
        "building_types": [{"id": k, "label": v} for k, v in BUILDING_TYPES.items()],
        "verification_levels": [{"id": k, "label": v} for k, v in VERIFICATION_LEVELS.items()],
        "source_types": [{"id": k, "label": v} for k, v in SOURCE_TYPES.items()],
    }


# =============================================================================
# DOMAIN B — BUILDING CONTEXT
# =============================================================================
class BuildingContextIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=180)
    address: Optional[str] = Field(default=None, max_length=280)
    city: Optional[str] = Field(default=None, max_length=120)
    construction_year: Optional[int] = Field(default=None, ge=1700, le=2100)
    building_type: Optional[str] = None
    number_of_units: Optional[int] = Field(default=None, ge=1, le=10000)
    floors: Optional[int] = Field(default=None, ge=0, le=200)
    source_type: Optional[str] = None
    source_name: Optional[str] = Field(default=None, max_length=160)
    source_reference: Optional[str] = Field(default=None, max_length=500)
    context_notes: Optional[str] = Field(default=None, max_length=2000)


def _serialize_building(b: dict) -> dict:
    if not b:
        return None
    ctx = b.get("context") or {}
    return {
        "id": str(b["_id"]),
        "name": b.get("name"),
        "address": b.get("address"),
        "city": b.get("city"),
        "construction_year": ctx.get("construction_year"),
        "building_type": ctx.get("building_type"),
        "building_type_label": BUILDING_TYPES.get(ctx.get("building_type") or ""),
        "number_of_units": ctx.get("number_of_units"),
        "floors": ctx.get("floors"),
        "source_type": ctx.get("source_type"),
        "source_type_label": SOURCE_TYPES.get(ctx.get("source_type") or ""),
        "source_name": ctx.get("source_name"),
        "source_reference": ctx.get("source_reference"),
        "verification_status": ctx.get("verification_status", "unverified"),
        "verification_status_label": VERIFICATION_LEVELS.get(
            ctx.get("verification_status", "unverified"), "Neverificat"
        ),
        "context_notes": ctx.get("context_notes"),
        "context_updated_at": ctx.get("updated_at"),
        "created_by": b.get("created_by"),
        "created_at": b.get("created_at"),
    }


async def _load_building_for_property(prop: dict) -> Optional[dict]:
    bid = prop.get("building_id")
    if not bid:
        return None
    try:
        return await db.buildings.find_one({"_id": ObjectId(bid)})
    except Exception:
        return None


@router.get("/properties/{prop_id}/building-context")
async def get_building_context(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    b = await _load_building_for_property(prop)
    if not b:
        return {"building": None, "attached": False}
    return {"building": _serialize_building(b), "attached": True}


@router.post("/properties/{prop_id}/building-context")
async def attach_or_create_building_context(
    prop_id: str,
    data: BuildingContextIn = Body(...),
    user: dict = Depends(get_current_user),
):
    """Atașează un building existent sau creează unul minim cu context.

    Dacă proprietatea are deja `building_id`, doar suprapunem câmpurile de context
    (aditiv, non-destructiv). Dacă nu are, creăm un building nou cu numele/adresa
    proprietății drept default și îl legăm.
    """
    prop = await _load_property_for(user, prop_id)
    ctx = _build_context_payload(data, user)

    existing = await _load_building_for_property(prop)
    if existing:
        merged_ctx = {**(existing.get("context") or {}), **ctx}
        await db.buildings.update_one(
            {"_id": existing["_id"]}, {"$set": {"context": merged_ctx}}
        )
        b = await db.buildings.find_one({"_id": existing["_id"]})
        return {"building": _serialize_building(b), "attached": True, "created": False}

    # Creează building nou minimal — non-destructiv, refolosește adresa proprietății
    name = (data.name or prop.get("name") or "Clădire").strip()
    address = (data.address or prop.get("address") or "").strip()
    if not address:
        raise HTTPException(400, "Adresa clădirii este obligatorie")
    doc = {
        "name": name,
        "address": address,
        "city": data.city,
        "created_by": user.get("id"),
        "created_by_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": ctx,
        "source": "property_technical_record",
    }
    res = await db.buildings.insert_one(doc)
    bid = str(res.inserted_id)
    await db.properties.update_one({"_id": ObjectId(prop_id)}, {"$set": {"building_id": bid}})
    doc["_id"] = res.inserted_id
    return {"building": _serialize_building(doc), "attached": True, "created": True}


def _build_context_payload(data: BuildingContextIn, user: dict) -> dict:
    """Construiește obiectul context; verification_status pornește UNVERIFIED."""
    if data.building_type and data.building_type not in BUILDING_TYPES:
        raise HTTPException(400, "Tip clădire invalid")
    if data.source_type and data.source_type not in SOURCE_TYPES:
        raise HTTPException(400, "Tip sursă invalid")
    now = datetime.now(timezone.utc).isoformat()
    ctx = {
        "construction_year": data.construction_year,
        "building_type": data.building_type,
        "number_of_units": data.number_of_units,
        "floors": data.floors,
        "source_type": data.source_type,
        "source_name": data.source_name,
        "source_reference": data.source_reference,
        "context_notes": data.context_notes,
        "verification_status": "unverified",  # v1: niciodată VERIFIED automat
        "updated_at": now,
        "updated_by": user.get("id"),
    }
    # elimină None-urile ca să facă un merge curat
    return {k: v for k, v in ctx.items() if v is not None}


@router.patch("/buildings/{building_id}/context")
async def update_building_context(
    building_id: str,
    data: BuildingContextIn = Body(...),
    user: dict = Depends(get_current_user),
):
    try:
        b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    except Exception:
        b = None
    if not b:
        raise HTTPException(404, "Clădirea nu există")
    # Autorizare: proprietar de proprietate din bloc SAU admin/operator
    role = user.get("active_view") or user.get("role")
    if role not in ("admin", "operator", "franchise_admin"):
        has_prop = await db.properties.count_documents(
            {"building_id": building_id, "owner_id": user.get("id")}
        )
        if not has_prop:
            raise HTTPException(403, "Nu ai acces la această clădire")
    ctx = _build_context_payload(data, user)
    merged = {**(b.get("context") or {}), **ctx}
    await db.buildings.update_one({"_id": b["_id"]}, {"$set": {"context": merged}})
    b2 = await db.buildings.find_one({"_id": b["_id"]})
    return {"building": _serialize_building(b2)}


# =============================================================================
# DOMAIN C — REGULATORY DIAGNOSTICS (colecție NOUĂ, izolată)
# =============================================================================
class DiagnosticIn(BaseModel):
    diagnostic_type: str = Field(min_length=2, max_length=80)
    jurisdiction: str = Field(min_length=2, max_length=8)
    issuing_professional: Optional[str] = Field(default=None, max_length=200)
    issuing_organization: Optional[str] = Field(default=None, max_length=200)
    issue_date: Optional[str] = Field(default=None, max_length=20)  # YYYY-MM-DD
    valid_from: Optional[str] = Field(default=None, max_length=20)
    valid_until: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=40)
    findings: Optional[str] = Field(default=None, max_length=4000)
    recommendations: Optional[str] = Field(default=None, max_length=4000)
    source_type: Optional[str] = Field(default=None, max_length=60)
    source_reference: Optional[str] = Field(default=None, max_length=500)
    document_ref: Optional[str] = Field(default=None, max_length=80)  # doc_id în property_documents
    notes: Optional[str] = Field(default=None, max_length=2000)


class DiagnosticPatch(BaseModel):
    diagnostic_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    issuing_professional: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    status: Optional[str] = None
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    source_type: Optional[str] = None
    source_reference: Optional[str] = None
    document_ref: Optional[str] = None
    notes: Optional[str] = None


def _diag_out(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "property_id": d.get("property_id"),
        "diagnostic_type": d.get("diagnostic_type"),
        "diagnostic_type_label": DIAGNOSTIC_TYPES.get(
            d.get("diagnostic_type") or "", d.get("diagnostic_type")
        ),
        "jurisdiction": d.get("jurisdiction"),
        "jurisdiction_label": JURISDICTIONS.get(d.get("jurisdiction") or "", d.get("jurisdiction")),
        "issuing_professional": d.get("issuing_professional"),
        "issuing_organization": d.get("issuing_organization"),
        "issue_date": d.get("issue_date"),
        "valid_from": d.get("valid_from"),
        "valid_until": d.get("valid_until"),
        "status": d.get("status"),
        "findings": d.get("findings"),
        "recommendations": d.get("recommendations"),
        "source_type": d.get("source_type"),
        "source_type_label": SOURCE_TYPES.get(d.get("source_type") or ""),
        "source_reference": d.get("source_reference"),
        "source": d.get("source"),
        "provenance": d.get("provenance"),
        "verification_status": d.get("verification_status", "unverified"),
        "verification_status_label": VERIFICATION_LEVELS.get(
            d.get("verification_status", "unverified"), "Neverificat"
        ),
        "confidence": d.get("confidence", "low"),
        "document_ref": d.get("document_ref"),
        "document_snapshot": d.get("document_snapshot"),
        "notes": d.get("notes"),
        "verified_at": d.get("verified_at"),
        "verified_by": d.get("verified_by"),
        "verified_by_name": d.get("verified_by_name"),
        "verification_notes": d.get("verification_notes"),
        "rejected_at": d.get("rejected_at"),
        "rejection_reason": d.get("rejection_reason"),
        "created_at": d.get("created_at"),
        "created_by": d.get("created_by"),
        "created_by_name": d.get("created_by_name"),
        "updated_at": d.get("updated_at"),
        "history": d.get("history") or [],
    }


def _validate_diag_common(data: DiagnosticIn | DiagnosticPatch):
    if getattr(data, "diagnostic_type", None) and data.diagnostic_type not in DIAGNOSTIC_TYPES:
        # extensibil: acceptăm și tipuri necunoscute dacă e valid string, dar limităm
        # pentru consistență la vocabular; agenții viitori pot extinde DIAGNOSTIC_TYPES.
        raise HTTPException(400, f"Tip diagnostic necunoscut: {data.diagnostic_type}")
    if getattr(data, "jurisdiction", None) and data.jurisdiction not in JURISDICTIONS:
        raise HTTPException(400, f"Jurisdicție necunoscută: {data.jurisdiction}")
    if getattr(data, "source_type", None) and data.source_type not in SOURCE_TYPES:
        raise HTTPException(400, f"Tip sursă necunoscut: {data.source_type}")


@router.get("/properties/{prop_id}/diagnostics")
async def list_diagnostics(prop_id: str, user: dict = Depends(get_current_user)):
    await _load_property_for(user, prop_id)
    items = []
    async for d in db.property_diagnostics.find(
        {"property_id": prop_id, "deleted": {"$ne": True}}
    ).sort("created_at", -1):
        items.append(_diag_out(d))
    return {
        "diagnostics": items,
        "total": len(items),
        "diagnostic_types": [{"id": k, "label": v} for k, v in DIAGNOSTIC_TYPES.items()],
        "jurisdictions": [{"id": k, "label": v} for k, v in JURISDICTIONS.items()],
    }


@router.post("/properties/{prop_id}/diagnostics")
async def add_diagnostic(
    prop_id: str,
    data: DiagnosticIn = Body(...),
    user: dict = Depends(get_current_user),
):
    prop = await _load_property_for(user, prop_id)
    _validate_diag_common(data)
    if not data.jurisdiction:
        raise HTTPException(400, "Jurisdicția este obligatorie pentru orice diagnostic")

    # sursă & provenance derivate din rol; niciodată VERIFIED automat.
    role = user.get("active_view") or user.get("role")
    source = "specialist" if role == "specialist" else (
        "platform" if role in ("admin", "operator") else "owner_upload"
    )
    provenance = "documented" if role in ("specialist", "admin", "operator") else "declared"

    # Validează document_ref (dacă e furnizat): trebuie să aparțină acestei proprietăți.
    doc_snapshot = None
    if data.document_ref:
        doc_snapshot = await _validate_and_snapshot_document(prop_id, data.document_ref)

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "property_id": prop_id,
        "owner_id": str(prop.get("owner_id")),
        **data.model_dump(exclude_none=True),
        "source": source,
        "provenance": provenance,
        "verification_status": "unverified",  # întotdeauna pornește neverificat
        "confidence": "low",
        "deleted": False,
        "created_at": now,
        "created_by": user.get("id"),
        "created_by_name": user.get("name"),
        "updated_at": now,
        "history": [{"at": now, "by": user.get("name"), "event": "create"}],
    }
    if doc_snapshot:
        doc["document_snapshot"] = doc_snapshot
    ins = await db.property_diagnostics.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return {"diagnostic": _diag_out(doc)}


async def _validate_and_snapshot_document(prop_id: str, doc_id: str) -> dict:
    """Verifică documentul aparține proprietății și returnează un snapshot minim."""
    try:
        pdoc = await db.property_documents.find_one(
            {"_id": ObjectId(doc_id), "property_id": prop_id, "deleted": {"$ne": True}}
        )
    except Exception:
        pdoc = None
    if not pdoc:
        raise HTTPException(400, "document_ref invalid pentru această proprietate")
    return {
        "id": str(pdoc["_id"]),
        "title": pdoc.get("title"),
        "category": pdoc.get("category"),
        "filename": pdoc.get("filename"),
        "uploaded_at": pdoc.get("uploaded_at"),
    }


@router.patch("/diagnostics/{diag_id}")
async def update_diagnostic(
    diag_id: str,
    data: DiagnosticPatch = Body(...),
    user: dict = Depends(get_current_user),
):
    try:
        d = await db.property_diagnostics.find_one({"_id": ObjectId(diag_id), "deleted": {"$ne": True}})
    except Exception:
        d = None
    if not d:
        raise HTTPException(404, "Diagnostic inexistent")
    await _load_property_for(user, d["property_id"])
    _validate_diag_common(data)

    changes = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not changes:
        return {"diagnostic": _diag_out(d)}
    now = datetime.now(timezone.utc).isoformat()
    changes["updated_at"] = now
    entry = {
        "at": now,
        "by": user.get("name"),
        "event": "edit",
        "changes": list(k for k in changes.keys() if k != "updated_at"),
    }
    await db.property_diagnostics.update_one(
        {"_id": d["_id"]}, {"$set": changes, "$push": {"history": entry}}
    )
    d2 = await db.property_diagnostics.find_one({"_id": d["_id"]})
    return {"diagnostic": _diag_out(d2)}


@router.delete("/diagnostics/{diag_id}")
async def delete_diagnostic(diag_id: str, user: dict = Depends(get_current_user)):
    try:
        d = await db.property_diagnostics.find_one({"_id": ObjectId(diag_id)})
    except Exception:
        d = None
    if not d:
        raise HTTPException(404, "Diagnostic inexistent")
    await _load_property_for(user, d["property_id"])
    now = datetime.now(timezone.utc).isoformat()
    entry = {"at": now, "by": user.get("name"), "event": "delete"}
    await db.property_diagnostics.update_one(
        {"_id": d["_id"]},
        {"$set": {"deleted": True, "updated_at": now}, "$push": {"history": entry}},
    )
    return {"ok": True}


# =============================================================================
# TRANSACTION READINESS — indicator DE COMPLETITUDINE, nu certificare juridică
# =============================================================================
async def _compute_transaction_readiness(prop_id: str, prop: dict) -> dict:
    """Statusuri simple per criteriu: COMPLETE | PARTIAL | MISSING | NOT_VERIFIED.

    Fără scor numeric. Fără afirmații juridice. Doar completitudine documentară.
    """
    docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}
    ).to_list(500)
    cats = {d.get("category") for d in docs}
    verified_docs = [d for d in docs if d.get("verification_status") == "verified"]

    assets_active = await db.property_assets.count_documents(
        {"property_id": prop_id, "status": "active"}
    )
    reqs_total = await db.requests.count_documents({"property_id": prop_id})
    events_total = await db.activity_events.count_documents({"property_id": prop_id})
    warranties = await db.warranties.count_documents({"property_id": prop_id, "status": "active"})

    building = await _load_building_for_property(prop)
    bctx = (building or {}).get("context") or {}
    building_has_year = bool(bctx.get("construction_year"))
    building_has_type = bool(bctx.get("building_type"))

    diags_count = await db.property_diagnostics.count_documents(
        {"property_id": prop_id, "deleted": {"$ne": True}}
    )
    diags_documented = await db.property_diagnostics.count_documents(
        {"property_id": prop_id, "deleted": {"$ne": True}, "verification_status": {"$in": ["documented", "verified"]}}
    )

    criteria = []

    # 1. Identity
    if prop.get("name") and prop.get("address") and prop.get("type"):
        st = "COMPLETE"
    elif prop.get("name") or prop.get("address"):
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "identity",
        "label": "Identitate proprietate",
        "status": st,
        "detail": "Nume, adresă, tip",
    })

    # 2. Basic property info
    filled = [x for x in (prop.get("rooms"), prop.get("surface")) if x]
    st = "COMPLETE" if len(filled) == 2 else ("PARTIAL" if filled else "MISSING")
    criteria.append({
        "id": "basic_info",
        "label": "Informații de bază",
        "status": st,
        "detail": "Suprafață, camere",
    })

    # 3. Technical documentation (act + cadastru)
    has_act = "act_proprietate" in cats
    has_cad = "cadastru" in cats
    if has_act and has_cad:
        st = "COMPLETE"
    elif has_act or has_cad:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "technical_documentation",
        "label": "Documentație tehnică de bază",
        "status": st,
        "detail": "Act de proprietate, cadastru",
    })

    # 4. Documents available (min. 3)
    if len(docs) >= 5:
        st = "COMPLETE"
    elif len(docs) >= 1:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "documents_available",
        "label": "Documente disponibile",
        "status": st,
        "detail": f"{len(docs)} documente încărcate",
    })

    # 5. Systems documented
    if assets_active >= 3:
        st = "COMPLETE"
    elif assets_active >= 1:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "systems_documented",
        "label": "Sisteme tehnice documentate",
        "status": st,
        "detail": f"{assets_active} active înregistrate",
    })

    # 6. Intervention history
    if reqs_total + events_total >= 3:
        st = "COMPLETE"
    elif reqs_total + events_total >= 1:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "intervention_history",
        "label": "Istoric intervenții",
        "status": st,
        "detail": f"{reqs_total} cereri, {events_total} evenimente",
    })

    # 7. Verification status
    if verified_docs and len(verified_docs) >= 2:
        st = "COMPLETE"
    elif verified_docs:
        st = "PARTIAL"
    else:
        st = "NOT_VERIFIED"
    criteria.append({
        "id": "verification",
        "label": "Verificare documente",
        "status": st,
        "detail": f"{len(verified_docs)} documente verificate",
    })

    # 8. Building context
    if building_has_year and building_has_type:
        st = "COMPLETE"
    elif building_has_year or building_has_type or building:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "building_context",
        "label": "Context clădire",
        "status": st,
        "detail": "An construcție, tipologie",
    })

    # 9. Regulatory diagnostics
    if diags_documented >= 1:
        st = "COMPLETE"
    elif diags_count >= 1:
        st = "PARTIAL"
    else:
        st = "MISSING"
    criteria.append({
        "id": "regulatory_diagnostics",
        "label": "Diagnostice tehnice",
        "status": st,
        "detail": f"{diags_count} înregistrate ({diags_documented} documentate)",
    })

    # 10. Warranties
    st = "COMPLETE" if warranties >= 1 else "MISSING"
    criteria.append({
        "id": "warranties",
        "label": "Garanții active",
        "status": st,
        "detail": f"{warranties} garanții active",
    })

    # Overall status — worst-case, dar fără scor numeric.
    status_priority = {"MISSING": 3, "NOT_VERIFIED": 2, "PARTIAL": 1, "COMPLETE": 0}
    worst = max((status_priority[c["status"]] for c in criteria), default=0)
    overall = {v: k for k, v in status_priority.items()}[worst]

    missing_evidence = [c["label"] for c in criteria if c["status"] == "MISSING"]

    return {
        "overall_status": overall,
        "criteria": criteria,
        "missing_evidence": missing_evidence,
        "disclaimer": (
            "Acesta este un indicator de completitudine a documentației, "
            "nu o certificare juridică sau un scor de conformitate."
        ),
    }


@router.get("/properties/{prop_id}/transaction-readiness")
async def transaction_readiness(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    return await _compute_transaction_readiness(prop_id, prop)


# =============================================================================
# PROPERTY TECHNICAL RECORD — agregare completă (single endpoint pentru UI)
# =============================================================================
@router.get("/properties/{prop_id}/technical-record")
async def technical_record(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)

    # ── Property Core (reutilizare TOTALĂ, fără duplicare) ──────────────────
    docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}
    ).to_list(500)

    docs_by_cat: dict = {}
    for d in docs:
        docs_by_cat[d.get("category", "?")] = docs_by_cat.get(d.get("category", "?"), 0) + 1

    assets_count = await db.property_assets.count_documents(
        {"property_id": prop_id, "status": "active"}
    )
    twin = await db.twins.find_one({"property_id": prop_id})
    reqs_count = await db.requests.count_documents({"property_id": prop_id})
    events_count = await db.activity_events.count_documents({"property_id": prop_id})
    maint_count = await db.maintenance_logs.count_documents({"property_id": prop_id})
    warranties_count = await db.warranties.count_documents(
        {"property_id": prop_id, "status": "active"}
    )

    verified_docs = sum(1 for d in docs if d.get("verification_status") == "verified")

    property_core = {
        "identity": {
            "id": prop_id,
            "name": prop.get("name"),
            "address": prop.get("address"),
            "type": prop.get("type"),
            "rooms": prop.get("rooms"),
            "surface": prop.get("surface"),
            "created_at": prop.get("created_at"),
        },
        "health": {
            "score": prop.get("health_score"),
            "structure": prop.get("structure_health"),
            "utilities": prop.get("utilities_health"),
            "documents": prop.get("documents_health"),
        },
        "digital_twin": {
            "status": (twin or {}).get("status"),
            "unlocked": bool(prop.get("twin_unlocked")),
            "assets_in_twin": len((twin or {}).get("assets") or []),
        },
        "stats": {
            "documents": len(docs),
            "documents_by_category": docs_by_cat,
            "documents_verified": verified_docs,
            "assets_active": assets_count,
            "requests": reqs_count,
            "events": events_count,
            "maintenance_logs": maint_count,
            "warranties_active": warranties_count,
        },
    }

    # ── Building Context ────────────────────────────────────────────────────
    building = await _load_building_for_property(prop)
    building_context = _serialize_building(building) if building else None

    # ── Regulatory Diagnostics ──────────────────────────────────────────────
    diag_list = []
    async for d in db.property_diagnostics.find(
        {"property_id": prop_id, "deleted": {"$ne": True}}
    ).sort("created_at", -1):
        diag_list.append(_diag_out(d))

    # ── Transaction Readiness (agregat) ─────────────────────────────────────
    readiness = await _compute_transaction_readiness(prop_id, prop)

    # ── Documentation completeness header stats ─────────────────────────────
    last_updated = None
    if docs:
        last_updated = max((d.get("uploaded_at") or "") for d in docs)

    return {
        "property_id": prop_id,
        "property_core": property_core,
        "building_context": building_context,
        "regulatory_diagnostics": {
            "items": diag_list,
            "total": len(diag_list),
            "by_jurisdiction": _by_jurisdiction(diag_list),
        },
        "transaction_readiness": readiness,
        "header": {
            "property_name": prop.get("name"),
            "property_address": prop.get("address"),
            "documents_count": len(docs),
            "documents_verified": verified_docs,
            "last_updated": last_updated,
            "overall_status": readiness["overall_status"],
        },
        "viewer": {
            "role": user.get("active_view") or user.get("role"),
            "is_verifier": (user.get("active_view") or user.get("role")) in ("admin", "operator"),
        },
        "endpoints": {
            "documents": f"/api/properties/{prop_id}/documents",
            "assets": f"/api/properties/{prop_id}/assets",
            "timeline": f"/api/properties/{prop_id}/timeline",
            "risks": f"/api/properties/{prop_id}/risks",
            "dna": f"/api/properties/{prop_id}/dna",
            "building_context": f"/api/properties/{prop_id}/building-context",
            "diagnostics": f"/api/properties/{prop_id}/diagnostics",
            "transaction_readiness": f"/api/properties/{prop_id}/transaction-readiness",
        },
    }


def _by_jurisdiction(items: list) -> dict:
    out: dict = {}
    for d in items:
        j = d.get("jurisdiction") or "OTHER"
        out[j] = out.get(j, 0) + 1
    return out


# =============================================================================
# ADMIN VERIFICATION FLOW — un diagnostic devine VERIFIED doar prin această cale
# =============================================================================
def _require_verifier(user: dict):
    role = user.get("active_view") or user.get("role")
    if role not in ("admin", "operator"):
        raise HTTPException(403, "Doar admin/operator poate verifica.")
    return role


class VerifyPayload(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


class RejectPayload(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/admin/diagnostics/{diag_id}/verify")
async def verify_diagnostic(
    diag_id: str,
    payload: VerifyPayload = Body(default_factory=VerifyPayload),
    user: dict = Depends(get_current_user),
):
    """Promovează un diagnostic la VERIFIED. Necesită evidence (document_ref sau source_reference)."""
    _require_verifier(user)
    try:
        d = await db.property_diagnostics.find_one(
            {"_id": ObjectId(diag_id), "deleted": {"$ne": True}}
        )
    except Exception:
        d = None
    if not d:
        raise HTTPException(404, "Diagnostic inexistent")
    if not (d.get("document_ref") or d.get("source_reference")):
        raise HTTPException(
            400,
            "Diagnosticul nu poate fi verificat fără evidență (document atașat sau referință sursă).",
        )
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "at": now, "by": user.get("name"), "event": "verify",
        "notes": (payload.notes or None),
    }
    await db.property_diagnostics.update_one(
        {"_id": d["_id"]},
        {
            "$set": {
                "verification_status": "verified",
                "confidence": "high",
                "verified_at": now,
                "verified_by": user.get("id"),
                "verified_by_name": user.get("name"),
                "verification_notes": payload.notes,
                "updated_at": now,
            },
            "$push": {"history": entry},
        },
    )
    d2 = await db.property_diagnostics.find_one({"_id": d["_id"]})
    return {"diagnostic": _diag_out(d2)}


@router.post("/admin/diagnostics/{diag_id}/reject")
async def reject_diagnostic(
    diag_id: str,
    payload: RejectPayload = Body(...),
    user: dict = Depends(get_current_user),
):
    """Respinge verificarea: readuce diagnosticul la UNVERIFIED cu motiv."""
    _require_verifier(user)
    try:
        d = await db.property_diagnostics.find_one(
            {"_id": ObjectId(diag_id), "deleted": {"$ne": True}}
        )
    except Exception:
        d = None
    if not d:
        raise HTTPException(404, "Diagnostic inexistent")
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "at": now, "by": user.get("name"), "event": "reject",
        "reason": payload.reason,
    }
    await db.property_diagnostics.update_one(
        {"_id": d["_id"]},
        {
            "$set": {
                "verification_status": "unverified",
                "confidence": "low",
                "rejected_at": now,
                "rejection_reason": payload.reason,
                "updated_at": now,
            },
            "$push": {"history": entry},
        },
    )
    d2 = await db.property_diagnostics.find_one({"_id": d["_id"]})
    return {"diagnostic": _diag_out(d2)}


@router.post("/admin/buildings/{building_id}/verify")
async def verify_building_context(
    building_id: str,
    payload: VerifyPayload = Body(default_factory=VerifyPayload),
    user: dict = Depends(get_current_user),
):
    """Marchează context-ul unei clădiri ca VERIFIED — devine sursă comună pentru toți vecinii."""
    _require_verifier(user)
    try:
        b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    except Exception:
        b = None
    if not b:
        raise HTTPException(404, "Clădirea nu există")
    now = datetime.now(timezone.utc).isoformat()
    ctx = {**(b.get("context") or {})}
    ctx["verification_status"] = "verified"
    ctx["verified_at"] = now
    ctx["verified_by"] = user.get("id")
    ctx["verified_by_name"] = user.get("name")
    ctx["verification_notes"] = payload.notes
    ctx["updated_at"] = now
    await db.buildings.update_one({"_id": b["_id"]}, {"$set": {"context": ctx}})
    b2 = await db.buildings.find_one({"_id": b["_id"]})
    return {"building": _serialize_building(b2)}


# =============================================================================
# DOCUMENT PICKER — helper pentru UI care leagă un diagnostic de un document existent
# =============================================================================
@router.get("/properties/{prop_id}/documents-picker")
async def documents_picker(prop_id: str, user: dict = Depends(get_current_user)):
    """Listă compactă de documente pentru selector în formularul de diagnostic."""
    await _load_property_for(user, prop_id)
    docs = []
    async for d in db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}
    ).sort("uploaded_at", -1):
        docs.append({
            "id": str(d["_id"]),
            "title": d.get("title"),
            "category": d.get("category"),
            "filename": d.get("filename"),
            "uploaded_at": d.get("uploaded_at"),
            "verification_status": d.get("verification_status", "unverified"),
        })
    return {"documents": docs, "total": len(docs)}


# =============================================================================
# BUILDING NEIGHBOURS — a doua axă: BUILDING → multiple PROPERTIES
# =============================================================================
@router.get("/properties/{prop_id}/building-neighbours")
async def building_neighbours(prop_id: str, user: dict = Depends(get_current_user)):
    """Alte proprietăți din aceeași clădire. Doar identitate minimă (nu date personale)."""
    prop = await _load_property_for(user, prop_id)
    bid = prop.get("building_id")
    if not bid:
        return {"building": None, "neighbours": [], "total": 0}
    building = await _load_building_for_property(prop)
    others = []
    async for p in db.properties.find(
        {"building_id": bid, "_id": {"$ne": ObjectId(prop_id)}},
        {"name": 1, "type": 1, "rooms": 1, "surface": 1, "created_at": 1},
    ):
        others.append({
            "id": str(p["_id"]),
            "name": p.get("name"),
            "type": p.get("type"),
            "rooms": p.get("rooms"),
            "surface": p.get("surface"),
        })
    return {
        "building": _serialize_building(building) if building else None,
        "neighbours": others,
        "total": len(others),
        "shared_context_verified": (building or {}).get("context", {}).get("verification_status") == "verified",
    }


class AttachBuildingPayload(BaseModel):
    building_id: str = Field(min_length=8)


@router.post("/properties/{prop_id}/attach-building")
async def attach_existing_building(
    prop_id: str,
    payload: AttachBuildingPayload = Body(...),
    user: dict = Depends(get_current_user),
):
    """Conectează o proprietate existentă la o clădire deja înregistrată (o clădire verificată).

    Nu modifică contextul clădirii, doar face legătura. Astfel toți vecinii moștenesc
    Building Context-ul verificat, fără duplicare de date.
    """
    prop = await _load_property_for(user, prop_id)
    try:
        b = await db.buildings.find_one({"_id": ObjectId(payload.building_id)})
    except Exception:
        b = None
    if not b:
        raise HTTPException(404, "Clădirea specificată nu există")
    # doar owner-ul proprietății sau admin poate conecta
    role = user.get("active_view") or user.get("role")
    if role not in ("admin", "operator", "franchise_admin") and str(prop.get("owner_id")) != str(user.get("id")):
        raise HTTPException(403, "Nu ai acces la această proprietate")
    await db.properties.update_one(
        {"_id": ObjectId(prop_id)},
        {"$set": {"building_id": payload.building_id}},
    )
    return {"attached": True, "building": _serialize_building(b)}


@router.get("/buildings/search")
async def search_buildings_for_ptr(
    q: str = "",
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """Caută clădiri după nume/adresă pentru „conectează la o clădire existentă"."""
    _ = user  # any authenticated user
    limit = max(1, min(limit, 50))
    query = {}
    if q and len(q) >= 2:
        import re as _re
        rx = {"$regex": _re.escape(q), "$options": "i"}
        query = {"$or": [{"name": rx}, {"address": rx}, {"city": rx}]}
    else:
        return {"buildings": [], "total": 0}
    items = []
    async for b in db.buildings.find(query).limit(limit):
        s = _serialize_building(b)
        s["units_registered"] = await db.properties.count_documents({"building_id": s["id"]})
        items.append(s)
    return {"buildings": items, "total": len(items)}


# =============================================================================
# TRANSACTION READINESS — export PDF (indicator de completitudine, nu certificare)
# =============================================================================
@router.get("/properties/{prop_id}/transaction-readiness.pdf")
async def transaction_readiness_pdf(prop_id: str, user: dict = Depends(get_current_user)):
    """One-page PDF cu checklist-ul de pregătire, disclaimer vizibil."""
    from fastapi.responses import Response as _R
    prop = await _load_property_for(user, prop_id)
    readiness = await _compute_transaction_readiness(prop_id, prop)
    building = await _load_building_for_property(prop)
    diags_count = await db.property_diagnostics.count_documents(
        {"property_id": prop_id, "deleted": {"$ne": True}}
    )
    pdf_bytes = _render_readiness_pdf(prop, readiness, building, diags_count)
    filename = f"pregatire-tranzactie-{prop_id[:8]}.pdf"
    return _R(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _render_readiness_pdf(prop: dict, readiness: dict, building: Optional[dict], diags_count: int) -> bytes:
    """Randează un raport A4 simplu cu reportlab. Nu depinde de resurse externe."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors as _c

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    x = 20 * mm
    y = H - 20 * mm

    def line(text, font="Helvetica", size=10, color=_c.black, dy=6 * mm):
        nonlocal y
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawString(x, y, text)
        y -= dy

    # Header
    c.setFillColor(_c.HexColor("#0f172a"))
    c.rect(0, H - 15 * mm, W, 15 * mm, fill=1, stroke=0)
    c.setFillColor(_c.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, H - 10 * mm, "PropManage · Pregătire tranzacție")
    c.setFont("Helvetica", 9)
    c.setFillColor(_c.HexColor("#94a3b8"))
    c.drawRightString(W - 20 * mm, H - 10 * mm, datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"))
    y = H - 25 * mm

    line(prop.get("name") or "Proprietate", "Helvetica-Bold", 14, _c.HexColor("#0f172a"), dy=6 * mm)
    if prop.get("address"):
        line(prop["address"], "Helvetica", 10, _c.HexColor("#475569"), dy=4 * mm)
    y -= 3 * mm

    # Status global
    status = readiness.get("overall_status", "MISSING")
    status_colors = {
        "COMPLETE": _c.HexColor("#059669"),
        "PARTIAL": _c.HexColor("#d97706"),
        "MISSING": _c.HexColor("#64748b"),
        "NOT_VERIFIED": _c.HexColor("#0284c7"),
    }
    labels = {"COMPLETE": "Complet", "PARTIAL": "Parțial", "MISSING": "Lipsă", "NOT_VERIFIED": "Neverificat"}
    c.setFillColor(status_colors.get(status, _c.gray))
    c.rect(x, y - 2 * mm, 40 * mm, 8 * mm, fill=1, stroke=0)
    c.setFillColor(_c.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 3 * mm, y + 1 * mm, f"Status general: {labels.get(status, status)}")
    y -= 12 * mm

    # Meta
    if building:
        meta = f"Clădire: {building.get('name') or '—'} · An: {building.get('construction_year') or '—'} · Tip: {building.get('building_type_label') or '—'}"
        line(meta, "Helvetica", 9, _c.HexColor("#475569"), dy=5 * mm)
    line(f"Diagnostice înregistrate: {diags_count}", "Helvetica", 9, _c.HexColor("#475569"), dy=5 * mm)
    y -= 2 * mm

    # Criteria list
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(_c.HexColor("#0f172a"))
    c.drawString(x, y, "Criterii de completitudine")
    y -= 6 * mm
    for crit in readiness.get("criteria", []):
        crit_status = crit["status"]
        col = status_colors.get(crit_status, _c.gray)
        # bullet
        c.setFillColor(col)
        c.circle(x + 1.5 * mm, y + 1 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(_c.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(x + 5 * mm, y + 0.5 * mm, crit["label"])
        c.setFont("Helvetica", 8.5)
        c.setFillColor(_c.HexColor("#64748b"))
        c.drawString(x + 5 * mm, y - 2 * mm, crit["detail"])
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(col)
        c.drawRightString(W - 20 * mm, y + 0.5 * mm, labels.get(crit_status, crit_status).upper())
        y -= 8 * mm
        if y < 40 * mm:
            c.showPage()
            y = H - 20 * mm

    # Missing evidence
    missing = readiness.get("missing_evidence") or []
    if missing:
        y -= 3 * mm
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(_c.HexColor("#0f172a"))
        c.drawString(x, y, "Ce lipsește / de completat")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        c.setFillColor(_c.HexColor("#475569"))
        for m in missing[:8]:
            c.drawString(x + 4 * mm, y, f"• {m}")
            y -= 4.5 * mm

    # Footer disclaimer
    c.setFillColor(_c.HexColor("#f1f5f9"))
    c.rect(0, 0, W, 18 * mm, fill=1, stroke=0)
    c.setFillColor(_c.HexColor("#475569"))
    c.setFont("Helvetica-Oblique", 8)
    disclaimer_lines = [
        readiness.get("disclaimer", ""),
        "Nu este un certificat juridic sau un scor de conformitate. Documentele individuale își păstrează statusul propriu de verificare.",
        "Generat de PropManage · propmanage.ro",
    ]
    yy = 12 * mm
    for ln in disclaimer_lines:
        c.drawString(x, yy, ln)
        yy -= 3.5 * mm

    c.showPage()
    c.save()
    return buf.getvalue()
