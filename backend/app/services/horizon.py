"""Normalize prediction horizons from minutes, hours, or days."""

from __future__ import annotations


def resolve_horizon(
    *,
    horizon_days: int | None = None,
    horizon_value: int | None = None,
    horizon_unit: str | None = None,
) -> dict:
    """Return horizon_minutes, horizon_days (ledger display), and horizon_label."""
    if horizon_value is not None and horizon_unit:
        unit = horizon_unit.lower()
        if unit == "minutes":
            minutes = max(15, min(int(horizon_value), 10_080))
        elif unit == "hours":
            minutes = max(60, min(int(horizon_value) * 60, 43_200))
        elif unit == "days":
            minutes = max(1_440, min(int(horizon_value) * 1_440, 180 * 1_440))
        else:
            raise ValueError("horizon_unit must be minutes, hours, or days")
    else:
        days = horizon_days if horizon_days is not None else 30
        days = max(1, min(int(days), 180))
        minutes = days * 1_440

    display_days = max(1, round(minutes / 1_440))
    return {
        "horizon_minutes": minutes,
        "horizon_days": display_days,
        "horizon_label": format_horizon_label(minutes),
    }


def format_horizon_label(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 1_440:
        hours = minutes // 60
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    days = round(minutes / 1_440)
    return f"{days} day" if days == 1 else f"{days} days"


def horizon_move_pct(minutes: int) -> float:
    """Scale expected move for short vs long horizons."""
    if minutes <= 60:
        return 0.004 * max(1, minutes / 15)
    if minutes <= 1_440:
        return 0.015 * max(1, minutes / 240)
    if minutes <= 7 * 1_440:
        return 0.04
    return 0.06
