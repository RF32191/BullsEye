"""Cross-market links: events ↔ tickers, macro pulse, conflict tracking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services.congress_trades import CongressTradesService
from app.services.event_market_data import EventMarketDataService
from app.services.market_data import MarketDataService

# Keyword → related equity tickers
_EVENT_TICKER_MAP: dict[str, list[str]] = {
    "fed": ["XLF", "TLT", "SPY", "QQQ", "JPM"],
    "rate": ["TLT", "XLF", "BAC", "GS"],
    "inflation": ["GLD", "TIP", "XLE", "COST"],
    "trump": ["XLE", "LMT", "RTX", "COIN", "DJT"],
    "biden": ["TSLA", "ENPH", "FSLR"],
    "election": ["META", "GOOGL", "COIN"],
    "bitcoin": ["COIN", "MSTR", "IBIT", "MARA"],
    "crypto": ["COIN", "MSTR", "SQ"],
    "oil": ["XLE", "CVX", "XOM", "USO"],
    "war": ["LMT", "RTX", "NOC", "GD"],
    "defense": ["LMT", "RTX", "NOC", "GD", "BA"],
    "ai": ["NVDA", "MSFT", "GOOGL", "AMD", "PLTR"],
    "tariff": ["AAPL", "DE", "CAT", "FXI"],
    "china": ["FXI", "BABA", "PDD", "AAPL"],
    "recession": ["TLT", "GLD", "WMT", "PG"],
    "unemployment": ["XLY", "AMZN", "HD"],
}

_MACRO_SYMBOLS = {
    "sp500": "SPY",
    "nasdaq": "QQQ",
    "10y_yield": "^TNX",
    "dollar": "UUP",
    "gold": "GLD",
    "oil": "USO",
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "eurusd": "EURUSD=X",
}


class CrossMarketService:
    def __init__(self):
        self.markets = EventMarketDataService()
        self.stocks = MarketDataService()
        self.congress = CongressTradesService()

    async def macro_dashboard(self) -> dict:
        async def q(key: str, sym: str) -> tuple[str, dict]:
            try:
                quote = await self.stocks.quote(sym)
                return key, {
                    "symbol": sym,
                    "name": quote.get("name", sym),
                    "price": quote.get("price"),
                    "change_pct": quote.get("changesPercentage") or quote.get("change_pct"),
                }
            except Exception:
                return key, {"symbol": sym, "name": sym, "price": None, "change_pct": None}

        macro_quotes = await asyncio.gather(*[q(k, s) for k, s in _MACRO_SYMBOLS.items()])
        macro = {k: v for k, v in macro_quotes}

        poly = await self.markets.list_trending(platform="polymarket", limit=6)
        kalshi = await self.markets.list_trending(platform="kalshi", limit=6)

        return {
            "macro_quotes": macro,
            "polymarket_hot": poly[:6],
            "kalshi_hot": kalshi[:6],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def ticker_links(self, ticker: str) -> dict:
        symbol = ticker.upper()
        poly = await self.markets.search(symbol, platform="polymarket", limit=8)
        kalshi = await self.markets.search(symbol, platform="kalshi", limit=8)

        related_events = []
        for m in poly + kalshi:
            q = (m.get("question") or "").lower()
            for kw, tickers in _EVENT_TICKER_MAP.items():
                if kw in q and symbol in tickers:
                    related_events.append({**m, "link_reason": f"Event theme '{kw}' maps to {symbol}"})

        reverse = []
        for m in (await self.markets.list_trending(platform=None, limit=20)):
            q = (m.get("question") or "").lower()
            for kw, tickers in _EVENT_TICKER_MAP.items():
                if kw in q and symbol in tickers:
                    reverse.append({"event": m, "keyword": kw, "related_tickers": tickers})

        return {
            "ticker": symbol,
            "linked_markets": (poly + kalshi)[:12],
            "theme_matches": reverse[:8],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def conflicts(self, limit: int = 15) -> dict:
        payload = await self.congress.fetch_trades(per_page=50)
        rows = []
        defense_tickers = set(_EVENT_TICKER_MAP.get("defense", []))
        for t in payload.get("trades", []):
            ticker = (t.get("ticker") or "").upper()
            chamber = t.get("chamber") or ""
            score = float(t.get("conflict_score") or 0)
            if score >= 0.4 or ticker in defense_tickers:
                rows.append(
                    {
                        "member_name": t.get("member_name"),
                        "member_slug": t.get("member_slug"),
                        "ticker": ticker,
                        "transaction_type": t.get("transaction_type"),
                        "amount_label": t.get("amount_label"),
                        "conflict_score": score,
                        "chamber": chamber,
                        "disclosure_date": t.get("disclosure_date"),
                        "note": "Defense/Armed Services overlap" if ticker in defense_tickers else "High conflict score",
                    }
                )
        rows.sort(key=lambda r: r.get("conflict_score", 0), reverse=True)
        return {"conflicts": rows[:limit], "updated_at": datetime.now(timezone.utc).isoformat()}

    def tickers_for_event_text(self, text: str) -> list[str]:
        lower = text.lower()
        found: list[str] = []
        for kw, tickers in _EVENT_TICKER_MAP.items():
            if kw in lower:
                found.extend(tickers)
        return list(dict.fromkeys(found))[:10]
