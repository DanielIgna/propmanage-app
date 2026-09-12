"""GI-5P Sprint 1 — Property Intelligence API (Board approved, spec frozen).

Maturity L0–L5, Registru Active (Trust Model 015) și Predictive actuarial.
Reuse: _load_property_for din property_dna (același control de acces, zero duplicare).
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import get_current_user
from routes.property_dna import _load_property_for
import property_intelligence as pi

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["property_intelligence"])

CLIENT_SOURCES = {"owner_declared", "official_document"}
ADMIN_SOURCES = CLIENT_SOURCES | {"professional_audit", "verified"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit_opp_id(prop_id: str):
    opp = await db.revenue_opportunities.find_one(
        {"property_id": prop_id, "service": "audit_tehnic", "status": "active"}, {"id": 1})
    return (opp or {}).get("id")


def _validate_asset_input(body: dict, user: dict) -> dict:
    out = {}
    if "installed_year" in body:
        year = body.get("installed_year")
        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                raise HTTPException(400, "An de instalare invalid")
            if year < 1900 or year > datetime.now(timezone.utc).year:
                raise HTTPException(400, "An de instalare invalid (1900 – prezent)")
        out["installed_year"] = year
    if "source" in body:
        source = body.get("source") or "owner_declared"
        role = user.get("active_view") or user.get("role")
        allowed = ADMIN_SOURCES if role in ("admin", "operator") else CLIENT_SOURCES
        if source not in allowed:
            raise HTTPException(400, f"Sursă invalidă. Permise: {', '.join(sorted(allowed))}")
        out["source"] = source
    if "notes" in body:
        out["notes"] = str(body.get("notes") or "")[:500]
    return out


@router.get("/properties/{prop_id}/maturity")
async def property_maturity(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    m = await pi.refresh_maturity(prop)
    m["audit_opportunity_id"] = await _audit_opp_id(prop_id)
    return m


@router.get("/properties/{prop_id}/assets")
async def property_assets(prop_id: str, user: dict = Depends(get_current_user)):
    await _load_property_for(user, prop_id)
    return {"property_id": prop_id, "library_version": pi.LIBRARY_VERSION,
            "slots": await pi.asset_slots(prop_id),
            "audit_opportunity_id": await _audit_opp_id(prop_id)}


@router.post("/properties/{prop_id}/assets")
async def register_asset(prop_id: str, body: dict = Body(...), user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    asset_type = body.get("asset_type")
    if asset_type not in pi.ASSET_LIBRARY:
        raise HTTPException(400, "Tip de activ necunoscut")
    fields = _validate_asset_input({"installed_year": body.get("installed_year"),
                                    "source": body.get("source") or "owner_declared",
                                    "notes": body.get("notes")}, user)
    source = fields["source"]
    # Slotul: activul vechi devine "replaced", noul moștenește slotul (Asset Lifecycle §8)
    await db.property_assets.update_many(
        {"property_id": prop_id, "asset_type": asset_type, "status": "active"},
        {"$set": {"status": "replaced", "replaced_at": _now()}})
    doc = {
        "id": uuid.uuid4().hex, "property_id": prop_id, "asset_type": asset_type,
        "label": pi.ASSET_LIBRARY[asset_type]["label"],
        "installed_year": fields.get("installed_year"), "notes": fields.get("notes") or "",
        # Trust Model — Directiva 015
        "source": source, "confidence": source,
        "verification_status": "verified" if source in ("verified", "professional_audit") else "unverified",
        "last_updated": _now(), "updated_by": user.get("email") or user.get("id"),
        "status": "active", "created_at": _now(),
    }
    await db.property_assets.insert_one({**doc})
    try:
        from event_bus import emit
        await emit("twin.asset_registered", property_id=prop_id, actor=user,
                   payload={"asset_type": asset_type, "source": source,
                            "installed_year": fields.get("installed_year")})
    except Exception:  # noqa: BLE001
        pass
    await pi.refresh_maturity({**prop, "maturity": prop.get("maturity")})
    return {"ok": True, "asset_id": doc["id"], "slots": await pi.asset_slots(prop_id)}


@router.patch("/properties/{prop_id}/assets/{asset_id}")
async def update_asset(prop_id: str, asset_id: str, body: dict = Body(...),
                       user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    asset = await db.property_assets.find_one({"id": asset_id, "property_id": prop_id, "status": "active"})
    if not asset:
        raise HTTPException(404, "Activul nu există")
    fields = _validate_asset_input({k: body[k] for k in ("installed_year", "source", "notes") if k in body}, user)
    if not fields:
        raise HTTPException(400, "Nimic de actualizat")
    if "source" in fields:
        fields["confidence"] = fields["source"]
        fields["verification_status"] = ("verified" if fields["source"] in ("verified", "professional_audit")
                                         else "unverified")
    fields["last_updated"] = _now()
    fields["updated_by"] = user.get("email") or user.get("id")
    await db.property_assets.update_one({"id": asset_id}, {"$set": fields})
    await pi.refresh_maturity(prop)
    return {"ok": True, "slots": await pi.asset_slots(prop_id)}


@router.get("/properties/{prop_id}/predictive")
async def property_predictive(prop_id: str, user: dict = Depends(get_current_user)):
    await _load_property_for(user, prop_id)
    return {"property_id": prop_id, "library_version": pi.LIBRARY_VERSION,
            "predictions": await pi.predictions(prop_id),
            "disclaimer": ("Valori estimate pe baza bibliotecii actuariale de referință — sunt recomandări, "
                           "nu fapte. Un audit tehnic confirmă starea reală.")}


# ── GI-5P Sprint 2 — DNA v2 atribute cu provenance + Risk Engine ─────────────
@router.get("/properties/{prop_id}/dna-attributes")
async def get_dna_attributes(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    stored = prop.get("dna_attributes") or {}
    attributes = []
    for key, spec in pi.DNA_ATTRIBUTES.items():
        cur = stored.get(key) or {}
        attributes.append({"key": key, "label": spec["label"], "type": spec["type"],
                           "options": spec.get("options"), "value": cur.get("value"),
                           "source": cur.get("source"),
                           "confidence_label": pi.CONFIDENCE_LABELS.get(cur.get("confidence")),
                           "last_updated": cur.get("last_updated")})
    return {"property_id": prop_id, "attributes": attributes}


@router.patch("/properties/{prop_id}/dna-attributes")
async def patch_dna_attributes(prop_id: str, body: dict = Body(...),
                               user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    source = body.get("source") or "owner_declared"
    role = user.get("active_view") or user.get("role")
    allowed = ADMIN_SOURCES if role in ("admin", "operator") else CLIENT_SOURCES
    if source not in allowed:
        raise HTTPException(400, f"Sursă invalidă. Permise: {', '.join(sorted(allowed))}")
    updates = body.get("attributes") or {}
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    sets = {}
    for key, value in updates.items():
        spec = pi.DNA_ATTRIBUTES.get(key)
        if not spec:
            raise HTTPException(400, f"Atribut necunoscut: {key}")
        if spec["type"] == "int":
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise HTTPException(400, f"{spec['label']}: valoare invalidă")
            if not (spec["min"] <= value <= spec["max"]):
                raise HTTPException(400, f"{spec['label']}: în afara intervalului {spec['min']}–{spec['max']}")
        elif spec["type"] == "enum" and value not in spec["options"]:
            raise HTTPException(400, f"{spec['label']}: opțiune invalidă")
        # Trust Model — Directiva 015: provenance pe fiecare atribut
        sets[f"dna_attributes.{key}"] = {"value": value, "source": source, "confidence": source,
                                         "last_updated": _now(),
                                         "updated_by": user.get("email") or user.get("id")}
    await db.properties.update_one({"_id": prop["_id"]}, {"$set": sets})
    try:
        from event_bus import emit
        await emit("twin.dna_attribute_updated", property_id=prop_id, actor=user,
                   payload={"attributes": list(updates.keys()), "source": source})
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "updated": list(updates.keys())}


@router.get("/properties/{prop_id}/risks")
async def property_risks(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    risks = await pi.compute_risks(prop)
    await pi.refresh_risk_profile(prop, risks)
    return {"property_id": prop_id, "risks": risks,
            "audit_opportunity_id": await _audit_opp_id(prop_id),
            "disclaimer": ("Riscuri estimate pe baza dovezilor din Digital Twin — "
                           "un audit tehnic confirmă starea reală.")}
