from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Direction, Prediction, PredictionOutcome, User
from app.schemas import TrackerStatsResponse
from app.services.ai_predictor import AIPredictor
from app.services.analysis_factors import build_analysis_factors
from app.services.fmp import snapshot_hash
from app.services.market_analysis import MarketAnalysisService
from app.services.market_data import MarketDataService
from app.services.tokens import charge_tokens
from app.services.horizon import horizon_move_pct, resolve_horizon
from app.services.aggregate_learning import AggregateLearningService
from app.services.market_signals import MarketSignalsService
from app.config import settings


def _horizon_kwargs(
    horizon_days: int | None = None,
    horizon_value: int | None = None,
    horizon_unit: str | None = None,
) -> dict:
    return resolve_horizon(
        horizon_days=horizon_days,
        horizon_value=horizon_value,
        horizon_unit=horizon_unit,
    )


class PredictionService:
    def __init__(self):
        self.market = MarketDataService()
        self.analysis = MarketAnalysisService()
        self.ai = AIPredictor()
        self.signals = MarketSignalsService()
        self.learning = AggregateLearningService()

    async def create_prediction(
        self,
        db: Session,
        user: User,
        ticker: str,
        horizon_days: int | None = None,
        horizon_value: int | None = None,
        horizon_unit: str | None = None,
    ) -> Prediction:
        horizon = _horizon_kwargs(horizon_days, horizon_value, horizon_unit)
        ledger_days = horizon["horizon_days"]
        horizon_minutes = horizon["horizon_minutes"]
        horizon_label = horizon["horizon_label"]

        cost = settings.tokens_per_prediction
        if user.token_balance < cost:
            raise ValueError("Insufficient tokens for AI prediction")

        snapshot = await self.market.build_analysis_snapshot(ticker)
        technicals = await self.analysis.get_technicals(ticker)
        snapshot["technicals"] = technicals
        try:
            signal_bundle = await self.signals.bundle(ticker)
            snapshot["enhanced_signals"] = signal_bundle
        except Exception:
            signal_bundle = {"signal_components": []}
            snapshot["enhanced_signals"] = signal_bundle
        snapshot["horizon_minutes"] = horizon_minutes
        snapshot["horizon_label"] = horizon_label

        learning_ctx = self.learning.build_learning_context(
            db, ticker=ticker, horizon_label=horizon_label, engine="ai"
        )
        snapshot["platform_learning"] = learning_ctx

        ai_result = await self.ai.predict(
            ticker, ledger_days, snapshot, horizon_label=horizon_label, learning_context=learning_ctx
        )

        signal_net = sum(c.get("score", 0) for c in signal_bundle.get("signal_components", []))
        raw_conf = float(ai_result["confidence"])
        raw_conf += self.learning.signal_confidence_adjustment(signal_net)
        ai_result["confidence"] = self.learning.calibrate_confidence(db, engine="ai", raw=raw_conf)

        if signal_net >= 15 and ai_result["direction"] == "bearish":
            ai_result["confidence"] = max(35, ai_result["confidence"] - 8)
        elif signal_net <= -15 and ai_result["direction"] == "bullish":
            ai_result["confidence"] = max(35, ai_result["confidence"] - 8)
        snapshot["analysis_factors"] = build_analysis_factors(
            snapshot, technicals, ai_result["direction"]
        )
        content_hash = snapshot_hash(snapshot, ai_result)

        existing = db.query(Prediction).filter(Prediction.content_hash == content_hash).first()
        if existing:
            raise ValueError("Duplicate prediction fingerprint")

        quote = snapshot.get("quote", {})
        company_name = quote.get("name") or snapshot.get("profile", {}).get("companyName", ticker.upper())
        price = float(quote.get("price", 0))

        prediction = Prediction(
            user_id=user.id,
            ticker=ticker.upper(),
            company_name=company_name,
            direction=Direction(ai_result["direction"]),
            confidence=float(ai_result["confidence"]),
            target_price=float(ai_result["target_price"]),
            stop_loss=float(ai_result["stop_loss"]),
            take_profit=float(ai_result["take_profit"]),
            horizon_days=ledger_days,
            price_at_prediction=price,
            reasoning=ai_result["reasoning"],
            bull_case=ai_result["bull_case"],
            bear_case=ai_result["bear_case"],
            market_snapshot=snapshot,
            content_hash=content_hash,
            tokens_charged=cost,
            ai_model=settings.openai_model,
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=PredictionOutcome.pending,
        )

        db.add(prediction)
        db.flush()
        charge_tokens(db, user, cost, reason="ai_prediction", reference_id=str(prediction.id))
        db.commit()
        db.refresh(prediction)
        return prediction

    async def create_technical_prediction(
        self,
        db: Session,
        user: User,
        ticker: str,
        horizon_days: int | None = None,
        horizon_value: int | None = None,
        horizon_unit: str | None = None,
    ) -> Prediction:
        horizon = _horizon_kwargs(horizon_days, horizon_value, horizon_unit)
        ledger_days = horizon["horizon_days"]
        horizon_minutes = horizon["horizon_minutes"]
        horizon_label = horizon["horizon_label"]

        cost = settings.tokens_per_technical_prediction
        if user.token_balance < cost:
            raise ValueError("Insufficient tokens for technical prediction")

        symbol = ticker.upper()
        technicals = await self.analysis.get_technicals(symbol)
        try:
            signal_bundle = await self.signals.bundle(symbol)
        except Exception:
            signal_bundle = {"signal_components": []}

        quote = await self.market.quote(symbol)
        company_name = quote.get("name", f"{symbol} Inc.")
        price = float(technicals["price"])

        direction = Direction(technicals["signal"])
        signal_net = sum(c.get("score", 0) for c in signal_bundle.get("signal_components", []))
        confidence = float(technicals["technical_score"]) + self.learning.signal_confidence_adjustment(signal_net) * 0.5
        confidence = self.learning.calibrate_confidence(db, engine="technical", raw=confidence)

        if signal_net >= 12 and direction == Direction.bearish:
            direction = Direction.bullish
            confidence = max(35, confidence - 5)
        elif signal_net <= -12 and direction == Direction.bullish:
            direction = Direction.bearish
            confidence = max(35, confidence - 5)
        move_pct = horizon_move_pct(horizon_minutes)
        target = round(price * (1 + move_pct), 2)
        stop = round(price * (1 - abs(move_pct) * 1.2), 2)
        take = round(price * (1 + abs(move_pct) * 1.5), 2)

        if direction == Direction.bearish:
            target = round(price * (1 - abs(move_pct)), 2)
            stop = round(price * (1 + abs(move_pct) * 1.2), 2)
            take = round(price * (1 - abs(move_pct) * 1.5), 2)

        reasoning = (
            f"Technical bot (Yahoo Finance): {technicals['signal'].upper()} "
            f"(RSI {technicals['rsi']}, MACD hist {technicals['macd_hist']}, "
            f"SMA50 ${technicals.get('sma_50', 'n/a')}, P/E {technicals.get('pe_ratio', 'n/a')}). "
            f"Score {technicals['technical_score']}/100. Horizon: {horizon_label}."
        )
        bull_case = f"Momentum and moving averages support {technicals['signal']} bias over {horizon_label}."
        bear_case = "Macro shocks or earnings surprises can override technical signals quickly."

        snapshot = await self.market.build_analysis_snapshot(symbol)
        snapshot["technicals"] = technicals
        snapshot["enhanced_signals"] = signal_bundle
        snapshot["horizon_minutes"] = horizon_minutes
        snapshot["horizon_label"] = horizon_label
        snapshot["platform_learning"] = self.learning.build_learning_context(
            db, ticker=symbol, horizon_label=horizon_label, engine="technical"
        )
        snapshot["analysis_factors"] = build_analysis_factors(snapshot, technicals, direction.value)
        content_hash = snapshot_hash(
            snapshot, {"engine": "technical-bot", "direction": direction.value, "ts": datetime.utcnow().isoformat()}
        )

        prediction = Prediction(
            user_id=user.id,
            ticker=symbol,
            company_name=company_name,
            direction=direction,
            confidence=confidence,
            target_price=target,
            stop_loss=stop,
            take_profit=take,
            horizon_days=ledger_days,
            price_at_prediction=price,
            reasoning=reasoning,
            bull_case=bull_case,
            bear_case=bear_case,
            market_snapshot=snapshot,
            content_hash=content_hash,
            tokens_charged=cost,
            ai_model="technical-bot",
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=PredictionOutcome.pending,
        )

        db.add(prediction)
        db.flush()
        if cost > 0:
            charge_tokens(db, user, cost, reason="technical_prediction", reference_id=str(prediction.id))
        db.commit()
        db.refresh(prediction)
        return prediction


