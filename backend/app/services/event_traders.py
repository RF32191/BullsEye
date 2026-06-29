"""Unified notable trader tracking — replaces mock event_traders."""

from app.services.polymarket_traders import PolymarketTradersService

_poly = PolymarketTradersService()

# Well-known Kalshi / finance personalities (curated; Kalshi has no public leaderboard API)
NOTABLE_KALSHI = [
    {
        "id": "kalshi-econ-1",
        "username": "MacroMarkets",
        "platform": "kalshi",
        "proxy_wallet": None,
        "rank": 1,
        "win_rate_pct": None,
        "total_trades": None,
        "pnl_usd": 0.0,
        "volume_usd": 0.0,
        "specialty": "Economics",
        "verified": False,
        "note": "Follow via Kalshi category filters",
    },
]


class EventTradersService:
    async def list_traders(self, *, platform: str | None = None, category: str | None = None, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if platform in (None, "polymarket", "both"):
            rows.extend(await _poly.list_leaderboard(limit=limit))
        if platform in (None, "kalshi", "both"):
            rows.extend(NOTABLE_KALSHI)
        if category:
            needle = category.lower()
            rows = [r for r in rows if needle in (r.get("specialty") or "").lower()]
        return rows[:limit]

    async def get_trader(self, trader_id: str) -> dict | None:
        if trader_id.startswith("0x"):
            return await _poly.get_trader(trader_id)
        detail = await _poly.get_trader(trader_id)
        if detail:
            return detail
        for t in NOTABLE_KALSHI:
            if t["id"] == trader_id:
                return t
        return None
