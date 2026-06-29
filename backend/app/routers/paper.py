from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    PaperAccountResponse,
    PaperDepositRequest,
    PaperOpenLiveRequest,
    PaperOpenRequest,
    PaperOpenFlowRequest,
    PaperPortfolioResponse,
    PaperPositionResponse,
    PaperResetRequest,
)
from app.services.paper_trading import PaperTradingService

router = APIRouter(prefix="/paper", tags=["paper"])
paper_service = PaperTradingService()


@router.get("/account", response_model=PaperAccountResponse)
async def paper_account(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = await paper_service.enrich_positions(db, user.id)
    return PaperAccountResponse(**paper_service.account_snapshot(db, user.id, positions))


@router.get("/portfolio", response_model=PaperPortfolioResponse)
async def get_paper_portfolio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = await paper_service.enrich_positions(db, user.id)
    return PaperPortfolioResponse(
        positions=[PaperPositionResponse(**p) for p in positions],
        summary=paper_service.portfolio_summary(positions),
        account=PaperAccountResponse(**paper_service.account_snapshot(db, user.id, positions)),
    )


@router.post("/deposit", response_model=PaperAccountResponse)
async def deposit_paper(
    body: PaperDepositRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper_service.deposit(db, user.id, body.amount)
    positions = await paper_service.enrich_positions(db, user.id)
    return PaperAccountResponse(**paper_service.account_snapshot(db, user.id, positions))


@router.post("/reset", response_model=PaperAccountResponse)
async def reset_paper(
    body: PaperResetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper_service.reset_wallet(db, user.id, body.amount)
    positions = await paper_service.enrich_positions(db, user.id)
    return PaperAccountResponse(**paper_service.account_snapshot(db, user.id, positions))


@router.post("/open", response_model=PaperPositionResponse)
async def open_paper_position(
    body: PaperOpenRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        pos = await paper_service.open_from_prediction(db, user.id, body.prediction_id, body.notional)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _enriched_one(db, user.id, pos.id)


@router.post("/open-flow", response_model=PaperPositionResponse)
async def open_paper_flow(
    body: PaperOpenFlowRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        pos = await paper_service.open_from_flow(
            db, user.id, ticker=body.ticker, direction=body.direction, notional=body.notional
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _enriched_one(db, user.id, pos.id)


@router.post("/open-live", response_model=PaperPositionResponse)
async def open_paper_live(
    body: PaperOpenLiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.ticker:
        raise HTTPException(status_code=400, detail="Ticker required for stock paper trade")
    try:
        pos = await paper_service.open_from_live(
            db,
            user.id,
            ticker=body.ticker,
            side=body.side,
            notional=body.notional,
            live_trade_id=body.live_trade_id,
            company_name=body.company_name,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _enriched_one(db, user.id, pos.id)


@router.post("/close/{position_id}", response_model=PaperPositionResponse)
async def close_paper_position(
    position_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pos = await paper_service.close_position(db, user.id, position_id)
    return await _enriched_one(db, user.id, pos.id)


@router.get("/stats")
async def paper_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = await paper_service.enrich_positions(db, user.id)
    return {
        "account": paper_service.account_snapshot(db, user.id, positions),
        "by_source": paper_service.stats_by_source(positions),
    }


async def _enriched_one(db: Session, user_id, position_id: UUID) -> PaperPositionResponse:
    enriched = await paper_service.enrich_positions(db, user_id)
    match = next((p for p in enriched if p["id"] == str(position_id)), None)
    if not match:
        raise HTTPException(status_code=500, detail="Position created but not found")
    return PaperPositionResponse(**match)
