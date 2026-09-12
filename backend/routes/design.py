"""PropManage router: design."""
import logging
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role
from services import notify
from models import (
    DesignConceptIn, DesignPhaseAcceptIn, DesignPhaseQuoteIn,
    DESIGN_CONCEPT_PRICE_PER_ROOM, DESIGN_MAX_TOKEN_DISCOUNT_PCT,
)
from email_service import (
    send_template, tpl_design_phase_quote,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["design"])

# ============= INTERIOR DESIGN (eligible only for clients with Digital Twin unlocked) =============

@router.get("/design/eligibility")
async def design_eligibility(user: dict = Depends(require_role("client"))):
    """Returns user's properties with twin_unlocked + rooms list per property."""
    props = await db.properties.find({"owner_id": user["id"], "twin_unlocked": True}).to_list(20)
    if not props:
        return {"eligible": False, "reason": "no_twin_unlocked", "properties": []}
    out = []
    for p in props:
        prop_id_str = str(p["_id"])
        twin = await db.twins.find_one({"property_id": prop_id_str, "status": "approved"})
        rooms = (twin or {}).get("rooms") or []
        out.append({
            "id": prop_id_str,
            "name": p.get("name"),
            "address": p.get("address"),
            "surface": p.get("surface"),
            "rooms": [{"id": r.get("id"), "name": r.get("name"), "type": r.get("type"), "area": r.get("area")} for r in rooms],
        })
    return {
        "eligible": True,
        "properties": out,
        "concept_price_per_room": DESIGN_CONCEPT_PRICE_PER_ROOM,
        "max_token_discount_pct": DESIGN_MAX_TOKEN_DISCOUNT_PCT,
        "available_tokens": user.get("tokens", 0),
    }

