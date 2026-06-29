from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class Direction(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"


class PredictionOutcome(str, Enum):
    pending = "pending"
    correct = "correct"
    incorrect = "incorrect"
    partial = "partial"
    expired = "expired"


class RegisterRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    device_id: str
    token_balance: int
    subscription_tier: str = "free"

    model_config = {"from_attributes": True}


class SubscriptionUpdateRequest(BaseModel):
    tier: str = Field(pattern="^(free|pro|elite)$")


class SubscriptionResponse(BaseModel):
    tier: str
    device_id: str


class TokenPackCatalogItem(BaseModel):
    id: str
    product_id: str
    label: str
    tokens: int
    price_usd: float
    subtitle: str


class SubscriptionCatalogItem(BaseModel):
    id: str
    product_id: str
    tier: str
    label: str
    price_usd: float
    period: str


class PurchaseCatalogResponse(BaseModel):
    token_packs: list[TokenPackCatalogItem]
    subscriptions: list[SubscriptionCatalogItem]


class TokenPurchaseRequest(BaseModel):
    pack_id: str | None = None
    product_id: str | None = None
    transaction_id: str | None = Field(default=None, max_length=256)
    source: str = Field(default="app_store", pattern="^(app_store|dev)$")


class TokenPurchaseResponse(BaseModel):
    balance: int
    tokens_granted: int
    pack_id: str
    message: str


class SubscriptionPurchaseRequest(BaseModel):
    product_id: str | None = None
    tier: str | None = Field(default=None, pattern="^(pro|elite)$")
    transaction_id: str | None = Field(default=None, max_length=256)
    source: str = Field(default="app_store", pattern="^(app_store|dev)$")


class TokenBalanceResponse(BaseModel):
    balance: int
    cost_per_prediction: int
    cost_per_chat_message: int


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    currency: str | None = None


class StockQuoteResponse(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    market_cap: float | None = None
    pe_ratio: float | None = None


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    price: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    ema_12: float
    ema_26: float
    signal: str
    trend_pct_30d: float | None = None
    technical_score: float
    trend_label: str | None = None
    trend_arrow: str | None = None
    trend_strength: float | None = None
    trend_pct: float | None = None
    trend_summary: str | None = None
    volume: float | None = None
    avg_volume: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    pct_from_52w_high: float | None = None
    data_source: str = "Yahoo Finance"


class AnalysisFactorResponse(BaseModel):
    category: str
    label: str
    value: str
    impact: str


class DailyAccuracyPoint(BaseModel):
    date: str
    day_win_rate_pct: float
    cumulative_win_rate_pct: float
    predictions_count: int


class TrendPointResponse(BaseModel):
    date: str
    close: float
    volume: float | None = None


class IndicatorPointResponse(BaseModel):
    date: str
    rsi: float | None = None
    macd_hist: float | None = None


class UpcomingEventResponse(BaseModel):
    type: str
    title: str
    date: str
    description: str


class TrendResponse(BaseModel):
    symbol: str
    points: list[TrendPointResponse]
    technicals: TechnicalAnalysisResponse
    indicators: list[IndicatorPointResponse] = []
    events: list[UpcomingEventResponse] = []


class ComparisonResponse(BaseModel):
    symbol: str
    technical_signal: str
    ai_direction: str
    agreement: bool
    technical_score: float
    ai_confidence: float
    combined_score: float
    summary: str
    technicals: TechnicalAnalysisResponse


class PredictionRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    horizon_days: int | None = Field(default=None, ge=1, le=180)
    horizon_value: int | None = Field(default=None, ge=1)
    horizon_unit: str | None = Field(default=None, pattern="^(minutes|hours|days)$")


class FlowComponentResponse(BaseModel):
    label: str
    value: str
    impact: str
    score: float


class FlowAnalysisResponse(BaseModel):
    ticker: str
    company_name: str
    price: float
    action: str
    flow_score: float
    congress_net_usd: float
    insider_net_usd: float
    volume_ratio: float | None
    technical_signal: str
    rsi: float
    macd_hist: float
    horizon_minutes: int
    horizon_days: int
    horizon_label: str
    suggested_target: float
    suggested_stop: float
    timing_note: str
    reasoning: str
    components: list[FlowComponentResponse]
    enhanced_signals: dict | None = None
    updated_at: str
    disclaimer: str


class FlowPredictRequest(BaseModel):
    horizon_days: int | None = Field(default=None, ge=1, le=180)
    horizon_value: int | None = Field(default=30, ge=1)
    horizon_unit: str | None = Field(default="days", pattern="^(minutes|hours|days)$")
    engine: str = Field(default="technical", pattern="^(ai|technical)$")


class PredictionResponse(BaseModel):
    id: UUID
    ticker: str
    company_name: str
    direction: Direction
    confidence: float
    target_price: float
    stop_loss: float
    take_profit: float
    horizon_days: int
    horizon_minutes: int | None = None
    horizon_label: str | None = None
    price_at_prediction: float
    reasoning: str
    bull_case: str
    bear_case: str
    tokens_charged: int
    ai_model: str = "gpt-4o-mini"
    is_locked: bool
    locked_at: datetime | None
    outcome: PredictionOutcome
    actual_price: float | None
    return_pct: float | None
    resolved_at: datetime | None
    created_at: datetime
    analysis_factors: list[AnalysisFactorResponse] = []

    model_config = {"from_attributes": True}


class TrackerStatsResponse(BaseModel):
    total_predictions: int
    locked_predictions: int
    resolved_predictions: int
    win_rate: float | None
    average_return_pct: float | None
    accuracy_by_direction: dict[str, float]


class ResolveBatchResponse(BaseModel):
    resolved_count: int


class ChatCitation(BaseModel):
    source: str
    label: str
    detail: str


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[ChatCitation] | None = None
    tokens_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SendChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None


class SendChatResponse(BaseModel):
    session_id: UUID
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    token_balance: int


class CongressTradeResponse(BaseModel):
    id: str
    member_name: str
    member_slug: str
    party: str | None = None
    chamber: str | None = None
    ticker: str
    asset_description: str
    transaction_type: str
    transaction_date: str | None = None
    disclosure_date: str | None = None
    amount_min: float | None = None
    amount_max: float | None = None
    amount_label: str
    owner: str | None = None
    conflict_score: float = 0.0
    source_url: str | None = None
    return_since_disclosure_pct: float | None = None
    return_since_trade_pct: float | None = None
    trade_outcome: str | None = None
    price_at_trade: float | None = None
    price_at_disclosure: float | None = None
    current_price: float | None = None
    latest_prediction_direction: str | None = None
    latest_prediction_confidence: float | None = None


class CongressTradesListResponse(BaseModel):
    trades: list[CongressTradeResponse]
    total: int
    page: int
    per_page: int
    has_more: bool
    data_source: str
    is_mock: bool = False
    disclaimer: str


class CongressPoliticianSummaryResponse(BaseModel):
    member_slug: str
    member_name: str
    party: str | None = None
    chamber: str | None = None
    total_trades: int
    tracked_trades: int
    win_rate_pct: float | None = None
    avg_return_since_trade_pct: float | None = None
    recent_trades: list[CongressTradeResponse] = []


class CongressPoliticianProfileResponse(BaseModel):
    member_slug: str
    member_name: str
    party: str | None = None
    chamber: str | None = None
    total_trades: int
    win_rate_pct: float | None = None
    wins: int
    losses: int
    avg_return_since_trade_pct: float | None = None
    trades: list[CongressTradeResponse]
    disclaimer: str


class InsiderTradeResponse(BaseModel):
    id: str
    symbol: str
    reporting_name: str
    reporting_title: str | None = None
    transaction_type: str
    securities_transacted: float | None = None
    price: float | None = None
    transaction_date: str | None = None
    filing_date: str | None = None
    securities_owned: float | None = None
    return_since_trade_pct: float | None = None
    trade_outcome: str | None = None
    current_price: float | None = None


class InsiderTradesListResponse(BaseModel):
    trades: list[InsiderTradeResponse]
    total: int
    page: int
    per_page: int
    has_more: bool
    data_source: str
    is_mock: bool = False
    disclaimer: str


class WatchlistItemResponse(BaseModel):
    id: UUID
    ticker: str
    company_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    company_name: str | None = None


class PaperPositionResponse(BaseModel):
    id: str
    ticker: str
    company_name: str
    direction: str
    entry_price: float
    current_price: float
    shares: float
    notional: float
    pnl_pct: float
    pnl_usd: float
    realized_pnl_usd: float | None = None
    source: str = "prediction"
    prediction_id: str | None = None
    live_trade_id: str | None = None
    opened_at: str
    closed_at: str | None = None
    is_open: bool


class PaperAccountResponse(BaseModel):
    cash_balance: float
    starting_balance: float
    invested_open: float
    equity: float
    unrealized_pnl_usd: float
    realized_pnl_usd: float
    total_pnl_usd: float
    total_return_pct: float
    open_positions: int
    closed_positions: int
    closed_win_rate_pct: float | None = None


class PaperPortfolioResponse(BaseModel):
    positions: list[PaperPositionResponse]
    summary: dict
    account: PaperAccountResponse


class PaperOpenRequest(BaseModel):
    prediction_id: UUID
    notional: float = Field(default=1000.0, ge=50, le=50_000)


class PaperOpenFlowRequest(BaseModel):
    ticker: str
    direction: str = Field(default="push", pattern="^(push|pull|bullish|bearish)$")
    notional: float = Field(default=1000.0, ge=50, le=50_000)


class PaperOpenLiveRequest(BaseModel):
    ticker: str
    side: str = "BUY"
    notional: float = Field(default=500.0, ge=50, le=50_000)
    live_trade_id: str
    company_name: str | None = None


class PaperDepositRequest(BaseModel):
    amount: float = Field(ge=1, le=1_000_000)


class PaperResetRequest(BaseModel):
    amount: float = Field(default=10_000.0, ge=1000, le=1_000_000)


class SmartMoneyFeedResponse(BaseModel):
    trades: list[dict]
    top_picks: list[dict]
    breakdown: dict[str, int]
    updated_at: str | None = None
    disclaimer: str | None = None


class EngineStatsResponse(BaseModel):
    total: int
    resolved: int
    win_rate_pct: float | None = None


class CalibrationBucketResponse(BaseModel):
    confidence_band: str
    predictions: int
    actual_win_rate_pct: float
    avg_stated_confidence: float


class AccuracyDashboardResponse(BaseModel):
    overall: EngineStatsResponse
    ai_engine: EngineStatsResponse
    technical_engine: EngineStatsResponse
    by_horizon: dict[str, EngineStatsResponse]
    accuracy_by_direction: dict[str, float]
    calibration: list[CalibrationBucketResponse]


class UsageLimitsResponse(BaseModel):
    tier: str
    daily_ai_used: int
    daily_ai_limit: int | None = None
    daily_chat_used: int
    daily_chat_limit: int | None = None
    watchlist_limit: int


class PublicStatsResponse(BaseModel):
    total_predictions: int
    resolved_predictions: int
    overall_win_rate_pct: float | None = None
    ai_win_rate_pct: float | None = None
    technical_win_rate_pct: float | None = None


class EventMarketResponse(BaseModel):
    platform: str
    external_id: str
    slug: str | None = None
    question: str
    category: str
    yes_price: float | None = None
    no_price: float | None = None
    volume: float = 0
    liquidity: float = 0
    end_date: str | None = None
    active: bool = True
    image_url: str | None = None


class EventTraderResponse(BaseModel):
    id: str
    username: str
    platform: str
    win_rate_pct: float | None = None
    total_trades: int | None = None
    pnl_usd: float
    volume_usd: float | None = None
    specialty: str
    rank: int
    proxy_wallet: str | None = None
    verified: bool = False
    x_username: str | None = None
    is_active: bool = False
    recent_live_trade: dict | None = None


class EventTraderDetailResponse(EventTraderResponse):
    recent_activity: list[dict] = []
    closed_positions: list[dict] = []
    live_trades: list[dict] = []
    strategy: dict | None = None


class EventMarketPredictionRequest(BaseModel):
    platform: str = Field(pattern="^(polymarket|kalshi)$")
    external_id: str = Field(min_length=1, max_length=128)
    horizon_days: int = Field(default=30, ge=7, le=180)


class EventMarketPredictionResponse(BaseModel):
    id: UUID
    platform: str
    external_id: str
    question: str
    category: str
    predicted_side: str
    confidence: float
    yes_price_at_prediction: float
    target_yes_price: float
    horizon_days: int
    reasoning: str
    bull_case: str
    bear_case: str
    tokens_charged: int
    ai_model: str
    is_locked: bool
    outcome: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EventMarketStatsResponse(BaseModel):
    total: int
    resolved: int
    win_rate_pct: float | None = None
    by_platform: dict[str, int]


class CategoryWatchAddRequest(BaseModel):
    platform: str = Field(pattern="^(polymarket|kalshi)$")
    category_slug: str = Field(min_length=1, max_length=64)
    category_label: str = Field(min_length=1, max_length=128)


class CategoryWatchResponse(BaseModel):
    id: UUID
    platform: str
    category_slug: str
    category_label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LiveTradeResponse(BaseModel):
    id: str
    market_type: str
    actor_type: str
    actor_name: str
    actor_id: str | None = None
    title: str
    subtitle: str | None = None
    side: str | None = None
    ticker: str | None = None
    platform: str | None = None
    amount_usd: float | None = None
    occurred_at: str | None = None
    disclosed_at: str | None = None
    timestamp: int | None = None
    trade_outcome: str | None = None
    return_since_trade_pct: float | None = None
    conflict_score: float = 0
    pick_score: float = 0
    pick_reason: str | None = None
    is_top_pick: bool = False
    yes_price: float | None = None
    category: str | None = None


class LiveTradesFeedResponse(BaseModel):
    trades: list[LiveTradeResponse]
    top_picks: list[LiveTradeResponse]
    updated_at: str
    disclaimer: str


class AssetMarketQuoteResponse(BaseModel):
    asset_class: str
    symbol: str
    name: str
    category: str
    price: float | None = None
    change_pct: float | None = None
    volume: float | None = None


class AssetMarketCategoryResponse(BaseModel):
    slug: str
    label: str


class AssetMarketPredictionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    horizon_days: int = Field(default=30, ge=7, le=180)


class AssetMarketPredictionResponse(BaseModel):
    id: UUID
    asset_class: str
    symbol: str
    name: str
    category: str
    direction: str
    confidence: float
    target_price: float
    stop_loss: float
    take_profit: float
    horizon_days: int
    price_at_prediction: float
    reasoning: str
    bull_case: str
    bear_case: str
    tokens_charged: int
    ai_model: str
    is_locked: bool
    outcome: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetMarketStatsResponse(BaseModel):
    total: int
    resolved: int
    win_rate_pct: float | None = None
    by_class: dict[str, int]


class EventMarketAnalyticsResponse(BaseModel):
    platform: str
    external_id: str
    question: str
    category: str
    yes_price: float | None = None
    no_price: float | None = None
    volume: float = 0
    liquidity: float = 0
    technical_signal: str
    technical_score: float
    momentum_score: float
    volume_score: float
    liquidity_score: float
    summary: str


class EventMarketCompareResponse(EventMarketAnalyticsResponse):
    ai_side: str
    ai_confidence: float
    agreement: bool
    combined_score: float
    comparison_summary: str


class MacroQuoteResponse(BaseModel):
    symbol: str
    name: str
    price: float | None = None
    change_pct: float | None = None


class MacroDashboardResponse(BaseModel):
    macro_quotes: dict[str, MacroQuoteResponse]
    polymarket_hot: list[dict] = []
    kalshi_hot: list[dict] = []
    updated_at: str


class CrossMarketLinksResponse(BaseModel):
    ticker: str
    linked_markets: list[dict]
    theme_matches: list[dict]
    updated_at: str


class ConflictItemResponse(BaseModel):
    member_name: str | None = None
    member_slug: str | None = None
    ticker: str
    transaction_type: str | None = None
    amount_label: str | None = None
    conflict_score: float
    chamber: str | None = None
    disclosure_date: str | None = None
    note: str


class ConflictsResponse(BaseModel):
    conflicts: list[ConflictItemResponse]
    updated_at: str


class MarketSignalsResponse(BaseModel):
    ticker: str
    short_interest_pct: float | None = None
    analyst_grade_bias: str
    institutional_net_change_pct: float | None = None
    insider_cluster_buys: int
    sector_relative_strength_pct: float | None = None
    next_earnings_date: str | None = None
    intraday: dict
    signal_components: list[FlowComponentResponse]
    data_sources: list[str]


class CryptoSignalsResponse(BaseModel):
    symbol: str
    price: float | None = None
    change_pct_24h: float | None = None
    volume_ratio: float | None = None
    funding_proxy: str
    technical_signal: str | None = None
    rsi: float | None = None
    action: str
    top_movers: list[dict]
    note: str


class UserWatchesResponse(BaseModel):
    politician_slugs: list[str]
    whale_wallets: list[str]
    flow_tickers: list[str]
    flow_score_push_threshold: float
    flow_score_pull_threshold: float
    congress_net_min_usd: float


class UserWatchesUpdateRequest(BaseModel):
    politician_slugs: list[str] | None = None
    whale_wallets: list[str] | None = None
    flow_tickers: list[str] | None = None
    flow_score_push_threshold: float | None = None
    flow_score_pull_threshold: float | None = None
    congress_net_min_usd: float | None = None


class FlowPaperOpenRequest(BaseModel):
    ticker: str
    direction: str = Field(pattern="^(bullish|bearish|push|pull)$")
    notional: float = Field(default=1000.0, ge=100, le=100_000)

