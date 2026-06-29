//
//  LocalAnalyticsStore.swift
//  Bullseye
//

import Foundation

struct LocalPredictionRecord: Codable, Identifiable, Sendable {
    let id: UUID
    let ticker: String
    let direction: String
    let confidence: Double
    let targetPrice: Double
    let priceAtPrediction: Double
    let outcome: String
    let returnPct: Double?
    let createdAt: Date
    var technicalRSI: Double?
    var technicalMACDHist: Double?
    var technicalSignal: String?
    var aiAgreesWithTechnical: Bool?
    var source: String?

    enum CodingKeys: String, CodingKey {
        case id, ticker, direction, confidence, outcome, source
        case targetPrice = "target_price"
        case priceAtPrediction = "price_at_prediction"
        case returnPct = "return_pct"
        case createdAt = "created_at"
        case technicalRSI = "technical_rsi"
        case technicalMACDHist = "technical_macd_hist"
        case technicalSignal = "technical_signal"
        case aiAgreesWithTechnical = "ai_agrees_with_technical"
    }
}

struct AccuracyTrendPoint: Identifiable, Sendable {
    let id = UUID()
    let date: Date
    let winRate: Double
    let count: Int
}

@Observable
@MainActor
final class LocalAnalyticsStore {
    static let shared = LocalAnalyticsStore()

    private let fileName = "prediction_analytics.json"
    private(set) var records: [LocalPredictionRecord] = []

    var resolvedCount: Int {
        records.filter { $0.outcome != "pending" }.count
    }

    var winRate: Double? {
        let resolved = records.filter { $0.outcome == "correct" || $0.outcome == "incorrect" || $0.outcome == "partial" }
        guard !resolved.isEmpty else { return nil }
        let wins = resolved.filter { $0.outcome == "correct" || $0.outcome == "partial" }.count
        return Double(wins) / Double(resolved.count) * 100
    }

    var accuracyTrend: [AccuracyTrendPoint] {
        let resolved = records
            .filter { $0.outcome != "pending" }
            .sorted { $0.createdAt < $1.createdAt }

        guard !resolved.isEmpty else { return [] }

        var points: [AccuracyTrendPoint] = []
        var wins = 0
        for (index, record) in resolved.enumerated() {
            if record.outcome == "correct" || record.outcome == "partial" { wins += 1 }
            points.append(AccuracyTrendPoint(
                date: record.createdAt,
                winRate: Double(wins) / Double(index + 1) * 100,
                count: index + 1
            ))
        }
        return points
    }

    private var fileURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(fileName)
    }

    func load() {
        guard let data = try? Data(contentsOf: fileURL),
              let decoded = try? JSONDecoder().decode([LocalPredictionRecord].self, from: data) else { return }
        records = decoded.sorted { $0.createdAt > $1.createdAt }
    }

    func save() {
        guard let data = try? JSONEncoder().encode(records) else { return }
        try? data.write(to: fileURL, options: .atomic)
    }

    func ingest(_ prediction: Prediction, technicals: TechnicalAnalysis? = nil, source: String? = nil) {
        let resolvedSource = source ?? (prediction.aiModel == "technical-bot" ? "technical" : "ai")
        let record = LocalPredictionRecord(
            id: prediction.id,
            ticker: prediction.ticker,
            direction: prediction.direction.rawValue,
            confidence: prediction.confidence,
            targetPrice: prediction.targetPrice,
            priceAtPrediction: prediction.priceAtPrediction,
            outcome: prediction.outcome.rawValue,
            returnPct: prediction.returnPct,
            createdAt: prediction.createdAt,
            technicalRSI: technicals?.rsi,
            technicalMACDHist: technicals?.macdHist,
            technicalSignal: technicals?.signal,
            aiAgreesWithTechnical: technicals.map { agrees(ai: prediction.direction.rawValue, technical: $0.signal) },
            source: resolvedSource
        )
        if let idx = records.firstIndex(where: { $0.id == record.id }) {
            records[idx] = record
        } else {
            records.insert(record, at: 0)
        }
        save()
    }

    func syncFromRailway() async {
        do {
            let remote = try await APIService.shared.fetchTracker()
            for prediction in remote {
                ingest(prediction)
            }
        } catch {
            // Keep local data if offline
        }
    }

    private func agrees(ai: String, technical: String) -> Bool {
        switch (ai, technical) {
        case ("bullish", "bullish"), ("bearish", "bearish"), ("neutral", "neutral"):
            return true
        default:
            return false
        }
    }
}
