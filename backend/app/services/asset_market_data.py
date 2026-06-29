"""Futures, crypto, and forex market data via Yahoo Finance."""

from __future__ import annotations

from app.services.crypto_prices import crypto_quote
from app.services.market_analysis import MarketAnalysisService
from app.services.yahoo_finance import YahooFinanceClient

_yahoo = YahooFinanceClient()
_analysis = MarketAnalysisService()

FUTURES_CATALOG = [
    {"symbol": "ES=F", "name": "E-mini S&P 500", "category": "Index"},
    {"symbol": "NQ=F", "name": "E-mini Nasdaq 100", "category": "Index"},
    {"symbol": "YM=F", "name": "E-mini Dow", "category": "Index"},
    {"symbol": "RTY=F", "name": "E-mini Russell 2000", "category": "Index"},
    {"symbol": "CL=F", "name": "Crude Oil WTI", "category": "Energy"},
    {"symbol": "NG=F", "name": "Natural Gas", "category": "Energy"},
    {"symbol": "GC=F", "name": "Gold", "category": "Metals"},
    {"symbol": "SI=F", "name": "Silver", "category": "Metals"},
    {"symbol": "HG=F", "name": "Copper", "category": "Metals"},
    {"symbol": "ZB=F", "name": "30-Year T-Bond", "category": "Rates"},
    {"symbol": "ZN=F", "name": "10-Year T-Note", "category": "Rates"},
    {"symbol": "6E=F", "name": "Euro FX Futures", "category": "FX Futures"},
    {"symbol": "6J=F", "name": "Japanese Yen Futures", "category": "FX Futures"},
]

CRYPTO_CATALOG = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "category": "Major"},
    {"symbol": "ETH-USD", "name": "Ethereum", "category": "Major"},
    {"symbol": "SOL-USD", "name": "Solana", "category": "Major"},
    {"symbol": "XRP-USD", "name": "XRP", "category": "Major"},
    {"symbol": "ADA-USD", "name": "Cardano", "category": "Alt"},
    {"symbol": "AVAX-USD", "name": "Avalanche", "category": "Alt"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "category": "Alt"},
    {"symbol": "LINK-USD", "name": "Chainlink", "category": "Alt"},
    {"symbol": "DOT-USD", "name": "Polkadot", "category": "Alt"},
    {"symbol": "MATIC-USD", "name": "Polygon", "category": "Alt"},
]

FOREX_CATALOG = [
    {"symbol": "EURUSD=X", "name": "EUR/USD", "category": "Major"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "category": "Major"},
    {"symbol": "USDJPY=X", "name": "USD/JPY", "category": "Major"},
    {"symbol": "AUDUSD=X", "name": "AUD/USD", "category": "Major"},
    {"symbol": "USDCAD=X", "name": "USD/CAD", "category": "Major"},
    {"symbol": "USDCHF=X", "name": "USD/CHF", "category": "Major"},
    {"symbol": "NZDUSD=X", "name": "NZD/USD", "category": "Major"},
    {"symbol": "EURGBP=X", "name": "EUR/GBP", "category": "Cross"},
    {"symbol": "EURJPY=X", "name": "EUR/JPY", "category": "Cross"},
    {"symbol": "GBPJPY=X", "name": "GBP/JPY", "category": "Cross"},
]

_CATALOGS = {
    "futures": FUTURES_CATALOG,
    "crypto": CRYPTO_CATALOG,
    "forex": FOREX_CATALOG,
}

_MOCK_PRICES = {
    "ES=F": 5840.0, "NQ=F": 21200.0, "YM=F": 42800.0, "RTY=F": 2180.0,
    "CL=F": 78.5, "NG=F": 2.85, "GC=F": 2650.0, "SI=F": 31.2, "HG=F": 4.35,
    "ZB=F": 118.5, "ZN=F": 110.2, "6E=F": 1.08, "6J=F": 0.0068,
    "BTC-USD": 98500.0, "ETH-USD": 3450.0, "SOL-USD": 185.0, "XRP-USD": 2.45,
    "ADA-USD": 0.72, "AVAX-USD": 38.0, "DOGE-USD": 0.21, "LINK-USD": 18.5,
    "DOT-USD": 7.2, "MATIC-USD": 0.55,
    "EURUSD=X": 1.085, "GBPUSD=X": 1.275, "USDJPY=X": 149.5, "AUDUSD=X": 0.665,
    "USDCAD=X": 1.365, "USDCHF=X": 0.885, "NZDUSD=X": 0.605, "EURGBP=X": 0.85,
    "EURJPY=X": 162.2, "GBPJPY=X": 190.5,
}

_SEARCH_TYPES = {
    "futures": {"FUTURE"},
    "crypto": {"CRYPTOCURRENCY"},
    "forex": {"CURRENCY"},
}

_CATEGORIES = {
    "futures": ["Index", "Energy", "Metals", "Rates", "FX Futures"],
    "crypto": ["Major", "Alt"],
    "forex": ["Major", "Cross"],
}


