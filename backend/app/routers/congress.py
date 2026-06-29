from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Prediction, User
from app.routers.auth import get_current_user
from app.schemas import (
    CongressPoliticianProfileResponse,
    CongressPoliticianSummaryResponse,
    CongressTradeResponse,
    CongressTradesListResponse,
)
from app.services.congress_analytics import CongressAnalyticsService
from app.services.congress_trades import CongressTradesService
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/congress", tags=["congress"])
service = CongressTradesService()
analytics = CongressAnalyticsService()
market = MarketDataService()


async def _enrich_trade(row: dict, db: Session, user_id) -> dict:
    row = await analytics.enrich_trade(row)
    ticker = row.get("ticker")
    if ticker:
        latest = (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id, Prediction.ticker == ticker.upper(), Prediction.is_locked.is_(True))
            .order_by(Prediction.created_at.desc())
            .first()
        )
        if latest:
            row["latest_prediction_direction"] = latest.direction.value
            row["latest_prediction_confidence"] = latest.confidence
    return row


@router.get("/politicians/top", response_model=list[CongressPoliticianSummaryResponse])
async def top_politicians(limit: int = Query(default=15, le=30)):
    rows = await analytics.top_politicians(limit=limit)
    return [CongressPoliticianSummaryResponse(**r) for r in rows]


@router.get("/politicians/{slug}", response_model=CongressPoliticianProfileResponse)
async def politician_profile(slug: str):
    profile = await analytics.politician_profile(slug)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Politician not found")
    return CongressPoliticianProfileResponse(
        member_slug=profile["member_slug"],
        member_name=profile["member_name"],
        party=profile.get("party"),
        chamber=profile.get("chamber"),
        total_trades=profile["total_trades"],
        win_rate_pct=profile.get("win_rate_pct"),
        wins=profile.get("wins", 0),
        losses=profile.get("losses", 0),
        avg_return_since_trade_pct=profile.get("avg_return_since_trade_pct"),
        trades=[CongressTradeResponse(**t) for t in profile.get("trades", [])],
        disclaimer=profile.get("disclaimer", ""),
    )


@router.get("/trades", response_model=CongressTradesListResponse)
async def list_congress_trades(
    ticker: str | None = Query(default=None, min_length=1, max_length=16),
    type: str | None = Query(default=None, pattern="^(purchase|sale|exchange)$"),
    party: str | None = Query(default=None, pattern="^(D|R|I)$"),
    politician: str | None = Query(default=None, min_length=1, max_length=64),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = await service.fetch_trades(
        ticker=ticker,
        trade_type=type,
        party=party,
        politician=politician,
        page=page,
        per_page=per_page,
    )
    enriched = []
    for row in payload["trades"]:
        enriched.append(await _enrich_trade(dict(row), db, user.id))

    return CongressTradesListResponse(
        trades=[CongressTradeResponse(**row) for row in enriched],
        total=payload["total"],
        page=payload["page"],
        per_page=payload["per_page"],
        has_more=payload["has_more"],
        data_source=payload["data_source"],
        is_mock=payload.get("is_mock", False),
        disclaimer=payload["disclaimer"],
    )
