"""Per-ticker money flow: congress/insider inflows, volume, and push/hold/pull timing."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.congress_trades import CongressTradesService
from app.services.horizon import format_horizon_label, horizon_move_pct, resolve_horizon
from app.services.insider_trades import InsiderTradesService
from app.services.market_analysis import MarketAnalysisService
from app.services.market_data import MarketDataService


from app.services.market_signals import MarketSignalsService


class MoneyFlowService:
    def __init__(self):
        self.market = MarketDataService()
        self.analysis = MarketAnalysisService()
        self.congress = CongressTradesService()
        self.insider = InsiderTradesService()
        self.signals = MarketSignalsService()

    async def analyze(
        self,
        ticker: str,
        *,
        horizon_days: int | None = None,
        horizon_value: int | None = None,
        horizon_unit: str | None = None,
    ) -> dict:
        symbol = ticker.upper()
        horizon = resolve_horizon(
            horizon_days=horizon_days,
            horizon_value=horizon_value,
            horizon_unit=horizon_unit,
        )
        minutes = horizon["horizon_minutes"]

        quote = await self.market.quote(symbol)
        technicals = await self.analysis.get_technicals(symbol)
        congress_payload = await self.congress.fetch_trades(ticker=symbol, per_page=30)
        insider_payload = await self.insider.list_trades(ticker=symbol, limit=20)
        signal_bundle = await self.signals.bundle(symbol)

        congress_net = self._net_congress_usd(congress_payload.get("trades", []))
        insider_net = self._net_insider_usd(insider_payload.get("trades", []))
        volume = float(technicals.get("volume") or 0)
        avg_volume = float(technicals.get("avg_volume") or 0)
        volume_ratio = round(volume / avg_volume, 2) if avg_volume > 0 else None

        rsi = float(technicals.get("rsi") or 50)
        macd_hist = float(technicals.get("macd_hist") or 0)
        signal = str(technicals.get("signal") or "neutral")
        price = float(technicals.get("price") or quote.get("price") or 0)

        components = self._score_components(
            congress_net=congress_net,
            insider_net=insider_net,
            volume_ratio=volume_ratio,
            rsi=rsi,
            macd_hist=macd_hist,
            signal=signal,
        )
        components.extend(signal_bundle.get("signal_components", []))
        flow_score = round(sum(c["score"] for c in components), 1)
        action = self._action_from_score(flow_score, signal)

        move_pct = horizon_move_pct(minutes)
        if action == "push":
            target = round(price * (1 + move_pct), 2)
            stop = round(price * (1 - move_pct * 1.1), 2)
            timing = f"Consider adding on dips within the next {horizon['horizon_label']}."
        elif action == "pull":
            target = round(price * (1 - move_pct), 2)
            stop = round(price * (1 + move_pct * 1.1), 2)
            timing = f"Consider trimming or exiting within the next {horizon['horizon_label']}."
        else:
            target = round(price * (1 + move_pct * 0.3), 2)
            stop = round(price * (1 - move_pct * 0.8), 2)
            timing = f"No strong flow edge — wait for clearer signal over {horizon['horizon_label']}."

        reasoning = self._build_reasoning(
            action=action,
            congress_net=congress_net,
            insider_net=insider_net,
            volume_ratio=volume_ratio,
            signal=signal,
            horizon_label=horizon["horizon_label"],
        )

        return {
            "ticker": symbol,
            "company_name": quote.get("name") or symbol,
            "price": price,
            "action": action,
            "flow_score": flow_score,
            "congress_net_usd": congress_net,
            "insider_net_usd": insider_net,
            "volume_ratio": volume_ratio,
            "technical_signal": signal,
            "rsi": rsi,
            "macd_hist": macd_hist,
            "horizon_minutes": minutes,
            "horizon_days": horizon["horizon_days"],
            "horizon_label": horizon["horizon_label"],
            "suggested_target": target,
            "suggested_stop": stop,
            "timing_note": timing,
            "reasoning": reasoning,
            "components": components,
            "enhanced_signals": {
                "short_interest_pct": signal_bundle.get("short_interest_pct"),
                "analyst_grade_bias": signal_bundle.get("analyst_grade_bias"),
                "institutional_net_change_pct": signal_bundle.get("institutional_net_change_pct"),
                "insider_cluster_buys": signal_bundle.get("insider_cluster_buys"),
                "sector_relative_strength_pct": signal_bundle.get("sector_relative_strength_pct"),
                "next_earnings_date": signal_bundle.get("next_earnings_date"),
                "intraday": signal_bundle.get("intraday"),
                "data_sources": signal_bundle.get("data_sources"),
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "Flow score blends congress/insider filings (lagged), institutional/short/analyst "
                "signals (FMP when configured), intraday VWAP, volume, and technicals. Not financial advice."
            ),
        }

    @staticmethod
    def _net_congress_usd(trades: list[dict]) -> float:
        net = 0.0
        for t in trades:
            amount = float(t.get("amount_max") or t.get("amount_min") or 0)
            if t.get("transaction_type") == "purchase":
                net += amount
            elif t.get("transaction_type") == "sale":
                net -= amount
        return round(net, 2)

    @staticmethod
    def _net_insider_usd(trades: list[dict]) -> float:
        net = 0.0
        for t in trades:
            qty = float(t.get("securities_transacted") or 0)
            price = float(t.get("price") or 0)
            usd = qty * price
            tx = str(t.get("transaction_type") or "").lower()
            if "purchase" in tx or "buy" in tx or "acquisition" in tx:
                net += usd
            elif "sale" in tx or "sell" in tx or "disposition" in tx:
                net -= usd
        return round(net, 2)

    @classmethod
    def _score_components(
        cls,
        *,
        congress_net: float,
        insider_net: float,
        volume_ratio: float | None,
        rsi: float,
        macd_hist: float,
        signal: str,
    ) -> list[dict]:
        components: list[dict] = []

        if congress_net > 50_000:
            components.append({"label": "Congress inflow", "value": f"+${congress_net:,.0f}", "impact": "positive", "score": 22})
        elif congress_net < -50_000:
            components.append({"label": "Congress outflow", "value": f"${congress_net:,.0f}", "impact": "negative", "score": -18})
        else:
            components.append({"label": "Congress activity", "value": f"${congress_net:,.0f} net", "impact": "neutral", "score": 0})

        if insider_net > 100_000:
            components.append({"label": "Insider buying", "value": f"+${insider_net:,.0f}", "impact": "positive", "score": 20})
        elif insider_net < -100_000:
            components.append({"label": "Insider selling", "value": f"${insider_net:,.0f}", "impact": "negative", "score": -16})
        else:
            components.append({"label": "Insider activity", "value": f"${insider_net:,.0f} net", "impact": "neutral", "score": 0})

        if volume_ratio is not None:
            if volume_ratio >= 1.5:
                components.append({"label": "Volume surge", "value": f"{volume_ratio}x avg", "impact": "positive", "score": 18})
            elif volume_ratio <= 0.6:
                components.append({"label": "Light volume", "value": f"{volume_ratio}x avg", "impact": "negative", "score": -8})
            else:
                components.append({"label": "Volume", "value": f"{volume_ratio}x avg", "impact": "neutral", "score": 4})

        tech_score = 50.0
        if signal == "bullish":
            tech_score += 12
        elif signal == "bearish":
            tech_score -= 12
        if rsi < 35:
            tech_score += 8
        elif rsi > 70:
            tech_score -= 8
        if macd_hist > 0:
            tech_score += 6
        elif macd_hist < 0:
            tech_score -= 6
        tech_score = max(0, min(100, tech_score))
        components.append(
            {
                "label": "Technicals",
                "value": f"{signal} · RSI {rsi:.0f}",
                "impact": "positive" if tech_score >= 55 else "negative" if tech_score <= 45 else "neutral",
                "score": round((tech_score - 50) * 0.5, 1),
            }
        )
        return components

    @staticmethod
    def _action_from_score(flow_score: float, signal: str) -> str:
        if flow_score >= 62:
            return "push"
        if flow_score <= 38:
            return "pull"
        if signal == "bullish" and flow_score >= 52:
            return "push"
        if signal == "bearish" and flow_score <= 48:
            return "pull"
        return "hold"

    @staticmethod
    def _build_reasoning(
        *,
        action: str,
        congress_net: float,
        insider_net: float,
        volume_ratio: float | None,
        signal: str,
        horizon_label: str,
    ) -> str:
        parts = [f"Over {horizon_label}:"]
        if congress_net > 0:
            parts.append(f"politicians net bought ~${congress_net:,.0f}")
        elif congress_net < 0:
            parts.append(f"politicians net sold ~${abs(congress_net):,.0f}")
        if insider_net > 0:
            parts.append(f"insiders net bought ~${insider_net:,.0f}")
        elif insider_net < 0:
            parts.append(f"insiders net sold ~${abs(insider_net):,.0f}")
        if volume_ratio is not None:
            parts.append(f"volume is {volume_ratio}x the average")
        parts.append(f"technicals read {signal}")
        verb = {"push": "lean toward adding exposure", "pull": "lean toward reducing exposure", "hold": "suggest waiting"}.get(action, "monitor")
        return " ".join(parts) + f" — {verb}."
