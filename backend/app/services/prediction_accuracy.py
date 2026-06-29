"""Prediction accuracy stats for chat, analytics dashboard, and calibration."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Prediction, PredictionOutcome
from app.services.aggregate_learning import AggregateLearningService


def _is_win(outcome: PredictionOutcome) -> bool:
    return outcome in (PredictionOutcome.correct, PredictionOutcome.partial)


def _engine_label(ai_model: str | None) -> str:
    if ai_model and "technical" in ai_model.lower():
        return "technical"
    return "ai"


class PredictionAccuracyService:
    def stats_for_user(self, db: Session, user_id, ticker: str | None = None) -> dict:
        query = db.query(Prediction).filter(
            Prediction.user_id == user_id,
            Prediction.is_locked.is_(True),
        )
        if ticker:
            query = query.filter(Prediction.ticker == ticker.upper())

        preds = query.order_by(Prediction.created_at.desc()).all()
        resolved = [p for p in preds if p.outcome not in (PredictionOutcome.pending,)]
        wins = [p for p in resolved if _is_win(p.outcome)]

        by_ticker: dict[str, dict] = {}
        for p in preds:
            t = p.ticker
            if t not in by_ticker:
                by_ticker[t] = {"total": 0, "resolved": 0, "wins": 0}
            by_ticker[t]["total"] += 1
            if p.outcome not in (PredictionOutcome.pending,):
                by_ticker[t]["resolved"] += 1
                if _is_win(p.outcome):
                    by_ticker[t]["wins"] += 1

        ticker_stats = {
            t: {
                "win_rate_pct": round(v["wins"] / v["resolved"] * 100, 1) if v["resolved"] else None,
                "total": v["total"],
                "resolved": v["resolved"],
            }
            for t, v in by_ticker.items()
        }

        return {
            "overall_win_rate_pct": round(len(wins) / len(resolved) * 100, 1) if resolved else None,
            "total_predictions": len(preds),
            "resolved_predictions": len(resolved),
            "by_ticker": ticker_stats,
        }

    def daily_accuracy_trend(self, db: Session, user_id, ticker: str | None = None) -> list[dict]:
        query = db.query(Prediction).filter(
            Prediction.user_id == user_id,
            Prediction.is_locked.is_(True),
            Prediction.outcome.notin_([PredictionOutcome.pending]),
            Prediction.resolved_at.isnot(None),
        )
        if ticker:
            query = query.filter(Prediction.ticker == ticker.upper())

        preds = query.order_by(Prediction.resolved_at.asc()).all()
        by_day: dict[str, list[Prediction]] = defaultdict(list)
        for p in preds:
            day = p.resolved_at.strftime("%Y-%m-%d")
            by_day[day].append(p)

        trend = []
        cumulative_wins = 0
        cumulative_total = 0
        for day in sorted(by_day.keys()):
            day_preds = by_day[day]
            day_wins = sum(1 for p in day_preds if _is_win(p.outcome))
            cumulative_wins += day_wins
            cumulative_total += len(day_preds)
            trend.append(
                {
                    "date": day,
                    "day_win_rate_pct": round(day_wins / len(day_preds) * 100, 1),
                    "cumulative_win_rate_pct": round(cumulative_wins / cumulative_total * 100, 1),
                    "predictions_count": len(day_preds),
                }
            )
        return trend

    def accuracy_dashboard(self, db: Session, user_id) -> dict:
        preds = (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id, Prediction.is_locked.is_(True))
            .all()
        )
        resolved = [p for p in preds if p.outcome not in (PredictionOutcome.pending, PredictionOutcome.expired)]

        def bucket_stats(items: list[Prediction]) -> dict:
            if not items:
                return {"total": 0, "resolved": 0, "win_rate_pct": None}
            res = [p for p in items if p.outcome not in (PredictionOutcome.pending, PredictionOutcome.expired)]
            wins = sum(1 for p in res if _is_win(p.outcome))
            return {
                "total": len(items),
                "resolved": len(res),
                "win_rate_pct": round(wins / len(res) * 100, 1) if res else None,
            }

        ai_preds = [p for p in preds if _engine_label(p.ai_model) == "ai"]
        tech_preds = [p for p in preds if _engine_label(p.ai_model) == "technical"]

        by_horizon: dict[str, dict] = AggregateLearningService().horizon_buckets(db, user_id)
        if not by_horizon:
            for h in (7, 30, 90):
                by_horizon[str(h)] = bucket_stats([p for p in preds if p.horizon_days == h])

        by_direction: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
        dir_counts: dict[str, list[float]] = {"bullish": [], "bearish": [], "neutral": []}
        for p in resolved:
            if p.outcome == PredictionOutcome.correct:
                dir_counts[p.direction.value].append(1.0)
            elif p.outcome == PredictionOutcome.partial:
                dir_counts[p.direction.value].append(0.5)
            elif p.outcome == PredictionOutcome.incorrect:
                dir_counts[p.direction.value].append(0.0)
        for k, v in dir_counts.items():
            by_direction[k] = round(sum(v) / len(v), 3) if v else 0.0

        calibration = self._calibration(resolved)

        return {
            "overall": bucket_stats(preds),
            "ai_engine": bucket_stats(ai_preds),
            "technical_engine": bucket_stats(tech_preds),
            "by_horizon": by_horizon,
            "accuracy_by_direction": by_direction,
            "calibration": calibration,
        }

    @staticmethod
    def _calibration(resolved: list[Prediction]) -> list[dict]:
        buckets = [(0, 40), (40, 60), (60, 80), (80, 101)]
        rows = []
        for lo, hi in buckets:
            group = [p for p in resolved if lo <= p.confidence < hi]
            if not group:
                continue
            wins = sum(1 for p in group if _is_win(p.outcome))
            rows.append(
                {
                    "confidence_band": f"{lo}-{hi - 1 if hi < 101 else 100}%",
                    "predictions": len(group),
                    "actual_win_rate_pct": round(wins / len(group) * 100, 1),
                    "avg_stated_confidence": round(sum(p.confidence for p in group) / len(group), 1),
                }
            )
        return rows

    def format_accuracy_for_chat(self, db: Session, user_id, tickers: list[str]) -> str:
        lines = []
        for ticker in tickers[:3]:
            stats = self.stats_for_user(db, user_id, ticker)
            ts = stats["by_ticker"].get(ticker.upper(), {})
            wr = ts.get("win_rate_pct")
            resolved = ts.get("resolved", 0)
            total = ts.get("total", 0)
            if wr is not None:
                lines.append(f"{ticker}: {wr}% accuracy ({resolved}/{total} resolved predictions)")
            elif total:
                lines.append(f"{ticker}: {total} predictions pending resolution")
            else:
                lines.append(f"{ticker}: no locked predictions yet")

            daily = self.daily_accuracy_trend(db, user_id, ticker)
            if daily:
                last = daily[-1]
                lines.append(
                    f"  Latest resolved day ({last['date']}): {last['day_win_rate_pct']}% accuracy on "
                    f"{last['predictions_count']} prediction(s), cumulative {last['cumulative_win_rate_pct']}%"
                )

        dash = self.accuracy_dashboard(db, user_id)
        ai_wr = dash["ai_engine"].get("win_rate_pct")
        tech_wr = dash["technical_engine"].get("win_rate_pct")
        if ai_wr is not None:
            lines.append(f"AI engine win rate: {ai_wr}%")
        if tech_wr is not None:
            lines.append(f"Technical bot win rate: {tech_wr}%")

        overall = self.stats_for_user(db, user_id)
        if overall["overall_win_rate_pct"] is not None:
            lines.append(
                f"Portfolio overall: {overall['overall_win_rate_pct']}% win rate "
                f"({overall['resolved_predictions']}/{overall['total_predictions']} resolved)"
            )
        return "\n".join(lines) if lines else "No prediction history yet — run predictions in the Predict tab."
