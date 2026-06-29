from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    ComparisonResponse,
    StockQuoteResponse,
    StockSearchResult,
    TechnicalAnalysisResponse,
    TrendResponse,
)
from app.services.market_analysis import MarketAnalysisService
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/stocks", tags=["stocks"])
market = MarketDataService()
analysis = MarketAnalysisService()


@router.get("/search", response_model=list[StockSearchResult])
async def search_stocks(q: str = Query(min_length=1), limit: int = Query(default=8, le=20)):
    results = await market.search(q, limit=limit)
    return [
        StockSearchResult(
            symbol=r.get("symbol", ""),
            name=r.get("name", ""),
            exchange=r.get("exchangeShortName"),
            currency=r.get("currency"),
        )
        for r in results
        if r.get("symbol")
    ]


@router.get("/{ticker}/quote", response_model=StockQuoteResponse)
async def get_quote(ticker: str):
    try:
        quote = await market.quote(ticker)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StockQuoteResponse(
        symbol=quote.get("symbol", ticker.upper()),
        name=quote.get("name", ticker.upper()),
        price=float(quote.get("price", 0)),
        change=float(quote.get("change", 0)),
        change_pct=float(quote.get("changesPercentage", 0)),
        market_cap=quote.get("marketCap"),
        pe_ratio=quote.get("pe"),
    )


@router.get("/{ticker}/technicals", response_model=TechnicalAnalysisResponse)
async def get_technicals(ticker: str):
    try:
        return await analysis.get_technicals(ticker)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{ticker}/trend", response_model=TrendResponse)
async def get_trend(ticker: str, days: int = Query(default=90, ge=7, le=365)):
    try:
        return await analysis.get_trend(ticker, days=days)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{ticker}/compare", response_model=ComparisonResponse)
async def compare_signals(
    ticker: str,
    ai_direction: str = Query(pattern="^(bullish|bearish|neutral)$"),
    ai_confidence: float = Query(ge=0, le=100),
):
    try:
        return await analysis.compare_ai_technical(ticker, ai_direction, ai_confidence)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
