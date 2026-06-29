//
//  APIModels.swift
//  Bullseye
//

import Foundation

struct UserProfile: Codable, Sendable {
    let id: UUID
    let deviceId: String
    let tokenBalance: Int
    let subscriptionTier: String?
}

struct TokenBalance: Codable, Sendable {
    let balance: Int
    let costPerPrediction: Int
    let costPerChatMessage: Int
}

struct StockSearchResult: Codable, Identifiable, Sendable {
    var id: String { symbol }
    let symbol: String
    let name: String
    let exchange: String?
    let currency: String?
}

struct StockQuote: Codable, Sendable {
    let symbol: String
    let name: String
    let price: Double
    let change: Double
    let changePct: Double
    let marketCap: Double?
    let peRatio: Double?
}

enum PredictionDirection: String, Codable, Sendable {
    case bullish, bearish, neutral
}

enum PredictionOutcome: String, Codable, Sendable {
    case pending, correct, incorrect, partial, expired
}

struct Prediction: Codable, Identifiable, Sendable {
    let id: UUID
    let ticker: String
    let companyName: String
    let direction: PredictionDirection
    let confidence: Double
    let targetPrice: Double
    let stopLoss: Double
    let takeProfit: Double
    let horizonDays: Int
    let horizonMinutes: Int?
    let horizonLabel: String?
    let priceAtPrediction: Double
    let reasoning: String
    let bullCase: String
    let bearCase: String
    let tokensCharged: Int
    let aiModel: String?
    let isLocked: Bool
    let lockedAt: Date?
    let outcome: PredictionOutcome
    let actualPrice: Double?
    let returnPct: Double?
    let resolvedAt: Date?
    let createdAt: Date
    let analysisFactors: [AnalysisFactor]?
}

struct AnalysisFactor: Codable, Identifiable, Sendable {
    var id: String { category + label + value }
    let category: String
    let label: String
    let value: String
    let impact: String
}

struct DailyAccuracyPoint: Codable, Identifiable, Sendable {
    var id: String { date }
    let date: String
    let dayWinRatePct: Double
    let cumulativeWinRatePct: Double
    let predictionsCount: Int
}

struct TrackerStats: Codable, Sendable {
    let totalPredictions: Int
    let lockedPredictions: Int
    let resolvedPredictions: Int
    let winRate: Double?
    let averageReturnPct: Double?
    let accuracyByDirection: [String: Double]
}

struct ChatCitation: Codable, Sendable, Identifiable {
    var id: String { label + source }
    let source: String
    let label: String
    let detail: String
}

struct ChatSession: Codable, Identifiable, Sendable {
    let id: UUID
    let title: String
    let createdAt: Date
    let updatedAt: Date
    let messageCount: Int
}

struct ChatMessage: Codable, Identifiable, Sendable {
    let id: UUID
    let sessionId: UUID
    let role: String
    let content: String
    let citations: [ChatCitation]?
    let tokensUsed: Int
    let createdAt: Date

    var isUser: Bool { role == "user" }
}

struct SendChatResponse: Codable, Sendable {
    let sessionId: UUID
    let userMessage: ChatMessage
    let assistantMessage: ChatMessage
    let tokenBalance: Int
}

struct HealthResponse: Codable, Sendable {
    let status: String
    let mockMode: Bool
}

struct CongressTrade: Codable, Identifiable, Sendable {
    let id: String
    let memberName: String
    let memberSlug: String
    let party: String?
    let chamber: String?
    let ticker: String
    let assetDescription: String
    let transactionType: String
    let transactionDate: String?
    let disclosureDate: String?
    let amountMin: Double?
    let amountMax: Double?
    let amountLabel: String
    let owner: String?
    let conflictScore: Double
    let sourceUrl: String?
    let returnSinceDisclosurePct: Double?
    let returnSinceTradePct: Double?
    let tradeOutcome: String?
    let priceAtTrade: Double?
    let priceAtDisclosure: Double?
    let currentPrice: Double?
    let latestPredictionDirection: String?
    let latestPredictionConfidence: Double?

