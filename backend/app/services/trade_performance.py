"""Score stock trades (congress, insider) by direction-aware returns."""

from __future__ import annotations


def price_on_date(history: list[dict], date_str: str | None) -> float | None:
    if not date_str or not history:
        return None
    target = date_str[:10]
    for bar in history:
        if bar.get("date", "")[:10] >= target:
            close = bar.get("close")
            if close is not None:
                return float(close)
    if history:
        return float(history[-1].get("close", 0))
    return None


def score_equity_trade(
    *,
    transaction_type: str,
    price_at_entry: float | None,
    current_price: float | None,
    win_threshold_pct: float = 1.0,
) -> dict:
    """Direction-aware outcome for purchases and sales."""
    if not price_at_entry or not current_price or price_at_entry <= 0:
        return {
            "return_pct": None,
            "trade_outcome": None,
            "price_at_entry": price_at_entry,
        }

    return_pct = ((current_price - price_at_entry) / price_at_entry) * 100
    tx = transaction_type.lower()

    if tx in ("purchase", "buy", "p"):
        if return_pct > win_threshold_pct:
            outcome = "win"
        elif return_pct < -win_threshold_pct:
            outcome = "loss"
        else:
            outcome = "neutral"
    elif tx in ("sale", "sell", "s"):
        if return_pct < -win_threshold_pct:
            outcome = "win"
        elif return_pct > win_threshold_pct:
            outcome = "loss"
        else:
            outcome = "neutral"
    else:
        outcome = "neutral" if abs(return_pct) <= win_threshold_pct else ("win" if return_pct > 0 else "loss")

    return {
        "return_pct": round(return_pct, 2),
        "trade_outcome": outcome,
        "price_at_entry": round(price_at_entry, 2),
    }
