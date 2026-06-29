//
//  AnalyticsView.swift
//  Bullseye
//

import Charts
import SwiftUI

struct AnalyticsView: View {
    @State private var store = LocalAnalyticsStore.shared
    @State private var serverAccuracy: [DailyAccuracyPoint] = []
    @State private var dashboard: AccuracyDashboard?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                header
                if let dashboard { accuracyDashboardSection(dashboard) }
                serverAccuracyChart
                accuracyChart
                recordsList
            }
            .padding(20)
        }
        .navigationTitle("Analytics")
        .refreshable {
            await store.syncFromRailway()
            store.load()
            await loadAll()
        }
        .task {
            store.load()
            await store.syncFromRailway()
            await loadAll()
        }
    }

    private func loadAll() async {
        serverAccuracy = (try? await APIService.shared.fetchAccuracyTrend()) ?? []
        dashboard = try? await APIService.shared.fetchAccuracyDashboard()
    }

    @ViewBuilder
    private func accuracyDashboardSection(_ dash: AccuracyDashboard) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Verified Accuracy Dashboard")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Scored from immutable Railway ledger · resolved by actual price + stop/target hits")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            HStack(spacing: 10) {
                engineCard("Overall", dash.overall)
                engineCard("AI Model", dash.aiEngine)
                engineCard("Technical", dash.technicalEngine)
            }

            if !dash.calibration.isEmpty {
                Text("Confidence Calibration")
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text("Does stated confidence match actual win rate?")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)

                Chart(dash.calibration) { bucket in
                    BarMark(
                        x: .value("Band", bucket.confidenceBand),
                        y: .value("Win %", bucket.actualWinRatePct)
                    )
                    .foregroundStyle(BullseyeTheme.neonGreen.opacity(0.8))
                }
                .frame(height: 140)
            }

            Text("By Horizon")
                .font(.subheadline.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            HStack(spacing: 10) {
                ForEach(["7", "30", "90"], id: \.self) { h in
                    if let stats = dash.byHorizon[h] {
                        engineCard("\(h)d", stats)
                    }
                }
            }

            Text("By Direction")
                .font(.subheadline.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            HStack(spacing: 10) {
                directionCard("Bullish", dash.accuracyByDirection["bullish"] ?? 0)
                directionCard("Bearish", dash.accuracyByDirection["bearish"] ?? 0)
                directionCard("Neutral", dash.accuracyByDirection["neutral"] ?? 0)
            }
        }
        .padding(16)
        .glassCard()
    }

    private func engineCard(_ title: String, _ stats: EngineStats) -> some View {
        VStack(spacing: 4) {
            Text(stats.winRatePct.map { String(format: "%.0f%%", $0) } ?? "—")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(title)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
            Text("\(stats.resolved)/\(stats.total)")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .glassCard(cornerRadius: 10)
    }

    private func directionCard(_ title: String, _ score: Double) -> some View {
        VStack(spacing: 4) {
            Text(String(format: "%.0f%%", score * 100))
                .font(.headline)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(title)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .glassCard(cornerRadius: 10)
    }

    @ViewBuilder
    private var serverAccuracyChart: some View {
        if !serverAccuracy.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Resolution Timeline")
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text("Grouped by resolve date — when outcomes were scored")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)

                Chart(serverAccuracy) { point in
                    LineMark(
                        x: .value("Date", point.date),
                        y: .value("Win Rate", point.cumulativeWinRatePct)
                    )
                    .foregroundStyle(BullseyeTheme.neonGreen)
                }
                .frame(height: 160)
            }
            .padding(16)
            .glassCard()
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Prediction Intelligence")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Local log + server-verified accuracy from locked predictions.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            HStack(spacing: 12) {
                statCard("Win Rate", store.winRate.map { String(format: "%.0f%%", $0) } ?? "—")
                statCard("Resolved", "\(store.resolvedCount)")
                statCard("Total", "\(store.records.count)")
            }
        }
    }

    private func statCard(_ title: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.headline).foregroundStyle(BullseyeTheme.neonGreen)
            Text(title).font(.caption2).foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .glassCard(cornerRadius: 12)
    }

    @ViewBuilder
    private var accuracyChart: some View {
        if !store.accuracyTrend.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Local Accuracy Trend")
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)

                Chart(store.accuracyTrend) { point in
                    LineMark(
                        x: .value("Date", point.date),
                        y: .value("Win Rate", point.winRate)
                    )
                    .foregroundStyle(BullseyeTheme.neonGreen)
                }
                .frame(height: 180)
            }
            .padding(16)
            .glassCard()
        }
    }

    private var recordsList: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Prediction Log")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            if store.records.isEmpty {
                Text("Run AI predictions to build your local accuracy database.")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            ForEach(store.records) { record in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(record.ticker).font(.headline).foregroundStyle(BullseyeTheme.textPrimary)
                        Text(record.direction.capitalized)
                            .font(.caption.bold())
                            .foregroundStyle(BullseyeTheme.neonGreen)
                        if let source = record.source {
                            Text(source == "technical" ? "Bot" : "AI")
                                .font(.caption2.bold())
                                .foregroundStyle(.black)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(source == "technical" ? Color.orange : BullseyeTheme.neonGreen)
                                .clipShape(Capsule())
                        }
                        Spacer()
                        Text(record.outcome.capitalized)
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                    }
                    if let rsi = record.technicalRSI, let hist = record.technicalMACDHist {
                        Text("RSI \(String(format: "%.1f", rsi)) · MACD hist \(String(format: "%.3f", hist))")
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                    if let agrees = record.aiAgreesWithTechnical {
                        Text(agrees ? "AI + Technical aligned" : "AI vs Technical diverge")
                            .font(.caption2)
                            .foregroundStyle(agrees ? BullseyeTheme.neonGreen : .orange)
                    }
                }
                .padding(12)
                .glassCard(cornerRadius: 12)
            }
        }
    }
}
