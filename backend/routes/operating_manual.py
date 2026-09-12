"""PropManage — Operating Manual API

Serves the canonical `/app/docs/OPERATING_MANUAL.md` to the admin UI so the
founder can read the full how-to inside the dashboard, no terminal needed.

Read-only. Markdown is rendered client-side.
"""
import os
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from deps import require_role

logger = logging.getLogger("propmanage.operating_manual")
router = APIRouter(prefix="/api/admin/operating-manual", tags=["operating-manual"])

OWNER_EMAILS = {e.strip().lower() for e in os.environ.get("OWNER_EMAIL", "").split(",") if e.strip()}


def _require_owner(user: dict) -> None:
    """Manualul este vizibil DOAR fondatorului (OWNER_EMAIL), nu tuturor adminilor."""
    if (user.get("email") or "").lower() not in OWNER_EMAILS:
        raise HTTPException(403, "Manualul de operare este disponibil doar fondatorului (owner).")

MANUAL_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "OPERATING_MANUAL.md"
TIER_GUIDE_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "TIER_TESTING_GUIDE.md"


@router.get("")
async def get_manual(user=Depends(require_role("admin"))):
    """Return the full markdown content of the operating manual."""
    _require_owner(user)
    if not MANUAL_PATH.exists():
        raise HTTPException(404, f"Manual file missing at {MANUAL_PATH}")
    try:
        content = MANUAL_PATH.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[operating_manual] read failed: {e}")
        raise HTTPException(500, "Could not read manual file.")
    stat = MANUAL_PATH.stat()
    return {
        "path": str(MANUAL_PATH),
        "content": content,
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
        "line_count": content.count("\n") + 1,
    }


@router.get("/tier-testing")
async def get_tier_testing_guide(user=Depends(require_role("admin"))):
    """Return the Tier Testing Guide markdown (pre-deploy checklist + test scenarios)."""
    _require_owner(user)
    if not TIER_GUIDE_PATH.exists():
        raise HTTPException(404, f"Tier guide missing at {TIER_GUIDE_PATH}")
    try:
        content = TIER_GUIDE_PATH.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[operating_manual] tier guide read failed: {e}")
        raise HTTPException(500, "Could not read tier guide file.")
    stat = TIER_GUIDE_PATH.stat()
    return {
        "path": str(TIER_GUIDE_PATH),
        "content": content,
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
        "line_count": content.count("\n") + 1,
    }
