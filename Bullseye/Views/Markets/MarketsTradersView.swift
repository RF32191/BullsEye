//
//  MarketsTradersView.swift
//  Bullseye
//

import SwiftUI

struct MarketsTradersView: View {
    let platform: EventMarketPlatform

    @State private var traders: [EventTrader] = []
    @State private var isLoading = false

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("\(platform.title) Traders")
                        .font(.title2.bold())
                        .foregroundStyle(platform.textPrimary)
                    Text(platform == .polymarket
                         ? "Live leaderboard with win rates, live trades, and derived strategies."
                         : "Notable Kalshi traders and market specialists.")
                        .font(.caption)
                        .foregroundStyle(platform.textSecondary)

                    if isLoading {
                        ProgressView().tint(platform.accent).frame(maxWidth: .infinity)
                    }

                    ForEach(traders) { trader in
                        NavigationLink {
                            EventTraderDetailView(traderId: trader.id, initialUsername: trader.username, platform: platform)
                        } label: {
                            traderRow(trader)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Traders")
        .refreshable { await load() }
        .task { await load() }
    }

    private var liveDot: some View {
        HStack(spacing: 3) {
            Circle().fill(Color.green).frame(width: 6, height: 6)
            Text("LIVE")
                .font(.caption2.bold())
                .foregroundStyle(Color.green)
        }
    }

    private func traderRow(_ trader: EventTrader) -> some View {
        HStack(spacing: 14) {
            Text("#\(trader.rank)")
                .font(.title3.bold())
                .foregroundStyle(platform.accent)
                .frame(width: 36)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(trader.username)
                        .font(.headline)
                        .foregroundStyle(platform.textPrimary)
                    if trader.verified == true {
                        Image(systemName: "checkmark.seal.fill")
                            .font(.caption2)
                            .foregroundStyle(platform.accent)
                    }
                    if trader.isActive == true {
                        liveDot
                    }
                }
                Text(trader.specialty)
                    .font(.caption2)
                    .foregroundStyle(platform.textTertiary)
                    .lineLimit(1)
                if let live = trader.recentLiveTrade, !live.title.isEmpty {
                    Text("Live: \(live.side ?? "TRADE") · \(live.title)")
                        .font(.caption2)
                        .foregroundStyle(platform.accentMuted)
                        .lineLimit(1)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                if let winRate = trader.winRatePct {
                    Text(String(format: "%.0f%% win", winRate))
                        .font(.headline)
                        .foregroundStyle(platform.accentBright)
                } else {
                    Text(formatUSD(trader.pnlUsd))
                        .font(.headline)
                        .foregroundStyle(trader.pnlUsd >= 0 ? platform.accentBright : .orange)
                }
                if trader.winRatePct != nil {
                    Text(formatUSD(trader.pnlUsd))
                        .font(.caption2)
                        .foregroundStyle(platform.textSecondary)
                }
                if let volume = trader.volumeUsd {
                    Text("\(formatUSD(volume)) vol")
                        .font(.caption2)
                        .foregroundStyle(platform.textTertiary)
                }
            }
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(platform.textTertiary)
        }
        .padding(14)
        .eventGlassCard(platform: platform, cornerRadius: 14)
    }

    private func formatUSD(_ value: Double) -> String {
        let absVal = abs(value)
        let sign = value >= 0 ? "+" : "-"
        if absVal >= 1_000_000 {
            return String(format: "%@$%.1fM", sign, absVal / 1_000_000)
        }
        if absVal >= 1000 {
            return String(format: "%@$%.0fK", sign, absVal / 1000)
        }
        return String(format: "%@$%.0f", sign, absVal)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        traders = (try? await APIService.shared.fetchEventTraders(platform: platform.rawValue)) ?? []
    }
}
