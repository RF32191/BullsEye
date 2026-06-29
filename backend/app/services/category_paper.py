"""Per-category fake wallets + buy/sell using user.preferences (no schema migration required)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import PaperPosition, Prediction, User
from app.services.paper_trading import PaperTradingService, DEFAULT_WALLET, MIN_BET, MAX_BET
from app.services.price_resolver import VALID_CATEGORIES, resolve_price

_legacy = PaperTradingService()


def _prefs(user: User) -> dict:
    if user.preferences is None:
        user.preferences = {}
    return user.preferences


def _wallets(user: User) -> dict:
    prefs = _prefs(user)
    wallets = prefs.get("category_wallets")
    if not wallets:
        wallets = {}
        # migrate legacy stocks balance
        if user.paper_cash_balance is not None:
            wallets["stocks"] = {
                "cash_balance": float(user.paper_cash_balance),
                "starting_balance": float(user.paper_starting_balance or DEFAULT_WALLET),
                "realized_pnl": float(user.paper_realized_pnl or 0),
            }
        prefs["category_wallets"] = wallets
    for cat in VALID_CATEGORIES:
        if cat not in wallets:
            wallets[cat] = {
                "cash_balance": DEFAULT_WALLET,
                "starting_balance": DEFAULT_WALLET,
                "realized_pnl": 0.0,
            }
    return wallets


def _positions_store(user: User) -> list[dict]:
    prefs = _prefs(user)
    if "category_positions" not in prefs:
        prefs["category_positions"] = []
    return prefs["category_positions"]


def _save_user(db: Session, user: User) -> None:
    flag_modified(user, "preferences")
    db.commit()
    db.refresh(user)


def _wallet_snapshot(user: User, category: str, positions: list[dict]) -> dict:
    cat = category.lower()
    w = _wallets(user)[cat]
    open_pos = [p for p in positions if p["category"] == cat and p["is_open"]]
    closed_pos = [p for p in positions if p["category"] == cat and not p["is_open"]]
    unrealized = sum(p["pnl_usd"] for p in open_pos)
    invested = sum(p["notional"] for p in open_pos)
    cash = float(w["cash_balance"])
    starting = float(w["starting_balance"])
    realized = float(w["realized_pnl"])
    total_pnl = round(realized + unrealized, 2)
    closed_wins = sum(1 for p in closed_pos if (p.get("realized_pnl_usd") or 0) > 0)
    return {
        "category": cat,
        "cash_balance": round(cash, 2),
        "starting_balance": round(starting, 2),
        "invested_open": round(invested, 2),
        "equity": round(cash + invested + unrealized, 2),
        "unrealized_pnl_usd": round(unrealized, 2),
        "realized_pnl_usd": round(realized, 2),
        "total_pnl_usd": total_pnl,
        "total_return_pct": round((total_pnl / starting) * 100, 2) if starting else 0.0,
        "open_positions": len(open_pos),
        "closed_positions": len(closed_pos),
        "closed_win_rate_pct": round(closed_wins / len(closed_pos) * 100, 1) if closed_pos else None,
    }


def _direction_map(direction: str, category: str) -> str:
    d = direction.lower()
    if d in ("yes", "long", "buy", "push", "bullish"):
        return "bullish"
    if d in ("no", "short", "sell", "pull", "bearish"):
        return "bearish"
    return "bullish"


async def _mark_position(pos: dict) -> dict:
    if not pos.get("is_open"):
        price = pos.get("close_price") or pos["entry_price"]
        pnl_usd = pos.get("realized_pnl_usd")
        if pnl_usd is not None:
            pnl_pct = round((pnl_usd / pos["notional"]) * 100, 2) if pos["notional"] else 0
        else:
            pnl_pct = 0
            pnl_usd = 0
    else:
        try:
            q = await resolve_price(pos["category"], pos["ticker"])
            price = float(q["price"])
        except Exception:
            price = pos["entry_price"]
        if pos["direction"] == "bearish":
            pnl_pct = ((pos["entry_price"] - price) / pos["entry_price"]) * 100 if pos["entry_price"] else 0
        else:
            pnl_pct = ((price - pos["entry_price"]) / pos["entry_price"]) * 100 if pos["entry_price"] else 0
        pnl_usd = round(pos["notional"] * (pnl_pct / 100), 2)
    out = dict(pos)
    out["current_price"] = round(price, 4)
    out["pnl_pct"] = round(pnl_pct, 2)
    out["pnl_usd"] = round(float(pnl_usd), 2)
    return out


async def all_wallets(db: Session, user_id: UUID) -> list[dict]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _wallets(user)
    legacy = await _legacy.enrich_positions(db, user_id)
    for p in legacy:
        p.setdefault("category", "stocks")
    stored = _positions_store(user)
    combined = legacy + [await _mark_position(p) for p in stored]
    return [_wallet_snapshot(user, cat, combined) for cat in sorted(VALID_CATEGORIES)]


async def category_portfolio(db: Session, user_id: UUID, category: str) -> dict:
    cat = category.lower()
    if cat not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use: {', '.join(sorted(VALID_CATEGORIES))}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _wallets(user)
    positions: list[dict] = []
    if cat == "stocks":
        positions.extend(await _legacy.enrich_positions(db, user_id))
        for p in positions:
            p["category"] = "stocks"
    stored = [await _mark_position(p) for p in _positions_store(user) if p.get("category") == cat]
    positions.extend(stored)
    account = _wallet_snapshot(user, cat, positions)
    open_pos = [p for p in positions if p.get("category") == cat and p["is_open"]]
    return {
        "category": cat,
        "account": account,
        "positions": [p for p in positions if p.get("category") == cat],
        "summary": {
            "open_positions": len(open_pos),
            "total_notional": round(sum(p["notional"] for p in open_pos), 2),
            "total_pnl_usd": round(sum(p["pnl_usd"] for p in open_pos), 2),
        },
    }


async def buy(
    db: Session,
    user_id: UUID,
    category: str,
    *,
    symbol: str,
    direction: str,
    notional: float,
    name: str | None = None,
) -> dict:
    cat = category.lower()
    if cat not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    notional = round(notional, 2)
    if notional < MIN_BET or notional > MAX_BET:
        raise HTTPException(status_code=400, detail=f"Amount must be ${MIN_BET:.0f}–${MAX_BET:,.0f}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    wallets = _wallets(user)
    w = wallets[cat]
    if float(w["cash_balance"]) < notional:
        raise HTTPException(status_code=402, detail=f"Insufficient {cat} wallet cash")

    q = await resolve_price(cat, symbol)
    entry = float(q["price"])
    if entry <= 0:
        raise HTTPException(status_code=400, detail="Invalid price")
    dir_value = _direction_map(direction, cat)
    shares = round(notional / entry, 6)
    w["cash_balance"] = round(float(w["cash_balance"]) - notional, 2)

    pos = {
        "id": str(uuid4()),
        "category": cat,
        "ticker": symbol.upper(),
        "company_name": name or q.get("name", symbol.upper())[:256],
        "direction": dir_value,
        "entry_price": round(entry, 6),
        "shares": shares,
        "notional": notional,
        "source": "manual",
        "prediction_id": None,
        "live_trade_id": None,
        "opened_at": datetime.utcnow().isoformat(),
        "closed_at": None,
        "is_open": True,
        "realized_pnl_usd": None,
        "close_price": None,
    }

    if cat == "stocks":
        # also persist in SQL for legacy portfolio tab
        db_pos = PaperPosition(
            user_id=user_id,
            ticker=symbol.upper(),
            company_name=pos["company_name"],
            direction=dir_value,
            entry_price=entry,
            shares=shares,
            notional=notional,
            source="manual",
        )
        db.add(db_pos)
        db.flush()
        pos["id"] = str(db_pos.id)
        user.paper_cash_balance = w["cash_balance"]
        db.commit()
        enriched = await _legacy.enrich_positions(db, user_id)
        match = next((p for p in enriched if p["id"] == pos["id"]), None)
        if match:
            match["category"] = "stocks"
            return match

    _positions_store(user).append(pos)
    _save_user(db, user)
    return await _mark_position(pos)


async def sell(db: Session, user_id: UUID, category: str, position_id: str) -> dict:
    cat = category.lower()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if cat == "stocks":
        try:
            pid = UUID(position_id)
            closed = await _legacy.close_position(db, user_id, pid)
            wallets = _wallets(user)
            w = wallets["stocks"]
            w["cash_balance"] = float(user.paper_cash_balance or w["cash_balance"])
            w["realized_pnl"] = float(user.paper_realized_pnl or w["realized_pnl"])
            _save_user(db, user)
            enriched = await _legacy.enrich_positions(db, user_id)
            match = next((p for p in enriched if p["id"] == str(closed.id)), None)
            if match:
                match["category"] = "stocks"
                return match
        except ValueError:
            pass

    store = _positions_store(user)
    idx = next((i for i, p in enumerate(store) if p["id"] == position_id and p.get("category") == cat), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Position not found")
    pos = store[idx]
    if not pos["is_open"]:
        return await _mark_position(pos)

    marked = await _mark_position(pos)
    pnl_usd = marked["pnl_usd"]
    proceeds = round(pos["notional"] + pnl_usd, 2)
    wallets = _wallets(user)
    w = wallets[cat]
    w["cash_balance"] = round(float(w["cash_balance"]) + proceeds, 2)
    w["realized_pnl"] = round(float(w["realized_pnl"]) + pnl_usd, 2)
    pos["is_open"] = False
    pos["closed_at"] = datetime.utcnow().isoformat()
    pos["close_price"] = marked["current_price"]
    pos["realized_pnl_usd"] = pnl_usd
    store[idx] = pos
    _save_user(db, user)
    return marked


def deposit(db: Session, user_id: UUID, category: str, amount: float) -> dict:
    if amount < 1 or amount > 1_000_000:
        raise HTTPException(status_code=400, detail="Deposit must be $1–$1,000,000")
    cat = category.lower()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    w = _wallets(user)[cat]
    w["cash_balance"] = round(float(w["cash_balance"]) + amount, 2)
    if cat == "stocks":
        user.paper_cash_balance = w["cash_balance"]
    _save_user(db, user)
    return _wallet_snapshot(user, cat, [])


def reset_wallet(db: Session, user_id: UUID, category: str, amount: float = DEFAULT_WALLET) -> dict:
    cat = category.lower()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    store = _positions_store(user)
    now = datetime.utcnow().isoformat()
    for p in store:
        if p.get("category") == cat and p["is_open"]:
            p["is_open"] = False
            p["closed_at"] = now
            p["realized_pnl_usd"] = 0.0
    w = _wallets(user)[cat]
    w["cash_balance"] = amount
    w["starting_balance"] = amount
    w["realized_pnl"] = 0.0
    if cat == "stocks":
        user.paper_cash_balance = amount
        user.paper_starting_balance = amount
        user.paper_realized_pnl = 0.0
        for pos in db.query(PaperPosition).filter(PaperPosition.user_id == user_id, PaperPosition.closed_at.is_(None)).all():
            pos.closed_at = datetime.utcnow()
            pos.realized_pnl_usd = 0.0
        db.commit()
    _save_user(db, user)
    return _wallet_snapshot(user, cat, store)