    var isPurchase: Bool { transactionType == "purchase" }
    var isSale: Bool { transactionType == "sale" }

    var partyLabel: String? {
        switch party?.uppercased() {
        case "D": "Democrat"
        case "R": "Republican"
        case "I": "Independent"
        default: party
        }
    }
}

struct CongressTradesResponse: Codable, Sendable {
    let trades: [CongressTrade]
    let total: Int
    let page: Int
    let perPage: Int
    let hasMore: Bool
    let dataSource: String
    let isMock: Bool
    let disclaimer: String
}

struct InsiderTrade: Codable, Identifiable, Sendable {
    let id: String
    let symbol: String
    let reportingName: String
    let reportingTitle: String?
    let transactionType: String
    let securitiesTransacted: Double?
    let price: Double?
    let transactionDate: String?
    let filingDate: String?
    let securitiesOwned: Double?
    let returnSinceTradePct: Double?
    let tradeOutcome: String?
    let currentPrice: Double?
}

struct InsiderTradesResponse: Codable, Sendable {
    let trades: [InsiderTrade]
    let total: Int
    let page: Int
    let perPage: Int
    let hasMore: Bool
    let dataSource: String
    let isMock: Bool
    let disclaimer: String
}

struct WatchlistItem: Codable, Identifiable, Sendable {
    let id: UUID
    let ticker: String
    let companyName: String
    let category: String?
    let createdAt: Date

    var categoryLabel: String { category ?? "stocks" }
}

struct PaperPosition: Codable, Identifiable, Sendable {
    let id: String
    let ticker: String
    let companyName: String
    let direction: String
    let entryPrice: Double
    let currentPrice: Double
    let shares: Double
    let notional: Double
    let pnlPct: Double
    let pnlUsd: Double
    let realizedPnlUsd: Double?
    let source: String?
    let predictionId: String?
    let liveTradeId: String?
    let openedAt: String
    let closedAt: String?
    let isOpen: Bool
}

struct PaperAccount: Codable, Sendable {
    let cashBalance: Double
    let startingBalance: Double
    let investedOpen: Double
    let equity: Double
    let unrealizedPnlUsd: Double
    let realizedPnlUsd: Double
    let totalPnlUsd: Double
    let totalReturnPct: Double
    let openPositions: Int
    let closedPositions: Int
    let closedWinRatePct: Double?
}

struct PaperPortfolioSummary: Codable, Sendable {
    let openPositions: Int
    let totalNotional: Double
    let totalPnlUsd: Double
    let totalPnlPct: Double
}

struct PaperPortfolioResponse: Codable, Sendable {
    let positions: [PaperPosition]
    let summary: PaperPortfolioSummary
    let account: PaperAccount
}

struct EngineStats: Codable, Sendable {
    let total: Int
    let resolved: Int
    let winRatePct: Double?
}

struct CalibrationBucket: Codable, Identifiable, Sendable {
    var id: String { confidenceBand }
    let confidenceBand: String
    let predictions: Int
    let actualWinRatePct: Double
    let avgStatedConfidence: Double
}

struct AccuracyDashboard: Codable, Sendable {
    let overall: EngineStats
    let aiEngine: EngineStats
    let technicalEngine: EngineStats
    let byHorizon: [String: EngineStats]
    let accuracyByDirection: [String: Double]
    let calibration: [CalibrationBucket]
}

struct UsageLimits: Codable, Sendable {
    let tier: String
    let dailyAiUsed: Int
    let dailyAiLimit: Int?
    let dailyChatUsed: Int
    let dailyChatLimit: Int?
    let watchlistLimit: Int
}

struct TokenPackCatalogItem: Codable, Identifiable, Sendable {
    let id: String
    let productId: String
    let label: String
    let tokens: Int
    let priceUsd: Double
    let subtitle: String
}

