"""Admin endpoints to view, trigger, and download database backups."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from deps import require_role
from backup_service import (
    create_backup, email_backup, list_local_backups,
    BACKUP_DIR, latest_backup_status,
)

logger = logging.getLogger("propmanage.admin_backups")
router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


@router.get("")
async def list_backups(user: dict = Depends(require_role("admin"))):
    """List local backup files (newest first) + latest run metadata."""
    return {
        "files": list_local_backups(),
        "latest_run": await latest_backup_status(),
        "retention_count": 7,
    }


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
    if not filename.startswith("propmanage-backup-") or not filename.endswith(".tar.gz"):
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
