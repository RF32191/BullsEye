"""Cross-user outcome learning — calibration and prompt context from all resolved predictions."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import Prediction, PredictionOutcome, Direction
from app.services.prediction_accuracy import _engine_label, _is_win


def _resolved_query(db: Session, *, ticker: str | None = None):
    q = db.query(Prediction).filter(
        Prediction.is_locked.is_(True),
        Prediction.outcome.notin_([PredictionOutcome.pending, PredictionOutcome.expired]),
    )
    if ticker:
        q = q.filter(Prediction.ticker == ticker.upper())
    return q


class AggregateLearningService:
    def global_stats(self, db: Session) -> dict:
        preds = _resolved_query(db).all()
        if not preds:
            return {"resolved": 0, "win_rate_pct": None, "ai_win_rate_pct": None, "technical_win_rate_pct": None}

        wins = sum(1 for p in preds if _is_win(p.outcome))
        ai = [p for p in preds if _engine_label(p.ai_model) == "ai"]
        tech = [p for p in preds if _engine_label(p.ai_model) == "technical"]
        ai_wins = sum(1 for p in ai if _is_win(p.outcome))
        tech_wins = sum(1 for p in tech if _is_win(p.outcome))

        return {
            "resolved": len(preds),
            "win_rate_pct": round(wins / len(preds) * 100, 1),
            "ai_win_rate_pct": round(ai_wins / len(ai) * 100, 1) if ai else None,
            "technical_win_rate_pct": round(tech_wins / len(tech) * 100, 1) if tech else None,
        }

    def ticker_stats(self, db: Session, ticker: str) -> dict:
        preds = _resolved_query(db, ticker=ticker).all()
        if not preds:
            return {"resolved": 0, "win_rate_pct": None}
        wins = sum(1 for p in preds if _is_win(p.outcome))
        return {"resolved": len(preds), "win_rate_pct": round(wins / len(preds) * 100, 1)}

    def horizon_stats(self, db: Session, horizon_label: str) -> dict:
        preds = _resolved_query(db).all()
        matched = [
            p
            for p in preds
            if (p.market_snapshot or {}).get("horizon_label") == horizon_label
            or str(p.horizon_days) in horizon_label
        ]
        if not matched:
            return {"resolved": 0, "win_rate_pct": None}
        wins = sum(1 for p in matched if _is_win(p.outcome))
        return {"resolved": len(matched), "win_rate_pct": round(wins / len(matched) * 100, 1)}

    def direction_stats(self, db: Session, direction: str) -> dict:
        try:
            dir_enum = Direction(direction.lower())
        except ValueError:
            return {"resolved": 0, "win_rate_pct": None}
        preds = _resolved_query(db).filter(Prediction.direction == dir_enum).all()
        if not preds:
            return {"resolved": 0, "win_rate_pct": None}
        wins = sum(1 for p in preds if _is_win(p.outcome))
        return {"resolved": len(preds), "win_rate_pct": round(wins / len(preds) * 100, 1)}

    def calibration_factor(self, db: Session, *, engine: str, confidence: float) -> float:
        """Scale raw confidence toward historical actual win rate in the same band."""
        preds = _resolved_query(db).all()
        if engine == "technical":
            preds = [p for p in preds if _engine_label(p.ai_model) == "technical"]
        else:
            preds = [p for p in preds if _engine_label(p.ai_model) == "ai"]
        if len(preds) < 8:
            return 1.0

        buckets = [(0, 40), (40, 60), (60, 80), (80, 101)]
        for lo, hi in buckets:
            if not (lo <= confidence < hi):
                continue
            group = [p for p in preds if lo <= p.confidence < hi]
            if len(group) < 5:
                return 1.0
            actual = sum(1 for p in group if _is_win(p.outcome)) / len(group)
            stated = sum(p.confidence for p in group) / len(group) / 100
            if stated <= 0.05:
                return 1.0
            factor = actual / stated
            return max(0.65, min(1.35, factor))
        return 1.0

    def calibrate_confidence(self, db: Session, *, engine: str, raw: float) -> float:
        factor = self.calibration_factor(db, engine=engine, confidence=raw)
        adjusted = raw * factor
        return round(max(35.0, min(92.0, adjusted)), 1)

    def build_learning_context(
        self,
        db: Session,
        *,
        ticker: str,
        horizon_label: str,
        engine: str = "ai",
    ) -> dict:
        global_s = self.global_stats(db)
        ticker_s = self.ticker_stats(db, ticker)
        horizon_s = self.horizon_stats(db, horizon_label)
        return {
            "global": global_s,
            "ticker": ticker_s,
            "horizon": horizon_s,
            "engine": engine,
            "summary_lines": self._format_lines(ticker, horizon_label, global_s, ticker_s, horizon_s, engine),
        }

    @staticmethod
    def _format_lines(
        ticker: str,
        horizon_label: str,
        global_s: dict,
        ticker_s: dict,
        horizon_s: dict,
        engine: str,
    ) -> list[str]:
        lines = []
        if global_s.get("resolved", 0) >= 10:
            lines.append(
                f"Platform-wide ({global_s['resolved']} resolved): {global_s['win_rate_pct']}% hit rate."
            )
            eng_key = "ai_win_rate_pct" if engine == "ai" else "technical_win_rate_pct"
            if global_s.get(eng_key) is not None:
                label = "AI" if engine == "ai" else "Technical bot"
                lines.append(f"{label} engine across all users: {global_s[eng_key]}% win rate.")
        if ticker_s.get("resolved", 0) >= 5:
            lines.append(f"{ticker.upper()} historical: {ticker_s['win_rate_pct']}% ({ticker_s['resolved']} resolved).")
        if horizon_s.get("resolved", 0) >= 5:
            lines.append(f"{horizon_label} horizon historical: {horizon_s['win_rate_pct']}% win rate.")
        if not lines:
            lines.append("Limited platform history — favor conservative confidence and tight stops.")
        return lines

    def signal_confidence_adjustment(self, signal_net_score: int) -> float:
        """Adjust confidence ± based on enhanced market signals (-50 to +50 typical)."""
        if signal_net_score >= 20:
            return 8.0
        if signal_net_score >= 10:
            return 4.0
        if signal_net_score <= -20:
            return -10.0
        if signal_net_score <= -10:
            return -5.0
        return 0.0

    def horizon_buckets(self, db: Session, user_id=None) -> dict[str, dict]:
        q = db.query(Prediction).filter(
            Prediction.is_locked.is_(True),
            Prediction.outcome.notin_([PredictionOutcome.pending, PredictionOutcome.expired]),
        )
        if user_id:
            q = q.filter(Prediction.user_id == user_id)
        preds = q.all()
        buckets: dict[str, list] = defaultdict(list)
        for p in preds:
            label = (p.market_snapshot or {}).get("horizon_label") or f"{p.horizon_days}d"
            buckets[label].append(p)
        out = {}
        for label, group in buckets.items():
            wins = sum(1 for p in group if _is_win(p.outcome))
            out[label] = {
                "resolved": len(group),
                "win_rate_pct": round(wins / len(group) * 100, 1) if group else None,
            }
        return out
