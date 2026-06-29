"""Enforce subscription tier daily limits."""

from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User

FREE_DAILY_AI = 5
FREE_DAILY_CHAT = 10
FREE_WATCHLIST_MAX = 1
PRO_WATCHLIST_MAX = 50
ELITE_WATCHLIST_MAX = 200


def _reset_usage_if_needed(user: User) -> None:
    today = date.today()
    reset = user.usage_reset_date.date() if user.usage_reset_date else None
    if reset != today:
        user.daily_ai_count = 0
        user.daily_chat_count = 0
        user.usage_reset_date = datetime.combine(today, datetime.min.time())


def tier_of(user: User) -> str:
    return (user.subscription_tier or "free").lower()


def require_ai_quota(db: Session, user: User) -> None:
    _reset_usage_if_needed(user)
    if tier_of(user) in ("pro", "elite"):
        return
    if user.daily_ai_count >= FREE_DAILY_AI:
        raise HTTPException(
            status_code=402,
            detail=f"Free tier limit: {FREE_DAILY_AI} AI analyses per day. Upgrade to Pro for unlimited.",
        )
    user.daily_ai_count += 1
    db.flush()


def require_chat_quota(db: Session, user: User) -> None:
    _reset_usage_if_needed(user)
    if tier_of(user) in ("pro", "elite"):
        return
    if user.daily_chat_count >= FREE_DAILY_CHAT:
        raise HTTPException(
            status_code=402,
            detail=f"Free tier limit: {FREE_DAILY_CHAT} chat messages per day. Upgrade to Pro for unlimited.",
        )
    user.daily_chat_count += 1
    db.flush()


def watchlist_limit(user: User) -> int:
    t = tier_of(user)
    if t == "elite":
        return ELITE_WATCHLIST_MAX
    if t == "pro":
        return PRO_WATCHLIST_MAX
    return FREE_WATCHLIST_MAX


def require_congress_access(user: User) -> None:
    if tier_of(user) == "free":
        raise HTTPException(
            status_code=402,
            detail="Congress trade tracker requires Pro or Elite subscription.",
        )


def usage_snapshot(user: User) -> dict:
    _reset_usage_if_needed(user)
    t = tier_of(user)
    unlimited = t in ("pro", "elite")
    return {
        "tier": t,
        "daily_ai_used": user.daily_ai_count,
        "daily_ai_limit": None if unlimited else FREE_DAILY_AI,
        "daily_chat_used": user.daily_chat_count,
        "daily_chat_limit": None if unlimited else FREE_DAILY_CHAT,
        "watchlist_limit": watchlist_limit(user),
    }