struct SubscriptionCatalogItem: Codable, Identifiable, Sendable {
    let id: String
    let productId: String
    let tier: String
    let label: String
    let priceUsd: Double
    let period: String
}

struct PurchaseCatalog: Codable, Sendable {
    let tokenPacks: [TokenPackCatalogItem]
    let subscriptions: [SubscriptionCatalogItem]
}

struct TokenPurchaseResponse: Codable, Sendable {
    let balance: Int
    let tokensGranted: Int
    let packId: String
    let message: String
}

struct PublicStats: Codable, Sendable {
    let totalPredictions: Int
    let resolvedPredictions: Int
    let overallWinRatePct: Double?
    let aiWinRatePct: Double?
    let technicalWinRatePct: Double?
}

struct EventMarket: Codable, Identifiable, Sendable {
    var id: String { "\(platform)-\(externalId)" }
    let platform: String
    let externalId: String
    let slug: String?
    let question: String
    let category: String
    let yesPrice: Double?
    let noPrice: Double?
    let volume: Double
    let liquidity: Double
    let endDate: String?
    let active: Bool
    let imageUrl: String?

    var platformLabel: String {
        platform == "kalshi" ? "Kalshi" : "Polymarket"
    }
}

struct EventTrader: Codable, Identifiable, Sendable {
    let id: String
    let username: String
    let platform: String
    let winRatePct: Double?
    let totalTrades: Int?
    let pnlUsd: Double
    let volumeUsd: Double?
    let specialty: String
    let rank: Int
    let proxyWallet: String?
    let verified: Bool?
    let xUsername: String?
    let isActive: Bool?
    let recentLiveTrade: TraderLiveTrade?
}

struct TraderLiveTrade: Codable, Sendable {
    let title: String
    let side: String?
    let sizeUsd: Double?
    let timestamp: Int?
}

struct TraderStrategy: Codable, Sendable {
    let specialty: String?
    let styleLabel: String?
    let focusCategories: [String]?
    let yesBiasPct: Double?
    let avgBetUsd: Double?
    let winRatePct: Double?
    let summary: String?
}

struct EventTraderDetail: Codable, Sendable {
    let id: String
    let username: String
    let platform: String
    let winRatePct: Double?
    let totalTrades: Int?
    let pnlUsd: Double
    let volumeUsd: Double?
    let specialty: String
    let rank: Int?
    let proxyWallet: String?
    let verified: Bool?
    let recentActivity: [TraderActivityItem]
    let closedPositions: [TraderClosedPosition]
    let liveTrades: [TraderLiveTradeItem]?
    let strategy: TraderStrategy?
    let isActive: Bool?
}

struct TraderLiveTradeItem: Codable, Identifiable, Sendable {
    var id: String { (title) + String(timestamp ?? 0) }
    let type: String?
    let title: String
    let side: String?
    let sizeUsd: Double?
    let timestamp: Int?
    let isLive: Bool?
}

struct TraderActivityItem: Codable, Sendable {
    let type: String
    let title: String
    let size: Double?
    let usdcSize: Double?
    let timestamp: Int?
    let side: String?
}

struct TraderClosedPosition: Codable, Identifiable, Sendable {
    var id: String { title + (outcome ?? "") }
    let title: String
    let outcome: String?
    let avgPrice: Double?
    let curPrice: Double?
    let pnlUsd: Double?
    let outcomeResult: String?
    let endDate: String?
}

struct PoliticianSummary: Codable, Identifiable, Sendable {
    var id: String { memberSlug }
    let memberSlug: String
    let memberName: String
    let party: String?
    let chamber: String?
    let totalTrades: Int
    let trackedTrades: Int
    let winRatePct: Double?
    let avgReturnSinceTradePct: Double?
    let recentTrades: [CongressTrade]
}

struct PoliticianProfile: Codable, Sendable {
    let memberSlug: String
    let memberName: String
    let party: String?
    let chamber: String?
    let totalTrades: Int
    let winRatePct: Double?
    let wins: Int
    let losses: Int
    let avgReturnSinceTradePct: Double?
    let trades: [CongressTrade]
    let disclaimer: String
}

