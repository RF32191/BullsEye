"""Live trade feed + top-pick scoring for politicians, whales, and event markets."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.services.asset_market_data import AssetMarketDataService
from app.services.congress_analytics import CongressAnalyticsService
from app.services.congress_trades import CongressTradesService
from app.services.event_market_data import EventMarketDataService
from app.services.insider_trades import InsiderTradesService
from app.services.polymarket_traders import PolymarketTradersService

_DATA_API = "https://data-api.polymarket.com"
_poly = PolymarketTradersService()
_congress = CongressTradesService()
_analytics = CongressAnalyticsService()
_insider = InsiderTradesService()
_markets = EventMarketDataService()
_assets = AssetMarketDataService()


class LiveTradesService:
    async def feed(self, *, market: str = "all", limit: int = 40) -> dict:
        tasks = []
        if market in ("all", "stocks"):
            tasks.append(self._congress_live())
            tasks.append(self._insider_live())
        if market in ("all", "polymarket"):
            tasks.append(self._polymarket_live())
        if market in ("all", "kalshi"):
            tasks.append(self._kalshi_live())
        if market in ("all", "futures"):
            tasks.append(self._asset_movers("futures"))
        if market in ("all", "crypto"):
            tasks.append(self._asset_movers("crypto"))
        if market in ("all", "forex"):
            tasks.append(self._asset_movers("forex"))

        chunks = await asyncio.gather(*tasks, return_exceptions=True)
        rows: list[dict] = []
        for chunk in chunks:
            if isinstance(chunk, list):
                rows.extend(chunk)

        rows.sort(key=lambda r: r.get("sort_key", 0), reverse=True)
        for row in rows:
            row.pop("sort_key", None)
            self._score_pick(row)

        picks = sorted(rows, key=lambda r: r.get("pick_score", 0), reverse=True)
        top_picks = [p for p in picks if p.get("pick_score", 0) >= 55][:8]
        top_ids = {p["id"] for p in top_picks}
        for row in rows:
            row["is_top_pick"] = row["id"] in top_ids

        return {
            "trades": rows[:limit],
            "top_picks": top_picks[:5],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "Congress/insider trades reflect public filings and may lag actual trades by weeks. "
                "Polymarket activity is near real-time. Kalshi shows high-volume market moves."
            ),
        }

    async def _congress_live(self) -> list[dict]:
        payload = await _congress.fetch_trades(per_page=25, page=1)
        out = []
        for t in payload.get("trades", []):
            enriched = await _analytics.enrich_trade(dict(t))
            ts = _date_sort_key(enriched.get("disclosure_date") or enriched.get("transaction_date"))
            out.append(
                {
                    "id": f"congress-{enriched.get('id')}",
                    "market_type": "stocks",
                    "actor_type": "politician",
                    "actor_name": enriched.get("member_name", ""),
                    "actor_id": enriched.get("member_slug"),
                    "title": f"{enriched.get('member_name')} · {enriched.get('ticker')}",
                    "subtitle": enriched.get("amount_label"),
                    "side": "BUY" if enriched.get("transaction_type") == "purchase" else "SELL",
                    "ticker": enriched.get("ticker"),
                    "platform": None,
                    "amount_usd": enriched.get("amount_max"),
                    "occurred_at": enriched.get("transaction_date"),
                    "disclosed_at": enriched.get("disclosure_date"),
                    "timestamp": ts,
                    "sort_key": ts,
                    "trade_outcome": enriched.get("trade_outcome"),
                    "return_since_trade_pct": enriched.get("return_since_trade_pct"),
                    "conflict_score": enriched.get("conflict_score", 0),
                }
            )
        return out

    async def _insider_live(self) -> list[dict]:
        payload = await _insider.list_trades(page=1, limit=15)
        out = []
        for t in payload.get("trades", []):
            ts = _date_sort_key(t.get("filing_date") or t.get("transaction_date"))
            qty = t.get("securities_transacted") or 0
            price = t.get("price") or 0
            out.append(
                {
                    "id": f"insider-{t.get('id')}",
                    "market_type": "stocks",
                    "actor_type": "insider",
                    "actor_name": t.get("reporting_name", ""),
                    "actor_id": None,
                    "title": f"{t.get('reporting_name')} · {t.get('symbol')}",
                    "subtitle": t.get("transaction_type"),
                    "side": t.get("transaction_type", "").upper(),
                    "ticker": t.get("symbol"),
                    "platform": None,
                    "amount_usd": round(qty * price, 2) if qty and price else None,
                    "occurred_at": t.get("transaction_date"),
                    "disclosed_at": t.get("filing_date"),
                    "timestamp": ts,
                    "sort_key": ts,
                    "trade_outcome": t.get("trade_outcome"),
                    "return_since_trade_pct": t.get("return_since_trade_pct"),
                    "conflict_score": 0,
                }
            )
        return out

    async def _polymarket_live(self) -> list[dict]:
        large = await self._polymarket_large_trades(min_usd=5000, limit=15)
        whale_rows = await self._polymarket_whale_wallets()
        out = large + whale_rows
        out.sort(key=lambda r: r.get("sort_key", 0), reverse=True)
        return out[:40]

    async def _polymarket_large_trades(self, *, min_usd: float, limit: int) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{_DATA_API}/trades", params={"limit": 50})
                if resp.status_code != 200:
                    return []
                trades = resp.json()
        except Exception:
            return []

        rows = []
        for t in trades if isinstance(trades, list) else []:
            if not isinstance(t, dict):
                continue
            usdc = float(t.get("size") or t.get("usdcSize") or 0)
            if usdc < min_usd:
                continue
            ts = int(t.get("timestamp") or 0)
            wallet = t.get("proxyWallet") or t.get("user") or "unknown"
            title = t.get("title") or t.get("market") or "Polymarket trade"
            side = (t.get("side") or "BUY").upper()
            rows.append(
                {
                    "id": f"poly-large-{wallet[:8]}-{ts}",
                    "market_type": "polymarket",
                    "actor_type": "whale",
                    "actor_name": t.get("name") or wallet[:10],
                    "actor_id": wallet,
                    "title": title,
                    "subtitle": f"${usdc:,.0f} · {side}",
                    "side": side,
                    "ticker": None,
                    "platform": "polymarket",
                    "amount_usd": usdc,
                    "occurred_at": None,
                    "disclosed_at": None,
                    "timestamp": ts,
                    "sort_key": ts,
                    "trade_outcome": None,
                    "return_since_trade_pct": None,
                    "conflict_score": 0,
                    "is_large_bet": usdc >= 25_000,
                }
            )
        return rows[:limit]

    async def _polymarket_whale_wallets(self) -> list[dict]:
        whales = await _poly.list_leaderboard(limit=8)
        wallets = [w.get("proxy_wallet") or w.get("id") for w in whales if w.get("proxy_wallet") or w.get("id")]

        async def fetch_wallet(wallet: str, username: str) -> list[dict]:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{_DATA_API}/activity",
                        params={"user": wallet, "limit": 8},
                    )
                    if resp.status_code != 200:
                        return []
                    activity = resp.json()
            except Exception:
                return []

            rows = []
            for a in activity if isinstance(activity, list) else []:
                if not isinstance(a, dict):
                    continue
                if a.get("type") not in ("TRADE", "REDEEM"):
                    continue
                ts = int(a.get("timestamp") or 0)
                usdc = float(a.get("usdcSize") or a.get("size") or 0)
                side = (a.get("side") or "").upper() or ("REDEEM" if a.get("type") == "REDEEM" else "TRADE")
                rows.append(
                    {
                        "id": f"poly-{wallet[:8]}-{ts}-{a.get('title', '')[:20]}",
                        "market_type": "polymarket",
                        "actor_type": "whale",
                        "actor_name": username,
                        "actor_id": wallet,
                        "title": a.get("title", "Polymarket trade"),
                        "subtitle": f"{username} · ${usdc:,.0f}",
                        "side": side,
                        "ticker": None,
                        "platform": "polymarket",
                        "amount_usd": usdc,
                        "occurred_at": None,
                        "disclosed_at": None,
                        "timestamp": ts,
                        "sort_key": ts,
                        "trade_outcome": None,
                        "return_since_trade_pct": None,
                        "conflict_score": 0,
                    }
                )
            return rows

        results = await asyncio.gather(
            *[fetch_wallet(w, whales[i].get("username", "Whale")) for i, w in enumerate(wallets)],
            return_exceptions=True,
        )
        out: list[dict] = []
        for chunk in results:
            if isinstance(chunk, list):
                out.extend(chunk)
        return out

    async def _kalshi_live(self) -> list[dict]:
        """High-volume Kalshi markets as live market activity (no public whale feed)."""
        rows = await _markets.list_trending(platform="kalshi", limit=12)
        out = []
        now = int(datetime.now(timezone.utc).timestamp())
        for i, m in enumerate(rows):
            vol = float(m.get("volume") or 0)
            liq = float(m.get("liquidity") or 0)
            yes = m.get("yes_price")
            out.append(
                {
                    "id": f"kalshi-{m.get('external_id')}-{i}",
                    "market_type": "kalshi",
                    "actor_type": "market",
                    "actor_name": "Kalshi Hot Market",
                    "actor_id": m.get("external_id"),
                    "title": m.get("question", "Kalshi market"),
                    "subtitle": f"Vol ${vol:,.0f} · Liq ${liq:,.0f}",
                    "side": "YES" if yes and yes >= 0.5 else "NO",
                    "ticker": None,
                    "platform": "kalshi",
                    "amount_usd": vol,
                    "occurred_at": None,
                    "disclosed_at": None,
                    "timestamp": now - i * 60,
                    "sort_key": now - i * 60,
                    "trade_outcome": None,
                    "return_since_trade_pct": None,
                    "conflict_score": 0,
                    "yes_price": yes,
                    "category": m.get("category"),
                }
            )
        return out

    async def _asset_movers(self, asset_class: str) -> list[dict]:
        rows = await _assets.movers(asset_class, limit=12)
        now = int(datetime.now(timezone.utc).timestamp())
        labels = {"futures": "Futures Mover", "crypto": "Crypto Mover", "forex": "FX Mover"}
        out = []
        for i, m in enumerate(rows):
            chg = float(m.get("change_pct") or 0)
            price = m.get("price")
            out.append(
                {
                    "id": f"{asset_class}-{m.get('symbol')}-{i}",
                    "market_type": asset_class,
                    "actor_type": "market",
                    "actor_name": labels.get(asset_class, "Market"),
                    "actor_id": m.get("symbol"),
                    "title": f"{m.get('name')} ({m.get('symbol')})",
                    "subtitle": f"{chg:+.2f}% · ${price}" if price else f"{chg:+.2f}%",
                    "side": "LONG" if chg >= 0 else "SHORT",
                    "ticker": m.get("symbol"),
                    "platform": asset_class,
                    "amount_usd": abs(chg) * 1000,
                    "occurred_at": None,
                    "disclosed_at": None,
                    "timestamp": now - i * 45,
                    "sort_key": now - i * 45,
                    "trade_outcome": None,
                    "return_since_trade_pct": chg,
                    "conflict_score": 0,
                    "category": m.get("category"),
                }
            )
        return out

    @staticmethod
    def _score_pick(row: dict) -> None:
        score = 0.0
        reasons: list[str] = []

        market = row.get("market_type")
        amount = float(row.get("amount_usd") or 0)

        if market == "stocks":
            conflict = float(row.get("conflict_score") or 0)
            if conflict >= 0.5:
                score += 25
                reasons.append("high conflict interest")
            if amount >= 50_000:
                score += 20
                reasons.append("large disclosed size")
            elif amount >= 15_000:
                score += 10
            actor = row.get("actor_type")
            if actor == "politician":
                score += 15
                reasons.append("politician filing")
            elif actor == "insider":
                score += 12
                reasons.append("insider Form 4")
            if row.get("trade_outcome") == "win":
                score += 10
                reasons.append("historically aligned move")

        elif market == "polymarket":
            if amount >= 100_000:
                score += 35
                reasons.append("whale-size bet")
            elif amount >= 25_000:
                score += 22
                reasons.append("large position")
            elif amount >= 5_000:
                score += 10
            if row.get("actor_type") == "whale":
                score += 15
                reasons.append("top trader activity")
            side = (row.get("side") or "").upper()
            if side in ("BUY", "YES"):
                score += 5

        elif market == "kalshi":
            vol = amount
            if vol >= 500_000:
                score += 30
                reasons.append("very high volume")
            elif vol >= 100_000:
                score += 18
                reasons.append("high volume")
            liq_note = row.get("subtitle", "")
            if "Liq" in liq_note:
                score += 8
                reasons.append("liquid market")

        elif market in ("futures", "crypto", "forex"):
            chg = abs(float(row.get("return_since_trade_pct") or 0))
            if chg >= 5:
                score += 28
                reasons.append("strong daily move")
            elif chg >= 2:
                score += 16
                reasons.append("notable move")
            elif chg >= 1:
                score += 8
            if market == "crypto" and chg >= 3:
                score += 10
                reasons.append("crypto volatility")
            if market == "futures" and chg >= 2:
                score += 8
                reasons.append("futures momentum")
            if market == "forex":
                score += 5
                reasons.append("major FX pair")

        row["pick_score"] = round(min(score, 100), 1)
        row["pick_reason"] = ", ".join(reasons[:3]) if reasons else None


def _date_sort_key(date_str: str | None) -> int:
    if not date_str:
        return 0
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return 0
