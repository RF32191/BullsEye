"""Polymarket Gamma API client."""

from __future__ import annotations

import json
import time

import httpx

from app.config import settings

_GAMMA = "https://gamma-api.polymarket.com"
_CACHE: dict[str, tuple[float, list]] = {}
_TTL = 120


class PolymarketClient:
    async def search(self, query: str, limit: int = 12) -> list[dict]:
        cache_key = f"search:{query}:{limit}"
        if cached := _get(cache_key):
            return cached

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{_GAMMA}/public-search",
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()

        events = data.get("events") or []
        rows = []
        for ev in events[:limit]:
            for m in ev.get("markets") or [ev]:
                rows.append(self._normalize_market(m, ev))
        if not rows and settings.mock_mode:
            rows = _MOCK_POLY[:limit]
        _set(cache_key, rows[:limit])
        return rows[:limit]

    async def list_markets(self, *, limit: int = 20, tag: str | None = None) -> list[dict]:
        cache_key = f"markets:{tag}:{limit}"
        if cached := _get(cache_key):
            return cached

        params: dict = {"limit": limit, "closed": "false", "order": "volume24hr", "ascending": "false"}
        if tag:
            params["tag_slug"] = tag

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{_GAMMA}/markets", params=params)
                resp.raise_for_status()
                data = resp.json()
            rows = [self._normalize_market(m) for m in (data if isinstance(data, list) else [])]
        except Exception:
            rows = _MOCK_POLY[:limit]

        if not rows:
            rows = _MOCK_POLY[:limit]
        _set(cache_key, rows)
        return rows

    async def categories(self, limit: int = 24) -> list[dict]:
        cache_key = f"tags:{limit}"
        if cached := _get(cache_key):
            return cached

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{_GAMMA}/tags", params={"limit": limit})
                resp.raise_for_status()
                tags = resp.json()
            rows = [
                {
                    "slug": t.get("slug", ""),
                    "label": t.get("label", t.get("slug", "")),
                    "platform": "polymarket",
                }
                for t in (tags if isinstance(tags, list) else [])
                if t.get("slug")
            ]
        except Exception:
            rows = []

        kalshi_cats = [
            {"slug": "politics", "label": "Politics", "platform": "kalshi"},
            {"slug": "economics", "label": "Economics", "platform": "kalshi"},
            {"slug": "world", "label": "World", "platform": "kalshi"},
            {"slug": "sports", "label": "Sports", "platform": "kalshi"},
            {"slug": "science", "label": "Science", "platform": "kalshi"},
            {"slug": "crypto", "label": "Crypto", "platform": "kalshi"},
        ]
        merged = rows + [c for c in kalshi_cats if c["slug"] not in {r["slug"] for r in rows}]
        _set(cache_key, merged[:limit])
        return merged[:limit]

    async def get_market(self, market_id: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{_GAMMA}/markets/{market_id}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return self._normalize_market(resp.json())
        except Exception:
            for m in _MOCK_POLY:
                if m["external_id"] == market_id:
                    return m
            return None

    @staticmethod
    def _normalize_market(raw: dict, event: dict | None = None) -> dict:
        prices = raw.get("outcomePrices") or "[]"
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except json.JSONDecodeError:
                prices = []

        yes_price = float(prices[0]) if prices else None
        volume = raw.get("volumeNum") or raw.get("volume") or 0
        question = raw.get("question") or (event or {}).get("title") or "Unknown market"

        return {
            "platform": "polymarket",
            "external_id": str(raw.get("id") or raw.get("conditionId") or ""),
            "slug": raw.get("slug"),
            "question": question,
            "category": (event or {}).get("category") or raw.get("category") or "General",
            "yes_price": round(float(yes_price), 4) if yes_price is not None else None,
            "no_price": round(1 - float(yes_price), 4) if yes_price is not None else None,
            "volume": float(volume) if volume else 0,
            "liquidity": float(raw.get("liquidityNum") or raw.get("liquidity") or 0),
            "end_date": raw.get("endDateIso") or raw.get("endDate"),
            "active": bool(raw.get("active", True) and not raw.get("closed", False)),
            "image_url": raw.get("image") or raw.get("icon"),
        }


_MOCK_POLY = [
    {
        "platform": "polymarket",
        "external_id": "mock-poly-1",
        "slug": "mock-election",
        "question": "Will the incumbent win the 2026 midterm governor race?",
        "category": "Politics",
        "yes_price": 0.62,
        "no_price": 0.38,
        "volume": 1_250_000,
        "liquidity": 85_000,
        "end_date": "2026-11-03",
        "active": True,
        "image_url": None,
    },
    {
        "platform": "polymarket",
        "external_id": "mock-poly-2",
        "slug": "mock-fed",
        "question": "Fed cuts rates before September 2026?",
        "category": "Economics",
        "yes_price": 0.44,
        "no_price": 0.56,
        "volume": 890_000,
        "liquidity": 120_000,
        "end_date": "2026-09-01",
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
