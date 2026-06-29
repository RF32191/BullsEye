"""Serialize predictions with analysis factors from stored snapshot."""

from app.models import Prediction
from app.schemas import AnalysisFactorResponse, PredictionResponse


def prediction_to_response(prediction: Prediction) -> PredictionResponse:
    snapshot = prediction.market_snapshot or {}
    raw_factors = snapshot.get("analysis_factors", [])
    factors = [AnalysisFactorResponse(**f) for f in raw_factors if isinstance(f, dict)]

    return PredictionResponse(
        id=prediction.id,
        ticker=prediction.ticker,
        company_name=prediction.company_name,
        direction=prediction.direction,
        confidence=prediction.confidence,
        target_price=prediction.target_price,
        stop_loss=prediction.stop_loss,
        take_profit=prediction.take_profit,
        horizon_days=prediction.horizon_days,
        horizon_minutes=snapshot.get("horizon_minutes"),
        horizon_label=snapshot.get("horizon_label"),
        price_at_prediction=prediction.price_at_prediction,
        reasoning=prediction.reasoning,
        bull_case=prediction.bull_case,
        bear_case=prediction.bear_case,
        tokens_charged=prediction.tokens_charged,
        ai_model=prediction.ai_model,
        is_locked=prediction.is_locked,
        locked_at=prediction.locked_at,
        outcome=prediction.outcome,
        actual_price=prediction.actual_price,
        return_pct=prediction.return_pct,
        resolved_at=prediction.resolved_at,
        created_at=prediction.created_at,
        analysis_factors=factors,
    )
