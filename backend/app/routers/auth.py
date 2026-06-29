from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, TokenBalanceResponse, UserResponse
from app.services.tokens import register_or_get_user

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
) -> User:
    if not x_device_id:
        raise HTTPException(status_code=401, detail="X-Device-ID header required")
    return register_or_get_user(db, x_device_id)


@router.post("/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = register_or_get_user(db, body.device_id)
    return UserResponse(
        id=user.id,
        device_id=user.device_id,
        token_balance=user.token_balance,
        subscription_tier=user.subscription_tier or "free",
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        device_id=user.device_id,
        token_balance=user.token_balance,
        subscription_tier=user.subscription_tier or "free",
    )


@router.get("/tokens", response_model=TokenBalanceResponse)
def token_balance(user: User = Depends(get_current_user)):
    return TokenBalanceResponse(
        balance=user.token_balance,
        cost_per_prediction=settings.tokens_per_prediction,
        cost_per_chat_message=settings.tokens_per_chat_message,
    )
