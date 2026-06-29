import json

from openai import OpenAI

from app.config import settings


PREDICTION_SCHEMA = {
    "type": "object",
    "properties": {
        "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 100},
        "target_price": {"type": "number"},
        "stop_loss": {"type": "number"},
        "take_profit": {"type": "number"},
        "reasoning": {"type": "string"},
        "bull_case": {"type": "string"},
        "bear_case": {"type": "string"},
    },
    "required": [
        "direction",
        "confidence",
        "target_price",
        "stop_loss",
        "take_profit",
        "reasoning",
        "bull_case",
        "bear_case",
    ],
    "additionalProperties": False,
}


class AIPredictor:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model

    async def predict(
        self,
        ticker: str,
        horizon_days: int,
        market_snapshot: dict,
        *,
        horizon_label: str | None = None,
        learning_context: dict | None = None,
    ) -> dict:
        label = horizon_label or f"{horizon_days} days"
        learning = learning_context or {}
        learning_text = "\n".join(f"- {line}" for line in learning.get("summary_lines", []))
        if settings.mock_mode or not self.client:
            price = float(market_snapshot.get("quote", {}).get("price", 100))
            return {
                "direction": "bullish",
                "confidence": 72.0,
                "target_price": round(price * 1.08, 2),
                "stop_loss": round(price * 0.94, 2),
                "take_profit": round(price * 1.12, 2),
                "reasoning": (
                    f"Based on Yahoo Finance live data and momentum for {ticker.upper()}, "
                    f"technicals and fundamentals lean modestly bullish over {label}."
                ),
                "bull_case": "Strong balance sheet, positive sector trends, and upward price momentum.",
                "bear_case": "Macro headwinds and valuation compression could limit upside.",
            }

        prompt = f"""You are Bullseye AI, an institutional stock analyst.
Analyze {ticker.upper()} for a {label} horizon using ONLY the market data below.
Return a directional prediction with explainable bull and bear cases.
Cite specific data points from the snapshot in your reasoning.

PLATFORM LEARNING (all users, resolved predictions — use to calibrate confidence, not override data):
{learning_text}

MARKET DATA (Yahoo Finance + technicals + enhanced signals):
{json.dumps(market_snapshot, indent=2, default=str)}

Rules:
- direction must be bullish, bearish, or neutral
- confidence is 0-100; be conservative when platform history underperforms at this horizon
- if enhanced signals contradict your direction, lower confidence by 10-20 points
- target_price, stop_loss, take_profit must be realistic vs current price for {label}
- Every claim must reference data from the snapshot
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a quantitative equity analyst. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "stock_prediction", "schema": PREDICTION_SCHEMA, "strict": True},
            },
            temperature=0.2,
        )

        content = response.choices[0].message.content
        return json.loads(content)