@router.post("/design/concept-request")
async def create_design_concept_request(data: DesignConceptIn, user: dict = Depends(require_role("client"))):
    """Create a design concept request after validating twin + room ids + tokens."""
    prop = await db.properties.find_one({"_id": ObjectId(data.property_id), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Property not found")
    if not prop.get("twin_unlocked"):
        raise HTTPException(403, "Digital Twin nu este activat pentru această proprietate. Solicită activarea twin-ului mai întâi.")

    twin = await db.twins.find_one({"property_id": data.property_id, "status": "approved"})
    if not twin:
        raise HTTPException(403, "Digital Twin pentru proprietate nu este aprobat")

    twin_room_ids = {r.get("id") for r in (twin.get("rooms") or [])}
    invalid_rooms = [r for r in data.room_ids if r not in twin_room_ids]
    if invalid_rooms:
        raise HTTPException(400, f"Camere invalide: {', '.join(invalid_rooms)}")

    rooms_count = len(data.room_ids)
    full_price = DESIGN_CONCEPT_PRICE_PER_ROOM * rooms_count
    max_token_discount = full_price * (DESIGN_MAX_TOKEN_DISCOUNT_PCT / 100)
    tokens_to_use = max(0, min(data.tokens_to_use, int(max_token_discount), user.get("tokens", 0)))
    final_price = full_price - tokens_to_use

    # Snapshot room details for the request
    rooms_snapshot = []
    for rid in data.room_ids:
        r = next((x for x in twin.get("rooms", []) if x.get("id") == rid), None)
        if r:
            rooms_snapshot.append({"id": r.get("id"), "name": r.get("name"), "type": r.get("type"), "area": r.get("area")})

    desc_lines = [f"📐 Faza CONCEPT pentru {rooms_count} {'cameră' if rooms_count == 1 else 'camere'}:"]
    for r in rooms_snapshot:
        desc_lines.append(f"  • {r['name']} ({r['type']}, {r.get('area', 0)} m²)")
    desc_lines.append(f"\nPreț standard: {DESIGN_CONCEPT_PRICE_PER_ROOM:.0f} RON/cameră × {rooms_count} = {full_price:.0f} RON")
    if tokens_to_use > 0:
        desc_lines.append(f"Tokeni utilizați: -{tokens_to_use} RON")
    desc_lines.append(f"Preț final concept: {final_price:.0f} RON")
    if data.style_preference:
        desc_lines.append(f"\nStil preferat: {data.style_preference}")
    if data.notes:
        desc_lines.append(f"\nNote suplimentare: {data.notes}")
    desc_lines.append("\nDupă livrarea conceptului, specialistul va trimite oferte pentru faze ulterioare (proiect tehnic, execuție, achiziții) direct prin chat.")

    title = f"Design Interior - Concept ({rooms_count} {'cameră' if rooms_count == 1 else 'camere'})"
    now_iso = datetime.now(timezone.utc).isoformat()
    req_doc = {
        "client_id": user["id"],
        "client_name": user.get("name"),
        "property_id": data.property_id,
        "property_name": prop.get("name"),
        "category": "interior_design",
        "title": title,
        "description": "\n".join(desc_lines),
        "priority": "normal",
        "photos": [],
        "status": "open",
        "specialist_id": None,
        "specialist_name": None,
        "escrow_amount": 0,
        "escrow_status": "none",
        "budget_estimate": final_price,
        "design_concept": {
            "rooms": rooms_snapshot,
            "rooms_count": rooms_count,
            "full_price": full_price,
            "tokens_used": tokens_to_use,
            "final_price": final_price,
            "style_preference": data.style_preference,
        },
        "phases": [],
        "created_at": now_iso,
    }
    res = await db.requests.insert_one(req_doc)
    req_id = str(res.inserted_id)

    # Deduct tokens immediately + record transaction
    if tokens_to_use > 0:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"tokens": -tokens_to_use}})
        await db.transactions.insert_one({
            "user_id": user["id"], "type": "design_token_discount",
            "amount": 0, "tokens": -tokens_to_use,
            "request_id": req_id, "created_at": now_iso,
        })

    # Notify available interior_design specialists (idle/coverage match)
    matched_specs = await db.users.find({
        "role": "specialist",
        "verified": True,
        "service_categories": "interior_design",
    }).limit(20).to_list(20)
    for s in matched_specs:
        await notify(str(s["_id"]), "Lead Design Interior", f"Nouă cerere de concept design — {rooms_count} {'cameră' if rooms_count == 1 else 'camere'}, {final_price:.0f} RON", type_="lead", link="/specialist")

    req_doc["id"] = req_id
    req_doc.pop("_id", None)
    return req_doc


@router.post("/design/phase-quote")
async def create_phase_quote(data: DesignPhaseQuoteIn, user: dict = Depends(require_role("specialist"))):
    """Specialist proposes a follow-up phase quote on a design request."""
    req = await db.requests.find_one({"_id": ObjectId(data.request_id), "specialist_id": user["id"]})
    if not req:
        raise HTTPException(404, "Cererea nu există sau nu îți este asignată")
    if req.get("category") != "interior_design":
        raise HTTPException(400, "Quote-urile pe faze sunt disponibile doar pentru lucrări de Design Interior")
    if req.get("status") not in ["in_progress", "completed", "confirmed"]:
        raise HTTPException(400, "Faza concept trebuie să fie cel puțin în desfășurare pentru a propune faze ulterioare")

    quote = {
        "id": str(uuid.uuid4()),
        "phase_name": data.phase_name,
        "description": data.description,
        "price": data.price,
        "estimated_days": data.estimated_days,
        "status": "pending",  # pending | accepted | rejected | paid
        "created_at": datetime.now(timezone.utc).isoformat(),
        "specialist_id": user["id"],
    }
    await db.requests.update_one(
        {"_id": ObjectId(data.request_id)},
        {"$push": {"phases": quote}}
    )
    client_u = await db.users.find_one({"_id": ObjectId(req["client_id"])})
    await notify(req["client_id"], "Ofertă fază nouă", f"{user.get('name','Specialistul')} a propus o fază nouă: {data.phase_name} — {data.price:.0f} RON", type_="design_phase", link="/client")
    if client_u and client_u.get("email"):
        await send_template(
            tpl_design_phase_quote,
            client_u.get("name", ""),
            user.get("name", "Specialist"),
            req.get("title", ""),
            data.phase_name,
            data.price,
            data.estimated_days,
            data.description,
            to=client_u["email"],
        )
    return quote


