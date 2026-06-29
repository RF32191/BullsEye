"""Resolve live prices by asset category for paper trading."""

from __future__ import annotations

from app.services.asset_market_data import AssetMarketDataService
from app.services.event_market_data import EventMarketDataService
from app.services.market_data import MarketDataService

_market = MarketDataService()
_assets = AssetMarketDataService()
_events = EventMarketDataService()

VALID_CATEGORIES = {"stocks", "crypto", "futures", "forex", "polymarket", "kalshi"}


async def resolve_price(
    category: str,
    symbol: str,
    *,
    fresh: bool = False,
    platform: str | None = None,
) -> dict:
    cat = (category or "stocks").lower()
    sym = symbol.upper().strip()

    if cat == "stocks":
        q = await _market.quote(sym, fresh=fresh)
        price = float(q.get("price", 0))
        return {
            "price": price,
            "name": q.get("name", sym),
            "source": q.get("source", "Yahoo Finance"),
            "change_pct": q.get("changesPercentage"),
        }

    if cat in ("crypto", "futures", "forex"):
        row = await _assets.get_symbol(cat, sym, fresh=fresh)
        if not row or row.get("price") is None:
            raise ValueError(f"No live price for {sym}")
        return {
            "price": float(row["price"]),
            "name": row.get("name", sym),
            "source": row.get("source", "Market data"),
            "change_pct": row.get("change_pct"),
        }

    if cat in ("polymarket", "kalshi"):
        plat = platform or cat
        markets = await _events.search(query=sym, platform=plat, limit=5)
        match = next((m for m in markets if m.get("external_id") == sym or m.get("slug") == sym), None)
        if not match and markets:
            match = markets[0]
        if not match:
            raise ValueError(f"Event market not found: {sym}")
        yes = match.get("yes_price")
        if yes is None:
            yes = match.get("yesPrice")
        if yes is None:
            raise ValueError("No yes price on market")
        return {
            "price": float(yes),
            "name": match.get("question", sym)[:256],
            "source": plat.title(),
            "change_pct": None,
            "external_id": match.get("external_id"),
        }

    raise ValueError(f"Unknown category: {cat}")
