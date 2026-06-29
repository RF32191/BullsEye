import os

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    AccuracyDashboardResponse,
    CalibrationBucketResponse,
    DailyAccuracyPoint,
    EngineStatsResponse,
    PredictionRequest,
    PredictionResponse,
    PublicStatsResponse,
    ResolveBatchResponse,
    TrackerStatsResponse,
    UsageLimitsResponse,
)
from app.services.prediction_accuracy import PredictionAccuracyService
from app.services.prediction_serializer import prediction_to_response
from app.services.predictions import PredictionService, TrackerService
from app.services.subscription_limits import check_ai_quota, record_ai_usage, usage_snapshot
from app.services.prediction_errors import friendly_prediction_error

router = APIRouter(prefix="/predictions", tags=["predictions"])
prediction_service = PredictionService()
tracker_service = TrackerService()
accuracy_service = PredictionAccuracyService()


@router.post("/analyze", response_model=PredictionResponse)
async def analyze_stock(
    body: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        check_ai_quota(user)
        prediction = await prediction_service.create_prediction(
            db, user, body.ticker, body.horizon_days, body.horizon_value, body.horizon_unit
        )
        record_ai_usage(db, user)
        db.commit()
    except ValueError as exc:
        db.rollback()
        status, detail = friendly_prediction_error(exc)
        raise HTTPException(status_code=status, detail=detail) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        status, detail = friendly_prediction_error(exc)
        raise HTTPException(status_code=status, detail=detail) from exc

    return prediction_to_response(prediction)


@router.post("/analyze-technical", response_model=PredictionResponse)
async def analyze_technical(
    body: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        prediction = await prediction_service.create_technical_prediction(
            db, user, body.ticker, body.horizon_days, body.horizon_value, body.horizon_unit
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Technical prediction failed: {exc}") from exc

    return prediction_to_response(prediction)


@router.get("/tracker", response_model=list[PredictionResponse])
async def list_locked_predictions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    """AI-free read of immutable locked predictions. Auto-resolves due predictions."""
    await tracker_service.resolve_due_predictions(db)
    preds = tracker_service.list_predictions(db, user.id, limit=limit)
    return [prediction_to_response(p) for p in preds]


@router.get("/tracker/stats", response_model=TrackerStatsResponse)
async def tracker_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    await tracker_service.resolve_due_predictions(db)
    return tracker_service.stats(db, user.id)


@router.get("/accuracy-trend", response_model=list[DailyAccuracyPoint])
async def accuracy_trend(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    ticker: str | None = Query(default=None),
):
    await tracker_service.resolve_due_predictions(db)
    return accuracy_service.daily_accuracy_trend(db, user.id, ticker)


@router.get("/accuracy-dashboard", response_model=AccuracyDashboardResponse)
async def accuracy_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    await tracker_service.resolve_due_predictions(db)
    dash = accuracy_service.accuracy_dashboard(db, user.id)
    return AccuracyDashboardResponse(
        overall=EngineStatsResponse(**dash["overall"]),
        ai_engine=EngineStatsResponse(**dash["ai_engine"]),
        technical_engine=EngineStatsResponse(**dash["technical_engine"]),
        by_horizon={k: EngineStatsResponse(**v) for k, v in dash["by_horizon"].items()},
        accuracy_by_direction=dash["accuracy_by_direction"],
        calibration=[CalibrationBucketResponse(**c) for c in dash["calibration"]],
    )


@router.get("/usage", response_model=UsageLimitsResponse)
def usage_limits(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.refresh(user)
    return UsageLimitsResponse(**usage_snapshot(user))


@router.get("/public-stats", response_model=PublicStatsResponse)
def public_stats(db: Session = Depends(get_db)):
    """Aggregate stats across all users for onboarding — no auth required."""
    from app.models import Prediction, PredictionOutcome

    preds = db.query(Prediction).filter(Prediction.is_locked.is_(True)).all()
    resolved = [p for p in preds if p.outcome not in (PredictionOutcome.pending, PredictionOutcome.expired)]
    wins = [p for p in resolved if p.outcome in (PredictionOutcome.correct, PredictionOutcome.partial)]

    ai_res = [p for p in resolved if p.ai_model and "technical" not in p.ai_model.lower()]
    tech_res = [p for p in resolved if p.ai_model and "technical" in p.ai_model.lower()]
    ai_wins = [p for p in ai_res if p.outcome in (PredictionOutcome.correct, PredictionOutcome.partial)]
    tech_wins = [p for p in tech_res if p.outcome in (PredictionOutcome.correct, PredictionOutcome.partial)]

    return PublicStatsResponse(
        total_predictions=len(preds),
        resolved_predictions=len(resolved),
        overall_win_rate_pct=round(len(wins) / len(resolved) * 100, 1) if resolved else None,
        ai_win_rate_pct=round(len(ai_wins) / len(ai_res) * 100, 1) if ai_res else None,
        technical_win_rate_pct=round(len(tech_wins) / len(tech_res) * 100, 1) if tech_res else None,
    )


@router.get("/tracker/{prediction_id}", response_model=PredictionResponse)
def get_locked_prediction(
    prediction_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prediction = tracker_service.get_prediction(db, user.id, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction_to_response(prediction)


@router.post("/resolve-due", response_model=ResolveBatchResponse)
async def resolve_due_predictions(
    db: Session = Depends(get_db),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    """Background/cron endpoint to score expired predictions. No AI involved."""
    admin_key = os.getenv("ADMIN_CRON_KEY", settings.admin_cron_key)
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    count = await tracker_service.resolve_due_predictions(db)
    return ResolveBatchResponse(resolved_count=count)