struct FlowComponent: Codable, Identifiable, Sendable {
    var id: String { label + value }
    let label: String
    let value: String
    let impact: String
    let score: Double
}

struct FlowAnalysis: Codable, Sendable {
    let ticker: String
    let companyName: String
    let price: Double
    let action: String
    let flowScore: Double
    let congressNetUsd: Double
    let insiderNetUsd: Double
    let volumeRatio: Double?
    let technicalSignal: String
    let rsi: Double
    let macdHist: Double
    let horizonMinutes: Int
    let horizonDays: Int
    let horizonLabel: String
    let suggestedTarget: Double
    let suggestedStop: Double
    let timingNote: String
    let reasoning: String
    let components: [FlowComponent]
    let enhancedSignals: EnhancedFlowSignals?
    let updatedAt: String
    let disclaimer: String
}

struct EnhancedFlowSignals: Codable, Sendable {
    let shortInterestPct: Double?
    let analystGradeBias: String?
    let institutionalNetChangePct: Double?
    let insiderClusterBuys: Int?
    let sectorRelativeStrengthPct: Double?
    let nextEarningsDate: String?
    let intraday: IntradaySnapshot?
    let dataSources: [String]?
}

struct IntradaySnapshot: Codable, Sendable {
    let available: Bool?
    let vwap: Double?
    let aboveVwap: Bool?
    let sessionChangePct: Double?
    let openingRangeBreakout: Bool?
}

struct MacroDashboard: Codable, Sendable {
    let macroQuotes: [String: MacroQuote]
    let polymarketHot: [EventMarketCard]
    let kalshiHot: [EventMarketCard]
    let updatedAt: String
}

struct MacroQuote: Codable, Sendable {
    let symbol: String
    let name: String
    let price: Double?
    let changePct: Double?
}

struct EventMarketCard: Codable, Identifiable, Sendable {
    var id: String { externalId ?? question ?? UUID().uuidString }
    let question: String?
    let platform: String?
    let externalId: String?
    let yesPrice: Double?
    let volume: Double?
    let category: String?
}

struct CrossMarketLinks: Codable, Sendable {
    let ticker: String
    let linkedMarkets: [EventMarketCard]
    let themeMatches: [ThemeMatch]
    let updatedAt: String
}

struct ThemeMatch: Codable, Identifiable, Sendable {
    var id: String { keyword + (event.question ?? "") }
    let keyword: String
    let relatedTickers: [String]
    let event: EventMarketCard
}

struct ConflictItem: Codable, Identifiable, Sendable {
    var id: String { "\(memberSlug ?? memberName ?? "")-\(ticker)" }
    let memberName: String?
    let memberSlug: String?
    let ticker: String
    let transactionType: String?
    let amountLabel: String?
    let conflictScore: Double
    let chamber: String?
    let disclosureDate: String?
    let note: String
}

struct ConflictsFeed: Codable, Sendable {
    let conflicts: [ConflictItem]
    let updatedAt: String
}

struct UserWatches: Codable, Sendable {
    let politicianSlugs: [String]
    let whaleWallets: [String]
    let flowTickers: [String]
    let flowScorePushThreshold: Double
    let flowScorePullThreshold: Double
    let congressNetMinUsd: Double
}

struct UserWatchesUpdate: Codable, Sendable {
    var politicianSlugs: [String]?
    var whaleWallets: [String]?
    var flowTickers: [String]?
    var flowScorePushThreshold: Double?
    var flowScorePullThreshold: Double?
    var congressNetMinUsd: Double?
}

struct LiveTrade: Codable, Identifiable, Sendable {
    let id: String
    let marketType: String
    let actorType: String
    let actorName: String
    let actorId: String?
    let title: String
    let subtitle: String?
    let side: String?
    let ticker: String?
    let platform: String?
    let amountUsd: Double?
    let occurredAt: String?
    let disclosedAt: String?
    let timestamp: Int?
    let tradeOutcome: String?
    let returnSinceTradePct: Double?
    let conflictScore: Double?
    let pickScore: Double
    let pickReason: String?
    let isTopPick: Bool
    let yesPrice: Double?
    let category: String?
}

