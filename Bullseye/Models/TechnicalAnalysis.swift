//
//  TechnicalAnalysis.swift
//  Bullseye
//

import Foundation

struct TechnicalAnalysis: Codable, Sendable {
    let symbol: String
    let price: Double
    let rsi: Double
    let macd: Double
    let macdSignal: Double
    let macdHist: Double
    let ema12: Double
    let ema26: Double
    let signal: String
    let trendPct30d: Double?
    let technicalScore: Double?
    let trendLabel: String?
    let trendArrow: String?
    let trendStrength: Double?
    let trendPct: Double?
    let trendSummary: String?
    let volume: Double?
    let avgVolume: Double?
    let marketCap: Double?
    let peRatio: Double?
    let forwardPe: Double?
    let beta: Double?
    let fiftyTwoWeekHigh: Double?
    let fiftyTwoWeekLow: Double?
    let dividendYield: Double?
    let eps: Double?
    let sma50: Double?
    let sma200: Double?
    let pctFrom52wHigh: Double?
    let dataSource: String?
}

struct TrendPoint: Codable, Identifiable, Sendable {
    var id: String { date }
    let date: String
    let close: Double
    let volume: Double?
}

struct IndicatorPoint: Codable, Identifiable, Sendable {
    var id: String { date }
    let date: String
    let rsi: Double?
    let macdHist: Double?
}

struct UpcomingEvent: Codable, Identifiable, Sendable {
    var id: String { type + date + title }
    let type: String
    let title: String
    let date: String
    let description: String
}

struct TrendResponse: Codable, Sendable {
    let symbol: String
    let points: [TrendPoint]
    let technicals: TechnicalAnalysis
    let indicators: [IndicatorPoint]?
    let events: [UpcomingEvent]?
}

struct ComparisonAnalysis: Codable, Sendable {
    let symbol: String
    let technicalSignal: String
    let aiDirection: String
    let agreement: Bool
    let technicalScore: Double
    let aiConfidence: Double
    let combinedScore: Double
    let summary: String
    let technicals: TechnicalAnalysis
}

struct SubscriptionInfo: Codable, Sendable {
    let tier: String
    let deviceId: String
}
