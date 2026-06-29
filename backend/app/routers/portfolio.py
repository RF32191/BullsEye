from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    InsiderTradeResponse,
    InsiderTradesListResponse,
    WatchlistAddRequest,
    WatchlistItemResponse,
)
from app.services.insider_trades import InsiderTradesService
from app.services.market_data import MarketDataService
from app.services.trade_performance import price_on_date, score_equity_trade
from app.services.subscription_limits import require_congress_access
from app.services.watchlist import WatchlistService

router = APIRouter(tags=["insider", "watchlist"])
insider_service = InsiderTradesService()
watchlist_service = WatchlistService()
market = MarketDataService()


async def _enrich_insider(row: dict) -> dict:
    symbol = row.get("symbol")
    if not symbol:
        return row
    try:
        quote = await market.quote(symbol)
        current = float(quote.get("price", 0))
        row["current_price"] = round(current, 2)
        history = await market.historical_prices(symbol, days=180)
        entry_date = row.get("transaction_date") or row.get("filing_date")
        entry = price_on_date(history, entry_date)
        tx_type = row.get("transaction_type", "Sale")
        if "purchase" in tx_type.lower() or "buy" in tx_type.lower():
            tx_type = "purchase"
        else:
            tx_type = "sale"
        scored = score_equity_trade(
            transaction_type=tx_type,
            price_at_entry=entry or row.get("price"),
            current_price=current,
        )
        row["return_since_trade_pct"] = scored["return_pct"]
        row["trade_outcome"] = scored["trade_outcome"]
    except Exception:
        pass
    return row


@router.get("/insider/trades", response_model=InsiderTradesListResponse)
async def list_insider_trades(
    ticker: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    require_congress_access(user)
    payload = await insider_service.list_trades(ticker=ticker, limit=per_page, page=page)
    enriched = [await _enrich_insider(dict(r)) for r in payload["trades"]]
    return InsiderTradesListResponse(
        trades=[InsiderTradeResponse(**row) for row in enriched],
        total=payload["total"],
        page=payload["page"],
        per_page=payload["per_page"],
        has_more=payload["has_more"],
        data_source=payload["data_source"],
        is_mock=payload.get("is_mock", False),
        disclaimer=payload["disclaimer"],
    )


@router.get("/watchlist", response_model=list[WatchlistItemResponse])
def get_watchlist(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return watchlist_service.list_items(db, user.id, category=category)


@router.post("/watchlist", response_model=WatchlistItemResponse)
def add_watchlist_item(
    body: WatchlistAddRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return watchlist_service.add(db, user, body.ticker, body.company_name, category=body.category)


@router.delete("/watchlist/{ticker}")
def remove_watchlist_item(
    ticker: str,
    category: str = Query(default="stocks"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not watchlist_service.remove(db, user.id, ticker, category=category):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"ok": True}
