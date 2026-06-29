"""Explain what the AI / technical bot considered during analysis."""


def build_analysis_factors(snapshot: dict, technicals: dict | None, direction: str) -> list[dict]:
    factors: list[dict] = []
    quote = snapshot.get("quote", {})
    profile = snapshot.get("profile", {})
    metrics = snapshot.get("key_metrics", {})

    def add(category: str, label: str, value: str, impact: str):
        factors.append(
            {"category": category, "label": label, "value": value, "impact": impact}
        )

    price = quote.get("price")
    if price is not None:
        add("Price", "Last price", f"${float(price):.2f}", _price_impact(quote))

    change_pct = quote.get("changesPercentage")
    if change_pct is not None:
        add("Momentum", "Daily change", f"{float(change_pct):+.2f}%", _pct_impact(float(change_pct)))

    mom = snapshot.get("momentum_30d_pct")
    if mom is not None:
        add("Momentum", "30-day return", f"{float(mom):+.2f}%", _pct_impact(float(mom)))

    pe = metrics.get("peRatio") or quote.get("pe")
    if pe is not None:
        pe_f = float(pe)
        impact = "neutral" if 10 <= pe_f <= 25 else "bearish" if pe_f > 35 else "bullish"
        add("Fundamental", "P/E ratio", f"{pe_f:.1f}", impact)

    beta = profile.get("beta") or quote.get("beta")
    if beta is not None:
        add("Risk", "Beta", f"{float(beta):.2f}", "neutral")

    high = quote.get("fiftyTwoWeekHigh")
    low = quote.get("fiftyTwoWeekLow")
    if price and high:
        pct = ((float(price) - float(high)) / float(high)) * 100
        add("Technical", "Distance from 52w high", f"{pct:+.1f}%", _pct_impact(pct))

    if technicals:
        rsi = technicals.get("rsi")
        if rsi is not None:
            impact = "bearish" if rsi > 70 else "bullish" if rsi < 30 else "neutral"
            add("Technical", "RSI (14)", f"{float(rsi):.1f}", impact)

        hist = technicals.get("macd_hist")
        if hist is not None:
            add("Technical", "MACD histogram", f"{float(hist):.4f}", "bullish" if hist > 0 else "bearish")

        signal = technicals.get("signal")
        if signal:
            add("Technical", "Bot signal", signal.upper(), signal)

        sma50 = technicals.get("sma_50")
        sma200 = technicals.get("sma_200")
        if price and sma50 and sma200:
            trend = "bullish" if float(sma50) > float(sma200) else "bearish"
            add("Technical", "SMA 50 vs 200", f"${float(sma50):.2f} / ${float(sma200):.2f}", trend)

        vol = technicals.get("volume")
        avg = technicals.get("avg_volume")
        if vol and avg and float(avg) > 0:
            ratio = float(vol) / float(avg)
            add("Volume", "Volume vs avg", f"{ratio:.2f}x", "bullish" if ratio > 1.2 else "neutral")

    sector = profile.get("sector")
    if sector:
        add("Fundamental", "Sector", str(sector), "neutral")

    add("Model", "Final direction", direction.upper(), direction)
    return factors


def _pct_impact(pct: float) -> str:
    if pct > 2:
        return "bullish"
    if pct < -2:
        return "bearish"
    return "neutral"


def _price_impact(quote: dict) -> str:
    pct = quote.get("changesPercentage")
    if pct is None:
        return "neutral"
    return _pct_impact(float(pct))
