//
//  MarketsTrackerView.swift
//  Bullseye
//

import SwiftUI

struct MarketsTrackerView: View {
    let platform: EventMarketPlatform

    @State private var predictions: [EventMarketPrediction] = []
    @State private var stats: EventMarketStats?
    @State private var isLoading = false

    private var platformPredictions: [EventMarketPrediction] {
        predictions.filter { $0.platform == platform.rawValue }
    }

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("\(platform.title) Ledger")
                        .font(.title2.bold())
                        .foregroundStyle(platform.textPrimary)
                    Text("Locked \(platform.title) predictions — immutable on Railway.")
                        .font(.caption)
                        .foregroundStyle(platform.textSecondary)

                    if let stats {
                        HStack(spacing: 12) {
                            statPill("Total", "\(stats.byPlatform[platform.rawValue] ?? 0)")
                            statPill("Win Rate", stats.winRatePct.map { String(format: "%.0f%%", $0) } ?? "—")
                        }
                    }

                    if isLoading {
                        ProgressView().tint(platform.accent)
                    }

                    ForEach(platformPredictions) { p in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(p.predictedSide.uppercased())
                                    .font(.caption.bold())
                                    .foregroundStyle(platform.accentBright)
                                Spacer()
                                Text(p.outcome.capitalized)
                                    .font(.caption2)
                                    .foregroundStyle(platform.textTertiary)
                            }
                            Text(p.question)
                                .font(.caption)
                                .foregroundStyle(platform.textPrimary)
                                .lineLimit(3)
                            Text("\(Int(p.confidence))% · Yes was \(Int(p.yesPriceAtPrediction * 100))%")
                                .font(.caption2)
                                .foregroundStyle(platform.textSecondary)
                        }
                        .padding(12)
                        .eventGlassCard(platform: platform, cornerRadius: 12)
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Tracker")
        .refreshable { await load() }
        .task { await load() }
    }

    private func statPill(_ label: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .foregroundStyle(platform.accent)
            Text(label)
                .font(.caption2)
                .foregroundStyle(platform.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(10)
        .eventGlassCard(platform: platform, cornerRadius: 10)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        predictions = (try? await APIService.shared.fetchEventTracker()) ?? []
        stats = try? await APIService.shared.fetchEventTrackerStats()
    }
}
