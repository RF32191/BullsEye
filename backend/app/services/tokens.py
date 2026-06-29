from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import TokenTransaction, User


def maybe_grant_daily_tokens(db: Session, user: User) -> User:
    now = datetime.utcnow()
    if user.last_daily_grant_at and user.last_daily_grant_at.date() == now.date():
        return user

    user.token_balance += settings.free_daily_token_grant
    user.last_daily_grant_at = now
    db.add(
        TokenTransaction(
            user_id=user.id,
            amount=settings.free_daily_token_grant,
            reason="daily_grant",
        )
    )
    db.commit()
    db.refresh(user)
    return user


def register_or_get_user(db: Session, device_id: str) -> User:
    user = db.query(User).filter(User.device_id == device_id).first()
    if user:
        return maybe_grant_daily_tokens(db, user)

    user = User(device_id=device_id, token_balance=settings.initial_token_grant)
    db.add(user)
    db.flush()
    db.add(
        TokenTransaction(
            user_id=user.id,
            amount=settings.initial_token_grant,
            reason="initial_grant",
        )
    )
    db.commit()
    db.refresh(user)
    return user


def grant_tokens(
    db: Session,
    user: User,
    amount: int,
    reason: str,
    reference_id: str | None = None,
) -> User:
    if amount <= 0:
        raise ValueError("Grant amount must be positive")

    if reference_id:
        existing = (
            db.query(TokenTransaction)
            .filter(
                TokenTransaction.user_id == user.id,
                TokenTransaction.reference_id == reference_id,
            )
            .first()
        )
        if existing:
            db.refresh(user)
            return user

    user.token_balance += amount
    db.add(
        TokenTransaction(
            user_id=user.id,
            amount=amount,
            reason=reason,
            reference_id=reference_id,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def charge_tokens(db: Session, user: User, amount: int, reason: str, reference_id: str | None = None) -> User:
    if user.token_balance < amount:
        raise ValueError("Insufficient tokens")

    user.token_balance -= amount
    db.add(
        TokenTransaction(
            user_id=user.id,
            amount=-amount,
            reason=reason,
            reference_id=reference_id,
        )
    )
    db.commit()
    db.refresh(user)
    return user
