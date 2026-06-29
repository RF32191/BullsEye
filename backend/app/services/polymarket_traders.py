"""Live Polymarket whale leaderboard + trade history from Data API."""

from __future__ import annotations

import asyncio
import time

import httpx

from app.services.trader_strategy import derive_strategy, format_live_trades

_DATA_API = "https://data-api.polymarket.com"
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 300


class PolymarketTradersService:
    async def list_leaderboard(self, *, limit: int = 25) -> list[dict]:
        cache_key = f"lb:{limit}"
        if cached := _get(cache_key):
            return cached

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(f"{_DATA_API}/v1/leaderboard", params={"limit": min(limit, 50)})
                resp.raise_for_status()
                rows = resp.json()
            if not isinstance(rows, list):
                rows = []

            enriched = []
            top_wallets = [r.get("proxyWallet") for r in rows[:limit] if r.get("proxyWallet")][:12]
            stats_map = await self._batch_wallet_stats(top_wallets)

            for i, row in enumerate(rows[:limit]):
                wallet = row.get("proxyWallet", f"trader-{i + 1}")
                stats = stats_map.get(wallet, {})
                normalized = self._normalize_leaderboard(row, rank=i + 1, stats=stats)
                if stats.get("recent_trade"):
                    normalized["recent_live_trade"] = stats["recent_trade"]
                    normalized["is_active"] = stats.get("is_active", False)
                enriched.append(normalized)

            if not enriched:
                enriched = _MOCK_WHALES[:limit]
            _set(cache_key, enriched)
            return enriched
        except Exception:
            return _MOCK_WHALES[:limit]

    async def get_trader(self, wallet: str) -> dict | None:
        cache_key = f"trader:{wallet}"
        if cached := _get(cache_key):
            return cached

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                stats = await self._wallet_stats(client=client, wallet=wallet)
                activity_resp = await client.get(
                    f"{_DATA_API}/activity",
                    params={"user": wallet, "limit": 25},
                )
                activity = activity_resp.json() if activity_resp.status_code == 200 else []
                closed_resp = await client.get(
                    f"{_DATA_API}/closed-positions",
                    params={"user": wallet, "limit": 20},
                )
                closed = closed_resp.json() if closed_resp.status_code == 200 else []

            formatted_closed = self._format_closed(closed[:10])
            formatted_activity = self._format_activity(activity[:15])
            strategy = derive_strategy(closed=formatted_closed, activity=formatted_activity)
            live_trades = format_live_trades(activity if isinstance(activity, list) else [], limit=10)

            row = {
                "id": wallet,
                "username": stats.get("username") or wallet[:10],
                "platform": "polymarket",
                "proxy_wallet": wallet,
                "rank": stats.get("rank"),
                "win_rate_pct": stats.get("win_rate_pct"),
                "total_trades": stats.get("closed_count", 0),
                "pnl_usd": stats.get("pnl_usd", 0),
                "volume_usd": stats.get("volume_usd", 0),
                "specialty": strategy.get("specialty", "Prediction Markets"),
                "verified": stats.get("verified", False),
                "x_username": stats.get("x_username"),
                "recent_activity": formatted_activity,
                "closed_positions": formatted_closed,
                "live_trades": live_trades,
                "strategy": strategy,
                "is_active": bool(live_trades),
            }
            _set(cache_key, row)
            return row
        except Exception:
            for w in _MOCK_WHALES:
                if w["id"] == wallet or w.get("proxy_wallet") == wallet:
                    return {**w, "recent_activity": [], "closed_positions": [], "live_trades": [], "strategy": {}}
            return None

    async def _batch_wallet_stats(self, wallets: list[str]) -> dict[str, dict]:
        if not wallets:
            return {}
        async with httpx.AsyncClient(timeout=20.0) as client:
            results = await asyncio.gather(
                *[self._wallet_stats(client=client, wallet=w, light=True) for w in wallets],
                return_exceptions=True,
            )
        out = {}
        for wallet, res in zip(wallets, results):
            if isinstance(res, dict):
                out[wallet] = res
        return out

    async def _wallet_stats(
        self, *, client: httpx.AsyncClient | None, wallet: str, light: bool = False
    ) -> dict:
        own_client = client is None
        if own_client:
            client = httpx.AsyncClient(timeout=20.0)
        try:
            activity_resp = await client.get(
                f"{_DATA_API}/activity",
                params={"user": wallet, "limit": 10 if light else 15},
            )
            activity = activity_resp.json() if activity_resp.status_code == 200 else []

            closed_resp = await client.get(
                f"{_DATA_API}/closed-positions",
                params={"user": wallet, "limit": 30 if light else 50},
            )
            closed = closed_resp.json() if closed_resp.status_code == 200 else []
            if not isinstance(closed, list):
                closed = []

            wins = 0
            total_pnl = 0.0
            for pos in closed if isinstance(closed, list) else []:
                pnl = self._position_pnl(pos)
                total_pnl += pnl
                if pnl > 0:
                    wins += 1
            count = len(closed) if isinstance(closed, list) else 0
            win_rate = round(wins / count * 100, 1) if count else None

            lb_resp = await client.get(f"{_DATA_API}/v1/leaderboard", params={"limit": 100})
            lb_row = {}
            if lb_resp.status_code == 200:
                for entry in lb_resp.json():
                    if entry.get("proxyWallet", "").lower() == wallet.lower():
                        lb_row = entry
                        break

            recent_trade = None
            is_active = False
            for act in activity if isinstance(activity, list) else []:
                if str(act.get("type", "")).upper() == "TRADE":
                    ts = act.get("timestamp") or 0
                    if ts and time.time() - ts < 86_400:
                        is_active = True
                    recent_trade = {
                        "title": act.get("title", ""),
                        "side": act.get("side"),
                        "size_usd": float(act.get("usdcSize") or act.get("size") or 0),
                        "timestamp": ts,
                    }
                    break

            formatted_closed = self._format_closed(closed[:5] if light else closed[:10])
            formatted_activity = self._format_activity(activity[:5] if light else activity[:10])
            strategy = derive_strategy(closed=formatted_closed, activity=formatted_activity)

            return {
                "username": lb_row.get("userName") or wallet[:10],
                "rank": int(lb_row.get("rank", 0)) if lb_row.get("rank") else None,
                "pnl_usd": float(lb_row.get("pnl", total_pnl)),
                "volume_usd": float(lb_row.get("vol", 0)),
                "win_rate_pct": win_rate,
                "closed_count": count,
                "verified": bool(lb_row.get("verifiedBadge")),
                "x_username": lb_row.get("xUsername"),
                "recent_trade": recent_trade,
                "is_active": is_active,
                "specialty": strategy.get("specialty"),
            }
        finally:
            if own_client:
                await client.aclose()

    @staticmethod
    def _position_pnl(pos: dict) -> float:
        realized = pos.get("realizedPnl")
        if realized is not None and float(realized) != 0:
            return float(realized)
        avg = float(pos.get("avgPrice") or 0)
        cur = float(pos.get("curPrice") or 0)
        size = float(pos.get("totalBought") or 0)
        if avg and size:
            return (cur - avg) * size
        return 0.0

    @staticmethod
    def _normalize_leaderboard(row: dict, *, rank: int, stats: dict) -> dict:
        specialty = stats.get("specialty") or "Whale"
        return {
            "id": row.get("proxyWallet", f"trader-{rank}"),
            "username": row.get("userName") or f"Trader{rank}",
            "platform": "polymarket",
            "proxy_wallet": row.get("proxyWallet"),
            "rank": int(row.get("rank", rank)),
            "win_rate_pct": stats.get("win_rate_pct"),
            "total_trades": stats.get("closed_count") or 0,
            "pnl_usd": float(row.get("pnl", 0)),
            "volume_usd": float(row.get("vol", 0)),
            "specialty": specialty,
            "verified": bool(row.get("verifiedBadge")),
            "x_username": row.get("xUsername") or None,
            "is_active": stats.get("is_active", False),
        }

    @staticmethod
    def _format_activity(rows: list) -> list[dict]:
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            out.append(
                {
                    "type": r.get("type", ""),
                    "title": r.get("title", ""),
                    "size": r.get("size"),
                    "usdc_size": r.get("usdcSize"),
                    "timestamp": r.get("timestamp"),
                    "side": r.get("side"),
                }
            )
        return out

    @staticmethod
    def _format_closed(rows: list) -> list[dict]:
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            pnl = PolymarketTradersService._position_pnl(r)
            out.append(
                {
                    "title": r.get("title", ""),
                    "outcome": r.get("outcome"),
                    "avg_price": r.get("avgPrice"),
                    "cur_price": r.get("curPrice"),
                    "pnl_usd": round(pnl, 2),
                    "outcome_result": "win" if pnl > 0 else "loss" if pnl < 0 else "neutral",
                    "end_date": r.get("endDate"),
                }
            )
        return out


_MOCK_WHALES = [
    {
        "id": "mock-whale-1",
        "username": "PolyWhale",
        "platform": "polymarket",
        "proxy_wallet": None,
        "rank": 1,
        "win_rate_pct": 68.4,
        "total_trades": 412,
        "pnl_usd": 284_000,
        "volume_usd": 1_800_000,
        "specialty": "Politics",
        "verified": False,
        "is_active": False,
    }
]


def _get(key: str):
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < _TTL:
        return entry[1]
    return None


def _set(key: str, value) -> None:
    _CACHE[key] = (time.time(), value)
