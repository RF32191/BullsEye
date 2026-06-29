"""Congress politician performance analytics."""

from __future__ import annotations

from collections import defaultdict

from app.services.congress_trades import CongressTradesService
from app.services.market_data import MarketDataService
from app.services.trade_performance import price_on_date, score_equity_trade


class CongressAnalyticsService:
    def __init__(self):
        self.congress = CongressTradesService()
        self.market = MarketDataService()

    async def enrich_trade(self, row: dict) -> dict:
        ticker = row.get("ticker")
        if not ticker:
            return row

        try:
            quote = await self.market.quote(ticker)
            current = float(quote.get("price", 0))
            row["current_price"] = round(current, 2)
            history = await self.market.historical_prices(ticker, days=365)
        except Exception:
            return row

        tx_date = row.get("transaction_date")
        disclosure = row.get("disclosure_date")
        tx_type = row.get("transaction_type", "")

        price_at_trade = price_on_date(history, tx_date)
        price_at_disclosure = price_on_date(history, disclosure) or price_at_trade

        if price_at_trade and current:
            scored = score_equity_trade(
                transaction_type=tx_type,
                price_at_entry=price_at_trade,
                current_price=current,
            )
            row["return_since_trade_pct"] = scored["return_pct"]
            row["trade_outcome"] = scored["trade_outcome"]
            row["price_at_trade"] = scored["price_at_entry"]

        if price_at_disclosure and current:
            ret_disc = ((current - price_at_disclosure) / price_at_disclosure) * 100
            row["return_since_disclosure_pct"] = round(ret_disc, 2)
            row["price_at_disclosure"] = round(price_at_disclosure, 2)

        return row

    async def top_politicians(self, *, limit: int = 15) -> list[dict]:
        payload = await self.congress.fetch_trades(per_page=100, page=1)
        trades = payload.get("trades", [])

        by_member: dict[str, list[dict]] = defaultdict(list)
        for t in trades:
            slug = t.get("member_slug") or t.get("member_name", "")
            by_member[slug].append(t)

        profiles = []
        for slug, member_trades in by_member.items():
            if not member_trades:
                continue
            sample = member_trades[0]
            enriched = []
            for t in member_trades[:20]:
                enriched.append(await self.enrich_trade(dict(t)))

            outcomes = [e.get("trade_outcome") for e in enriched if e.get("trade_outcome")]
            wins = sum(1 for o in outcomes if o == "win")
            resolved = len(outcomes)
            returns = [e["return_since_trade_pct"] for e in enriched if e.get("return_since_trade_pct") is not None]

            profiles.append(
                {
                    "member_slug": slug,
                    "member_name": sample.get("member_name", slug),
                    "party": sample.get("party"),
                    "chamber": sample.get("chamber"),
                    "total_trades": len(member_trades),
                    "tracked_trades": resolved,
                    "win_rate_pct": round(wins / resolved * 100, 1) if resolved else None,
                    "avg_return_since_trade_pct": round(sum(returns) / len(returns), 2) if returns else None,
                    "recent_trades": enriched[:5],
                }
            )

        profiles.sort(key=lambda p: (p.get("win_rate_pct") or 0, p.get("total_trades", 0)), reverse=True)
        return profiles[:limit]

    async def politician_profile(self, slug: str) -> dict | None:
        payload = await self.congress.fetch_trades(politician=slug.replace("-", " ").title(), per_page=50)
        trades = payload.get("trades", [])
        if not trades:
            payload = await self.congress.fetch_trades(per_page=100)
            trades = [t for t in payload.get("trades", []) if t.get("member_slug") == slug]
        if not trades:
            return None

        enriched = []
        for t in trades:
            enriched.append(await self.enrich_trade(dict(t)))

        outcomes = [e.get("trade_outcome") for e in enriched if e.get("trade_outcome")]
        wins = sum(1 for o in outcomes if o == "win")
        losses = sum(1 for o in outcomes if o == "loss")
        returns = [e["return_since_trade_pct"] for e in enriched if e.get("return_since_trade_pct") is not None]

        return {
            "member_slug": slug,
            "member_name": trades[0].get("member_name", slug),
            "party": trades[0].get("party"),
            "chamber": trades[0].get("chamber"),
            "total_trades": len(enriched),
            "win_rate_pct": round(wins / len(outcomes) * 100, 1) if outcomes else None,
            "wins": wins,
            "losses": losses,
            "avg_return_since_trade_pct": round(sum(returns) / len(returns), 2) if returns else None,
            "trades": enriched,
            "disclaimer": (
                "Performance uses Yahoo Finance prices from disclosed trade dates. "
                "STOCK Act filings may lag actual trades by up to 45 days."
            ),
        }
