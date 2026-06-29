"""Event market technical analytics for Polymarket/Kalshi."""

from __future__ import annotations

from app.services.event_market_data import EventMarketDataService

_data = EventMarketDataService()


class EventMarketAnalyticsService:
    async def analyze(self, platform: str, external_id: str) -> dict:
        market = await _data.get_market(platform, external_id)
        if not market:
            raise ValueError("Market not found")

        yes = float(market.get("yes_price") or 0.5)
        volume = float(market.get("volume") or 0)
        liquidity = float(market.get("liquidity") or 0)

        momentum_score = round(abs(yes - 0.5) * 200, 1)
        volume_score = min(100.0, round((volume / 500_000) * 100, 1)) if volume else 0.0
        liquidity_score = min(100.0, round((liquidity / 100_000) * 100, 1)) if liquidity else 0.0
        technical_score = round((momentum_score * 0.5 + volume_score * 0.3 + liquidity_score * 0.2), 1)

        if yes >= 0.58:
            signal = "yes"
        elif yes <= 0.42:
            signal = "no"
        else:
            signal = "neutral"

        summary = (
            f"Yes priced at {yes:.0%}. Volume ${volume:,.0f}, liquidity ${liquidity:,.0f}. "
            f"Technical bot leans {signal.upper()} (score {technical_score}/100)."
        )

        return {
            "platform": platform,
            "external_id": external_id,
            "question": market.get("question", ""),
            "category": market.get("category", "General"),
            "yes_price": yes,
            "no_price": market.get("no_price"),
            "volume": volume,
            "liquidity": liquidity,
            "technical_signal": signal,
            "technical_score": technical_score,
            "momentum_score": momentum_score,
            "volume_score": volume_score,
            "liquidity_score": liquidity_score,
            "summary": summary,
        }

    async def compare(self, platform: str, external_id: str, ai_side: str, ai_confidence: float) -> dict:
        analytics = await self.analyze(platform, external_id)
        tech = analytics["technical_signal"]
        ai_norm = ai_side.lower()
        agreement = tech == ai_norm or (tech == "neutral" and ai_norm in ("yes", "no"))
        combined = round((analytics["technical_score"] + ai_confidence) / 2, 1)
        if agreement:
            combined = min(100.0, combined + 5)

        return {
            **analytics,
            "ai_side": ai_norm,
            "ai_confidence": ai_confidence,
            "agreement": agreement,
            "combined_score": combined,
            "comparison_summary": (
                f"Technical: {tech.upper()} ({analytics['technical_score']}/100). "
                f"AI: {ai_norm.upper()} at {ai_confidence}%. "
                f"{'Aligned' if agreement else 'Divergent'} — combined {combined}/100."
            ),
        }

    def technical_prediction(self, market: dict, analytics: dict) -> dict:
        yes = float(market.get("yes_price") or 0.5)
        side = analytics["technical_signal"]
        if side == "neutral":
            side = "yes" if yes >= 0.5 else "no"
        conf = min(92.0, max(52.0, analytics["technical_score"]))
        target = yes + 0.06 if side == "yes" else yes - 0.06
        target = round(min(0.95, max(0.05, target)), 3)
        return {
            "side": side,
            "confidence": conf,
            "target_yes_price": target,
            "reasoning": analytics["summary"],
            "bull_case": f"Volume ${market.get('volume', 0):,.0f} supports {side.upper()} momentum.",
            "bear_case": "News or liquidity shocks can move odds quickly before resolution.",
        }
