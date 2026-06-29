"""User watchlists stored on Railway PostgreSQL — one list per category."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import WatchlistItem
from app.services.subscription_limits import watchlist_limit

VALID_CATEGORIES = {"stocks", "crypto", "futures", "forex", "polymarket", "kalshi"}


class WatchlistService:
    def list_items(self, db: Session, user_id: UUID, category: str | None = None) -> list[WatchlistItem]:
        query = db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id)
        if category:
            query = query.filter(WatchlistItem.category == category.lower())
        return query.order_by(WatchlistItem.created_at.desc()).all()

    def add(
        self,
        db: Session,
        user,
        ticker: str,
        company_name: str | None = None,
        category: str = "stocks",
    ) -> WatchlistItem:
        symbol = ticker.upper().strip()
        cat = (category or "stocks").lower()
        if cat not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Use one of: {', '.join(sorted(VALID_CATEGORIES))}")

        existing = (
            db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == user.id,
                WatchlistItem.category == cat,
                WatchlistItem.ticker == symbol,
            )
            .first()
        )
        if existing:
            return existing

        count = (
            db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user.id, WatchlistItem.category == cat)
            .count()
        )
        if count >= watchlist_limit(user):
            raise HTTPException(
                status_code=402,
                detail=f"Watchlist limit reached for {cat} ({watchlist_limit(user)}). Upgrade for more.",
            )

        item = WatchlistItem(
            user_id=user.id,
            ticker=symbol,
            company_name=company_name or symbol,
            category=cat,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def remove(self, db: Session, user_id: UUID, ticker: str, category: str = "stocks") -> bool:
        cat = (category or "stocks").lower()
        deleted = (
            db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == user_id,
                WatchlistItem.category == cat,
                WatchlistItem.ticker == ticker.upper(),
            )
            .delete()
        )
        db.commit()
        return deleted > 0
