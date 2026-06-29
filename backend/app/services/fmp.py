import hashlib
import json
from datetime import datetime, timedelta

import httpx

from app.config import settings


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/stable"

    MOCK_STOCKS = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchangeShortName": "NYSE", "currency": "USD"},
        {"symbol": "V", "name": "Visa Inc.", "exchangeShortName": "NYSE", "currency": "USD"},
        {"symbol": "DIS", "name": "The Walt Disney Company", "exchangeShortName": "NYSE", "currency": "USD"},
        {"symbol": "BA", "name": "The Boeing Company", "exchangeShortName": "NYSE", "currency": "USD"},
        {"symbol": "COIN", "name": "Coinbase Global Inc.", "exchangeShortName": "NASDAQ", "currency": "USD"},
        {"symbol": "PLTR", "name": "Palantir Technologies Inc.", "exchangeShortName": "NYSE", "currency": "USD"},
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.fmp_api_key

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        if settings.mock_mode or not self.api_key:
            return []

        query = {"apikey": self.api_key, **(params or {})}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}{path}", params=query)
            response.raise_for_status()
            return response.json()

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        if settings.mock_mode or not self.api_key:
            needle = query.strip().upper()
            if not needle:
                return self.MOCK_STOCKS[:limit]

            matches = [
                stock
                for stock in self.MOCK_STOCKS
                if needle in stock["symbol"] or needle in stock["name"].upper()
            ]
            if not matches:
                matches = [
                    stock
                    for stock in self.MOCK_STOCKS
                    if stock["symbol"].startswith(needle) or stock["name"].upper().startswith(needle)
                ]
            return matches[:limit]

        data = await self._get("/search-symbol", {"query": query.upper(), "limit": limit})
        return data if isinstance(data, list) else []

    @classmethod
    def filter_mock_search(cls, query: str, limit: int = 8) -> list[dict]:
        needle = query.strip().upper()
        if not needle:
            return cls.MOCK_STOCKS[:limit]
        matches = [
            s for s in cls.MOCK_STOCKS
            if needle in s["symbol"] or needle in s["name"].upper()
        ]
        return (matches or cls.MOCK_STOCKS)[:limit]

    async def quote(self, ticker: str) -> dict:
        if settings.mock_mode or not self.api_key:
            return {
                "symbol": ticker.upper(),
                "name": f"{ticker.upper()} Inc.",
                "price": 185.42,
                "change": 2.15,
                "changesPercentage": 1.17,
                "marketCap": 2_800_000_000_000,
                "pe": 28.5,
            }

        data = await self._get("/quote", {"symbol": ticker.upper()})
        if isinstance(data, list) and data:
            return data[0]
        raise ValueError(f"No quote found for {ticker}")

    async def profile(self, ticker: str) -> dict:
        if settings.mock_mode or not self.api_key:
            return {
                "symbol": ticker.upper(),
                "companyName": f"{ticker.upper()} Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "description": "Leading technology company.",
                "beta": 1.2,
                "mktCap": 2_800_000_000_000,
            }

        data = await self._get("/profile", {"symbol": ticker.upper()})
        if isinstance(data, list) and data:
            return data[0]
        return {}

    async def key_metrics(self, ticker: str) -> dict:
        if settings.mock_mode or not self.api_key:
            return {"peRatio": 28.5, "returnOnEquity": 1.47, "debtToEquity": 1.8}

        data = await self._get("/key-metrics", {"symbol": ticker.upper(), "limit": 1})
        if isinstance(data, list) and data:
            return data[0]
        return {}

    async def analyst_estimates(self, ticker: str) -> list[dict]:
        if settings.mock_mode or not self.api_key:
            return [{"estimatedRevenueAvg": 400_000_000_000, "estimatedEpsAvg": 6.5}]

        data = await self._get("/analyst-estimates", {"symbol": ticker.upper(), "period": "annual", "limit": 1})
        return data if isinstance(data, list) else []

    async def stock_news(self, ticker: str, limit: int = 5) -> list[dict]:
        if settings.mock_mode or not self.api_key:
            return [{"title": "Company reports strong earnings", "publishedDate": datetime.utcnow().isoformat()}]

        data = await self._get("/news/stock", {"symbols": ticker.upper(), "limit": limit})
        return data if isinstance(data, list) else []

    async def historical_prices(self, ticker: str, days: int = 90) -> list[dict]:
        if settings.mock_mode or not self.api_key:
            base = 180.0
            return [
                {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"), "close": base + i * 0.05}
                for i in range(days, 0, -1)
            ]

        data = await self._get(
            "/historical-price-eod/full",
            {"symbol": ticker.upper(), "from": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")},
        )
        if isinstance(data, list):
            return data[:days]
        return []

    async def build_analysis_snapshot(self, ticker: str) -> dict:
        symbol = ticker.upper()
        quote = await self.quote(symbol)
        profile = await self.profile(symbol)
        metrics = await self.key_metrics(symbol)
        estimates = await self.analyst_estimates(symbol)
        news = await self.stock_news(symbol)
        history = await self.historical_prices(symbol, days=60)

        closes = [float(h.get("close", 0)) for h in history if h.get("close")]
        momentum_30d = None
        if len(closes) >= 2 and closes[0]:
            momentum_30d = round(((closes[-1] - closes[0]) / closes[0]) * 100, 2)

        return {
            "source": "Financial Modeling Prep",
            "fetched_at": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "quote": quote,
            "profile": profile,
            "key_metrics": metrics,
            "analyst_estimates": estimates[:1],
            "recent_news": news[:5],
            "momentum_30d_pct": momentum_30d,
            "historical_closes": closes[-30:],
        }


def snapshot_hash(snapshot: dict, ai_payload: dict) -> str:
    payload = json.dumps({"snapshot": snapshot, "ai": ai_payload}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
