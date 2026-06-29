"""Trend classification for charts, quotes, and accuracy context."""

from __future__ import annotations

from app.services.technicals import technical_signal, technical_score


def trend_mark(
    *,
    closes: list[float],
    rsi: float,
    macd_hist: float,
    ema12: float,
    ema26: float,
    trend_pct_30d: float | None = None,
    change_pct: float | None = None,
) -> dict:
    signal = technical_signal(rsi, macd_hist, ema12, ema26)
    score = technical_score(rsi, macd_hist, ema12, ema26)

    pct = trend_pct_30d
    if pct is None and change_pct is not None:
        pct = change_pct
    if pct is None and len(closes) >= 5 and closes[0]:
        pct = round(((closes[-1] - closes[0]) / closes[0]) * 100, 2)

    label = "sideways"
    arrow = "→"
    if pct is not None:
        if pct >= 12:
            label = "strong_uptrend"
            arrow = "↑↑"
        elif pct >= 4:
            label = "uptrend"
            arrow = "↑"
        elif pct <= -12:
            label = "strong_downtrend"
            arrow = "↓↓"
        elif pct <= -4:
            label = "downtrend"
            arrow = "↓"

    if label == "sideways" and signal == "bullish":
        label, arrow = "uptrend", "↑"
    elif label == "sideways" and signal == "bearish":
        label, arrow = "downtrend", "↓"

    strength = round(min(100.0, max(0.0, abs(pct or 0) * 4 + (score - 50) * 0.4)), 1)

    return {
        "trend_label": label,
        "trend_arrow": arrow,
        "trend_strength": strength,
        "trend_pct": pct,
        "technical_signal": signal,
        "technical_score": score,
        "trend_summary": _summary(label, pct, signal, score),
    }


def _summary(label: str, pct: float | None, signal: str, score: float) -> str:
    pct_txt = f"{pct:+.1f}%" if pct is not None else "n/a"
    readable = label.replace("_", " ").title()
    return f"{readable} ({pct_txt} · {signal} · score {score:.0f}/100)"