@router.post("/design/phase-accept")
async def accept_phase_quote(data: DesignPhaseAcceptIn, request_id: str, user: dict = Depends(require_role("client"))):
    """Client accepts a phase quote — funds escrow from wallet (or via Stripe in future)."""
    req = await db.requests.find_one({"_id": ObjectId(request_id), "client_id": user["id"]})
    if not req:
        raise HTTPException(404, "Cerere inexistentă")
    phases = req.get("phases", [])
    quote = next((p for p in phases if p.get("id") == data.quote_id), None)
    if not quote:
        raise HTTPException(404, "Ofertă inexistentă")
    if quote.get("status") != "pending":
        raise HTTPException(400, "Această ofertă nu mai este disponibilă")

    if (user.get("wallet_balance") or 0) < quote["price"]:
        raise HTTPException(400, f"Sold insuficient. Necesar: {quote['price']:.0f} RON, Disponibil: {user.get('wallet_balance', 0):.0f} RON")

    now_iso = datetime.now(timezone.utc).isoformat()
    # Deduct from wallet, mark phase paid (held in escrow logically)
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -quote["price"]}})
    await db.requests.update_one(
        {"_id": ObjectId(request_id), "phases.id": data.quote_id},
        {"$set": {"phases.$.status": "paid", "phases.$.paid_at": now_iso}}
    )
    await db.transactions.insert_one({
        "user_id": user["id"], "type": "design_phase_payment", "amount": -quote["price"],
        "request_id": request_id, "phase_id": data.quote_id, "created_at": now_iso,
    })
    await notify(quote["specialist_id"], "Plată fază confirmată", f"Clientul a achitat faza '{quote['phase_name']}' — {quote['price']:.0f} RON sunt în escrow", type_="design_phase", link="/specialist")
    return {"ok": True, "phase_id": data.quote_id}


@router.post("/design/phase-complete")
async def complete_phase(data: DesignPhaseAcceptIn, request_id: str, user: dict = Depends(require_role("client"))):
    """Client confirms phase completion — releases escrow to specialist wallet (95/5 split)."""
    req = await db.requests.find_one({"_id": ObjectId(request_id), "client_id": user["id"]})
    if not req:
        raise HTTPException(404, "Cerere inexistentă")
    phases = req.get("phases", [])
    quote = next((p for p in phases if p.get("id") == data.quote_id), None)
    if not quote:
        raise HTTPException(404, "Ofertă inexistentă")
    if quote.get("status") != "paid":
        raise HTTPException(400, "Această fază nu este în escrow")

    specialist_share = quote["price"] * 0.95
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": ObjectId(quote["specialist_id"])}, {"$inc": {"wallet_balance": specialist_share}})
    await db.requests.update_one(
        {"_id": ObjectId(request_id), "phases.id": data.quote_id},
        {"$set": {"phases.$.status": "completed", "phases.$.completed_at": now_iso}}
    )
    await db.transactions.insert_one({
        "user_id": quote["specialist_id"], "type": "design_phase_payout", "amount": specialist_share,
        "request_id": request_id, "phase_id": data.quote_id, "created_at": now_iso,
    })
    await notify(quote["specialist_id"], "Fază finalizată", f"Faza '{quote['phase_name']}' confirmată — {specialist_share:.0f} RON adăugați în portofel", type_="design_phase", link="/specialist")
    return {"ok": True, "released_amount": specialist_share}


