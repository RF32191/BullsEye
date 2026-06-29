"""Map upstream API failures to user-friendly prediction errors."""

from __future__ import annotations


def friendly_prediction_error(exc: Exception) -> tuple[int, str]:
    msg = str(exc).lower()
    if "rate limit" in msg or "too many request" in msg or "429" in msg:
        return (
            429,
            "Market data or AI provider rate limit reached. Wait 1–2 minutes and retry, "
            "or use the free Technical bot (no OpenAI call).",
        )
    if "insufficient tokens" in msg:
        return (402, str(exc))
    if "free tier limit" in msg:
        return (402, str(exc))
    if "duplicate prediction" in msg:
        return (409, str(exc))
    if "no yahoo finance" in msg or "no price history" in msg:
        return (
            503,
            "Live market data temporarily unavailable (Yahoo rate limit). Try again in a few minutes.",
        )
    return (500, f"Prediction failed: {exc}")
