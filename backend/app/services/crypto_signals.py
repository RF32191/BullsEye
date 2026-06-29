"""Crypto-specific live signals: momentum, volatility, 24h flow proxy."""

from __future__ import annotations

from app.services.asset_market_data import AssetMarketDataService
from app.services.market_analysis import MarketAnalysisService


class CryptoSignalsService:
    def __init__(self):
        self.assets = AssetMarketDataService()
        self.analysis = MarketAnalysisService()

    async def analyze(self, symbol: str = "BTC-USD") -> dict:
        sym = symbol.upper()
        if not sym.endswith("-USD") and sym in ("BTC", "ETH", "SOL"):
            sym = f"{sym}-USD"

        quote = await self.assets.quote("crypto", sym)
        technicals = await self.analysis.get_technicals(sym)
        movers = await self.assets.movers("crypto", limit=5)

        change = float(quote.get("change_pct") or 0)
        vol_ratio = None
        vol = technicals.get("volume")
        avg = technicals.get("avg_volume")
        if vol and avg:
            try:
                vol_ratio = round(float(vol) / float(avg), 2)
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        funding_proxy = "long_crowded" if change > 3 and (vol_ratio or 0) > 1.2 else (
            "short_crowded" if change < -3 and (vol_ratio or 0) > 1.2 else "balanced"
        )

        action = "push" if change > 2 and technicals.get("signal") == "bullish" else (
            "pull" if change < -2 and technicals.get("signal") == "bearish" else "hold"
        )

        return {
            "symbol": sym,
            "price": quote.get("price"),
            "change_pct_24h": change,
            "volume_ratio": vol_ratio,
            "funding_proxy": funding_proxy,
            "technical_signal": technicals.get("signal"),
            "rsi": technicals.get("rsi"),
            "action": action,
            "top_movers": movers[:5],
            "note": "Funding proxy inferred from 24h move + volume (not exchange funding rate).",
        }
