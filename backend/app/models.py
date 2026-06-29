import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Direction(str, enum.Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"


class PredictionOutcome(str, enum.Enum):
    pending = "pending"
    correct = "correct"
    incorrect = "incorrect"
    partial = "partial"
    expired = "expired"


class SubscriptionTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    elite = "elite"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    token_balance: Mapped[int] = mapped_column(Integer, default=0)
    subscription_tier: Mapped[str] = mapped_column(String(16), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_daily_grant_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    daily_ai_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_chat_count: Mapped[int] = mapped_column(Integer, default=0)
    usage_reset_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    paper_cash_balance: Mapped[float] = mapped_column(Float, default=10_000.0)
    paper_starting_balance: Mapped[float] = mapped_column(Float, default=10_000.0)
    paper_realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="user")
    token_transactions: Mapped[list["TokenTransaction"]] = relationship(back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # negative = spend, positive = grant
    reason: Mapped[str] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="token_transactions")


class Prediction(Base):
    """Immutable ledger entry once is_locked=True. Outcome fields updated only by resolver."""

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    ticker: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str] = mapped_column(String(256))

    direction: Mapped[Direction] = mapped_column(Enum(Direction))
    confidence: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    horizon_days: Mapped[int] = mapped_column(Integer)

    price_at_prediction: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    bull_case: Mapped[str] = mapped_column(Text)
    bear_case: Mapped[str] = mapped_column(Text)

    # FMP snapshot + AI metadata frozen at prediction time
    market_snapshot: Mapped[dict] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    tokens_charged: Mapped[int] = mapped_column(Integer)
    ai_model: Mapped[str] = mapped_column(String(64))

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    outcome: Mapped[PredictionOutcome] = mapped_column(
        Enum(PredictionOutcome), default=PredictionOutcome.pending
    )
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="predictions")

    __table_args__ = (UniqueConstraint("content_hash", name="uq_prediction_content_hash"),)


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(256), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),)


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str] = mapped_column(String(256))
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True
    )
    direction: Mapped[str] = mapped_column(String(16))
    entry_price: Mapped[float] = mapped_column(Float)
    shares: Mapped[float] = mapped_column(Float)
    notional: Mapped[float] = mapped_column(Float, default=1000.0)
    source: Mapped[str] = mapped_column(String(32), default="prediction")
    live_trade_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EventPlatform(str, enum.Enum):
    polymarket = "polymarket"
    kalshi = "kalshi"


class EventSide(str, enum.Enum):
    yes = "yes"
    no = "no"


class EventOutcome(str, enum.Enum):
    pending = "pending"
    correct = "correct"
    incorrect = "incorrect"
    expired = "expired"


class EventMarketPrediction(Base):
    __tablename__ = "event_market_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    platform: Mapped[EventPlatform] = mapped_column(Enum(EventPlatform))
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    predicted_side: Mapped[EventSide] = mapped_column(Enum(EventSide))
    confidence: Mapped[float] = mapped_column(Float)
    yes_price_at_prediction: Mapped[float] = mapped_column(Float)
    target_yes_price: Mapped[float] = mapped_column(Float)
    horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    reasoning: Mapped[str] = mapped_column(Text)
    bull_case: Mapped[str] = mapped_column(Text)
    bear_case: Mapped[str] = mapped_column(Text)
    market_snapshot: Mapped[dict] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    tokens_charged: Mapped[int] = mapped_column(Integer)
    ai_model: Mapped[str] = mapped_column(String(64))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[EventOutcome] = mapped_column(Enum(EventOutcome), default=EventOutcome.pending)
    resolved_yes_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CategoryWatch(Base):
    __tablename__ = "category_watches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(16))
    category_slug: Mapped[str] = mapped_column(String(64))
    category_label: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "platform", "category_slug", name="uq_category_watch"),)


class AssetClass(str, enum.Enum):
    futures = "futures"
    crypto = "crypto"
    forex = "forex"


class AssetOutcome(str, enum.Enum):
    pending = "pending"
    correct = "correct"
    incorrect = "incorrect"
    partial = "partial"
    expired = "expired"


class AssetMarketPrediction(Base):
    __tablename__ = "asset_market_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass))
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    direction: Mapped[Direction] = mapped_column(Enum(Direction))
    confidence: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    horizon_days: Mapped[int] = mapped_column(Integer)
    price_at_prediction: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    bull_case: Mapped[str] = mapped_column(Text)
    bear_case: Mapped[str] = mapped_column(Text)
    market_snapshot: Mapped[dict] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    tokens_charged: Mapped[int] = mapped_column(Integer)
    ai_model: Mapped[str] = mapped_column(String(64))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[AssetOutcome] = mapped_column(Enum(AssetOutcome), default=AssetOutcome.pending)
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
