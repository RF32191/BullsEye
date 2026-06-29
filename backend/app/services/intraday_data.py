"""Intraday bars, VWAP, and opening-range signals via Yahoo/yfinance."""

from __future__ import annotations

import asyncio
import math
import time

import yfinance as yf

_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 90


class IntradayDataService:
    async def snapshot(self, symbol: str, interval: str = "5m") -> dict:
        return await asyncio.to_thread(self._snapshot_sync, symbol.upper(), interval)

    def _snapshot_sync(self, symbol: str, interval: str) -> dict:
        cache_key = f"{symbol}:{interval}"
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

        period = "1d" if interval in ("1m", "5m", "15m") else "5d"
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, auto_adjust=True)
        if hist.empty or len(hist) < 3:
            result = {"symbol": symbol, "available": False, "bars": [], "vwap": None}
            _CACHE[cache_key] = (time.time(), result)
            return result

        rows = []
        cum_vol = 0.0
        cum_pv = 0.0
        for idx, row in hist.iterrows():
            close = float(row["Close"])
            vol = float(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0.0
            cum_vol += vol
            cum_pv += close * vol
            rows.append(
                {
                    "time": idx.isoformat(),
                    "close": round(close, 4),
                    "volume": vol,
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                }
            )

        vwap = round(cum_pv / cum_vol, 4) if cum_vol > 0 else None
        last = rows[-1]["close"]
        first = rows[0]["close"]
        session_change_pct = round(((last - first) / first) * 100, 2) if first else 0.0

        highs = [b["high"] for b in rows]
        lows = [b["low"] for b in rows]
        or_high = max(highs[: min(6, len(highs))])
        or_low = min(lows[: min(6, len(lows))])

        above_vwap = vwap is not None and last > vwap
        or_breakout = last > or_high or last < or_low

        result = {
            "symbol": symbol,
            "available": True,
            "interval": interval,
            "bar_count": len(rows),
            "last_price": last,
            "vwap": vwap,
            "above_vwap": above_vwap,
            "session_change_pct": session_change_pct,
            "opening_range_high": round(or_high, 4),
            "opening_range_low": round(or_low, 4),
            "opening_range_breakout": or_breakout,
            "bars": rows[-30:],
        }
        _CACHE[cache_key] = (time.time(), result)
        return result
