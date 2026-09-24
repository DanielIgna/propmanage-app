"""Admin endpoints to view, trigger, and download database backups."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from deps import require_role
from backup_service import (
    create_backup, email_backup, list_local_backups,
    create_bson_dump, list_bson_dumps, BSON_DUMP_PREFIX, BSON_DUMP_RETENTION,
    BACKUP_DIR, latest_backup_status,
)

logger = logging.getLogger("propmanage.admin_backups")
router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


@router.get("")
async def list_backups(user: dict = Depends(require_role("admin"))):
    """List local backup files (newest first) + latest run metadata."""
    return {
        "files": list_local_backups(),
        "bson_dumps": list_bson_dumps(),
        "latest_run": await latest_backup_status(),
        "retention_count": 7,
        "bson_retention_count": BSON_DUMP_RETENTION,
    }


@router.post("/dump-bson")
async def trigger_bson_dump(user: dict = Depends(require_role("admin"))):
    """Create a native BSON dump NOW (restorable with ``mongorestore``)."""
    result = await create_bson_dump()
    if not result.get("ok"):
        raise HTTPException(500, f"BSON dump failed: {result.get('error')}")
    logger.info(f"[BSON Dump] manual trigger by {user.get('email')}: {result['filename']}")
    return {"dump": result, "download_url": f"/api/admin/backups/download/{result['filename']}"}


@router.post("/run")
async def trigger_backup(user: dict = Depends(require_role("admin"))):
    """Manually create a backup NOW + email it."""
    result = await create_backup()
    if not result.get("ok"):
        raise HTTPException(500, f"Backup failed: {result.get('error')}")
    email_result = await email_backup(result["path"], result["size_mb"], result)
    logger.info(f"[Backup] manual trigger by {user.get('email')}: {result['filename']}")
    return {"backup": result, "email": email_result}


@router.get("/download/{filename}")
async def download_backup(filename: str, user: dict = Depends(require_role("admin"))):
    """Stream a specific backup file to admin for download."""
    # Sanitize: only allow our naming pattern, no traversal
    valid_prefix = filename.startswith("propmanage-backup-") or filename.startswith(BSON_DUMP_PREFIX)
    if not valid_prefix or not filename.endswith(".tar.gz"):
        raise HTTPException(400, "Invalid backup filename")
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid backup filename")

    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "Backup file not found (may have been pruned)")

    return FileResponse(
        path=str(filepath),
        media_type="application/gzip",
        filename=filename,
    )
