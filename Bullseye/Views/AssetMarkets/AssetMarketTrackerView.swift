//
//  AssetMarketTrackerView.swift
//  Bullseye
//

import SwiftUI

struct AssetMarketTrackerView: View {
    let platform: AssetMarketPlatform

    @State private var predictions: [AssetMarketPrediction] = []
    @State private var stats: AssetMarketStats?
    @State private var isLoading = false

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("\(platform.title) Ledger")
                        .font(.title2.bold())
                        .foregroundStyle(platform.textPrimary)

                    if let stats {
                        HStack(spacing: 12) {
                            statPill("Total", "\(stats.total)")
                            statPill("Win Rate", stats.winRatePct.map { String(format: "%.0f%%", $0) } ?? "—")
                        }
                    }

                    if isLoading { ProgressView().tint(platform.accent) }

                    ForEach(predictions) { p in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(p.direction.uppercased())
                                    .font(.caption.bold())
                                    .foregroundStyle(platform.accentBright)
                                Text(p.symbol)
                                    .font(.caption2)
                                    .foregroundStyle(platform.textTertiary)
                                Spacer()
                                Text(p.outcome.capitalized)
                                    .font(.caption2)
                                    .foregroundStyle(platform.textSecondary)
                            }
                            Text(p.name).font(.caption).foregroundStyle(platform.textPrimary)
                            Text("\(Int(p.confidence))% · Target \(Formatters.currency(p.targetPrice))")
                                .font(.caption2).foregroundStyle(platform.textSecondary)
                        }
                        .padding(12)
                        .assetGlassCard(platform: platform, cornerRadius: 12)
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
            Text(value).font(.headline).foregroundStyle(platform.accent)
            Text(label).font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(10)
        .assetGlassCard(platform: platform, cornerRadius: 10)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        predictions = (try? await APIService.shared.fetchAssetTracker(assetClass: platform.rawValue)) ?? []
        stats = try? await APIService.shared.fetchAssetTrackerStats(assetClass: platform.rawValue)
    }
}
