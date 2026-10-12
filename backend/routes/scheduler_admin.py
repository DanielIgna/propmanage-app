"""/api/admin/scheduler — cron jobs: list, profile (full/lite), add / edit / delete / restore, toggle, run now."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import job_control as jc
from deps import require_role

admin_router = APIRouter(prefix="/api/admin/scheduler", tags=["scheduler-admin"])
CATEGORIES = {"business", "monitoring", "ai", "reports", "other"}


def _scheduler():
    from server import scheduler
    return scheduler


class ProfileIn(BaseModel):
    profile: str
    reset_overrides: bool = False


class ToggleIn(BaseModel):
    enabled: bool


class JobIn(BaseModel):
    task: str
    label: str
    cron: str
    category: Optional[str] = None
    enabled: bool = True


class JobEdit(BaseModel):
    label: Optional[str] = None
    category: Optional[str] = None
    cron: Optional[str] = None  # "" = back to the default schedule (code jobs)
    enabled: Optional[bool] = None


async def _update(mutate):
    try:
        await jc.update_settings(_scheduler(), mutate)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return await jc.snapshot(_scheduler())


async def _require_job(job_id: str) -> dict:
    settings = await jc.load_settings()
    if not jc.is_known(job_id, settings):
        raise HTTPException(404, "Job inexistent")
    return settings


def _check(category: Optional[str], cron: Optional[str]):
    if category is not None and category not in CATEGORIES:
        raise HTTPException(400, "Categorie invalidă")
    if cron:
        try:
            jc.parse_cron(cron)
        except ValueError as e:
            raise HTTPException(400, f"Program invalid: {e}")


@admin_router.get("/jobs")
async def list_jobs(user: dict = Depends(require_role("admin"))):
    return await jc.snapshot(_scheduler())


@admin_router.post("/profile")
async def set_profile(data: ProfileIn, user: dict = Depends(require_role("admin"))):
    if data.profile not in jc.PROFILES:
        raise HTTPException(400, "Profil invalid")

    def mutate(s):
        s["profile"] = data.profile
        if data.reset_overrides:  # edits go, deleted jobs stay deleted
            s["overrides"] = {k: {"deleted": True} for k, v in s["overrides"].items() if v.get("deleted")}
    return await _update(mutate)


@admin_router.post("/jobs")
async def add_job(data: JobIn, user: dict = Depends(require_role("admin"))):
    jc._capture(_scheduler())
    if data.task not in jc._BASE:
        raise HTTPException(400, "Sarcină necunoscută")
    if not data.label.strip():
        raise HTTPException(400, "Numele e obligatoriu")
    _check(data.category, data.cron)
    if not data.cron.strip():
        raise HTTPException(400, "Programul e obligatoriu")
    job = {"id": jc.new_custom_id(), "task": data.task, "label": data.label.strip()[:120],
           "category": data.category or jc.JOBS.get(data.task, ("other",))[0],
           "cron": data.cron.strip(), "enabled": data.enabled}
    return await _update(lambda s: s["custom_jobs"].append(job))


@admin_router.put("/jobs/{job_id}")
async def edit_job(job_id: str, data: JobEdit, user: dict = Depends(require_role("admin"))):
    await _require_job(job_id)
    _check(data.category, data.cron)

    def mutate(s):
        custom = next((c for c in s["custom_jobs"] if c["id"] == job_id), None)
        if custom:
            if data.label:
                custom["label"] = data.label.strip()[:120]
            if data.category:
                custom["category"] = data.category
            if data.cron:
                custom["cron"] = data.cron.strip()
            if data.enabled is not None:
                custom["enabled"] = data.enabled
            return
        ov = s["overrides"].setdefault(job_id, {})
        default_label = jc.JOBS.get(job_id, ("other", job_id))[1]
        if data.label is not None:
            label = data.label.strip()[:120]
            ov.pop("label", None) if not label or label == default_label else ov.update(label=label)
        if data.category is not None:
            ov.pop("category", None) if data.category == jc.JOBS.get(job_id, ("other",))[0] else ov.update(category=data.category)
        if data.cron is not None:
            ov.pop("cron", None) if not data.cron.strip() else ov.update(cron=data.cron.strip())
        if data.enabled is not None:
            ov["enabled"] = data.enabled
        if not ov:
            s["overrides"].pop(job_id)
    return await _update(mutate)


@admin_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(require_role("admin"))):
    await _require_job(job_id)

    def mutate(s):
        if job_id.startswith(jc.CUSTOM_PREFIX):
            s["custom_jobs"] = [c for c in s["custom_jobs"] if c["id"] != job_id]
        else:  # code job: hidden and unscheduled until restored
            s["overrides"][job_id] = {"deleted": True}
    return await _update(mutate)


@admin_router.post("/jobs/{job_id}/restore")
async def restore_job(job_id: str, user: dict = Depends(require_role("admin"))):
    await _require_job(job_id)
    return await _update(lambda s: s["overrides"].pop(job_id, None))


@admin_router.post("/jobs/{job_id}/toggle")
async def toggle_job(job_id: str, data: ToggleIn, user: dict = Depends(require_role("admin"))):
    return await edit_job(job_id, JobEdit(enabled=data.enabled), user)


@admin_router.post("/jobs/{job_id}/run")
async def run_job(job_id: str, user: dict = Depends(require_role("admin"))):
    settings = await _require_job(job_id)
    custom = next((c for c in settings["custom_jobs"] if c["id"] == job_id), None)
    if not jc.run_now(job_id, custom["task"] if custom else job_id):
        raise HTTPException(409, "Jobul rulează deja")
    return await jc.snapshot(_scheduler())


@admin_router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str, user: dict = Depends(require_role("admin"))):
    await _require_job(job_id)
    if not jc.stop(_scheduler(), job_id):
        raise HTTPException(409, "Jobul nu rulează sau nu poate fi oprit")
    await asyncio.sleep(0.3)  # let the cancellation land before the snapshot
    return await jc.snapshot(_scheduler())
