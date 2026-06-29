"""Aggregate enhanced market signals for flow scoring."""

from __future__ import annotations

from app.config import settings
from app.services.fmp_extended import FMPExtendedClient
from app.services.insider_trades import InsiderTradesService
from app.services.intraday_data import IntradayDataService
from app.services.market_analysis import MarketAnalysisService
from app.services.market_data import MarketDataService


class MarketSignalsService:
    def __init__(self):
        self.fmp = FMPExtendedClient()
        self.market = MarketDataService()
        self.analysis = MarketAnalysisService()
        self.insider = InsiderTradesService()
        self.intraday = IntradayDataService()

    async def bundle(self, ticker: str) -> dict:
        symbol = ticker.upper()
        profile = {}
        try:
            quote = await self.market.quote(symbol)
            profile = await self.market.build_analysis_snapshot(symbol)
        except Exception:
            quote = {"price": 0, "name": symbol}
            profile = {}

        technicals = await self.analysis.get_technicals(symbol)
        insider_rows = (await self.insider.list_trades(ticker=symbol, limit=30)).get("trades", [])
        intraday = await self.intraday.snapshot(symbol, interval="5m")

        grades = await self.fmp.analyst_grades(symbol) if self.fmp.available else []
        float_data = await self.fmp.shares_float(symbol) if self.fmp.available else {}
        institutions = await self.fmp.institutional_holders(symbol) if self.fmp.available else []
        insider_stats = await self.fmp.insider_statistics(symbol) if self.fmp.available else {}
        earnings = await self.fmp.earnings_calendar(symbol) if self.fmp.available else []
        peers = await self.fmp.stock_peers(symbol) if self.fmp.available else []

        sector_rs = await self._sector_relative_strength(symbol, technicals, peers)
        cluster_buys = self._insider_cluster_buys(insider_rows)
        grade_bias = self._grade_bias(grades)
        short_pct = float(float_data.get("shortPercentOfFloat") or float_data.get("shortPercent") or 0)
        inst_change = self._institutional_change(institutions)
        next_earnings = earnings[0] if earnings else None

        components = self._score_signals(
            short_pct=short_pct,
            grade_bias=grade_bias,
            inst_change=inst_change,
            cluster_buys=cluster_buys,
            sector_rs=sector_rs,
            intraday=intraday,
            insider_stats=insider_stats,
        )

        return {
            "ticker": symbol,
            "short_interest_pct": round(short_pct, 2) if short_pct else None,
            "analyst_grade_bias": grade_bias,
            "institutional_net_change_pct": inst_change,
            "insider_cluster_buys": cluster_buys,
            "sector_relative_strength_pct": sector_rs,
            "next_earnings_date": (next_earnings or {}).get("date"),
            "intraday": intraday,
            "signal_components": components,
            "data_sources": self._sources(),
        }

    async def _sector_relative_strength(
        self, symbol: str, technicals: dict, peers: list[str]
    ) -> float | None:
        stock_trend = technicals.get("trend_pct_30d")
        if stock_trend is None:
            return None
        peer_changes = []
        for peer in peers[:4]:
            if peer.upper() == symbol:
                continue
            try:
                t = await self.analysis.get_technicals(peer)
                if t.get("trend_pct_30d") is not None:
                    peer_changes.append(float(t["trend_pct_30d"]))
            except Exception:
                continue
        if not peer_changes:
            return None
        avg_peer = sum(peer_changes) / len(peer_changes)
        return round(float(stock_trend) - avg_peer, 2)

    @staticmethod
    def _insider_cluster_buys(trades: list[dict]) -> int:
        buyers = set()
        for t in trades:
            tx = str(t.get("transaction_type") or "").lower()
            if "purchase" in tx or "buy" in tx or "acquisition" in tx:
                buyers.add(t.get("reporting_name") or t.get("id"))
        return len(buyers)

    @staticmethod
    def _grade_bias(grades: list[dict]) -> str:
        if not grades:
            return "neutral"
        upgrades = sum(1 for g in grades if "upgrade" in str(g.get("action", "")).lower())
        downgrades = sum(1 for g in grades if "downgrade" in str(g.get("action", "")).lower())
        if upgrades > downgrades:
            return "bullish"
        if downgrades > upgrades:
            return "bearish"
        return "neutral"

    @staticmethod
    def _institutional_change(holders: list[dict]) -> float | None:
        if not holders:
            return None
        changes = []
        for h in holders:
            ch = h.get("changeInSharesNumberPercentage") or h.get("changeInOwnership")
            if ch is not None:
                try:
                    changes.append(float(ch))
                except (TypeError, ValueError):
                    pass
        if not changes:
            return None
        return round(sum(changes) / len(changes), 2)

    @classmethod
    def _score_signals(
        cls,
        *,
        short_pct: float,
        grade_bias: str,
        inst_change: float | None,
        cluster_buys: int,
        sector_rs: float | None,
        intraday: dict,
        insider_stats: dict,
    ) -> list[dict]:
        components: list[dict] = []

        if short_pct >= 15:
            components.append({"label": "High short interest", "value": f"{short_pct:.1f}% float", "impact": "negative", "score": -12})
        elif short_pct >= 8:
            components.append({"label": "Elevated shorts", "value": f"{short_pct:.1f}%", "impact": "negative", "score": -6})
        elif short_pct > 0:
            components.append({"label": "Short interest", "value": f"{short_pct:.1f}%", "impact": "neutral", "score": 0})

        if grade_bias == "bullish":
            components.append({"label": "Analyst upgrades", "value": "Recent upgrades", "impact": "positive", "score": 10})
        elif grade_bias == "bearish":
            components.append({"label": "Analyst downgrades", "value": "Recent downgrades", "impact": "negative", "score": -10})

        if inst_change is not None:
            if inst_change >= 2:
                components.append({"label": "Institutional buying", "value": f"+{inst_change:.1f}% holders", "impact": "positive", "score": 14})
            elif inst_change <= -2:
                components.append({"label": "Institutional selling", "value": f"{inst_change:.1f}% holders", "impact": "negative", "score": -12})

        if cluster_buys >= 3:
            components.append({"label": "Insider cluster buy", "value": f"{cluster_buys} buyers", "impact": "positive", "score": 16})
        elif cluster_buys >= 2:
            components.append({"label": "Multiple insider buys", "value": f"{cluster_buys} buyers", "impact": "positive", "score": 8})

        buys = insider_stats.get("totalBought") or insider_stats.get("purchases")
        sells = insider_stats.get("totalSold") or insider_stats.get("sales")
        if buys and sells:
            try:
                ratio = float(buys) / max(float(sells), 1)
                if ratio >= 1.5:
                    components.append({"label": "Insider buy/sell ratio", "value": f"{ratio:.1f}x", "impact": "positive", "score": 8})
                elif ratio <= 0.6:
                    components.append({"label": "Insider sell pressure", "value": f"{ratio:.1f}x", "impact": "negative", "score": -8})
            except (TypeError, ValueError):
                pass

        if sector_rs is not None:
            if sector_rs >= 3:
                components.append({"label": "Sector outperformance", "value": f"+{sector_rs:.1f}% vs peers", "impact": "positive", "score": 10})
            elif sector_rs <= -3:
                components.append({"label": "Sector underperformance", "value": f"{sector_rs:.1f}% vs peers", "impact": "negative", "score": -8})

        if intraday.get("available"):
            if intraday.get("above_vwap"):
                components.append({"label": "Above VWAP", "value": f"${intraday.get('vwap')}", "impact": "positive", "score": 8})
            else:
                components.append({"label": "Below VWAP", "value": f"${intraday.get('vwap')}", "impact": "negative", "score": -6})
            if intraday.get("opening_range_breakout"):
                chg = intraday.get("session_change_pct", 0)
                impact = "positive" if chg >= 0 else "negative"
                components.append({"label": "Opening range break", "value": f"{chg:+.1f}% session", "impact": impact, "score": 6 if chg >= 0 else -6})

        return components

    @staticmethod
    def _sources() -> list[str]:
        sources = ["Yahoo Finance"]
        if settings.fmp_api_key and not settings.mock_mode:
            sources.append("Financial Modeling Prep")
        return sources
