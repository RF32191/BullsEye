"""Kalshi Trade API v2 client."""

from __future__ import annotations

import time

import httpx

_KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
_CACHE: dict[str, tuple[float, list]] = {}
_TTL = 120


class KalshiClient:
    async def search(self, query: str, limit: int = 12) -> list[dict]:
        cache_key = f"kalshi:search:{query}:{limit}"
        if cached := _get(cache_key):
            return cached

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{_KALSHI}/events",
                    params={"status": "open", "limit": min(limit * 2, 40)},
                )
                resp.raise_for_status()
                events = resp.json().get("events") or []

            needle = query.lower()
            rows = []
            for ev in events:
                title = (ev.get("title") or ev.get("sub_title") or "").lower()
                cat = (ev.get("category") or "").lower()
                if needle in title or needle in cat:
                    rows.append(self._normalize_event(ev))
            if len(rows) < limit:
                markets = await self.list_markets(limit=limit)
                for m in markets:
                    if needle in m["question"].lower():
                        rows.append(m)
            rows = rows[:limit]
        except Exception:
            rows = _MOCK_KALSHI[:limit]

        if not rows:
            rows = _MOCK_KALSHI[:limit]
        _set(cache_key, rows)
        return rows

    async def list_markets(self, *, limit: int = 20, category: str | None = None) -> list[dict]:
        cache_key = f"kalshi:markets:{category}:{limit}"
        if cached := _get(cache_key):
            return cached

        rows: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{_KALSHI}/events",
                    params={"status": "open", "limit": min(limit * 3, 60)},
                )
                resp.raise_for_status()
                events = resp.json().get("events") or []

                for ev in events:
                    if category and (ev.get("category") or "").lower() != category.lower():
                        continue
                    rows.append(self._normalize_event(ev))
                    if len(rows) >= limit:
                        break

                if len(rows) < limit:
                    mresp = await client.get(
                        f"{_KALSHI}/markets",
                        params={"status": "open", "limit": limit * 2},
                    )
                    mresp.raise_for_status()
                    for m in mresp.json().get("markets") or []:
                        if m.get("market_type") != "binary":
                            continue
                        norm = self._normalize_market(m)
                        if category and norm.get("category", "").lower() != category.lower():
                            continue
                        if norm["external_id"] not in {r["external_id"] for r in rows}:
                            rows.append(norm)
                        if len(rows) >= limit:
                            break
        except Exception:
            rows = _MOCK_KALSHI[:limit]

        if not rows:
            rows = _MOCK_KALSHI[:limit]
        _set(cache_key, rows[:limit])
        return rows[:limit]

    async def get_market(self, ticker: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{_KALSHI}/markets/{ticker}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return self._normalize_market(resp.json().get("market") or resp.json())
        except Exception:
            for m in _MOCK_KALSHI:
                if m["external_id"] == ticker:
                    return m
            return None

    @staticmethod
    def _normalize_event(ev: dict) -> dict:
        return {
            "platform": "kalshi",
            "external_id": ev.get("event_ticker") or ev.get("ticker") or "",
            "slug": ev.get("series_ticker"),
            "question": ev.get("title") or ev.get("sub_title") or "Kalshi event",
            "category": ev.get("category") or "General",
            "yes_price": None,
            "no_price": None,
            "volume": 0,
            "liquidity": 0,
            "end_date": ev.get("strike_date"),
            "active": True,
            "image_url": None,
        }

    @staticmethod
    def _normalize_market(m: dict) -> dict:
        yes = m.get("yes_bid_dollars") or m.get("last_price_dollars")
        try:
            yes_f = float(yes) if yes is not None else None
        except (TypeError, ValueError):
            yes_f = None

        title = m.get("title") or m.get("subtitle") or m.get("yes_sub_title") or m.get("ticker")
        return {
            "platform": "kalshi",
            "external_id": m.get("ticker") or "",
            "slug": m.get("event_ticker"),
            "question": title,
            "category": m.get("category") or "General",
            "yes_price": round(yes_f, 4) if yes_f is not None else None,
            "no_price": round(1 - yes_f, 4) if yes_f is not None else None,
            "volume": float(m.get("volume") or 0),
            "liquidity": float(m.get("liquidity_dollars") or 0),
            "end_date": (m.get("close_time") or "")[:10] or None,
            "active": m.get("status") == "open",
            "image_url": None,
        }


_MOCK_KALSHI = [
    {
        "platform": "kalshi",
        "external_id": "MOCK-KALSHI-1",
        "slug": "KXMOCK-1",
        "question": "Will CPI come in below 3% in Q3 2026?",
        "category": "Economics",
        "yes_price": 0.38,
        "no_price": 0.62,
        "volume": 420_000,
        "liquidity": 55_000,
        "end_date": "2026-10-15",
        "active": True,
        "image_url": None,
    },
    {
        "platform": "kalshi",
        "external_id": "MOCK-KALSHI-2",
        "slug": "KXMOCK-2",
        "question": "Will a major AI lab release AGI benchmark above 90% in 2026?",
        "category": "Science",
        "yes_price": 0.21,
        "no_price": 0.79,
        "volume": 310_000,
        "liquidity": 40_000,
        "end_date": "2026-12-31",
        "active": True,
        "image_url": None,
    },
]


def _get(key: str) -> list | None:
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < _TTL:
        return entry[1]
    return None


def _set(key: str, value: list) -> None:
    _CACHE[key] = (time.time(), value)