class AssetMarketDataService:
    async def trending(self, asset_class: str, limit: int = 16) -> list[dict]:
        catalog = _CATALOGS.get(asset_class, [])[:limit]
        rows = []
        for item in catalog:
            row = await self._quote_row(asset_class, item["symbol"], item["name"], item["category"])
            if row:
                rows.append(row)
        rows.sort(key=lambda r: abs(r.get("change_pct") or 0), reverse=True)
        return rows[:limit]

    async def search(self, asset_class: str, query: str, limit: int = 12) -> list[dict]:
        needle = query.strip()
        if not needle:
            return []

        seen: set[str] = set()
        out: list[dict] = []

        async def add_row(row: dict | None) -> None:
            if not row:
                return
            sym = row.get("symbol", "").upper()
            if sym and sym not in seen:
                seen.add(sym)
                out.append(row)

        catalog = _CATALOGS.get(asset_class, [])
        n_upper = needle.upper()
        n_lower = needle.lower()
        for item in catalog:
            if (
                n_upper in item["symbol"].upper()
                or n_lower in item["name"].lower()
                or n_lower in item["category"].lower()
            ):
                await add_row(await self._quote_row(asset_class, item["symbol"], item["name"], item["category"]))

        typed = await _yahoo.search_typed(needle, limit, _SEARCH_TYPES.get(asset_class, set()))
        for t in typed:
            await add_row(
                await self._quote_row(
                    asset_class,
                    t["symbol"],
                    t.get("name", t["symbol"]),
                    self._category_for_symbol(asset_class, t["symbol"]),
                )
            )

        for guess in _symbol_guesses(asset_class, needle):
            if len(out) >= limit:
                break
            if guess.upper() in seen:
                continue
            await add_row(
                await self._quote_row(
                    asset_class,
                    guess,
                    guess,
                    self._category_for_symbol(asset_class, guess),
                )
            )

        return out[:limit]

    async def categories(self, asset_class: str) -> list[dict]:
        return [{"slug": c.lower().replace(" ", "-"), "label": c} for c in _CATEGORIES.get(asset_class, [])]

    async def category_markets(self, asset_class: str, slug: str, limit: int = 20) -> list[dict]:
        label = slug.replace("-", " ").title()
        catalog = [c for c in _CATALOGS.get(asset_class, []) if c["category"].lower() == label.lower()]
        rows = []
        for item in catalog[:limit]:
            row = await self._quote_row(asset_class, item["symbol"], item["name"], item["category"])
            if row:
                rows.append(row)
        return rows

    async def get_symbol(self, asset_class: str, symbol: str, fresh: bool = False) -> dict | None:
        sym = symbol.upper()
        cat = self._category_for_symbol(asset_class, sym)
        name = sym
        for c in _CATALOGS.get(asset_class, []):
            if c["symbol"] == sym:
                name = c["name"]
                cat = c["category"]
                break
        return await self._quote_row(asset_class, sym, name, cat, fresh=fresh)

    async def movers(self, asset_class: str, limit: int = 12) -> list[dict]:
        return await self.trending(asset_class, limit=limit)

    @staticmethod
    def _category_for_symbol(asset_class: str, symbol: str) -> str:
        for c in _CATALOGS.get(asset_class, []):
            if c["symbol"] == symbol.upper():
                return c["category"]
        return "General"

    async def _quote_row(
        self, asset_class: str, symbol: str, name: str, category: str, fresh: bool = False
    ) -> dict | None:
        meta: dict = {}
        q: dict | None = None

        if asset_class == "crypto":
            q = await crypto_quote(symbol, fresh=fresh)
            if q:
                meta = {
                    "source": q.get("source"),
                    "is_live": q.get("is_live", True),
                    "fetched_at": q.get("fetched_at"),
                    "price_note": q.get("price_note"),
                }

        if not q:
            try:
                q = await _yahoo.quote(symbol, fresh=fresh)
                meta = {
                    "source": q.get("source", "Yahoo Finance"),
                    "is_live": q.get("is_live", True),
                    "fetched_at": q.get("fetched_at"),
                    "price_note": q.get("price_note"),
                }
            except Exception:
                q = None

        if not q or q.get("price") is None:
            return {
                "asset_class": asset_class,
                "symbol": symbol,
                "name": name,
                "category": category,
                "price": None,
                "change_pct": None,
                "volume": None,
                "source": "unavailable",
                "is_live": False,
                "fetched_at": None,
                "price_note": "Live price unavailable — try again or check your symbol.",
            }

        return {
            "asset_class": asset_class,
            "symbol": symbol,
            "name": q.get("name") or name,
            "category": category,
            "price": q.get("price"),
            "change_pct": q.get("changesPercentage"),
            "volume": q.get("volume"),
            "source": meta.get("source"),
            "is_live": meta.get("is_live", True),
            "fetched_at": meta.get("fetched_at"),
            "price_note": meta.get("price_note"),
        }

    async def build_snapshot(self, asset_class: str, symbol: str) -> dict:
        snapshot = await _yahoo.build_snapshot(symbol)
        snapshot["asset_class"] = asset_class
        try:
            snapshot["technicals"] = await _analysis.get_technicals(symbol)
        except Exception:
            snapshot["technicals"] = {}
        return snapshot


def _symbol_guesses(asset_class: str, text: str) -> list[str]:
    t = text.strip().upper()
    if not t:
        return []
    if asset_class == "futures":
        if t.endswith("=F"):
            return [t]
        if len(t) <= 4 and t.isalpha():
            return [f"{t}=F", t]
        return [t]
    if asset_class == "crypto":
        if "-USD" in t or "-USDT" in t:
            return [t]
        if t.endswith("USD") and len(t) > 3:
            return [f"{t[:-3]}-USD", t]
        return [f"{t}-USD", t]
    if asset_class == "forex":
        if t.endswith("=X"):
            return [t]
        clean = t.replace("/", "").replace("_", "")
        if len(clean) == 6 and clean.isalpha():
            return [f"{clean}=X", clean]
        return [f"{t}=X", t]
    return [t]
