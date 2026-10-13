"""Plan de culturi al proiectului: culturi, suprafețe, avertizări de rotație."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, check_finite, mark_demo, now_iso, oid_or_404
from .constants import CROPS, CROP_STATUS_IDS
from .projects import ensure_active, load_project, need_coordinator

router = APIRouter(route_class=RadaciniRoute)

_BY_KEY = {}
for _c in CROPS:
    _BY_KEY[_c["id"]] = _c
    _BY_KEY[_c["label"].lower()] = _c


def resolve_crop(raw: str) -> dict:
    """Cultură din meta (după id sau etichetă) sau text liber (familia `other`)."""
    known = _BY_KEY.get(raw.strip().lower())
    if known:
        return {"crop": known["label"], "crop_id": known["id"], "family": known["family"]}
    return {"crop": raw.strip(), "crop_id": None, "family": "other"}


# ----------------------------------------------------------------- scheme

class _Common(BaseModel):
    """Validări comune (acceptă None pentru PATCH)."""

    @field_validator("crop", check_fields=False)
    @classmethod
    def _v_crop(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not 2 <= len(v) <= 60:
            raise ValueError("Cultura trebuie să aibă între 2 și 60 de caractere.")
        return v

    @field_validator("area_m2", check_fields=False)
    @classmethod
    def _v_area(cls, v):
        if v is not None and v < 1:
            raise ValueError("Suprafața trebuie să fie pozitivă.")
        return v

    @field_validator("expected_yield_kg", check_fields=False)
    @classmethod
    def _v_yield(cls, v):
        check_finite(v, "Producția estimată nu este validă.")
        if v is not None and not 0 <= v <= 100_000_000:
            raise ValueError("Producția estimată nu este validă.")
        return v

    @field_validator("notes", check_fields=False)
    @classmethod
    def _v_notes(cls, v):
        if v is None:
            return None
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Notele au cel mult 1000 de caractere.")
        return v or None

    @field_validator("status", check_fields=False)
    @classmethod
    def _v_status(cls, v):
        if v is not None and v not in CROP_STATUS_IDS:
            raise ValueError("Stare invalidă.")
        return v


class CropIn(_Common):
    crop: str
    area_m2: int
    sow_date: date
    expected_harvest_date: Optional[date] = None
    expected_yield_kg: Optional[float] = None
    notes: Optional[str] = None
    status: str = "planned"


class CropPatch(_Common):
    crop: Optional[str] = None
    area_m2: Optional[int] = None
    sow_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    expected_yield_kg: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ----------------------------------------------------------------- logică

def check_dates(sow: str, harvest: Optional[str]) -> None:
    if harvest and harvest < sow:
        raise HTTPException(400, "Recolta estimată nu poate fi înaintea semănatului.")


async def rotation_warnings(project: dict, crops: list[dict]) -> list[str]:
    """Familii cultivate și în proiectul anterior pe același teren (doar avertizare)."""
    families = {c.get("family") for c in crops if c.get("family") and c.get("family") != "other"}
    if not families or not project.get("parcel_id"):
        return []
    prevs = await db.radacini_projects.find(
        {"parcel_id": project["parcel_id"], "created_at": {"$lt": project["created_at"]}}
    ).sort("created_at", -1).to_list(1)
    if not prevs:
        return []
    prev_crops = await db.radacini_crop_plans.find({"project_id": str(prevs[0]["_id"])}).to_list(500)
    prev_families = {c.get("family") for c in prev_crops}
    return [
        f"Rotație: familia {fam} a fost cultivată și în proiectul anterior pe acest teren."
        for fam in sorted(families & prev_families)
    ]


def area_warning(project: dict, crops: list[dict]) -> list[str]:
    total = sum(c.get("area_m2") or 0 for c in crops)
    if project.get("area_m2") and total > project["area_m2"]:
        return [f"Suprafața culturilor ({total} m²) depășește suprafața proiectului ({project['area_m2']} m²)."]
    return []


async def _check_area(project: dict, project_id: str, area: int, exclude_id=None) -> None:
    others = await db.radacini_crop_plans.find({"project_id": project_id}).to_list(500)
    used = sum(c.get("area_m2") or 0 for c in others if c["_id"] != exclude_id)
    limit = project.get("area_m2") or 0
    if used + area > limit:
        raise HTTPException(
            400,
            f"Suprafața totală a culturilor ({used + area} m²) depășește suprafața proiectului ({limit} m²).",
        )


async def _load_crop(crop_id: str, user: dict) -> tuple[dict, dict, str, Optional[str]]:
    crop = await db.radacini_crop_plans.find_one({"_id": oid_or_404(crop_id)})
    if not crop:
        raise HTTPException(404, "Cultura nu există.")
    project, access, role = await load_project(crop["project_id"], user)
    return crop, project, access, role


# ----------------------------------------------------------------- rute

@router.get("/projects/{project_id}/crops")
async def list_crops(project_id: str, user: dict = Depends(get_current_user)):
    project, _, _ = await load_project(project_id, user)
    docs = await db.radacini_crop_plans.find({"project_id": str(project["_id"])}).sort("sow_date", 1).to_list(500)
    warnings = area_warning(project, docs) + await rotation_warnings(project, docs)
    return {"items": [serialize_doc(d) for d in docs], "warnings": warnings}


@router.post("/projects/{project_id}/crops")
async def create_crop(project_id: str, body: CropIn, user: dict = Depends(get_current_user)):
    project, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    pid = str(project["_id"])
    data = body.model_dump(mode="json")
    check_dates(data["sow_date"], data.get("expected_harvest_date"))
    await _check_area(project, pid, body.area_m2)
    now = now_iso()
    doc = mark_demo({
        "project_id": pid,
        **resolve_crop(data.pop("crop")),
        **data,
        "created_by": str(user["id"]),
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_crop_plans.insert_one(doc)
    await emit("radacini.project_crop_added", actor=user, payload={"project_id": pid, "crop_plan_id": str(doc["_id"])})
    return {"crop": serialize_doc(doc), "warnings": await rotation_warnings(project, [doc])}


@router.patch("/crops/{crop_id}")
async def patch_crop(crop_id: str, body: CropPatch, user: dict = Depends(get_current_user)):
    crop, project, access, role = await _load_crop(crop_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    changes = body.model_dump(mode="json", exclude_unset=True)
    for key in ("crop", "area_m2", "sow_date", "status"):
        if key in changes and changes[key] is None:
            raise HTTPException(400, f"Câmpul {key} nu poate fi gol.")
    if "crop" in changes:
        changes.update(resolve_crop(changes["crop"]))
    merged = {**crop, **changes}
    check_dates(merged["sow_date"], merged.get("expected_harvest_date"))
    if "area_m2" in changes:
        await _check_area(project, crop["project_id"], changes["area_m2"], exclude_id=crop["_id"])
    if not changes:
        return {"crop": serialize_doc(crop), "warnings": []}
    changes["updated_at"] = now_iso()
    await db.radacini_crop_plans.update_one({"_id": crop["_id"]}, {"$set": changes})
    await emit("radacini.project_crop_updated", actor=user, payload={"project_id": crop["project_id"], "crop_plan_id": crop_id})
    return {"crop": serialize_doc({**crop, **changes}), "warnings": await rotation_warnings(project, [merged])}


@router.delete("/crops/{crop_id}")
async def delete_crop(crop_id: str, user: dict = Depends(get_current_user)):
    crop, project, access, role = await _load_crop(crop_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    await db.radacini_crop_plans.delete_one({"_id": crop["_id"]})
    await emit("radacini.project_crop_removed", actor=user, payload={"project_id": crop["project_id"], "crop_plan_id": crop_id})
    return {"ok": True}
