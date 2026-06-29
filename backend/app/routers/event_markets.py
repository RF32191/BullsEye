from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    CategoryWatchAddRequest,
    CategoryWatchResponse,
    EventMarketAnalyticsResponse,
    EventMarketCompareResponse,
    EventMarketPredictionRequest,
    EventMarketPredictionResponse,
    EventMarketResponse,
    EventMarketStatsResponse,
    EventTraderDetailResponse,
    EventTraderResponse,
)
from app.services.category_watch import CategoryWatchService
from app.services.event_market_analytics import EventMarketAnalyticsService
from app.services.event_market_data import EventMarketDataService
from app.services.event_market_predictions import EventMarketPredictionService
from app.services.event_traders import EventTradersService
from app.services.subscription_limits import require_ai_quota

router = APIRouter(prefix="/event-markets", tags=["event-markets"])
data = EventMarketDataService()
predictions = EventMarketPredictionService()
traders = EventTradersService()
categories = CategoryWatchService()
event_analytics = EventMarketAnalyticsService()


def _market_response(m: dict) -> EventMarketResponse:
    return EventMarketResponse(**m)


def _pred_response(p) -> EventMarketPredictionResponse:
    return EventMarketPredictionResponse(
        id=p.id,
        platform=p.platform.value,
        external_id=p.external_id,
        question=p.question,
        category=p.category,
        predicted_side=p.predicted_side.value,
        confidence=p.confidence,
        yes_price_at_prediction=p.yes_price_at_prediction,
        target_yes_price=p.target_yes_price,
        horizon_days=p.horizon_days,
        reasoning=p.reasoning,
        bull_case=p.bull_case,
        bear_case=p.bear_case,
        tokens_charged=p.tokens_charged,
        ai_model=p.ai_model,
        is_locked=p.is_locked,
        outcome=p.outcome.value,
        created_at=p.created_at,
    )


@router.get("/trending", response_model=list[EventMarketResponse])
async def trending(
    platform: str | None = Query(default=None, pattern="^(polymarket|kalshi|both)$"),
    limit: int = Query(default=16, le=40),
):
    rows = await data.list_trending(platform=platform, limit=limit)
    return [_market_response(m) for m in rows]


@router.get("/search", response_model=list[EventMarketResponse])
async def search_markets(
    q: str = Query(min_length=1),
    platform: str | None = Query(default=None),
    limit: int = Query(default=12, le=30),
):
    rows = await data.search(q, platform=platform, limit=limit)
    return [_market_response(m) for m in rows]


@router.get("/categories", response_model=list[dict])
async def list_categories():
    return await data.categories()


@router.get("/categories/{slug}/markets", response_model=list[EventMarketResponse])
async def category_markets(
    slug: str,
    platform: str = Query(default="polymarket"),
    limit: int = Query(default=20, le=40),
):
    rows = await data.markets_for_category(slug, platform, limit=limit)
    return [_market_response(m) for m in rows]


@router.get("/traders", response_model=list[EventTraderResponse])
async def list_traders(
    platform: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
):
    rows = await traders.list_traders(platform=platform, category=category, limit=limit)
    return [EventTraderResponse(**r) for r in rows]


@router.get("/traders/{trader_id}", response_model=EventTraderDetailResponse)
async def get_trader(trader_id: str):
    row = await traders.get_trader(trader_id)
    if not row:
        raise HTTPException(status_code=404, detail="Trader not found")
    return EventTraderDetailResponse(**row)


@router.get("/watches", response_model=list[CategoryWatchResponse])
def list_watches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return categories.list_watches(db, user.id)


@router.post("/watches", response_model=CategoryWatchResponse)
def add_watch(
    body: CategoryWatchAddRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return categories.add(db, user.id, body.platform, body.category_slug, body.category_label)


@router.delete("/watches/{watch_id}")
def remove_watch(watch_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not categories.remove(db, user.id, watch_id):
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"ok": True}


@router.get("/analytics", response_model=EventMarketAnalyticsResponse)
async def market_analytics(
    platform: str = Query(pattern="^(polymarket|kalshi)$"),
    external_id: str = Query(min_length=1, max_length=128),
):
    try:
        row = await event_analytics.analyze(platform, external_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EventMarketAnalyticsResponse(**row)


@router.get("/compare", response_model=EventMarketCompareResponse)
async def market_compare(
    platform: str = Query(pattern="^(polymarket|kalshi)$"),
    external_id: str = Query(min_length=1, max_length=128),
    ai_side: str = Query(pattern="^(yes|no)$"),
    ai_confidence: float = Query(ge=0, le=100),
):
    try:
        row = await event_analytics.compare(platform, external_id, ai_side, ai_confidence)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EventMarketCompareResponse(**row)


@router.post("/predict-technical", response_model=EventMarketPredictionResponse)
async def predict_technical_market(
    body: EventMarketPredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        pred = await predictions.predict_technical(
            db,
            user,
            platform=body.platform,
            external_id=body.external_id,
            horizon_days=body.horizon_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return _pred_response(pred)


@router.post("/predict", response_model=EventMarketPredictionResponse)
async def predict_market(
    body: EventMarketPredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        require_ai_quota(db, user)
        pred = await predictions.predict(
            db,
            user,
            platform=body.platform,
            external_id=body.external_id,
            horizon_days=body.horizon_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return _pred_response(pred)


@router.get("/tracker", response_model=list[EventMarketPredictionResponse])
def list_tracker(db: Session = Depends(get_db), user: User = Depends(get_current_user), limit: int = 50):
    return [_pred_response(p) for p in predictions.list_predictions(db, user.id, limit=limit)]


@router.get("/tracker/stats", response_model=EventMarketStatsResponse)
def tracker_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return EventMarketStatsResponse(**predictions.stats(db, user.id))
