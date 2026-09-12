"""PropManage router: root."""
import logging
from fastapi import APIRouter


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["root"])

# ============= ROOT =============
@router.get("/")
async def root():
    return {"message": "PropManage API", "version": "1.0"}