class TrackerService:
    """AI-free read and resolution service for locked predictions."""

    def __init__(self):
        self.market = MarketDataService()

    def list_predictions(self, db: Session, user_id, limit: int = 50) -> list[Prediction]:
        return (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id, Prediction.is_locked.is_(True))
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_prediction(self, db: Session, user_id, prediction_id) -> Prediction | None:
        return (
            db.query(Prediction)
            .filter(
                Prediction.id == prediction_id,
                Prediction.user_id == user_id,
                Prediction.is_locked.is_(True),
            )
            .first()
        )

    def stats(self, db: Session, user_id) -> TrackerStatsResponse:
        preds = (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id, Prediction.is_locked.is_(True))
            .all()
        )
        resolved = [p for p in preds if p.outcome not in (PredictionOutcome.pending,)]
        wins = [p for p in resolved if p.outcome in (PredictionOutcome.correct, PredictionOutcome.partial)]
        returns = [p.return_pct for p in resolved if p.return_pct is not None]

        by_dir: dict[str, list] = {"bullish": [], "bearish": [], "neutral": []}
        for p in resolved:
            if p.outcome == PredictionOutcome.correct:
                by_dir[p.direction.value].append(1.0)
            elif p.outcome == PredictionOutcome.incorrect:
                by_dir[p.direction.value].append(0.0)

        accuracy = {
            k: (sum(v) / len(v) if v else 0.0)
            for k, v in by_dir.items()
        }

        return TrackerStatsResponse(
            total_predictions=len(preds),
            locked_predictions=len(preds),
            resolved_predictions=len(resolved),
            win_rate=(len(wins) / len(resolved) * 100) if resolved else None,
            average_return_pct=(sum(returns) / len(returns)) if returns else None,
            accuracy_by_direction=accuracy,
        )

    async def resolve_due_predictions(self, db: Session) -> int:
        now = datetime.utcnow()
        due = (
            db.query(Prediction)
            .filter(
                Prediction.is_locked.is_(True),
                Prediction.outcome == PredictionOutcome.pending,
            )
            .all()
        )

        resolved_count = 0
        for pred in due:
            if not pred.locked_at:
                continue
            snapshot = pred.market_snapshot or {}
            horizon_minutes = snapshot.get("horizon_minutes") or pred.horizon_days * 1_440
            due_at = pred.locked_at + timedelta(minutes=int(horizon_minutes))
            if due_at > now:
                continue

            try:
                quote = await self.market.quote(pred.ticker)
                actual = float(quote.get("price", pred.price_at_prediction))
                history_days = max(pred.horizon_days + 14, 7)
                history = await self.market.historical_prices(pred.ticker, days=history_days)
            except Exception:
                pred.outcome = PredictionOutcome.expired
                pred.resolved_at = now
                resolved_count += 1
                continue

            return_pct = ((actual - pred.price_at_prediction) / pred.price_at_prediction) * 100
            pred.actual_price = actual
            pred.return_pct = round(return_pct, 2)
            pred.resolved_at = now
            pred.outcome = self._score_outcome_with_bars(pred, actual, history)
            resolved_count += 1

        db.commit()
        return resolved_count

    @classmethod
    def _score_outcome_with_bars(cls, pred: Prediction, actual: float, bars: list[dict]) -> PredictionOutcome:
        """Score using intraperiod high/low when available, else closing price."""
        start = pred.locked_at.date() if pred.locked_at else None
        window = []
        for bar in bars:
            bar_date = bar.get("date", "")[:10]
            if not bar_date:
                continue
            if start and bar_date >= start.isoformat():
                window.append(bar)

        if window:
            highs = [float(b.get("high") or b.get("close", 0)) for b in window]
            lows = [float(b.get("low") or b.get("close", 0)) for b in window]
            period_high = max(highs) if highs else actual
            period_low = min(lows) if lows else actual

            if pred.direction == Direction.bullish:
                if period_high >= pred.take_profit:
                    return PredictionOutcome.correct
                if period_low <= pred.stop_loss:
                    return PredictionOutcome.incorrect
            elif pred.direction == Direction.bearish:
                if period_low <= pred.take_profit:
                    return PredictionOutcome.correct
                if period_high >= pred.stop_loss:
                    return PredictionOutcome.incorrect

        return cls._score_outcome(pred, actual)

    @staticmethod
    def _score_outcome(pred: Prediction, actual: float) -> PredictionOutcome:
        entry = pred.price_at_prediction
        move_pct = ((actual - entry) / entry) * 100

        if pred.direction == Direction.bullish:
            if actual >= pred.take_profit:
                return PredictionOutcome.correct
            if actual <= pred.stop_loss:
                return PredictionOutcome.incorrect
            if move_pct <= -0.5:
                return PredictionOutcome.incorrect
            if move_pct >= 3.0:
                return PredictionOutcome.correct
            if move_pct >= 1.0:
                return PredictionOutcome.partial
            return PredictionOutcome.incorrect

        if pred.direction == Direction.bearish:
            if actual <= pred.take_profit:
                return PredictionOutcome.correct
            if actual >= pred.stop_loss:
                return PredictionOutcome.incorrect
            if move_pct >= 0.5:
                return PredictionOutcome.incorrect
            if move_pct <= -3.0:
                return PredictionOutcome.correct
            if move_pct <= -1.0:
                return PredictionOutcome.partial
            return PredictionOutcome.incorrect

        if abs(move_pct) <= 2.5:
            return PredictionOutcome.correct
        return PredictionOutcome.incorrect
