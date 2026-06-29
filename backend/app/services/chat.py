import json
import re
from datetime import datetime

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ChatMessage, ChatRole, ChatSession, Prediction, User
from app.services.market_data import MarketDataService
from app.services.prediction_accuracy import PredictionAccuracyService
from app.services.money_flow import MoneyFlowService
from app.services.tokens import charge_tokens

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")
ACCURACY_KEYWORDS = {"trend", "accuracy", "performance", "win rate", "track record", "how accurate", "predictions"}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "label": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["source", "label", "detail"],
                "additionalProperties": False,
            },
        },
        "session_title": {"type": "string"},
    },
    "required": ["reply", "citations", "session_title"],
    "additionalProperties": False,
}


class ChatService:
    def __init__(self):
        self.market = MarketDataService()
        self.accuracy = PredictionAccuracyService()
        self.flow = MoneyFlowService()
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def list_sessions(self, db: Session, user_id) -> list[tuple[ChatSession, int]]:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .all()
        )
        result = []
        for session in sessions:
            count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
            result.append((session, count))
        return result

    def get_messages(self, db: Session, user_id, session_id) -> list[ChatMessage]:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            return []
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    async def send_message(
        self, db: Session, user: User, message: str, session_id=None
    ) -> tuple[ChatSession, ChatMessage, ChatMessage, int]:
        cost = settings.tokens_per_chat_message
        if user.token_balance < cost:
            raise ValueError("Insufficient tokens")

        session = self._get_or_create_session(db, user, session_id, message)
        context = await self._build_context(db, user, message)

        user_msg = ChatMessage(
            session_id=session.id,
            role=ChatRole.user,
            content=message,
            tokens_used=0,
        )
        db.add(user_msg)
        db.flush()

        ai_payload = await self._generate_reply(db, message, context, session)
        assistant_msg = ChatMessage(
            session_id=session.id,
            role=ChatRole.assistant,
            content=ai_payload["reply"],
            citations=ai_payload["citations"],
            tokens_used=cost,
        )
        db.add(assistant_msg)

        if session.title == "New Chat" and ai_payload.get("session_title"):
            session.title = ai_payload["session_title"][:256]

        session.updated_at = datetime.utcnow()
        db.flush()

        charge_tokens(db, user, cost, reason="ai_chat", reference_id=str(assistant_msg.id))
        db.refresh(session)
        db.refresh(user_msg)
        db.refresh(assistant_msg)
        return session, user_msg, assistant_msg, user.token_balance

    def _get_or_create_session(
        self, db: Session, user: User, session_id, first_message: str
    ) -> ChatSession:
        if session_id:
            session = (
                db.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
                .first()
            )
            if session:
                return session
            raise ValueError("Chat session not found")

        session = ChatSession(user_id=user.id, title="New Chat")
        db.add(session)
        db.flush()
        return session

    async def _build_context(self, db: Session, user: User, message: str) -> dict:
        tickers = self._extract_tickers(message)
        market_data = {}
        for ticker in tickers[:3]:
            try:
                market_data[ticker] = await self.market.build_analysis_snapshot(ticker)
                flow = await self.flow.analyze(ticker, horizon_value=1, horizon_unit="days")
                market_data[ticker]["money_flow"] = {
                    "action": flow.get("action"),
                    "flow_score": flow.get("flow_score"),
                    "reasoning": flow.get("reasoning"),
                    "enhanced_signals": flow.get("enhanced_signals"),
                }
            except Exception:
                continue

        predictions = (
            db.query(Prediction)
            .filter(Prediction.user_id == user.id, Prediction.is_locked.is_(True))
            .order_by(Prediction.created_at.desc())
            .limit(10)
            .all()
        )

        prediction_context = [
            {
                "ticker": p.ticker,
                "direction": p.direction.value,
                "confidence": p.confidence,
                "target_price": p.target_price,
                "outcome": p.outcome.value,
                "return_pct": p.return_pct,
                "ai_model": p.ai_model,
                "created_at": p.created_at.isoformat(),
            }
            for p in predictions
        ]

        ctx = {
            "market_data": market_data,
            "locked_predictions": prediction_context,
            "data_sources": ["Yahoo Finance", "Bullseye AI prediction ledger"],
        }

        lower = message.lower()
        if any(k in lower for k in ACCURACY_KEYWORDS):
            ctx["accuracy_report"] = self.accuracy.format_accuracy_for_chat(
                db, user.id, tickers or [p.ticker for p in predictions[:3]]
            )
            ctx["accuracy_trend"] = self.accuracy.daily_accuracy_trend(
                db, user.id, tickers[0] if tickers else None
            )

        return ctx

    async def _generate_reply(
        self, db: Session, message: str, context: dict, session: ChatSession
    ) -> dict:
        if settings.mock_mode or not self.client:
            market = context.get("market_data", {})
            ticker = next(iter(market), None)
            if not ticker:
                tickers = self._extract_tickers(message)
                ticker = tickers[0] if tickers else "the stock"

            quote = market.get(ticker, {}).get("quote", {}) if ticker in market else {}
            price = quote.get("price")
            change_pct = quote.get("changesPercentage")
            pe = quote.get("pe")
            beta = quote.get("beta")
            price_line = (
                f"Last price: ${float(price):.2f} ({float(change_pct):+.2f}%)"
                if price is not None and change_pct is not None
                else "Fetching live price from Yahoo Finance…"
            )
            fund_line = ""
            if pe is not None:
                fund_line += f"P/E: {float(pe):.1f} · "
            if beta is not None:
                fund_line += f"Beta: {float(beta):.2f}"

            accuracy_block = ""
            if context.get("accuracy_report"):
                accuracy_block = f"\n\nYour prediction track record:\n{context['accuracy_report']}\n"

            return {
                "reply": (
                    f"{ticker} outlook (Yahoo Finance)\n\n"
                    f"{price_line}\n"
                    f"{fund_line}\n\n"
                    f"• Check Trends tab for RSI, MACD, SMA50/200 charts.\n"
                    f"• AI Model: full analysis in Predict tab (250 tokens).\n"
                    f"• Technical Bot: free, uses live Yahoo data.\n"
                    f"{accuracy_block}\n"
                    f"This is research only — not financial advice."
                ),
                "citations": [
                    {
                        "source": "Yahoo Finance",
                        "label": f"{ticker} live quote",
                        "detail": "Real-time price, volume, P/E, beta, 52-week range.",
                    },
                    {
                        "source": "Bullseye AI Ledger",
                        "label": "Locked predictions",
                        "detail": "Immutable prediction records with auto-resolved accuracy.",
                    },
                ],
                "session_title": message[:48],
            }

        prior = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(6)
            .all()
        )
        history = [{"role": m.role.value, "content": m.content} for m in prior]

        prompt = f"""You are Bullseye AI, a stock research assistant.
Answer using ONLY the context below. Cite specific sources in citations array.
If data is missing, say so clearly — never invent prices or filings.
When accuracy_report or accuracy_trend is present, explain win rates and daily accuracy clearly.

USER QUESTION:
{message}

CONTEXT:
{json.dumps(context, indent=2, default=str)}

CONVERSATION HISTORY:
{json.dumps(history, default=str)}
"""

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are Bullseye AI. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "chat_reply", "schema": CHAT_SCHEMA, "strict": True},
            },
            temperature=0.4,
        )
        return json.loads(response.choices[0].message.content)

    @staticmethod
    def _extract_tickers(message: str) -> list[str]:
        upper = message.upper()
        dollar = re.findall(r"\$([A-Z]{1,5})\b", upper)
        candidates = dollar + TICKER_PATTERN.findall(upper)
        stopwords = {
            "I", "A", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AI", "VS",
            "BUY", "SELL", "HOLD", "ETF", "IPO", "API", "USA", "NYSE", "USD",
            "CAN", "ALL", "ANY", "ARE", "WAS", "GET", "USE", "RUN", "TAB",
            "WHAT", "WHY", "HOW", "WHO", "WHEN", "WHERE", "IS", "IT", "IF",
            "MY", "ME", "WE", "DO", "SO", "UP", "AT", "BE", "BY", "AN",
        }
        return [t for t in dict.fromkeys(candidates) if t not in stopwords]
