"""Derive trading style and live activity from Polymarket wallet history."""

from __future__ import annotations

import re
from collections import Counter


_CATEGORY_KEYWORDS = {
    "Politics": ["election", "president", "trump", "biden", "congress", "senate", "vote", "politic"],
    "Sports": ["nba", "nfl", "mlb", "soccer", "super bowl", "championship", "game", "match"],
    "Crypto": ["bitcoin", "btc", "eth", "crypto", "solana"],
    "Economics": ["fed", "rate", "cpi", "inflation", "gdp", "recession", "jobs"],
    "Science/Tech": ["ai", "spacex", "apple", "google", "openai"],
}


def _categorize_title(title: str) -> str:
    lower = title.lower()
    for cat, keys in _CATEGORY_KEYWORDS.items():
        if any(k in lower for k in keys):
            return cat
    return "General"


def derive_strategy(*, closed: list[dict], activity: list[dict]) -> dict:
    categories = Counter()
    for pos in closed:
        categories[_categorize_title(pos.get("title", ""))] += 1
    for act in activity:
        if act.get("type") == "TRADE":
            categories[_categorize_title(act.get("title", ""))] += 1

    specialty = categories.most_common(1)[0][0] if categories else "Prediction Markets"

    yes_count = sum(1 for a in activity if str(a.get("side", "")).upper() in ("BUY", "YES"))
    no_count = sum(1 for a in activity if str(a.get("side", "")).upper() in ("SELL", "NO"))
    total_side = yes_count + no_count
    yes_bias_pct = round(yes_count / total_side * 100, 1) if total_side else None

    sizes = [
        float(a.get("usdcSize") or a.get("usdc_size") or a.get("size") or 0)
        for a in activity
        if a.get("type") == "TRADE"
    ]
    avg_bet = round(sum(sizes) / len(sizes), 0) if sizes else None

    wins = sum(1 for p in closed if (p.get("pnl_usd") or p.get("realizedPnl") or 0) > 0)
    win_rate = round(wins / len(closed) * 100, 1) if closed else None

    style = _style_label(specialty, avg_bet, yes_bias_pct, len(closed))

    focus = [cat for cat, _ in categories.most_common(3)]

    return {
        "specialty": specialty,
        "style_label": style,
        "focus_categories": focus,
        "yes_bias_pct": yes_bias_pct,
        "avg_bet_usd": avg_bet,
        "win_rate_pct": win_rate,
        "summary": _strategy_summary(style, specialty, yes_bias_pct, avg_bet, win_rate),
    }


def _style_label(specialty: str, avg_bet: float | None, yes_bias: float | None, closed_count: int) -> str:
    if avg_bet and avg_bet >= 25_000:
        base = "High-conviction whale"
    elif closed_count >= 30:
        base = "Active diversified"
    else:
        base = "Selective trader"
    if yes_bias is not None:
        if yes_bias >= 65:
            base += " · YES lean"
        elif yes_bias <= 35:
            base += " · NO lean"
    return f"{base} · {specialty}"


def _strategy_summary(
    style: str,
    specialty: str,
    yes_bias: float | None,
    avg_bet: float | None,
    win_rate: float | None,
) -> str:
    parts = [style]
    if avg_bet:
        parts.append(f"avg trade ${avg_bet:,.0f}")
    if yes_bias is not None:
        parts.append(f"{yes_bias:.0f}% YES-side")
    if win_rate is not None:
        parts.append(f"{win_rate:.0f}% closed win rate")
    parts.append(f"focus: {specialty}")
    return " · ".join(parts)


def format_live_trades(activity: list[dict], *, limit: int = 8) -> list[dict]:
    trades = []
    for r in activity:
        if not isinstance(r, dict):
            continue
        if str(r.get("type", "")).upper() not in ("TRADE",):
            continue
        size = float(r.get("usdcSize") or r.get("usdc_size") or r.get("size") or 0)
        trades.append(
            {
                "type": "TRADE",
                "title": r.get("title", ""),
                "side": r.get("side"),
                "size_usd": round(size, 2),
                "timestamp": r.get("timestamp"),
                "market_slug": r.get("slug") or r.get("eventSlug"),
                "is_live": True,
            }
        )
        if len(trades) >= limit:
            break
    return trades
