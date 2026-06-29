from app.services.market_data import MarketDataService
from app.services.trend_marks import trend_mark
from app.services.technicals import (
    compute_macd,
    compute_rsi,
    ema,
    macd_hist_series,
    rsi_series,
    sma,
    technical_score,
    technical_signal,
)


class MarketAnalysisService:
    def __init__(self):
        self.market = MarketDataService()

    async def get_technicals(self, ticker: str) -> dict:
        symbol = ticker.upper()
        quote = await self.market.quote(symbol)
        history = await self.market.historical_prices(symbol, days=120)
        closes = [float(h.get("close", 0)) for h in history if h.get("close")]
        if not closes:
            price = float(quote.get("price", 0))
            closes = [price] * 30

        rsi = compute_rsi(closes)
        macd, macd_signal, macd_hist = compute_macd(closes)
        ema12 = ema(closes, 12)[-1] if closes else 0.0
        ema26 = ema(closes, 26)[-1] if closes else 0.0
        signal = technical_signal(rsi, macd_hist, ema12, ema26)

        trend_pct = None
        if len(closes) >= 30 and closes[-30]:
            trend_pct = round(((closes[-1] - closes[-30]) / closes[-30]) * 100, 2)

        price = float(quote.get("price", closes[-1]))
        high_52 = quote.get("fiftyTwoWeekHigh")
        low_52 = quote.get("fiftyTwoWeekLow")
        pct_from_high = None
        if high_52 and price:
            pct_from_high = round(((price - float(high_52)) / float(high_52)) * 100, 2)

        sma50 = sma(closes, 50)
        sma200 = sma(closes, 200) if len(closes) >= 200 else sma(closes, min(len(closes), 200))

        marks = trend_mark(
            closes=closes,
            rsi=rsi,
            macd_hist=macd_hist,
            ema12=ema12,
            ema26=ema26,
            trend_pct_30d=trend_pct,
            change_pct=quote.get("changesPercentage"),
        )

        return {
            "symbol": symbol,
            "price": price,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "ema_12": round(ema12, 2),
            "ema_26": round(ema26, 2),
            "signal": signal,
            "trend_pct_30d": trend_pct,
            "technical_score": technical_score(rsi, macd_hist, ema12, ema26),
            **marks,
            "volume": quote.get("volume"),
            "avg_volume": quote.get("avgVolume"),
            "market_cap": quote.get("marketCap"),
            "pe_ratio": quote.get("pe"),
            "forward_pe": quote.get("forwardPE"),
            "beta": quote.get("beta"),
            "fifty_two_week_high": high_52,
            "fifty_two_week_low": low_52,
            "dividend_yield": quote.get("dividendYield"),
            "eps": quote.get("eps"),
            "sma_50": sma50,
            "sma_200": sma200,
            "pct_from_52w_high": pct_from_high,
            "data_source": "Yahoo Finance",
        }

    async def get_trend(self, ticker: str, days: int = 90) -> dict:
        symbol = ticker.upper()
        history = await self.market.historical_prices(symbol, days=days)
        points = [
            {
                "date": h.get("date", ""),
                "close": float(h.get("close", 0)),
                "volume": float(h.get("volume", 0)) if h.get("volume") else None,
            }
            for h in history
            if h.get("close")
        ]
        closes = [p["close"] for p in points]
        rsi_vals = rsi_series(closes)
        macd_hist_vals = macd_hist_series(closes)

        indicators = []
        for idx, point in enumerate(points):
            indicators.append(
                {
                    "date": point["date"],
                    "rsi": rsi_vals[idx] if idx < len(rsi_vals) else None,
                    "macd_hist": macd_hist_vals[idx] if idx < len(macd_hist_vals) else None,
                }
            )

        technicals = await self.get_technicals(symbol)
        events = await self.market.upcoming_events(symbol)
        return {
            "symbol": symbol,
            "points": points,
            "technicals": technicals,
            "indicators": indicators,
            "events": events,
        }

    async def compare_ai_technical(self, ticker: str, ai_direction: str, ai_confidence: float) -> dict:
        technicals = await self.get_technicals(ticker)
        tech_signal = technicals["signal"]
        agreement = ai_direction == tech_signal
        combined = round((technicals["technical_score"] + ai_confidence) / 2, 1)
        if agreement:
            combined = min(100.0, combined + 5)

        summary = (
            f"Technical bot: {tech_signal.upper()} (RSI {technicals['rsi']}, MACD hist {technicals['macd_hist']}). "
            f"AI: {ai_direction.upper()} at {ai_confidence}% confidence. "
            f"{'Signals align' if agreement else 'Signals diverge'} — combined score {combined}/100."
        )

        return {
            "symbol": ticker.upper(),
            "technical_signal": tech_signal,
            "ai_direction": ai_direction,
            "agreement": agreement,
            "technical_score": technicals["technical_score"],
            "ai_confidence": ai_confidence,
            "combined_score": combined,
            "summary": summary,
            "technicals": technicals,
        }
