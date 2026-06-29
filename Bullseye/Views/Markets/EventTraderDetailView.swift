//
//  EventTraderDetailView.swift
//  Bullseye
//

import SwiftUI

struct EventTraderDetailView: View {
    let traderId: String
    let initialUsername: String
    let platform: EventMarketPlatform

    @State private var detail: EventTraderDetail?
    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    if isLoading {
                        ProgressView()
                            .tint(platform.accent)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 40)
                    } else if let detail {
                        headerSection(detail)
                        if !detail.closedPositions.isEmpty {
                            sectionTitle("Closed positions")
                            ForEach(detail.closedPositions) { position in
                                closedPositionRow(position)
                            }
                        }
                        if !detail.recentActivity.isEmpty {
                            sectionTitle("Recent activity")
                            ForEach(Array(detail.recentActivity.enumerated()), id: \.offset) { _, item in
                                activityRow(item)
                            }
                        }
                    } else {
                        Text(errorMessage ?? "Could not load trader")
                            .foregroundStyle(platform.textSecondary)
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle(detail?.username ?? initialUsername)
        .navigationBarTitleDisplayMode(.inline)
        .withModeHomeButton(accent: platform.accent)
        .task { await load() }
        .refreshable { await load() }
    }

    private func headerSection(_ detail: EventTraderDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Text(platform.title)
                    .font(.caption.bold())
                    .foregroundStyle(platform.accentMuted)
                if detail.verified == true {
                    Label("Verified", systemImage: "checkmark.seal.fill")
                        .font(.caption2)
                        .foregroundStyle(platform.accent)
                }
                if let rank = detail.rank {
                    Text("#\(rank)")
                        .font(.caption.bold())
                        .foregroundStyle(platform.textTertiary)
                }
            }

            HStack(spacing: 12) {
                statTile(title: "Win rate", value: detail.winRatePct.map { String(format: "%.0f%%", $0) } ?? "—")
                statTile(title: "P/L", value: formatUSD(detail.pnlUsd))
                statTile(title: "Volume", value: detail.volumeUsd.map { formatUSD($0) } ?? "—")
            }

            if let trades = detail.totalTrades {
                Text("\(trades) closed positions tracked")
                    .font(.caption2)
                    .foregroundStyle(platform.textTertiary)
            }

            Text(detail.specialty)
                .font(.caption)
                .foregroundStyle(platform.textSecondary)
        }
        .padding(14)
        .eventGlassCard(platform: platform, cornerRadius: 14)
    }

    private func statTile(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(platform.textTertiary)
            Text(value)
                .font(.subheadline.bold())
                .foregroundStyle(platform.accentBright)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func sectionTitle(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(platform.textPrimary)
    }

    private func closedPositionRow(_ position: TraderClosedPosition) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(position.title)
                .font(.subheadline.bold())
                .foregroundStyle(platform.textPrimary)
            HStack {
                if let outcome = position.outcome {
                    Text(outcome)
                        .font(.caption2.bold())
                        .foregroundStyle(platform.accentMuted)
                }
                if let result = position.outcomeResult {
                    Text(result.uppercased())
                        .font(.caption2.bold())
                        .foregroundStyle(result.lowercased() == "win" ? platform.accent : .orange)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background {
                            Capsule()
                                .fill((result.lowercased() == "win" ? platform.accent : Color.orange).opacity(0.15))
                        }
                }
                Spacer()
                if let pnl = position.pnlUsd {
                    Text(formatUSD(pnl))
                        .font(.caption.bold())
                        .foregroundStyle(pnl >= 0 ? platform.accentBright : .orange)
                }
            }
            if let end = position.endDate {
                Text("Closed \(end)")
                    .font(.caption2)
                    .foregroundStyle(platform.textTertiary)
            }
        }
        .padding(12)
        .eventGlassCard(platform: platform, cornerRadius: 12)
    }

    private func activityRow(_ item: TraderActivityItem) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: item.type == "TRADE" ? "arrow.left.arrow.right" : "clock")
                .foregroundStyle(platform.accentMuted)
            VStack(alignment: .leading, spacing: 4) {
                Text(item.title)
                    .font(.caption.bold())
                    .foregroundStyle(platform.textPrimary)
                    .lineLimit(2)
                HStack(spacing: 8) {
                    Text(item.type)
                        .font(.caption2)
                        .foregroundStyle(platform.textTertiary)
                    if let side = item.side {
                        Text(side)
                            .font(.caption2.bold())
                            .foregroundStyle(platform.accentMuted)
                    }
                    if let size = item.usdcSize ?? item.size {
                        Text(formatUSD(size))
                            .font(.caption2)
                            .foregroundStyle(platform.textSecondary)
                    }
                }
            }
            Spacer()
        }
        .padding(12)
        .eventGlassCard(platform: platform, cornerRadius: 12)
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
        do {
            detail = try await APIService.shared.fetchEventTraderDetail(id: traderId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
