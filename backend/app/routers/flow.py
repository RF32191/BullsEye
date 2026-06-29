from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import FlowAnalysisResponse, FlowComponentResponse, FlowPredictRequest, PredictionResponse
from app.services.money_flow import MoneyFlowService
from app.services.prediction_serializer import prediction_to_response
from app.services.predictions import PredictionService
from app.services.subscription_limits import require_ai_quota

router = APIRouter(prefix="/flow", tags=["flow"])
_flow = MoneyFlowService()
_predictions = PredictionService()


@router.get("/{ticker}", response_model=FlowAnalysisResponse)
async def analyze_flow(
    ticker: str,
    horizon_days: int | None = Query(default=None, ge=1, le=180),
    horizon_value: int | None = Query(default=None, ge=1),
    horizon_unit: str | None = Query(default=None, pattern="^(minutes|hours|days)$"),
    _: User = Depends(get_current_user),
):
    try:
        payload = await _flow.analyze(
            ticker,
            horizon_days=horizon_days,
            horizon_value=horizon_value,
            horizon_unit=horizon_unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Flow analysis failed: {exc}") from exc

    return FlowAnalysisResponse(
        ticker=payload["ticker"],
        company_name=payload["company_name"],
        price=payload["price"],
        action=payload["action"],
        flow_score=payload["flow_score"],
        congress_net_usd=payload["congress_net_usd"],
        insider_net_usd=payload["insider_net_usd"],
        volume_ratio=payload["volume_ratio"],
        technical_signal=payload["technical_signal"],
        rsi=payload["rsi"],
        macd_hist=payload["macd_hist"],
        horizon_minutes=payload["horizon_minutes"],
        horizon_days=payload["horizon_days"],
        horizon_label=payload["horizon_label"],
        suggested_target=payload["suggested_target"],
        suggested_stop=payload["suggested_stop"],
        timing_note=payload["timing_note"],
        reasoning=payload["reasoning"],
        components=[FlowComponentResponse(**c) for c in payload["components"]],
        enhanced_signals=payload.get("enhanced_signals"),
        updated_at=payload["updated_at"],
        disclaimer=payload["disclaimer"],
    )


@router.post("/{ticker}/predict", response_model=PredictionResponse)
async def predict_with_flow(
    ticker: str,
    body: FlowPredictRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    symbol = ticker.upper()
    try:
        if body.engine == "ai":
            require_ai_quota(db, user)
            prediction = await _predictions.create_prediction(
                db,
                user,
                symbol,
                horizon_days=body.horizon_days,
                horizon_value=body.horizon_value,
                horizon_unit=body.horizon_unit,
            )
        else:
            prediction = await _predictions.create_technical_prediction(
                db,
                user,
                symbol,
                horizon_days=body.horizon_days,
                horizon_value=body.horizon_value,
                horizon_unit=body.horizon_unit,
            )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Flow prediction failed: {exc}") from exc

    return prediction_to_response(prediction)
