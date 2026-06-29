from fastapi import APIRouter, Query

from app.schemas import LiveTradesFeedResponse, SmartMoneyFeedResponse
from app.services.live_trades import LiveTradesService
from app.services.smart_money import SmartMoneyService

router = APIRouter(prefix="/alerts", tags=["alerts"])
service = LiveTradesService()
_smart = SmartMoneyService()


@router.get("/live-trades", response_model=LiveTradesFeedResponse)
async def live_trades(
    market: str = Query(default="all", pattern="^(all|stocks|polymarket|kalshi|futures|crypto|forex)$"),
    limit: int = Query(default=40, le=80),
    politician: str | None = Query(default=None),
):
    payload = await service.feed(market=market, limit=limit)
    if politician and market in ("all", "stocks"):
        needle = politician.lower()
        payload["trades"] = [
            t for t in payload.get("trades", [])
            if t.get("actor_type") == "politician" and needle in (t.get("actor_name") or "").lower()
        ]
    return LiveTradesFeedResponse(**payload)


@router.get("/smart-money", response_model=SmartMoneyFeedResponse)
async def smart_money(limit: int = Query(default=50, le=80)):
    return SmartMoneyFeedResponse(**await _smart.feed(limit=limit))
