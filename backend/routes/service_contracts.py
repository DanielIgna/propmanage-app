"""Service Contract — Romanian editable template + electronic signature.

Generates a service contract from a request, lets both parties sign,
and the Operator can add mediation resolution if needed.

Template stored in app_settings.contract_template. Default template included
inline (Romanian, generic intention-letter level — NOT a notarial act).

Collection: service_contracts
  {id, request_id, client_id, client_email, specialist_id, specialist_email,
   body_html, signed_by_client, signed_by_client_at, signed_by_specialist,
   signed_by_specialist_at, operator_resolution, status, created_at, version}
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import get_current_user, require_role
from db import db

logger = logging.getLogger("propmanage.contracts")
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Default Romanian template — clauze de bază, nu act notarial, intention-letter style.
DEFAULT_TEMPLATE = """
<h1 style="text-align:center;font-family:serif;">CONTRACT DE PRESTĂRI SERVICII</h1>
<p style="text-align:center;color:#666;font-size:13px;">Mediat prin platforma PropManage, operată de VINTAGE FURNITURE S.R.L. (CUI 35250247, Nr. Reg. Com. J12/3534/2015) · Document electronic non-notarial</p>

<h3>1. PĂRȚILE CONTRACTANTE</h3>
<p><strong>CLIENT:</strong> {{client_name}}, email: {{client_email}}, telefon: {{client_phone}}<br>
<strong>SPECIALIST:</strong> {{specialist_name}}, specialitate: {{specialist_specialty}}, email: {{specialist_email}}, oraș: {{specialist_city}}</p>

<h3>2. OBIECTUL CONTRACTULUI</h3>
<p>Specialistul se obligă să presteze următoarele servicii: <strong>{{request_title}}</strong>.<br>
Descriere detaliată: {{request_description}}<br>
Categorie: {{request_category}} · Prioritate: {{request_priority}}</p>

<h3>3. PREȚ ȘI MOD DE PLATĂ</h3>
<p>Prețul total estimat al lucrării este de <strong>{{price}} RON</strong> (inclusiv TVA dacă este cazul).<br>
Plata se efectuează prin sistemul ESCROW al platformei PropManage (Stripe), conform următorului grafic:
<br>— 50% la confirmarea contractului (avans, blocat în escrow);
<br>— 50% la recepția lucrării, după validarea de către Client.<br>
Comisionul platformei (2.5%) este reținut automat la deblocarea fondurilor.</p>

<h3>4. OBLIGAȚIILE CLIENTULUI</h3>
<ul>
<li>Să furnizeze toate informațiile, accesul și materialele necesare execuției lucrării.</li>
<li>Să respecte termenele de plată stabilite prin platformă.</li>
<li>Să comunice cu Specialistul prin canalele oficiale PropManage (chat în aplicație).</li>
<li>Să recepționeze lucrarea în maxim 48h de la notificarea finalizării.</li>
</ul>

<h3>5. OBLIGAȚIILE SPECIALISTULUI</h3>
<ul>
<li>Să execute lucrarea cu profesionalism și conform standardelor specialității sale.</li>
<li>Să respecte termenul agreat: <strong>{{deadline}}</strong>.</li>
<li>Să folosească materiale corespunzătoare normelor în vigoare.</li>
<li>Să comunice orice întârziere sau modificare cel puțin 24h în avans.</li>
<li>Să ofere garanție de minim 30 de zile pentru lucrare.</li>
</ul>

<h3>6. MEDIEREA PRIN OPERATOR PROPMANAGE</h3>
<p>În caz de neînțelegere între Părți, acestea convin <strong>să apeleze cu prioritate la serviciul de mediere</strong> oferit
de Operatorul PropManage prin sistemul intern de Dispute & Mediere. Operatorul va analiza dovezile depuse de ambele
părți (mesaje, fotografii, devize) și va emite o <em>recomandare de rezoluție</em> în maxim 5 zile lucrătoare.
Această procedură de mediere este <strong>obligatorie înainte</strong> de a recurge la instanțele competente.</p>

<h3>7. DISPUTĂ ȘI INSTANȚĂ COMPETENTĂ</h3>
<p>Dacă medierea nu duce la o rezoluție, Părțile pot recurge la instanțele de drept comun de pe raza Municipiului
București. Prezentul contract se supune legii române.</p>

