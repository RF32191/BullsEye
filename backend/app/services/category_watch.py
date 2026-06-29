"""Category watchlists for Polymarket/Kalshi."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import CategoryWatch


class CategoryWatchService:
    def list_watches(self, db: Session, user_id: UUID) -> list[CategoryWatch]:
        return (
            db.query(CategoryWatch)
            .filter(CategoryWatch.user_id == user_id)
            .order_by(CategoryWatch.created_at.desc())
            .all()
        )

    def add(self, db: Session, user_id: UUID, platform: str, slug: str, label: str) -> CategoryWatch:
        existing = (
            db.query(CategoryWatch)
            .filter(
                CategoryWatch.user_id == user_id,
                CategoryWatch.platform == platform,
                CategoryWatch.category_slug == slug,
            )
            .first()
        )
        if existing:
            return existing
        item = CategoryWatch(
            user_id=user_id,
            platform=platform,
            category_slug=slug,
            category_label=label,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def remove(self, db: Session, user_id: UUID, watch_id: UUID) -> bool:
        deleted = (
            db.query(CategoryWatch)
            .filter(CategoryWatch.id == watch_id, CategoryWatch.user_id == user_id)
            .delete()
        )
        db.commit()
        return deleted > 0
