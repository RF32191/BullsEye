from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    ConflictsResponse,
    CrossMarketLinksResponse,
    CryptoSignalsResponse,
    MacroDashboardResponse,
    MarketSignalsResponse,
    UserWatchesResponse,
    UserWatchesUpdateRequest,
)
from app.services.cross_market import CrossMarketService
from app.services.crypto_signals import CryptoSignalsService
from app.services.market_signals import MarketSignalsService
from app.services.user_watches import UserWatchesService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/intelligence", tags=["intelligence"])
_cross = CrossMarketService()
_signals = MarketSignalsService()
_crypto = CryptoSignalsService()
_watches = UserWatchesService()


@router.get("/macro", response_model=MacroDashboardResponse)
async def macro_dashboard(_: User = Depends(get_current_user)):
    return MacroDashboardResponse(**await _cross.macro_dashboard())


@router.get("/cross-market/{ticker}", response_model=CrossMarketLinksResponse)
async def cross_market_links(ticker: str, _: User = Depends(get_current_user)):
    return CrossMarketLinksResponse(**await _cross.ticker_links(ticker))


@router.get("/conflicts", response_model=ConflictsResponse)
async def conflict_tracker(_: User = Depends(get_current_user), limit: int = 15):
    return ConflictsResponse(**await _cross.conflicts(limit=limit))


@router.get("/signals/{ticker}", response_model=MarketSignalsResponse)
async def market_signals(ticker: str, _: User = Depends(get_current_user)):
    try:
        return MarketSignalsResponse(**await _signals.bundle(ticker))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/crypto/{symbol}", response_model=CryptoSignalsResponse)
async def crypto_signals(symbol: str = "BTC-USD", _: User = Depends(get_current_user)):
    return CryptoSignalsResponse(**await _crypto.analyze(symbol))


@router.get("/watches", response_model=UserWatchesResponse)
def get_watches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.refresh(user)
    return UserWatchesResponse(**_watches.get(user))


@router.put("/watches", response_model=UserWatchesResponse)
def update_watches(
    body: UserWatchesUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = body.model_dump(exclude_none=True)
    return UserWatchesResponse(**_watches.update(db, user, payload))
