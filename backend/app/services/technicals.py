"""Technical indicator calculations from historical closes."""

from __future__ import annotations


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    result = [values[0]]
    for price in values[1:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 4)


def compute_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    series: list[float | None] = []
    for i in range(len(closes)):
        if i < period:
            series.append(None)
        else:
            series.append(compute_rsi(closes[: i + 1], period))
    return series


def macd_hist_series(closes: list[float]) -> list[float | None]:
    if len(closes) < 26:
        return [None] * len(closes)

    result: list[float | None] = []
    for i in range(len(closes)):
        if i < 25:
            result.append(None)
        else:
            _, _, hist = compute_macd(closes[: i + 1])
            result.append(hist)
    return result


def compute_macd(closes: list[float]) -> tuple[float, float, float]:
    if len(closes) < 26:
        last = closes[-1] if closes else 0.0
        return last, last, 0.0

    ema12_series = ema(closes, 12)
    ema26_series = ema(closes, 26)
    macd_series = [a - b for a, b in zip(ema12_series, ema26_series)]
    signal_series = ema(macd_series, 9)
    macd = macd_series[-1]
    signal = signal_series[-1]
    hist = macd - signal
    return round(macd, 4), round(signal, 4), round(hist, 4)


def technical_signal(rsi: float, macd_hist: float, ema12: float, ema26: float) -> str:
    bullish_points = 0
    bearish_points = 0

    if rsi >= 55:
        bullish_points += 1
    elif rsi <= 45:
        bearish_points += 1

    if macd_hist > 0:
        bullish_points += 1
    elif macd_hist < 0:
        bearish_points += 1

    if ema12 > ema26:
        bullish_points += 1
    elif ema12 < ema26:
        bearish_points += 1

    if bullish_points > bearish_points:
        return "bullish"
    if bearish_points > bullish_points:
        return "bearish"
    return "neutral"


def technical_score(rsi: float, macd_hist: float, ema12: float, ema26: float) -> float:
    score = 50.0
    if rsi > 70:
        score -= 10
    elif rsi < 30:
        score += 10
    elif rsi > 55:
        score += 5
    elif rsi < 45:
        score -= 5

    if macd_hist > 0:
        score += 8
    else:
        score -= 8

    if ema12 > ema26:
        score += 7
    else:
        score -= 7

    return max(0.0, min(100.0, round(score, 1)))
