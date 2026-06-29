"""Unified Polymarket + Kalshi discovery."""

from app.services.kalshi_client import KalshiClient
from app.services.polymarket_client import PolymarketClient


class EventMarketDataService:
    def __init__(self):
        self.poly = PolymarketClient()
        self.kalshi = KalshiClient()

    async def search(self, query: str, platform: str | None = None, limit: int = 12) -> list[dict]:
        rows: list[dict] = []
        if platform in (None, "polymarket", "both"):
            rows.extend(await self.poly.search(query, limit=limit))
        if platform in (None, "kalshi", "both"):
            rows.extend(await self.kalshi.search(query, limit=limit))
        return rows[:limit]

    async def list_trending(self, platform: str | None = None, limit: int = 16) -> list[dict]:
        rows: list[dict] = []
        half = max(limit // 2, 4)
        if platform in (None, "polymarket", "both"):
            rows.extend(await self.poly.list_markets(limit=half))
        if platform in (None, "kalshi", "both"):
            rows.extend(await self.kalshi.list_markets(limit=half))
        return rows[:limit]

    async def categories(self) -> list[dict]:
        return await self.poly.categories()

    async def markets_for_category(self, slug: str, platform: str, limit: int = 20) -> list[dict]:
        if platform == "kalshi":
            return await self.kalshi.list_markets(limit=limit, category=slug.title())
        return await self.poly.list_markets(limit=limit, tag=slug)

    async def get_market(self, platform: str, external_id: str) -> dict | None:
        if platform == "kalshi":
            return await self.kalshi.get_market(external_id)
        return await self.poly.get_market(external_id)
