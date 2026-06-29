"""SEC Form 4 insider trading disclosures via FMP with mock fallback."""

from __future__ import annotations

import time

import httpx

from app.config import settings
from app.services.fmp import FMPClient

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300

MOCK_INSIDER = [
    {
        "id": "ins-1",
        "symbol": "NVDA",
        "reporting_name": "Jensen Huang",
        "reporting_title": "CEO",
        "transaction_type": "Sale",
        "securities_transacted": 40000,
        "price": 192.50,
        "transaction_date": "2026-06-10",
        "filing_date": "2026-06-12",
        "securities_owned": 85000000,
    },
    {
        "id": "ins-2",
        "symbol": "AAPL",
        "reporting_name": "Tim Cook",
        "reporting_title": "CEO",
        "transaction_type": "Sale",
        "securities_transacted": 75000,
        "price": 210.20,
        "transaction_date": "2026-06-08",
        "filing_date": "2026-06-10",
        "securities_owned": 3200000,
    },
    {
        "id": "ins-3",
        "symbol": "MSFT",
        "reporting_name": "Satya Nadella",
        "reporting_title": "CEO",
        "transaction_type": "Sale",
        "securities_transacted": 25000,
        "price": 445.00,
        "transaction_date": "2026-06-05",
        "filing_date": "2026-06-07",
        "securities_owned": 790000,
    },
]


class InsiderTradesService:
    def __init__(self):
        self.fmp = FMPClient()

    async def list_trades(
        self,
        *,
        ticker: str | None = None,
        limit: int = 30,
        page: int = 1,
    ) -> dict:
        cache_key = f"insider:{ticker}:{limit}:{page}"
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _CACHE_TTL:
            return cached[1]

        is_mock = not settings.fmp_api_key
        rows: list[dict] = []

        if not is_mock:
            try:
                params: dict = {"limit": min(limit * page, 100)}
                if ticker:
                    params["symbol"] = ticker.upper()
                data = await self.fmp._get("/insider-trading/search", params)
                if isinstance(data, list):
                    rows = [self._normalize(r) for r in data[:limit]]
                    is_mock = False
            except Exception:
                is_mock = True

        if is_mock or not rows:
            rows = [self._normalize(r) for r in MOCK_INSIDER]
            if ticker:
                needle = ticker.upper()
                rows = [r for r in rows if r["symbol"] == needle]
            is_mock = True

        start = (page - 1) * limit
        page_rows = rows[start : start + limit]

        result = {
            "trades": page_rows,
            "total": len(rows),
            "page": page,
            "per_page": limit,
            "has_more": start + limit < len(rows),
            "data_source": "Mock Form 4 sample" if is_mock else "SEC Form 4 via FMP",
            "is_mock": is_mock,
            "disclaimer": "Insider filings (Form 4) are public SEC disclosures, not real-time trades.",
        }
        _CACHE[cache_key] = (time.time(), result)
        return result

    @staticmethod
    def _normalize(row: dict) -> dict:
        symbol = str(row.get("symbol") or row.get("ticker") or "").upper()
        tx_date = str(row.get("transactionDate") or row.get("transaction_date") or "")[:10]
        filing = str(row.get("filingDate") or row.get("filing_date") or "")[:10]
        return {
            "id": str(row.get("id") or f"{symbol}-{tx_date}-{row.get('reportingName', 'x')}"),
            "symbol": symbol,
            "reporting_name": str(row.get("reportingName") or row.get("reporting_name") or "Unknown"),
            "reporting_title": row.get("typeOfOwner") or row.get("reporting_title"),
            "transaction_type": str(row.get("transactionType") or row.get("transaction_type") or "Unknown"),
            "securities_transacted": row.get("securitiesTransacted") or row.get("securities_transacted"),
            "price": row.get("price"),
            "transaction_date": tx_date or None,
            "filing_date": filing or None,
            "securities_owned": row.get("securitiesOwned") or row.get("securities_owned"),
        }
