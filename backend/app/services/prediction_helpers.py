"""Shared prediction outcome helpers (avoids circular imports)."""

from app.models import PredictionOutcome


def is_win(outcome: PredictionOutcome) -> bool:
    return outcome in (PredictionOutcome.correct, PredictionOutcome.partial)


def engine_label(ai_model: str | None) -> str:
    if ai_model and "technical" in ai_model.lower():
        return "technical"
    return "ai"
