from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    AssetMarketCategoryResponse,
    AssetMarketPredictionRequest,
    AssetMarketPredictionResponse,
    AssetMarketQuoteResponse,
    AssetMarketStatsResponse,
    ComparisonResponse,
    TechnicalAnalysisResponse,
)
from app.services.asset_market_data import AssetMarketDataService
from app.services.asset_market_predictions import AssetMarketPredictionService
from app.services.market_analysis import MarketAnalysisService
from app.services.subscription_limits import require_ai_quota

router = APIRouter(prefix="/asset-markets", tags=["asset-markets"])
data = AssetMarketDataService()
predictions = AssetMarketPredictionService()
analysis = MarketAnalysisService()

_VALID = {"futures", "crypto", "forex"}


def _check_class(asset_class: str) -> str:
    if asset_class not in _VALID:
        raise HTTPException(status_code=400, detail="Invalid asset class")
    return asset_class


@router.get("/{asset_class}/trending", response_model=list[AssetMarketQuoteResponse])
async def trending(asset_class: str, limit: int = Query(default=16, le=40)):
    _check_class(asset_class)
    rows = await data.trending(asset_class, limit=limit)
    return [AssetMarketQuoteResponse(**r) for r in rows]


@router.get("/{asset_class}/search", response_model=list[AssetMarketQuoteResponse])
async def search(asset_class: str, q: str = Query(min_length=1), limit: int = Query(default=12, le=30)):
    _check_class(asset_class)
    rows = await data.search(asset_class, q, limit=limit)
    return [AssetMarketQuoteResponse(**r) for r in rows]


@router.get("/{asset_class}/quote", response_model=AssetMarketQuoteResponse)
async def quote(
    asset_class: str,
    symbol: str = Query(min_length=1, max_length=32),
    fresh: bool = Query(default=False),
):
    _check_class(asset_class)
    row = await data.get_symbol(asset_class, symbol, fresh=fresh)
    if not row:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return AssetMarketQuoteResponse(**row)


@router.get("/{asset_class}/technicals", response_model=TechnicalAnalysisResponse)
async def technicals(asset_class: str, symbol: str = Query(min_length=1, max_length=32)):
    _check_class(asset_class)
    try:
        return await analysis.get_technicals(symbol)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_class}/compare", response_model=ComparisonResponse)
async def compare(
    asset_class: str,
    symbol: str = Query(min_length=1, max_length=32),
    ai_direction: str = Query(pattern="^(bullish|bearish|neutral)$"),
    ai_confidence: float = Query(ge=0, le=100),
):
    _check_class(asset_class)
    try:
        return await predictions.compare(asset_class, symbol, ai_direction, ai_confidence)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_class}/categories", response_model=list[AssetMarketCategoryResponse])
async def categories(asset_class: str):
    _check_class(asset_class)
    rows = await data.categories(asset_class)
    return [AssetMarketCategoryResponse(**r) for r in rows]


@router.get("/{asset_class}/categories/{slug}/markets", response_model=list[AssetMarketQuoteResponse])
async def category_markets(asset_class: str, slug: str, limit: int = Query(default=20, le=40)):
    _check_class(asset_class)
    rows = await data.category_markets(asset_class, slug, limit=limit)
    return [AssetMarketQuoteResponse(**r) for r in rows]


@router.post("/{asset_class}/predict", response_model=AssetMarketPredictionResponse)
async def predict(
    asset_class: str,
    body: AssetMarketPredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _check_class(asset_class)
    try:
        require_ai_quota(db, user)
        pred = await predictions.predict(
            db, user, asset_class=asset_class, symbol=body.symbol, horizon_days=body.horizon_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return _pred_response(pred)


@router.post("/{asset_class}/predict-technical", response_model=AssetMarketPredictionResponse)
async def predict_technical(
    asset_class: str,
    body: AssetMarketPredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _check_class(asset_class)
    try:
        pred = await predictions.predict_technical(
            db, user, asset_class=asset_class, symbol=body.symbol, horizon_days=body.horizon_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return _pred_response(pred)


@router.get("/{asset_class}/tracker", response_model=list[AssetMarketPredictionResponse])
def tracker(
    asset_class: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    _check_class(asset_class)
    return [_pred_response(p) for p in predictions.list_predictions(db, user.id, asset_class=asset_class, limit=limit)]


@router.get("/{asset_class}/tracker/stats", response_model=AssetMarketStatsResponse)
def tracker_stats(asset_class: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_class(asset_class)
    return AssetMarketStatsResponse(**predictions.stats(db, user.id, asset_class=asset_class))


def _pred_response(p) -> AssetMarketPredictionResponse:
    return AssetMarketPredictionResponse(
        id=p.id,
        asset_class=p.asset_class.value,
        symbol=p.symbol,
        name=p.name,
        category=p.category,
        direction=p.direction.value,
        confidence=p.confidence,
        target_price=p.target_price,
        stop_loss=p.stop_loss,
        take_profit=p.take_profit,
        horizon_days=p.horizon_days,
        price_at_prediction=p.price_at_prediction,
        reasoning=p.reasoning,
        bull_case=p.bull_case,
        bear_case=p.bear_case,
        tokens_charged=p.tokens_charged,
        ai_model=p.ai_model,
        is_locked=p.is_locked,
        outcome=p.outcome.value,
        created_at=p.created_at,
    )