<h3>8. RECEPȚIA LUCRĂRII</h3>
<p>La finalizare, Specialistul marchează lucrarea ca <em>completă</em>. Clientul are 48h pentru a o accepta sau
contesta. Lipsa unui răspuns în acest interval este considerată acceptare tacită, iar restul fondurilor escrow
sunt deblocate către Specialist.</p>

<h3>9. CLAUZE FINALE</h3>
<p>Prezentul contract este încheiat electronic prin acceptarea ambelor părți pe platforma PropManage și are valoarea
juridică a unei <em>scrisori de intenție comercială</em>. Pentru valoarea de act autentic, Părțile pot opta separat
pentru notarizare.</p>

<p style="margin-top:30px;border-top:1px dashed #ccc;padding-top:15px;font-size:12px;color:#666;">
Generat automat de PropManage · {{now}}<br>
ID contract: {{contract_id}} · Versiunea template: {{template_version}}
</p>
"""


def _render(template: str, ctx: dict) -> str:
    """Simple {{var}} replacement — safe for HTML (no eval)."""
    out = template
    for k, v in ctx.items():
        out = out.replace(f"{{{{{k}}}}}", str(v) if v is not None else "—")
    # Replace any unresolved placeholders with em-dash
    import re
    out = re.sub(r"\{\{[a-zA-Z_]+\}\}", "—", out)
    return out


# ---------- Schemas ----------
class GenerateIn(BaseModel):
    request_id: str = Field(min_length=3)


class SignIn(BaseModel):
    signature_name: str = Field(min_length=2, max_length=200)


class OperatorResolveIn(BaseModel):
    resolution: str = Field(min_length=10, max_length=4000)


# ---------- Endpoints ----------
@router.post("/generate")
async def generate(payload: GenerateIn, user: dict = Depends(get_current_user)):
    """Generate a contract from a request. Client OR specialist OR admin can trigger."""
    from bson import ObjectId
    # Dual lookup: try ObjectId (Mongo _id) first, fall back to string id field.
    req = None
    try:
        req = await db.requests.find_one({"_id": ObjectId(payload.request_id)})
    except Exception:
        pass
    if not req:
        req = await db.requests.find_one({"id": payload.request_id})
    if not req:
        raise HTTPException(404, "Solicitarea nu a fost găsită")

    uid = str(user.get("id"))
    if uid not in (str(req.get("client_id")), str(req.get("specialist_id"))) and user.get("role") not in ("admin", "operator"):
        raise HTTPException(403, "Acces refuzat")

    # Existing contract?
    existing = await db.service_contracts.find_one({"request_id": payload.request_id})
    if existing:
        existing.pop("_id", None)
        return existing

    # Build context
    settings_doc = await db.app_settings.find_one({"_id": "app_settings"}) or {}
    template = settings_doc.get("contract_template") or DEFAULT_TEMPLATE
    template_version = settings_doc.get("contract_template_version") or "v1.0"

    # Lookup client + specialist users
    from bson import ObjectId
    async def _find_user(uid):
        if not uid:
            return {}
        try:
            return await db.users.find_one({"_id": ObjectId(uid)}) or await db.users.find_one({"id": str(uid)}) or {}
        except Exception:
            return await db.users.find_one({"id": str(uid)}) or {}

    client = await _find_user(req.get("client_id"))
    specialist = await _find_user(req.get("specialist_id"))

    ctx = {
        "client_name": client.get("name") or "Client",
        "client_email": client.get("email") or "",
        "client_phone": client.get("phone") or "—",
        "specialist_name": specialist.get("name") or req.get("specialist_name") or "Specialist",
        "specialist_email": specialist.get("email") or "",
        "specialist_specialty": specialist.get("specialty") or req.get("specialist_specialty") or "—",
        "specialist_city": specialist.get("city") or req.get("specialist_city") or "—",
        "request_title": req.get("title") or "Lucrare",
        "request_description": req.get("description") or "—",
        "request_category": req.get("category") or "—",
        "request_priority": req.get("priority") or "normal",
        "price": req.get("budget_estimate") or req.get("accepted_price") or "0",
        "deadline": req.get("deadline") or "30 de zile de la semnare",
        "now": datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
        "contract_id": "",  # filled below
        "template_version": template_version,
    }
    contract_id = uuid.uuid4().hex
    ctx["contract_id"] = contract_id
    body_html = _render(template, ctx)

    # Normalize request_id to string for stable lookups via /by-request/{request_id}
    request_id_str = str(req.get("_id") or req.get("id") or payload.request_id)

    doc = {
        "id": contract_id,
        "request_id": request_id_str,
        "client_id": str(req.get("client_id")) if req.get("client_id") else None,
        "client_email": ctx["client_email"],
        "specialist_id": str(req.get("specialist_id")) if req.get("specialist_id") else None,
        "specialist_email": ctx["specialist_email"],
        "body_html": body_html,
        "signed_by_client": False,
        "signed_by_client_at": None,
        "signed_by_client_name": None,
        "signed_by_specialist": False,
        "signed_by_specialist_at": None,
        "signed_by_specialist_name": None,
        "operator_resolution": None,
        "status": "draft",
        "template_version": template_version,
        "created_at": _now(),
        "version": 1,
    }
    await db.service_contracts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/{cid}")
async def get_contract(cid: str, user: dict = Depends(get_current_user)):
    c = await db.service_contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    uid = str(user.get("id"))
    allowed = uid in (str(c.get("client_id")), str(c.get("specialist_id"))) or user.get("role") in ("admin", "operator")
    if not allowed:
        raise HTTPException(403, "Acces refuzat")
    c.pop("_id", None)
    return c


@router.post("/{cid}/sign")
async def sign(cid: str, payload: SignIn, user: dict = Depends(get_current_user)):
    c = await db.service_contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    uid = str(user.get("id"))
    is_client = uid == str(c.get("client_id"))
    is_specialist = uid == str(c.get("specialist_id"))
    if not (is_client or is_specialist):
        raise HTTPException(403, "Doar părțile contractante pot semna")

    update = {}
    if is_client:
        update["signed_by_client"] = True
        update["signed_by_client_at"] = _now()
        update["signed_by_client_name"] = payload.signature_name
    if is_specialist:
        update["signed_by_specialist"] = True
        update["signed_by_specialist_at"] = _now()
        update["signed_by_specialist_name"] = payload.signature_name

    # Status transition
    refreshed = {**c, **update}
    if refreshed.get("signed_by_client") and refreshed.get("signed_by_specialist"):
        update["status"] = "active"

    await db.service_contracts.update_one({"id": cid}, {"$set": update})
    new_c = await db.service_contracts.find_one({"id": cid})
    new_c.pop("_id", None)
    return new_c


@router.post("/{cid}/operator-resolve")
async def operator_resolve(cid: str, payload: OperatorResolveIn, user: dict = Depends(require_role("operator", "admin"))):
    c = await db.service_contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    await db.service_contracts.update_one(
        {"id": cid},
        {"$set": {
            "operator_resolution": payload.resolution,
            "operator_resolved_by": user.get("email"),
            "operator_resolved_at": _now(),
            "status": "mediated",
        }},
    )
    new_c = await db.service_contracts.find_one({"id": cid})
    new_c.pop("_id", None)
    return new_c


@router.get("/by-request/{request_id}")
async def by_request(request_id: str, user: dict = Depends(get_current_user)):
    # Try direct match first; if not found and request_id is a uuid form, also try ObjectId
    c = await db.service_contracts.find_one({"request_id": request_id})
    if not c:
        from bson import ObjectId
        try:
            c = await db.service_contracts.find_one({"request_id": str(ObjectId(request_id))})
        except Exception:
            pass
    if not c:
        return {"contract": None}
    uid = str(user.get("id"))
    allowed = uid in (str(c.get("client_id")), str(c.get("specialist_id"))) or user.get("role") in ("admin", "operator")
    if not allowed:
        raise HTTPException(403, "Acces refuzat")
    c.pop("_id", None)
    return {"contract": c}


@router.get("/list/my")
async def my_contracts(user: dict = Depends(get_current_user)):
    """List contracts where current user is a party."""
    uid = str(user.get("id"))
    cur = db.service_contracts.find({
        "$or": [{"client_id": uid}, {"specialist_id": uid}],
    }, {"body_html": 0}).sort("created_at", -1).limit(100)
    items = []
    async for c in cur:
        c.pop("_id", None)
        items.append(c)
    return {"items": items, "total": len(items)}