struct LiveTradesFeed: Codable, Sendable {
    let trades: [LiveTrade]
    let topPicks: [LiveTrade]
    let updatedAt: String
    let disclaimer: String
}

struct AssetMarketQuote: Codable, Identifiable, Sendable {
    var id: String { symbol }
    let assetClass: String
    let symbol: String
    let name: String
    let category: String
    let price: Double?
    let changePct: Double?
    let volume: Double?
}

struct AssetMarketCategory: Codable, Identifiable, Sendable {
    var id: String { slug }
    let slug: String
    let label: String
}

struct AssetMarketPrediction: Codable, Identifiable, Sendable {
    let id: UUID
    let assetClass: String
    let symbol: String
    let name: String
    let category: String
    let direction: String
    let confidence: Double
    let targetPrice: Double
    let stopLoss: Double
    let takeProfit: Double
    let horizonDays: Int
    let priceAtPrediction: Double
    let reasoning: String
    let bullCase: String
    let bearCase: String
    let tokensCharged: Int
    let aiModel: String
    let isLocked: Bool
    let outcome: String
    let createdAt: Date
}

struct AssetMarketStats: Codable, Sendable {
    let total: Int
    let resolved: Int
    let winRatePct: Double?
    let byClass: [String: Int]
}

struct EventMarketAnalytics: Codable, Sendable {
    let platform: String
    let externalId: String
    let question: String
    let category: String
    let yesPrice: Double?
    let noPrice: Double?
    let volume: Double
    let liquidity: Double
    let technicalSignal: String
    let technicalScore: Double
    let momentumScore: Double
    let volumeScore: Double
    let liquidityScore: Double
    let summary: String
}

struct EventMarketCompare: Codable, Sendable {
    let platform: String
    let externalId: String
    let question: String
    let category: String
    let yesPrice: Double?
    let noPrice: Double?
    let volume: Double
    let liquidity: Double
    let technicalSignal: String
    let technicalScore: Double
    let momentumScore: Double
    let volumeScore: Double
    let liquidityScore: Double
    let summary: String
    let aiSide: String
    let aiConfidence: Double
    let agreement: Bool
    let combinedScore: Double
    let comparisonSummary: String
}

struct EventMarketPrediction: Codable, Identifiable, Sendable {
    let id: UUID
    let platform: String
    let externalId: String
    let question: String
    let category: String
    let predictedSide: String
    let confidence: Double
    let yesPriceAtPrediction: Double
    let targetYesPrice: Double
    let horizonDays: Int
    let reasoning: String
    let bullCase: String
    let bearCase: String
    let tokensCharged: Int
    let aiModel: String
    let isLocked: Bool
    let outcome: String
    let createdAt: Date
}

struct EventMarketStats: Codable, Sendable {
    let total: Int
    let resolved: Int
    let winRatePct: Double?
    let byPlatform: [String: Int]
}

struct EventCategory: Codable, Identifiable, Sendable {
    var id: String { "\(platform)-\(slug)" }
    let slug: String
    let label: String
    let platform: String
}

struct CategoryWatch: Codable, Identifiable, Sendable {
    let id: UUID
    let platform: String
    let categorySlug: String
    let categoryLabel: String
    let createdAt: Date
}

struct APIErrorResponse: Codable {
    let detail: String
}

enum APIError: LocalizedError {
    case invalidResponse
    case server(String)
    case insufficientTokens
    case unreachable(String)
    case decoding(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: "Unexpected server response"
        case .server(let msg): msg
        case .insufficientTokens: "Not enough tokens. You receive 500 free tokens daily."
        case .unreachable(let msg): msg
        case .decoding(let msg): msg
        }
    }
}
