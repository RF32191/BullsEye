"""AI predictions for futures, crypto, and forex."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AssetClass, AssetMarketPrediction, AssetOutcome, Direction, User
from app.services.asset_market_data import AssetMarketDataService
from app.services.analysis_factors import build_analysis_factors
from app.services.fmp import snapshot_hash
from app.services.market_analysis import MarketAnalysisService
from app.services.tokens import charge_tokens

ASSET_PREDICTION_COST = 150


class AssetMarketPredictionService:
    def __init__(self):
        self.data = AssetMarketDataService()
        self.analysis = MarketAnalysisService()

    async def predict(
        self,
        db: Session,
        user: User,
        *,
        asset_class: str,
        symbol: str,
        horizon_days: int = 30,
    ) -> AssetMarketPrediction:
        cost = ASSET_PREDICTION_COST
        if user.token_balance < cost:
            raise ValueError("Insufficient tokens for asset market prediction")

        row = await self.data.get_symbol(asset_class, symbol)
        if not row or row.get("price") is None:
            raise ValueError("Symbol not found or no price data")

        snapshot = await self.data.build_snapshot(asset_class, symbol.upper())
        ai = await self._run_ai(asset_class, symbol, horizon_days, snapshot)
        price = float(snapshot.get("quote", {}).get("price", row["price"]))

        pred = AssetMarketPrediction(
            user_id=user.id,
            asset_class=AssetClass(asset_class),
            symbol=symbol.upper(),
            name=row.get("name") or symbol.upper(),
            category=row.get("category") or "General",
            direction=Direction(ai["direction"]),
            confidence=float(ai["confidence"]),
            target_price=float(ai["target_price"]),
            stop_loss=float(ai["stop_loss"]),
            take_profit=float(ai["take_profit"]),
            horizon_days=horizon_days,
            price_at_prediction=price,
            reasoning=ai["reasoning"],
            bull_case=ai.get("bull_case", ""),
            bear_case=ai.get("bear_case", ""),
            market_snapshot=snapshot,
            content_hash=self._hash(asset_class, symbol, ai),
            tokens_charged=cost,
            ai_model=settings.openai_model if settings.openai_api_key and not settings.mock_mode else "asset-mock",
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=AssetOutcome.pending,
        )
        db.add(pred)
        db.flush()
        charge_tokens(db, user, cost, reason="asset_prediction", reference_id=str(pred.id))
        db.commit()
        db.refresh(pred)
        return pred

    async def predict_technical(
        self,
        db: Session,
        user: User,
        *,
        asset_class: str,
        symbol: str,
        horizon_days: int = 30,
    ) -> AssetMarketPrediction:
        sym = symbol.upper()
        row = await self.data.get_symbol(asset_class, sym)
        if not row or row.get("price") is None:
            raise ValueError("Symbol not found or no price data")

        technicals = await self.analysis.get_technicals(sym)
        price = float(technicals["price"])
        direction = Direction(technicals["signal"])
        confidence = float(technicals["technical_score"])
        move_pct = 0.05 if direction == Direction.bullish else -0.05 if direction == Direction.bearish else 0.02
        target = round(price * (1 + move_pct), 4)
        stop = round(price * (1 - abs(move_pct) * 1.2), 4)
        take = round(price * (1 + abs(move_pct) * 1.5), 4)
        if direction == Direction.bearish:
            target = round(price * (1 - abs(move_pct)), 4)
            stop = round(price * (1 + abs(move_pct) * 1.2), 4)
            take = round(price * (1 - abs(move_pct) * 1.5), 4)

        reasoning = (
            f"Technical bot (Yahoo Finance): {technicals['signal'].upper()} "
            f"(RSI {technicals['rsi']}, MACD hist {technicals['macd_hist']}). "
            f"Score {technicals['technical_score']}/100."
        )
        snapshot = await self.data.build_snapshot(asset_class, sym)
        snapshot["technicals"] = technicals
        snapshot["analysis_factors"] = build_analysis_factors(snapshot, technicals, direction.value)

        pred = AssetMarketPrediction(
            user_id=user.id,
            asset_class=AssetClass(asset_class),
            symbol=sym,
            name=row.get("name") or sym,
            category=row.get("category") or "General",
            direction=direction,
            confidence=confidence,
            target_price=target,
            stop_loss=stop,
            take_profit=take,
            horizon_days=horizon_days,
            price_at_prediction=price,
            reasoning=reasoning,
            bull_case=f"RSI/MACD support {technicals['signal']} over {horizon_days} days.",
            bear_case="Volatility spikes can override technical signals quickly.",
            market_snapshot=snapshot,
            content_hash=snapshot_hash(snapshot, {"engine": "technical-bot", "symbol": sym}),
            tokens_charged=0,
            ai_model="technical-bot",
            is_locked=True,
            locked_at=datetime.utcnow(),
            outcome=AssetOutcome.pending,
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)
        return pred

    async def compare(self, asset_class: str, symbol: str, ai_direction: str, ai_confidence: float) -> dict:
        result = await self.analysis.compare_ai_technical(symbol, ai_direction, ai_confidence)
        result["asset_class"] = asset_class
        return result

    async def _run_ai(self, asset_class: str, symbol: str, horizon_days: int, snapshot: dict) -> dict:
        labels = {
            "futures": "futures/commodities analyst",
            "crypto": "cryptocurrency analyst",
            "forex": "FX analyst",
        }
        price = float(snapshot.get("quote", {}).get("price", 100))
        prompt = (
            f"Analyze {symbol.upper()} ({asset_class}) for a {horizon_days}-day horizon.\n"
            f"Market data:\n{json.dumps(snapshot, indent=2, default=str)}\n\n"
            "Return JSON: direction (bullish|bearish|neutral), confidence (0-100), "
            "target_price, stop_loss, take_profit, reasoning, bull_case, bear_case."
        )

        if settings.openai_api_key and not settings.mock_mode:
            try:
                client = OpenAI(api_key=settings.openai_api_key)
                resp = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": f"You are a {labels.get(asset_class, 'market')} for Bullseye AI."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.4,
                )
                data = json.loads(resp.choices[0].message.content or "{}")
                if data.get("direction") in ("bullish", "bearish", "neutral"):
                    return data
            except Exception:
                pass

        return self._heuristic(asset_class, symbol, price, snapshot)

    def _heuristic(self, asset_class: str, symbol: str, price: float, snapshot: dict) -> dict:
        mom = snapshot.get("momentum_30d_pct") or 0
        direction = "bullish" if mom > 1 else "bearish" if mom < -1 else "neutral"
        mult = 1.06 if direction == "bullish" else 0.94 if direction == "bearish" else 1.0
        conf = min(88, max(55, 60 + abs(float(mom))))
        return {
            "direction": direction,
            "confidence": round(conf, 1),
            "target_price": round(price * mult, 4),
            "stop_loss": round(price * (0.96 if direction == "bullish" else 1.04), 4),
            "take_profit": round(price * (1.08 if direction == "bullish" else 0.92), 4),
            "reasoning": (
                f"{symbol.upper()} ({asset_class}) shows {mom:+.1f}% 30-day momentum. "
                f"Model leans {direction} based on Yahoo Finance price action."
            ),
            "bull_case": f"Trend continuation and volume support favor {direction} move.",
            "bear_case": f"Macro shock or volatility spike could reverse {asset_class} trend.",
        }

    @staticmethod
    def _hash(asset_class: str, symbol: str, ai: dict) -> str:
        payload = json.dumps({"class": asset_class, "symbol": symbol, "ai": ai}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def list_predictions(self, db: Session, user_id, asset_class: str | None = None, limit: int = 50) -> list[AssetMarketPrediction]:
        q = db.query(AssetMarketPrediction).filter(
            AssetMarketPrediction.user_id == user_id,
            AssetMarketPrediction.is_locked.is_(True),
        )
        if asset_class:
            q = q.filter(AssetMarketPrediction.asset_class == AssetClass(asset_class))
        return q.order_by(AssetMarketPrediction.created_at.desc()).limit(limit).all()

    def stats(self, db: Session, user_id, asset_class: str | None = None) -> dict:
        preds = self.list_predictions(db, user_id, asset_class=asset_class, limit=500)
        resolved = [p for p in preds if p.outcome != AssetOutcome.pending]
        wins = [p for p in resolved if p.outcome == AssetOutcome.correct]
        by_class = {c.value: 0 for c in AssetClass}
        for p in preds:
            by_class[p.asset_class.value] = by_class.get(p.asset_class.value, 0) + 1
        return {
            "total": len(preds),
            "resolved": len(resolved),
            "win_rate_pct": round(len(wins) / len(resolved) * 100, 1) if resolved else None,
            "by_class": by_class,
        }

    async def resolve_due(self, db: Session) -> int:
        now = datetime.utcnow()
        pending = (
            db.query(AssetMarketPrediction)
            .filter(AssetMarketPrediction.outcome == AssetOutcome.pending, AssetMarketPrediction.is_locked.is_(True))
            .limit(100)
            .all()
        )
        count = 0
        for pred in pending:
            due = pred.created_at + timedelta(days=pred.horizon_days)
            if now < due:
                continue
            try:
                q = await self.data.get_symbol(pred.asset_class.value, pred.symbol)
                actual = float(q.get("price") or pred.price_at_prediction)
            except Exception:
                continue
            pred.actual_price = actual
            pred.return_pct = round(((actual - pred.price_at_prediction) / pred.price_at_prediction) * 100, 2)
            if pred.direction == Direction.bullish:
                pred.outcome = AssetOutcome.correct if actual >= pred.target_price else AssetOutcome.incorrect
            elif pred.direction == Direction.bearish:
                pred.outcome = AssetOutcome.correct if actual <= pred.target_price else AssetOutcome.incorrect
            else:
                pred.outcome = AssetOutcome.partial
            pred.resolved_at = now
            count += 1
        if count:
            db.commit()
        return count
