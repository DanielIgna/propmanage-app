"""ST-001 · Storage routes — utilizare user + config/overview/migrare admin."""
from fastapi import APIRouter, Body, Depends

from deps import get_current_user, require_role
import storage_service as st

user_router = APIRouter(prefix="/api/storage", tags=["storage"])
admin_router = APIRouter(prefix="/api/admin/storage", tags=["storage-admin"])


@user_router.get("/usage")
async def my_usage(user: dict = Depends(get_current_user)):
    await st.ensure_initial_recompute()
    return await st.usage_snapshot(user)


@admin_router.get("/config")
async def get_storage_config(user: dict = Depends(require_role("admin"))):
    return await st.get_config()


@admin_router.put("/config")
async def put_storage_config(body: dict = Body(...), user: dict = Depends(require_role("admin"))):
    return await st.update_config(body, by=user.get("email"))


@admin_router.get("/overview")
async def storage_overview(user: dict = Depends(require_role("admin"))):
    await st.ensure_initial_recompute()
    return await st.admin_overview()


@admin_router.post("/recompute")
async def storage_recompute(user: dict = Depends(require_role("admin"))):
    return await st.recompute_all()


@admin_router.post("/migrate")
async def storage_migrate(user: dict = Depends(require_role("admin"))):
    return await st.start_migration()


@admin_router.get("/migrate/status")
async def storage_migrate_status(user: dict = Depends(require_role("admin"))):
    return await st.migration_status()
