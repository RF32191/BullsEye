"""Category-scoped paper trading routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.services.price_resolver import VALID_CATEGORIES
from app.services.category_paper import (
    all_wallets,
    buy,
    category_portfolio,
    deposit,
    reset_wallet,
    sell,
)
from app.services.paper_trading import PaperTradingService

router = APIRouter(prefix="/paper", tags=["paper"])
legacy = PaperTradingService()


class PaperBuyRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    direction: str = Field(default="bullish", pattern="^(bullish|bearish|yes|no|buy|sell|long|short|push|pull)$")
    notional: float = Field(default=1000.0, ge=50, le=50_000)
    name: str | None = None


class PaperCategoryDepositRequest(BaseModel):
    amount: float = Field(ge=1, le=1_000_000)


class PaperCategoryResetRequest(BaseModel):
    amount: float = Field(default=10_000.0, ge=1000, le=1_000_000)


def _check_category(category: str) -> str:
    cat = category.lower()
    if cat not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    return cat


@router.get("/wallets")
async def list_category_wallets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"wallets": await all_wallets(db, user.id)}


@router.get("/category/{category}/portfolio")
async def get_category_portfolio(
    category: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await category_portfolio(db, user.id, _check_category(category))


@router.post("/category/{category}/buy")
async def category_buy(
    category: str,
    body: PaperBuyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await buy(
            db,
            user.id,
            _check_category(category),
            symbol=body.symbol,
            direction=body.direction,
            notional=body.notional,
            name=body.name,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/category/{category}/sell/{position_id}")
async def category_sell(
    category: str,
    position_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await sell(db, user.id, _check_category(category), position_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/category/{category}/deposit")
async def category_deposit(
    category: str,
    body: PaperCategoryDepositRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return deposit(db, user.id, _check_category(category), body.amount)


@router.post("/category/{category}/reset")
async def category_reset(
    category: str,
    body: PaperCategoryResetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return reset_wallet(db, user.id, _check_category(category), body.amount)
