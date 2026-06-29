"""Virtual cash wallet — deposit fake money, track wins/losses on close."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import PaperPosition, Prediction, User
from app.services.market_data import MarketDataService

DEFAULT_WALLET = 10_000.0
MIN_BET = 50.0
MAX_BET = 50_000.0


class PaperTradingService:
    def __init__(self):
        self.market = MarketDataService()

    def _user(self, db: Session, user_id: UUID) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.paper_cash_balance is None:
            user.paper_cash_balance = DEFAULT_WALLET
        if user.paper_starting_balance is None:
            user.paper_starting_balance = DEFAULT_WALLET
        if user.paper_realized_pnl is None:
            user.paper_realized_pnl = 0.0
        return user

    def account_snapshot(self, db: Session, user_id: UUID, positions: list[dict]) -> dict:
        user = self._user(db, user_id)
        open_pos = [p for p in positions if p["is_open"]]
        closed_pos = [p for p in positions if not p["is_open"]]
        unrealized = sum(p["pnl_usd"] for p in open_pos)
        invested = sum(p["notional"] for p in open_pos)
        cash = float(user.paper_cash_balance or 0)
        starting = float(user.paper_starting_balance or DEFAULT_WALLET)
        realized = float(user.paper_realized_pnl or 0)
        equity = round(cash + invested + unrealized, 2)
        total_pnl = round(realized + unrealized, 2)
        closed_wins = sum(1 for p in closed_pos if (p.get("realized_pnl_usd") or 0) > 0)
        closed_total = len(closed_pos)
        return {
            "cash_balance": round(cash, 2),
            "starting_balance": round(starting, 2),
            "invested_open": round(invested, 2),
            "equity": equity,
            "unrealized_pnl_usd": round(unrealized, 2),
            "realized_pnl_usd": round(realized, 2),
            "total_pnl_usd": total_pnl,
            "total_return_pct": round((total_pnl / starting) * 100, 2) if starting else 0.0,
            "open_positions": len(open_pos),
            "closed_positions": closed_total,
            "closed_win_rate_pct": round(closed_wins / closed_total * 100, 1) if closed_total else None,
        }

    def deposit(self, db: Session, user_id: UUID, amount: float) -> dict:
        if amount < 1 or amount > 1_000_000:
            raise HTTPException(status_code=400, detail="Deposit must be between $1 and $1,000,000")
        user = self._user(db, user_id)
        user.paper_cash_balance = float(user.paper_cash_balance or 0) + amount
        db.commit()
        db.refresh(user)
        return {"cash_balance": round(user.paper_cash_balance, 2), "deposited": amount}

    def reset_wallet(self, db: Session, user_id: UUID, amount: float = DEFAULT_WALLET) -> dict:
        user = self._user(db, user_id)
        open_positions = self.list_positions(db, user_id, open_only=True)
        now = datetime.utcnow()
        for pos in open_positions:
            pos.closed_at = now
            pos.realized_pnl_usd = 0.0
        user.paper_cash_balance = amount
        user.paper_starting_balance = amount
        user.paper_realized_pnl = 0.0
        db.commit()
        return {"cash_balance": amount, "reset": True}

    def _reserve_cash(self, user: User, notional: float) -> None:
        notional = round(notional, 2)
        if notional < MIN_BET or notional > MAX_BET:
            raise HTTPException(status_code=400, detail=f"Bet must be ${MIN_BET:.0f}–${MAX_BET:,.0f}")
        cash = float(user.paper_cash_balance or 0)
        if cash < notional:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient paper cash (${cash:,.0f} available, ${notional:,.0f} needed). Deposit fake money in Portfolio.",
            )
        user.paper_cash_balance = cash - notional

    async def _open_position(
        self,
        db: Session,
        user_id: UUID,
        *,
        ticker: str,
        company_name: str,
        direction: str,
        notional: float,
        source: str,
        prediction_id: UUID | None = None,
        live_trade_id: str | None = None,
    ) -> PaperPosition:
        user = self._user(db, user_id)
        self._reserve_cash(user, notional)
        quote = await self.market.quote(ticker)
        entry = float(quote.get("price", 0))
        if entry <= 0:
            user.paper_cash_balance = float(user.paper_cash_balance or 0) + notional
            raise HTTPException(status_code=400, detail="Invalid price")
        shares = round(notional / entry, 4)
        pos = PaperPosition(
            user_id=user_id,
            ticker=ticker.upper(),
            company_name=company_name,
            prediction_id=prediction_id,
            direction=direction,
            entry_price=entry,
            shares=shares,
            notional=notional,
            source=source,
            live_trade_id=live_trade_id,
        )
        db.add(pos)
        db.commit()
        db.refresh(pos)
        return pos

    def list_positions(self, db: Session, user_id: UUID, open_only: bool = True) -> list[PaperPosition]:
        q = db.query(PaperPosition).filter(PaperPosition.user_id == user_id)
        if open_only:
            q = q.filter(PaperPosition.closed_at.is_(None))
        return q.order_by(PaperPosition.opened_at.desc()).all()

    async def open_from_prediction(
        self, db: Session, user_id: UUID, prediction_id: UUID, notional: float = 1000.0
    ) -> PaperPosition:
        pred = (
            db.query(Prediction)
            .filter(Prediction.id == prediction_id, Prediction.user_id == user_id, Prediction.is_locked.is_(True))
            .first()
        )
        if not pred:
            raise HTTPException(status_code=404, detail="Prediction not found")
        existing = (
            db.query(PaperPosition)
            .filter(
                PaperPosition.user_id == user_id,
                PaperPosition.prediction_id == prediction_id,
                PaperPosition.closed_at.is_(None),
            )
            .first()
        )
        if existing:
            return existing
        return await self._open_position(
            db,
            user_id,
            ticker=pred.ticker,
            company_name=pred.company_name,
            direction=pred.direction.value,
            notional=notional,
            source="prediction",
            prediction_id=prediction_id,
        )

    async def open_from_flow(
        self, db: Session, user_id: UUID, *, ticker: str, direction: str, notional: float = 1000.0
    ) -> PaperPosition:
        direction_map = {"push": "bullish", "pull": "bearish", "bullish": "bullish", "bearish": "bearish"}
        dir_value = direction_map.get(direction.lower(), "bullish")
        quote = await self.market.quote(ticker)
        name = quote.get("name", ticker.upper())
        return await self._open_position(
            db,
            user_id,
            ticker=ticker,
            company_name=name,
            direction=dir_value,
            notional=notional,
            source="flow",
        )

    async def open_from_live(
        self,
        db: Session,
        user_id: UUID,
        *,
        ticker: str,
        side: str,
        notional: float,
        live_trade_id: str,
        company_name: str | None = None,
    ) -> PaperPosition:
        side_u = side.upper()
        if side_u in ("SELL", "SHORT", "NO"):
            direction = "bearish"
        else:
            direction = "bullish"
        name = company_name or ticker.upper()
        return await self._open_position(
            db,
            user_id,
            ticker=ticker,
            company_name=name,
            direction=direction,
            notional=notional,
            source="live",
            live_trade_id=live_trade_id,
        )

    async def close_position(self, db: Session, user_id: UUID, position_id: UUID) -> PaperPosition:
        pos = (
            db.query(PaperPosition)
            .filter(PaperPosition.id == position_id, PaperPosition.user_id == user_id)
            .first()
        )
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")
        if pos.closed_at:
            return pos
        user = self._user(db, user_id)
        try:
            quote = await self.market.quote(pos.ticker)
            price = float(quote.get("price", pos.entry_price))
        except Exception:
            price = pos.entry_price
        if pos.direction == "bearish":
            pnl_pct = ((pos.entry_price - price) / pos.entry_price) * 100
        else:
            pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100
        pnl_usd = round(pos.notional * (pnl_pct / 100), 2)
        proceeds = round(pos.notional + pnl_usd, 2)
        user.paper_cash_balance = float(user.paper_cash_balance or 0) + proceeds
        user.paper_realized_pnl = float(user.paper_realized_pnl or 0) + pnl_usd
        pos.close_price = round(price, 2)
        pos.realized_pnl_usd = pnl_usd
        pos.closed_at = datetime.utcnow()
        db.commit()
        db.refresh(pos)
        return pos

    async def enrich_positions(self, db: Session, user_id: UUID) -> list[dict]:
        positions = self.list_positions(db, user_id, open_only=False)
        output = []
        for pos in positions[:100]:
            if pos.closed_at and pos.close_price:
                price = pos.close_price
                pnl_pct = ((pos.realized_pnl_usd or 0) / pos.notional * 100) if pos.notional else 0
                pnl_usd = pos.realized_pnl_usd or 0
            else:
                try:
                    quote = await self.market.quote(pos.ticker)
                    price = float(quote.get("price", pos.entry_price))
                except Exception:
                    price = pos.entry_price
                if pos.direction == "bearish":
                    pnl_pct = ((pos.entry_price - price) / pos.entry_price) * 100
                else:
                    pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100
                pnl_usd = round(pos.notional * (pnl_pct / 100), 2)
            output.append(
                {
                    "id": str(pos.id),
                    "ticker": pos.ticker,
                    "company_name": pos.company_name,
                    "direction": pos.direction,
                    "entry_price": pos.entry_price,
                    "current_price": round(price, 2),
                    "shares": pos.shares,
                    "notional": pos.notional,
                    "pnl_pct": round(pnl_pct, 2),
                    "pnl_usd": pnl_usd,
                    "realized_pnl_usd": pos.realized_pnl_usd,
                    "source": pos.source or "prediction",
                    "prediction_id": str(pos.prediction_id) if pos.prediction_id else None,
                    "live_trade_id": pos.live_trade_id,
                    "opened_at": pos.opened_at.isoformat(),
                    "closed_at": pos.closed_at.isoformat() if pos.closed_at else None,
                    "is_open": pos.closed_at is None,
                }
            )
        return output

    def stats_by_source(self, positions: list[dict]) -> dict:
        closed = [p for p in positions if not p["is_open"]]
        by_source: dict[str, dict] = {}
        for p in closed:
            src = p.get("source") or "prediction"
            bucket = by_source.setdefault(src, {"trades": 0, "wins": 0, "total_pnl": 0.0})
            bucket["trades"] += 1
            pnl = float(p.get("realized_pnl_usd") or p.get("pnl_usd") or 0)
            bucket["total_pnl"] += pnl
            if pnl > 0:
                bucket["wins"] += 1
        for src, b in by_source.items():
            b["win_rate_pct"] = round(b["wins"] / b["trades"] * 100, 1) if b["trades"] else None
            b["total_pnl"] = round(b["total_pnl"], 2)
        return by_source

    def portfolio_summary(self, positions: list[dict]) -> dict:
        open_positions = [p for p in positions if p["is_open"]]
        total_pnl = sum(p["pnl_usd"] for p in open_positions)
        total_notional = sum(p["notional"] for p in open_positions)
        return {
            "open_positions": len(open_positions),
            "total_notional": round(total_notional, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "total_pnl_pct": round((total_pnl / total_notional * 100) if total_notional else 0, 2),
        }
