"""Congressional stock trade disclosures (STOCK Act PTR filings)."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import httpx

from app.config import settings

_USER_AGENT = "Mozilla/5.0 (compatible; BullseyeAI/1.0)"
_CAPITOL_BASE = "https://www.capitolexposed.com/api/v1"
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 180

MOCK_TRADES: list[dict] = [
    {
        "id": "mock-1",
        "member_name": "Nancy Pelosi",
        "member_slug": "nancy-pelosi",
        "party": "D",
        "chamber": "House",
        "ticker": "NVDA",
        "asset_description": "NVIDIA Corporation",
        "transaction_type": "purchase",
        "transaction_date": "2026-05-12",
        "disclosure_date": "2026-06-10",
        "amount_min": 250000,
        "amount_max": 500000,
        "owner": "spouse",
        "conflict_score": 0.72,
        "source_url": "https://disclosures-clerk.house.gov/",
    },
    {
        "id": "mock-2",
        "member_name": "Tommy Tuberville",
        "member_slug": "tommy-tuberville",
        "party": "R",
        "chamber": "Senate",
        "ticker": "LMT",
        "asset_description": "Lockheed Martin Corporation",
        "transaction_type": "purchase",
        "transaction_date": "2026-05-28",
        "disclosure_date": "2026-06-18",
        "amount_min": 15000,
        "amount_max": 50000,
        "owner": "self",
        "conflict_score": 0.55,
        "source_url": "https://efdsearch.senate.gov/",
    },
    {
        "id": "mock-3",
        "member_name": "Dan Crenshaw",
        "member_slug": "dan-crenshaw",
        "party": "R",
        "chamber": "House",
        "ticker": "MSFT",
        "asset_description": "Microsoft Corporation",
        "transaction_type": "sale",
        "transaction_date": "2026-06-01",
        "disclosure_date": "2026-06-15",
        "amount_min": 1001,
        "amount_max": 15000,
        "owner": "self",
        "conflict_score": 0.12,
        "source_url": "https://disclosures-clerk.house.gov/",
    },
    {
        "id": "mock-4",
        "member_name": "Mark Warner",
        "member_slug": "mark-warner",
        "party": "D",
        "chamber": "Senate",
        "ticker": "AAPL",
        "asset_description": "Apple Inc.",
        "transaction_type": "purchase",
        "transaction_date": "2026-06-05",
        "disclosure_date": "2026-06-20",
        "amount_min": 50000,
        "amount_max": 100000,
        "owner": "joint",
        "conflict_score": 0.18,
        "source_url": "https://efdsearch.senate.gov/",
    },
    {
        "id": "mock-5",
        "member_name": "Josh Gottheimer",
        "member_slug": "josh-gottheimer",
        "party": "D",
        "chamber": "House",
        "ticker": "META",
        "asset_description": "Meta Platforms Inc.",
        "transaction_type": "sale",
        "transaction_date": "2026-06-08",
        "disclosure_date": "2026-06-19",
        "amount_min": 15001,
        "amount_max": 50000,
        "owner": "self",
        "conflict_score": 0.31,
        "source_url": "https://disclosures-clerk.house.gov/",
    },
]


class CongressTradesService:
    async def fetch_trades(
        self,
        *,
        ticker: str | None = None,
        trade_type: str | None = None,
        party: str | None = None,
        politician: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> dict:
        cache_key = f"trades:{ticker}:{trade_type}:{party}:{politician}:{page}:{per_page}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, str | int] = {
            "page": page,
            "per_page": min(per_page, 100),
            "sort": "date",
        }
        if ticker:
            params["ticker"] = ticker.upper()
        if trade_type:
            params["type"] = trade_type
        if party:
            params["party"] = party.upper()

        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        if settings.capitol_exposed_api_key:
            headers["X-API-Key"] = settings.capitol_exposed_api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{_CAPITOL_BASE}/trades", params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            result = self._filter_mock(
                ticker=ticker,
                trade_type=trade_type,
                party=party,
                politician=politician,
                page=page,
                per_page=per_page,
            )
            result["is_mock"] = True
            return result

        rows = payload.get("data") if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            rows = []

        normalized = [self._normalize(row) for row in rows if isinstance(row, dict)]
        if politician:
            needle = politician.strip().lower()
            normalized = [r for r in normalized if needle in r["member_name"].lower()]

        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
        result = {
            "trades": normalized,
            "total": int(meta.get("total", len(normalized))),
            "page": int(meta.get("page", page)),
            "per_page": int(meta.get("per_page", per_page)),
            "has_more": bool(meta.get("has_more", False)),
            "data_source": "CapitolExposed (STOCK Act filings)",
            "is_mock": False,
            "disclaimer": (
                "Congressional trades are disclosed under the STOCK Act and may lag "
                "the actual transaction by up to 45 days."
            ),
        }
        self._cache_set(cache_key, result)
        return result

    @staticmethod
    def _cache_get(key: str) -> dict | None:
        entry = _CACHE.get(key)
        if entry and time.time() - entry[0] < _CACHE_TTL_SECONDS:
            return entry[1]
        return None

    @staticmethod
    def _cache_set(key: str, value: dict) -> dict:
        _CACHE[key] = (time.time(), value)
        return value

    @classmethod
    def _normalize(cls, row: dict) -> dict:
        tx_type = str(row.get("transaction_type", "")).lower()
        if tx_type in ("buy", "p"):
            tx_type = "purchase"
        elif tx_type in ("sell", "s"):
            tx_type = "sale"

        tx_date = cls._short_date(row.get("transaction_date"))
        disclosure = cls._short_date(row.get("disclosure_date"))

        amount_min = cls._to_number(row.get("amount_min"))
        amount_max = cls._to_number(row.get("amount_max"))

        member_slug = row.get("member_slug") or ""
        chamber = "Senate" if "senate" in str(row.get("source_url", "")).lower() else "House"
        if not chamber and member_slug:
            chamber = None

        return {
            "id": str(row.get("id", "")),
            "member_name": str(row.get("member_name", "Unknown")),
            "member_slug": str(member_slug),
            "party": row.get("party"),
            "chamber": row.get("chamber") or chamber,
            "ticker": str(row.get("ticker", "")).upper(),
            "asset_description": str(row.get("asset_description", "")),
            "transaction_type": tx_type or "unknown",
            "transaction_date": tx_date,
            "disclosure_date": disclosure,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "amount_label": cls._amount_label(amount_min, amount_max),
            "owner": row.get("owner"),
            "conflict_score": float(row.get("conflict_score") or 0),
            "source_url": row.get("source_url"),
        }

    @staticmethod
    def _short_date(value: object) -> str | None:
        if not value:
            return None
        text = str(value)
        if "T" in text:
            text = text.split("T", 1)[0]
        return text[:10] if len(text) >= 10 else text

    @staticmethod
    def _to_number(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _amount_label(amount_min: float | None, amount_max: float | None) -> str:
        def fmt(n: float) -> str:
            if n >= 1_000_000:
                return f"${n / 1_000_000:.1f}M"
            if n >= 1_000:
                return f"${n:,.0f}"
            return f"${n:.0f}"

        if amount_min is not None and amount_max is not None:
            return f"{fmt(amount_min)} – {fmt(amount_max)}"
        if amount_min is not None:
            return f"{fmt(amount_min)}+"
        if amount_max is not None:
            return f"Up to {fmt(amount_max)}"
        return "Undisclosed range"

    @classmethod
    def _filter_mock(
        cls,
        *,
        ticker: str | None,
        trade_type: str | None,
        party: str | None,
        politician: str | None,
        page: int,
        per_page: int,
    ) -> dict:
        rows = [cls._normalize(r) for r in MOCK_TRADES]
        if ticker:
            needle = ticker.upper()
            rows = [r for r in rows if r["ticker"] == needle]
        if trade_type:
            rows = [r for r in rows if r["transaction_type"] == trade_type.lower()]
        if party:
            rows = [r for r in rows if (r.get("party") or "").upper() == party.upper()]
        if politician:
            needle = politician.lower()
            rows = [r for r in rows if needle in r["member_name"].lower()]

        start = max(0, (page - 1) * per_page)
        end = start + per_page
        page_rows = rows[start:end]

        return {
            "trades": page_rows,
            "total": len(rows),
            "page": page,
            "per_page": per_page,
            "has_more": end < len(rows),
            "data_source": "Mock STOCK Act sample data",
            "is_mock": True,
            "disclaimer": (
                "Congressional trades are disclosed under the STOCK Act and may lag "
                "the actual transaction by up to 45 days."
            ),
        }
