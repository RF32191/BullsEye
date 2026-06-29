from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


IMMUTABLE_PREDICTION_TRIGGER = """
CREATE OR REPLACE FUNCTION prevent_locked_prediction_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_locked = TRUE THEN
        -- Only allow outcome resolution fields to change after lock
        IF NEW.ticker IS DISTINCT FROM OLD.ticker
           OR NEW.direction IS DISTINCT FROM OLD.direction
           OR NEW.confidence IS DISTINCT FROM OLD.confidence
           OR NEW.target_price IS DISTINCT FROM OLD.target_price
           OR NEW.stop_loss IS DISTINCT FROM OLD.stop_loss
           OR NEW.take_profit IS DISTINCT FROM OLD.take_profit
           OR NEW.horizon_days IS DISTINCT FROM OLD.horizon_days
           OR NEW.price_at_prediction IS DISTINCT FROM OLD.price_at_prediction
           OR NEW.reasoning IS DISTINCT FROM OLD.reasoning
           OR NEW.bull_case IS DISTINCT FROM OLD.bull_case
           OR NEW.bear_case IS DISTINCT FROM OLD.bear_case
           OR NEW.market_snapshot IS DISTINCT FROM OLD.market_snapshot
           OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
           OR NEW.tokens_charged IS DISTINCT FROM OLD.tokens_charged
           OR NEW.ai_model IS DISTINCT FROM OLD.ai_model
           OR NEW.is_locked IS DISTINCT FROM OLD.is_locked
           OR NEW.locked_at IS DISTINCT FROM OLD.locked_at THEN
            RAISE EXCEPTION 'Locked predictions are immutable on Railway ledger';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prediction_immutable ON predictions;
CREATE TRIGGER trg_prediction_immutable
    BEFORE UPDATE ON predictions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_locked_prediction_mutation();
"""


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(16) DEFAULT 'free'"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_ai_count INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_chat_count INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS usage_reset_date TIMESTAMP"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS paper_cash_balance DOUBLE PRECISION DEFAULT 10000"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS paper_starting_balance DOUBLE PRECISION DEFAULT 10000"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS paper_realized_pnl DOUBLE PRECISION DEFAULT 0"))
        conn.execute(text("ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS source VARCHAR(32) DEFAULT 'prediction'"))
        conn.execute(text("ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS live_trade_id VARCHAR(128)"))
        conn.execute(text("ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS close_price DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS realized_pnl_usd DOUBLE PRECISION"))
        conn.execute(text(IMMUTABLE_PREDICTION_TRIGGER))
        conn.commit()
