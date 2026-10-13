"""Personal Rădăcini (operator/manager): coada de verificare și gestionarea personalului."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from .bridge import db, emit, get_current_user, is_super_admin, notify, serialize_doc
from .common import RadaciniRoute, load_owners, mark_demo, now_iso, oid_or_404
from .constants import LOCALITIES

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)


async def get_staff(user: dict) -> Optional[dict]:
    """{role, areas} pentru personalul Rădăcini, None dacă userul nu e personal.
    Super-adminul PropManage este manager cu acces la toate localitățile."""
    if is_super_admin(user):
        return {"role": "manager", "areas": []}
    doc = await db.radacini_staff.find_one({"user_id": str(user["id"])})
    if not doc:
        return None
    return {"role": doc.get("role"), "areas": doc.get("areas") or []}


def require_staff(*roles: str):
    """Dependență: userul trebuie să fie personal (cu unul din rolurile date; fără roluri = orice)."""

    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        staff = await get_staff(user)
        if staff is None or (roles and staff["role"] not in roles):
            detail = "Acces doar pentru manager." if roles == ("manager",) else "Acces doar pentru personalul Rădăcini."
            raise HTTPException(403, detail)
        return {"user": user, **staff}

    return dependency


def _queue_view(doc: dict, owners: dict) -> dict:
    out = serialize_doc(doc)
    owner = owners.get(str(doc.get("owner_user_id")), {})
    out["owner_name"] = owner.get("name", "")
    out["owner_email"] = owner.get("email", "")
    return out


@router.get("/staff/me")
async def my_staff(user: dict = Depends(get_current_user)):
    staff = await get_staff(user)
    if staff is None:
        return {"is_staff": False, "role": None, "areas": []}
    return {"is_staff": True, **staff}


@router.get("/staff/queue")
async def verification_queue(staff: dict = Depends(require_staff("operator", "manager"))):
    flt: dict = {"status": "pending_verification", "archived_at": {"$exists": False}}
    if staff["role"] == "operator" and staff["areas"]:
        flt["locality"] = {"$in": list(staff["areas"])}
    docs = await db.radacini_parcels.find(flt).sort("updated_at", 1).to_list(200)
    owners = await load_owners(d.get("owner_user_id") for d in docs)
    return {"items": [_queue_view(d, owners) for d in docs]}


class VerifyIn(BaseModel):
    decision: str
    note: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("Decizie invalidă.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Nota are cel mult 1000 de caractere.")
        return v or None

    @model_validator(mode="after")
    def _reject_needs_note(self):
        if self.decision == "reject" and not self.note:
            raise ValueError("Motivul respingerii este obligatoriu.")
        return self


@router.post("/staff/parcels/{parcel_id}/verify")
async def verify_parcel(
    parcel_id: str,
    body: VerifyIn,
    staff: dict = Depends(require_staff("operator", "manager")),
):
    user = staff["user"]
    doc = await db.radacini_parcels.find_one({"_id": oid_or_404(parcel_id)})
    if not doc or doc.get("archived_at"):
        raise HTTPException(404, "Terenul nu există.")
    if staff["role"] == "operator" and staff["areas"] and doc.get("locality") not in staff["areas"]:
        raise HTTPException(403, "Terenul nu este în zona ta de lucru.")
    if doc.get("status") != "pending_verification":
        raise HTTPException(409, "Terenul nu așteaptă verificarea.")
    # Conflict de interese: personalul nu își verifică propriile terenuri (super-adminul e exceptat cât e singur).
    if str(doc.get("owner_user_id")) == str(user["id"]) and not is_super_admin(user):
        raise HTTPException(403, "Nu poți verifica propriul teren.")

    now = now_iso()
    approved = body.decision == "approve"
    changes = {
        "status": "published" if approved else "rejected",
        "verification": {"by": str(user["id"]), "at": now, "decision": body.decision, "note": body.note},
        "updated_at": now,
    }
    await db.radacini_parcels.update_one({"_id": doc["_id"]}, {"$set": changes})
    doc = {**doc, **changes}

    title = doc.get("title") or "Terenul tău"
    if approved:
        notif_title, message = "Terenul a fost aprobat", f"„{title}” este publicat acum."
    else:
        notif_title, message = "Terenul a fost respins", f"„{title}” a fost respins: {body.note}"
    try:
        await notify(
            str(doc.get("owner_user_id")),
            notif_title,
            message,
            type_="verification",
            link="/radacini/terenurile-mele",
        )
    except Exception:  # noqa: BLE001 — notificarea nu trebuie să blocheze verificarea
        log.warning("radacini: notificarea de verificare nu a putut fi trimisă", exc_info=True)

    await emit(
        "radacini.parcel_verified",
        actor=user,
        payload={"parcel_id": str(doc["_id"]), "decision": body.decision},
    )
    return {"parcel": serialize_doc(doc)}


@router.get("/staff")
async def list_staff(_: dict = Depends(require_staff("manager"))):
    docs = await db.radacini_staff.find({}).sort("created_at", 1).to_list(500)
    return {"items": [serialize_doc(d) for d in docs]}


class StaffIn(BaseModel):
    email: str
    role: str
    areas: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v) > 254:
            raise ValueError("Email invalid.")
        return v

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in ("operator", "manager"):
            raise ValueError("Rol invalid. Alege operator sau manager.")
        return v

    @field_validator("areas")
    @classmethod
    def _areas(cls, v: list[str]) -> list[str]:
        if any(a not in LOCALITIES for a in v):
            raise ValueError("Localitate necunoscută.")
        return list(dict.fromkeys(v))


@router.post("/staff")
async def add_staff(body: StaffIn, staff: dict = Depends(require_staff("manager"))):
    user = staff["user"]
    target = await db.users.find_one({"email": body.email})
    if not target:
        raise HTTPException(404, "Nu există un cont PropManage cu acest email.")
    uid = str(target["_id"])
    if await db.radacini_staff.find_one({"user_id": uid}):
        raise HTTPException(409, "Utilizatorul face deja parte din personal.")
    doc = mark_demo({
        "user_id": uid,
        "email": target.get("email") or body.email,
        "name": target.get("name") or "",
        "role": body.role,
        "areas": body.areas,
        "created_at": now_iso(),
        "created_by": str(user["id"]),
    })
    await db.radacini_staff.insert_one(doc)
    return {"staff": serialize_doc(doc)}


@router.delete("/staff/{user_id}")
async def remove_staff(user_id: str, _: dict = Depends(require_staff("manager"))):
    doc = await db.radacini_staff.find_one({"user_id": str(user_id)})
    if not doc:
        raise HTTPException(404, "Membrul de personal nu există.")
    await db.radacini_staff.delete_one({"_id": doc["_id"]})
    return {"ok": True}
