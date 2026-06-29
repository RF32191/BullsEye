"""AI + momentum predictions on Polymarket/Kalshi contracts."""

import hashlib
import json
from datetime import datetime

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EventMarketPrediction, EventOutcome, EventPlatform, EventSide, User
from app.services.event_market_data import EventMarketDataService
from app.services.event_market_analytics import EventMarketAnalyticsService
from app.services.tokens import charge_tokens

EVENT_PREDICTION_COST = 150


class EventMarketPredictionService:
    def __init__(self):
        self.data = EventMarketDataService()
        self.analytics = EventMarketAnalyticsService()

    async def predict(
        self,
        db: Session,
        user: User,
        *,
        platform: str,
        external_id: str,
        horizon_days: int = 30,
    ) -> EventMarketPrediction:
        cost = EVENT_PREDICTION_COST
        if user.token_balance < cost:
            raise ValueError("Insufficient tokens for event market prediction")

        market = await self.data.get_market(platform, external_id)
        if not market:
            raise ValueError("Market not found")

        ai = await self._run_ai(market)
        side_raw = str(ai.get("side", "yes")).lower()
        if side_raw not in ("yes", "no"):
            side_raw = "yes"
        yes_price = market.get("yes_price") or 0.5

        pred = EventMarketPrediction(
            user_id=user.id,
            platform=EventPlatform(platform),
            external_id=external_id,
            question=market["question"],
            category=market.get("category") or "General",
            predicted_side=EventSide(side_raw),
            confidence=float(ai["confidence"]),
            yes_price_at_prediction=float(yes_price),
            target_yes_price=float(ai.get("target_yes_price", yes_price)),
            horizon_days=horizon_days,
            reasoning=ai["reasoning"],
            bull_case=ai.get("bull_case", ""),
            bear_case=ai.get("bear_case", ""),
            market_snapshot=market,
            content_hash=self._hash(market, {**ai, "ts": datetime.utcnow().isoformat()}),
            tokens_charged=cost,
            ai_model=settings.openai_model if settings.openai_api_key and not settings.mock_mode else "event-mock",
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=EventOutcome.pending,
        )
        db.add(pred)
        db.flush()
        charge_tokens(db, user, cost, reason="event_prediction", reference_id=str(pred.id))
        db.commit()
        db.refresh(pred)
        return pred

    async def predict_technical(
        self,
        db: Session,
        user: User,
        *,
        platform: str,
        external_id: str,
        horizon_days: int = 30,
    ) -> EventMarketPrediction:
        market = await self.data.get_market(platform, external_id)
        if not market:
            raise ValueError("Market not found")

        analysis = await self.analytics.analyze(platform, external_id)
        ai = self.analytics.technical_prediction(market, analysis)
        yes_price = float(market.get("yes_price") or 0.5)

        pred = EventMarketPrediction(
            user_id=user.id,
            platform=EventPlatform(platform),
            external_id=external_id,
            question=market["question"],
            category=market.get("category") or "General",
            predicted_side=EventSide(ai["side"]),
            confidence=float(ai["confidence"]),
            yes_price_at_prediction=yes_price,
            target_yes_price=float(ai["target_yes_price"]),
            horizon_days=horizon_days,
            reasoning=ai["reasoning"],
            bull_case=ai.get("bull_case", ""),
            bear_case=ai.get("bear_case", ""),
            market_snapshot={**market, "analytics": analysis},
            content_hash=self._hash(market, {**ai, "engine": "technical-bot"}),
            tokens_charged=0,
            ai_model="technical-bot",
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=EventOutcome.pending,
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)
        return pred

    async def _run_ai(self, market: dict) -> dict:
        yes = market.get("yes_price")
        prompt = (
            f"Prediction market on {market['platform']}:\n"
            f"Question: {market['question']}\n"
            f"Category: {market.get('category')}\n"
            f"Current Yes price: {yes}\n"
            f"Volume: {market.get('volume')}\n"
            f"End date: {market.get('end_date')}\n\n"
            "Respond JSON with: side (yes|no), confidence (0-100), target_yes_price (0-1), "
            "reasoning, bull_case, bear_case."
        )

        if settings.openai_api_key and not settings.mock_mode:
            try:
                client = OpenAI(api_key=settings.openai_api_key)
                resp = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a prediction market analyst for Polymarket/Kalshi."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.4,
                )
                return json.loads(resp.choices[0].message.content or "{}")
            except Exception:
                pass

        return self._heuristic(market)

    def _heuristic(self, market: dict) -> dict:
        yes_f = float(market.get("yes_price") or 0.5)
        side = "yes" if yes_f >= 0.5 else "no"
        conf = min(92, max(52, abs(yes_f - 0.5) * 200 + 55))
        return {
            "side": side,
            "confidence": round(conf, 1),
            "target_yes_price": round(min(0.95, max(0.05, yes_f + (0.08 if side == "yes" else -0.08))), 3),
            "reasoning": (
                f"Market prices Yes at {yes_f:.0%}. Volume ${market.get('volume', 0):,.0f}. "
                f"Momentum model leans {side.upper()} with category context ({market.get('category')})."
            ),
            "bull_case": f"Yes resolves if market consensus ({yes_f:.0%}) understates true probability.",
            "bear_case": f"Low liquidity or news shock could move odds sharply before resolution.",
        }

    @staticmethod
    def _hash(market: dict, ai: dict) -> str:
        payload = json.dumps({"market": market, "ai": ai}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def list_predictions(self, db: Session, user_id, limit: int = 50) -> list[EventMarketPrediction]:
        return (
            db.query(EventMarketPrediction)
            .filter(EventMarketPrediction.user_id == user_id, EventMarketPrediction.is_locked.is_(True))
            .order_by(EventMarketPrediction.created_at.desc())
            .limit(limit)
            .all()
        )

    def stats(self, db: Session, user_id) -> dict:
        preds = self.list_predictions(db, user_id, limit=500)
        resolved = [p for p in preds if p.outcome != EventOutcome.pending]
        wins = [p for p in resolved if p.outcome == EventOutcome.correct]
        return {
            "total": len(preds),
            "resolved": len(resolved),
            "win_rate_pct": round(len(wins) / len(resolved) * 100, 1) if resolved else None,
            "by_platform": {
                "polymarket": sum(1 for p in preds if p.platform == EventPlatform.polymarket),
                "kalshi": sum(1 for p in preds if p.platform == EventPlatform.kalshi),
            },
        }
