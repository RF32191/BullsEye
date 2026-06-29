"""Unified market data — Yahoo Finance primary, FMP optional overlay."""

from app.config import settings
from app.services.fmp import FMPClient
from app.services.yahoo_finance import YahooFinanceClient


class MarketDataService:
    def __init__(self):
        self.yahoo = YahooFinanceClient()
        self.fmp = FMPClient()

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        results = await self.yahoo.search(query, limit=limit)
        if results:
            return results
        if settings.fmp_api_key and not settings.mock_mode:
            fmp_results = await self.fmp.search(query, limit=limit)
            if fmp_results:
                return fmp_results
        # Filtered static fallback when Yahoo is rate-limited
        return self.fmp.filter_mock_search(query, limit=limit)

    async def quote(self, ticker: str) -> dict:
        return await self.yahoo.quote(ticker)

    async def historical_prices(self, ticker: str, days: int = 90) -> list[dict]:
        return await self.yahoo.historical_prices(ticker, days=days)

    async def build_analysis_snapshot(self, ticker: str) -> dict:
        snapshot = await self.yahoo.build_snapshot(ticker)
        if settings.fmp_api_key and not settings.mock_mode:
            try:
                fmp_news = await self.fmp.stock_news(ticker)
                snapshot["recent_news"] = fmp_news[:5]
                snapshot["data_sources"] = ["Yahoo Finance", "Financial Modeling Prep"]
            except Exception:
                snapshot["data_sources"] = ["Yahoo Finance"]
        else:
            snapshot["data_sources"] = ["Yahoo Finance"]
        return snapshot

    async def upcoming_events(self, ticker: str) -> list[dict]:
        import asyncio

        return await asyncio.to_thread(self.yahoo.upcoming_events_sync, ticker.upper())
