"""Unified smart-money feed — congress, insider, whales, movers in one stream."""

from __future__ import annotations

from app.services.live_trades import LiveTradesService

_live = LiveTradesService()


class SmartMoneyService:
    async def feed(self, *, limit: int = 50) -> dict:
        payload = await _live.feed(market="all", limit=limit)
        trades = payload.get("trades", [])
        by_type: dict[str, int] = {}
        for t in trades:
            key = f"{t.get('market_type')}:{t.get('actor_type')}"
            by_type[key] = by_type.get(key, 0) + 1
        return {
            "trades": trades,
            "top_picks": payload.get("top_picks", []),
            "breakdown": by_type,
            "updated_at": payload.get("updated_at"),
            "disclaimer": payload.get("disclaimer"),
        }
