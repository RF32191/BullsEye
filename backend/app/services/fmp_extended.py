"""Extended FMP endpoints for institutional, short interest, grades, earnings."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from app.config import settings


class FMPExtendedClient:
    BASE = "https://financialmodelingprep.com/stable"

    def __init__(self):
        self.api_key = settings.fmp_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key) and not settings.mock_mode

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        if not self.available:
            return []
        query = {"apikey": self.api_key, **(params or {})}
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(f"{self.BASE}{path}", params=query)
            resp.raise_for_status()
            return resp.json()

    async def analyst_grades(self, symbol: str, limit: int = 5) -> list[dict]:
        data = await self._get("/grades", {"symbol": symbol.upper(), "limit": limit})
        return data if isinstance(data, list) else []

    async def shares_float(self, symbol: str) -> dict:
        data = await self._get("/shares-float", {"symbol": symbol.upper()})
        if isinstance(data, list) and data:
            return data[0]
        return {}

    async def institutional_holders(self, symbol: str, limit: int = 8) -> list[dict]:
        data = await self._get(
            "/institutional-ownership/symbol-ownership",
            {"symbol": symbol.upper(), "limit": limit, "includeCurrentQuarter": "true"},
        )
        return data if isinstance(data, list) else []

    async def insider_statistics(self, symbol: str) -> dict:
        data = await self._get("/insider-trading/statistics", {"symbol": symbol.upper()})
        if isinstance(data, list) and data:
            return data[0]
        return {}

    async def earnings_calendar(self, symbol: str) -> list[dict]:
        today = datetime.utcnow().date()
        data = await self._get(
            "/earning-calendar",
            {
                "symbol": symbol.upper(),
                "from": today.isoformat(),
                "to": (today + timedelta(days=90)).isoformat(),
            },
        )
        return data if isinstance(data, list) else []

    async def stock_peers(self, symbol: str) -> list[str]:
        data = await self._get("/stock-peers", {"symbol": symbol.upper()})
        if isinstance(data, list) and data:
            row = data[0]
            peers = row.get("peersList") or row.get("peers") or []
            if isinstance(peers, str):
                return [p.strip() for p in peers.split(",") if p.strip()]
            return peers if isinstance(peers, list) else []
        return []
