"""Live market data via Yahoo Finance HTTP API + yfinance fallback."""

from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime, timedelta

import httpx
import yfinance as yf
from yfinance import Search

_USER_AGENT = "Mozilla/5.0 (compatible; BullseyeAI/1.0)"
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300
_STALE_CACHE_TTL_SECONDS = 1800


class YahooFinanceClient:
    async def search(self, query: str, limit: int = 8) -> list[dict]:
        return await asyncio.to_thread(self._search_sync, query, limit)

    async def quote(self, ticker: str) -> dict:
        return await asyncio.to_thread(self._quote_sync, ticker.upper())

    async def historical_prices(self, ticker: str, days: int = 90) -> list[dict]:
        return await asyncio.to_thread(self._history_sync, ticker.upper(), days)

    async def build_snapshot(self, ticker: str) -> dict:
        return await asyncio.to_thread(self._snapshot_sync, ticker.upper())

    @staticmethod
    def _cache_get(key: str) -> dict | None:
        entry = _CACHE.get(key)
        if entry and time.time() - entry[0] < _CACHE_TTL_SECONDS:
            return entry[1]
        return None

    @staticmethod
    def _cache_get_stale(key: str) -> dict | None:
        entry = _CACHE.get(key)
        if entry and time.time() - entry[0] < _STALE_CACHE_TTL_SECONDS:
            return entry[1]
        return None

    @staticmethod
    def _cache_set(key: str, value: dict) -> dict:
        _CACHE[key] = (time.time(), value)
        return value

    @staticmethod
    def _http_get(url: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=20.0, headers={"User-Agent": _USER_AGENT}) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def _search_http(self, query: str, limit: int) -> list[dict]:
        data = self._http_get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            {"q": query, "quotesCount": limit, "newsCount": 0},
        )
        output = []
        for item in data.get("quotes", []):
            symbol = item.get("symbol")
            if not symbol:
                continue
            quote_type = item.get("quoteType", "")
            if quote_type and quote_type not in ("EQUITY", "ETF"):
                continue
            output.append(
                {
                    "symbol": symbol.upper(),
                    "name": item.get("shortname") or item.get("longname") or symbol,
                    "exchangeShortName": item.get("exchange"),
                    "currency": item.get("currency", "USD"),
                }
            )
        return output[:limit]

    def _search_http_typed(self, query: str, limit: int, allowed_types: set[str]) -> list[dict]:
        data = self._http_get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            {"q": query, "quotesCount": limit * 2, "newsCount": 0},
        )
        output = []
        for item in data.get("quotes", []):
            symbol = item.get("symbol")
            if not symbol:
                continue
            quote_type = item.get("quoteType", "")
            if allowed_types and quote_type and quote_type not in allowed_types:
                continue
            output.append(
                {
                    "symbol": symbol.upper(),
                    "name": item.get("shortname") or item.get("longname") or symbol,
                    "exchangeShortName": item.get("exchange"),
                    "currency": item.get("currency", "USD"),
                    "quoteType": quote_type,
                }
            )
        return output[:limit]

    async def search_typed(self, query: str, limit: int, allowed_types: set[str]) -> list[dict]:
        return await asyncio.to_thread(self._search_typed_sync, query, limit, allowed_types)

    def _search_typed_sync(self, query: str, limit: int, allowed_types: set[str]) -> list[dict]:
        needle = query.strip()
        if not needle:
            return []
        cache_key = f"search:{needle.lower()}:{limit}:{','.join(sorted(allowed_types))}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached["rows"]
        try:
            output = self._search_http_typed(needle, limit, allowed_types)
            if output:
                self._cache_set(cache_key, {"rows": output})
                return output
        except Exception:
            pass
        return []

    def _quote_http(self, symbol: str) -> dict | None:
        data = self._http_get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            {"symbols": symbol},
        )
        results = data.get("quoteResponse", {}).get("result", [])
        if not results:
            return None
        item = results[0]
        price = item.get("regularMarketPrice")
        if price is None:
            return None
        prev = item.get("regularMarketPreviousClose") or price
        change = float(price) - float(prev)
        change_pct = item.get("regularMarketChangePercent")
        if change_pct is None and prev:
            change_pct = (change / float(prev)) * 100

        return {
            "symbol": symbol,
            "name": item.get("shortName") or item.get("longName") or symbol,
            "price": round(float(price), 4),
            "change": round(change, 4),
            "changesPercentage": round(float(change_pct or 0), 2),
            "marketCap": item.get("marketCap"),
            "pe": item.get("trailingPE"),
            "forwardPE": item.get("forwardPE"),
            "beta": item.get("beta"),
            "volume": item.get("regularMarketVolume"),
            "avgVolume": item.get("averageDailyVolume3Month"),
            "fiftyTwoWeekHigh": item.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": item.get("fiftyTwoWeekLow"),
            "dividendYield": item.get("trailingAnnualDividendYield"),
            "eps": item.get("epsTrailingTwelveMonths"),
            "exchange": item.get("fullExchangeName") or item.get("exchange"),
            "sector": item.get("sector"),
            "industry": item.get("industry"),
        }

    def _history_http(self, symbol: str, days: int) -> list[dict]:
        range_map = {7: "1mo", 30: "3mo", 90: "6mo", 180: "1y", 365: "2y"}
        range_val = "6mo"
        for threshold, val in sorted(range_map.items()):
            if days <= threshold:
                range_val = val
                break
        else:
            range_val = "2y"

        data = self._http_get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            {"interval": "1d", "range": range_val},
        )
        chart = data.get("chart", {}).get("result", [])
        if not chart:
            raise ValueError(f"No chart data for {symbol}")

        result = chart[0]
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close") or []
        opens = indicators.get("open") or []
        highs = indicators.get("high") or []
        lows = indicators.get("low") or []
        volumes = indicators.get("volume") or []

        rows = []
        for i, ts in enumerate(timestamps):
            close = closes[i] if i < len(closes) else None
            if close is None or (isinstance(close, float) and math.isnan(close)):
                continue
            date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            vol = volumes[i] if i < len(volumes) else None
            if vol is not None and isinstance(vol, float) and math.isnan(vol):
                vol = None
            rows.append(
                {
                    "date": date_str,
                    "close": round(float(close), 4),
                    "volume": float(vol) if vol is not None else None,
                    "open": round(float(opens[i]), 4) if i < len(opens) and opens[i] is not None and not math.isnan(opens[i]) else round(float(close), 4),
                    "high": round(float(highs[i]), 4) if i < len(highs) and highs[i] is not None and not math.isnan(highs[i]) else round(float(close), 4),
                    "low": round(float(lows[i]), 4) if i < len(lows) and lows[i] is not None and not math.isnan(lows[i]) else round(float(close), 4),
                }
            )
        if not rows:
            raise ValueError(f"No valid price history for {symbol}")
        return rows[-days:]

    def _search_sync(self, query: str, limit: int) -> list[dict]:
        needle = query.strip()
        if not needle:
            return []

        cache_key = f"search:{needle.lower()}:{limit}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached["rows"]

        # 1) Yahoo HTTP search (most reliable on servers)
        try:
            output = self._search_http(needle, limit)
            if output:
                self._cache_set(cache_key, {"rows": output})
                return output
        except Exception:
            pass

        # 2) yfinance Search class
        try:
            results = Search(needle, max_results=limit)
            quotes = getattr(results, "quotes", None) or []
            output = []
            for item in quotes:
                symbol = item.get("symbol") or item.get("ticker")
                if not symbol:
                    continue
                output.append(
                    {
                        "symbol": symbol.upper(),
                        "name": item.get("shortname") or item.get("longname") or symbol,
                        "exchangeShortName": item.get("exchange"),
                        "currency": item.get("currency", "USD"),
                    }
                )
            if output:
                self._cache_set(cache_key, {"rows": output[:limit]})
                return output[:limit]
        except Exception:
            pass

        # 3) Direct ticker lookup if query looks like a symbol
        symbol_guess = needle.upper()
        if symbol_guess.isalpha() and 1 <= len(symbol_guess) <= 5:
            try:
                q = self._quote_sync(symbol_guess)
                output = [
                    {
                        "symbol": q["symbol"],
                        "name": q.get("name", q["symbol"]),
                        "exchangeShortName": q.get("exchange"),
                        "currency": "USD",
                    }
                ]
                self._cache_set(cache_key, {"rows": output})
                return output
            except Exception:
                pass

        return []

    def _quote_sync(self, symbol: str) -> dict:
        cache_key = f"quote:{symbol}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        # HTTP quote first
        try:
            result = self._quote_http(symbol)
            if result:
                return self._cache_set(cache_key, result)
        except Exception:
            stale = self._cache_get_stale(cache_key)
            if stale and stale.get("price"):
                out = dict(stale)
                out["is_stale"] = True
                out["price_note"] = "Cached price — Yahoo Finance rate limit. Retry in a few minutes."
                return out

        # yfinance fallback
        ticker = yf.Ticker(symbol)
        info: dict = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        price = None
        try:
            fi = ticker.fast_info
            price = getattr(fi, "last_price", None) or getattr(fi, "lastPrice", None)
        except Exception:
            price = None

        if price is None:
            price = info.get("regularMarketPrice") or info.get("currentPrice")
        if price is None:
            hist = ticker.history(period="5d")
            if not hist.empty:
                close = hist["Close"].iloc[-1]
                if not math.isnan(float(close)):
                    price = float(close)
        if price is None:
            stale = self._cache_get_stale(cache_key)
            if stale and stale.get("price"):
                out = dict(stale)
                out["is_stale"] = True
                out["price_note"] = "Cached price — Yahoo Finance rate limit. Retry in a few minutes."
                return out
            raise ValueError(f"No Yahoo Finance data for {symbol}")

        price = float(price)
        prev = float(info.get("regularMarketPreviousClose") or info.get("previousClose") or price)
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        result = {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName") or symbol,
            "price": round(price, 4),
            "change": round(change, 4),
            "changesPercentage": round(change_pct, 2),
            "marketCap": info.get("marketCap"),
            "pe": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "beta": info.get("beta"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "avgVolume": info.get("averageVolume"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "dividendYield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "exchange": info.get("exchange"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
        return self._cache_set(cache_key, result)

    def _history_sync(self, symbol: str, days: int) -> list[dict]:
        cache_key = f"hist:{symbol}:{days}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached["rows"]

        try:
            rows = self._history_http(symbol, days)
            self._cache_set(cache_key, {"rows": rows})
            return rows
        except Exception:
            stale = self._cache_get_stale(cache_key)
            if stale and stale.get("rows"):
                return stale["rows"]

        ticker = yf.Ticker(symbol)
        period = "1y" if days > 180 else "6mo" if days > 90 else "3mo"
        hist = ticker.history(period=period, auto_adjust=True)
        if hist.empty:
            stale = self._cache_get_stale(cache_key)
            if stale and stale.get("rows"):
                return stale["rows"]
            raise ValueError(f"No price history for {symbol}")

        rows = []
        for idx, row in hist.tail(days).iterrows():
            close = row["Close"]
            if math.isnan(float(close)):
                continue
            rows.append(
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(float(close), 4),
                    "volume": float(row["Volume"]) if not math.isnan(float(row["Volume"])) else None,
                    "open": round(float(row["Open"]), 4) if not math.isnan(float(row["Open"])) else round(float(close), 4),
                    "high": round(float(row["High"]), 4) if not math.isnan(float(row["High"])) else round(float(close), 4),
                    "low": round(float(row["Low"]), 4) if not math.isnan(float(row["Low"])) else round(float(close), 4),
                }
            )
        if not rows:
            stale = self._cache_get_stale(cache_key)
            if stale and stale.get("rows"):
                return stale["rows"]
            raise ValueError(f"No valid price history for {symbol}")
        self._cache_set(cache_key, {"rows": rows})
        return rows

    def _snapshot_sync(self, symbol: str) -> dict:
        quote = self._quote_sync(symbol)
        history = self._history_sync(symbol, 60)
        closes = [h["close"] for h in history if h.get("close")]
        momentum_30d = None
        if len(closes) >= 30 and closes[-30]:
            momentum_30d = round(((closes[-1] - closes[-30]) / closes[-30]) * 100, 2)

        return {
            "source": "Yahoo Finance",
            "fetched_at": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "quote": quote,
            "profile": {
                "symbol": symbol,
                "companyName": quote.get("name"),
                "sector": quote.get("sector"),
                "industry": quote.get("industry"),
                "beta": quote.get("beta"),
                "mktCap": quote.get("marketCap"),
            },
            "key_metrics": {
                "peRatio": quote.get("pe"),
                "forwardPE": quote.get("forwardPE"),
                "dividendYield": quote.get("dividendYield"),
                "eps": quote.get("eps"),
            },
            "calendar": {},
            "momentum_30d_pct": momentum_30d,
            "historical_closes": closes[-30:],
        }

    def upcoming_events_sync(self, symbol: str) -> list[dict]:
        """Return empty when exact earnings date unavailable — avoids misleading placeholders."""
        return []
