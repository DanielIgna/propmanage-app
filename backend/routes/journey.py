"""SH-001 · Journey & FairPrice routes — compunere, zero logică proprie."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from propbenefits.house_journey import compute_journey, fairprice_signals

router = APIRouter(prefix="/api/journey", tags=["journey"])
fairprice_router = APIRouter(prefix="/api/fairprice", tags=["fairprice"])


@router.get("/house")
async def house_journey_endpoint(user: dict = Depends(get_current_user)):
    return await compute_journey(user)


@fairprice_router.get("/signals")
async def fairprice_signals_endpoint(user: dict = Depends(get_current_user)):
    return await fairprice_signals(user)
