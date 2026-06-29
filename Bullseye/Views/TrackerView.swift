//
//  TrackerView.swift
//  Bullseye
//

import SwiftUI

struct TrackerView: View {
    @State private var predictions: [Prediction] = []
    @State private var stats: TrackerStats?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                headerSection
                if let stats { statsSection(stats) }
                if isLoading {
                    ProgressView().tint(BullseyeTheme.neonGreen).frame(maxWidth: .infinity)
                }
                ForEach(predictions) { prediction in
                    PredictionTrackerRow(prediction: prediction)
                }
                if predictions.isEmpty && !isLoading {
                    emptyState
                }
            }
            .padding(20)
        }
        .navigationTitle("Prediction Tracker")
        .refreshable { await load() }
        .task { await load() }
        .task { await LocalAnalyticsStore.shared.syncFromRailway() }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Immutable Ledger")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("AI-free tracker. Predictions lock to Railway PostgreSQL and cannot be edited.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    private func statsSection(_ stats: TrackerStats) -> some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                StatPill(title: "Total", value: "\(stats.totalPredictions)")
                StatPill(
                    title: "Win Rate",
                    value: stats.winRate.map { String(format: "%.0f%%", $0) } ?? "—"
                )
                StatPill(
                    title: "Avg Return",
                    value: stats.averageReturnPct.map { String(format: "%+.1f%%", $0) } ?? "—"
                )
            }
            HStack(spacing: 12) {
                directionPill("Bullish", stats.accuracyByDirection["bullish"])
                directionPill("Bearish", stats.accuracyByDirection["bearish"])
                directionPill("Neutral", stats.accuracyByDirection["neutral"])
            }
        }
    }

    private func directionPill(_ title: String, _ score: Double?) -> some View {
        StatPill(
            title: title,
            value: score.map { String(format: "%.0f%%", $0 * 100) } ?? "—"
        )
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "lock.doc")
                .font(.largeTitle)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text("No locked predictions yet")
                .foregroundStyle(BullseyeTheme.textSecondary)
            Text("Run an AI prediction to record it here.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let preds = APIService.shared.fetchTracker()
            async let st = APIService.shared.fetchTrackerStats()
            predictions = try await preds
            stats = try await st
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct StatPill: View {
    let title: String
    let value: String

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(title)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .glassCard(cornerRadius: 12)
    }
}

private struct PredictionTrackerRow: View {
    let prediction: Prediction

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(prediction.ticker)
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text(prediction.direction.rawValue.capitalized)
                    .font(.caption.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
                Spacer()
                outcomeBadge
            }

            HStack {
                Label("\(Int(prediction.confidence))%", systemImage: "gauge")
                Spacer()
                Text(prediction.createdAt.formatted(date: .abbreviated, time: .omitted))
            }
            .font(.caption)
            .foregroundStyle(BullseyeTheme.textSecondary)

            HStack {
                Text("Entry \(Formatters.currency(prediction.priceAtPrediction))")
                Spacer()
                if let actual = prediction.actualPrice {
                    Text("Exit \(Formatters.currency(actual))")
                } else {
                    Text("\(prediction.horizonDays)d horizon")
                }
            }
            .font(.caption)
            .foregroundStyle(BullseyeTheme.textTertiary)

            if prediction.isLocked {
                HStack(spacing: 4) {
                    Image(systemName: "lock.fill")
                    Text("Locked")
                }
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.neonGreenMuted)
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }

    @ViewBuilder
    private var outcomeBadge: some View {
        let (label, color): (String, Color) = switch prediction.outcome {
        case .pending: ("Pending", .yellow)
        case .correct: ("Correct", BullseyeTheme.neonGreen)
        case .incorrect: ("Incorrect", .red)
        case .partial: ("Partial", .orange)
        case .expired: ("Expired", BullseyeTheme.textTertiary)
        }
        Text(label)
            .font(.caption2.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.15))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}
