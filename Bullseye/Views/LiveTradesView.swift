//
//  LiveTradesView.swift
//  Bullseye
//

import SwiftUI

struct LiveTradesView: View {
    let market: String
    var eventPlatform: EventMarketPlatform?
    var assetPlatform: AssetMarketPlatform?

    @ObservedObject private var alerts = TradeAlertManager.shared
    @State private var feed: LiveTradesFeed?
    @State private var isLoading = false
    @State private var pollTask: Task<Void, Never>?

    private var isStocks: Bool { market == "stocks" }
    private var accent: Color {
        if isStocks { return BullseyeTheme.neonGreen }
        if let assetPlatform { return assetPlatform.accent }
        return eventPlatform?.accent ?? BullseyeBlueTheme.neonBlue
    }

    private var themeTextPrimary: Color {
        if isStocks { return BullseyeTheme.textPrimary }
        if let assetPlatform { return assetPlatform.textPrimary }
        return eventPlatform?.textPrimary ?? BullseyeBlueTheme.textPrimary
    }

    private var themeTextSecondary: Color {
        if isStocks { return BullseyeTheme.textSecondary }
        if let assetPlatform { return assetPlatform.textSecondary }
        return eventPlatform?.textSecondary ?? BullseyeBlueTheme.textSecondary
    }

    private var themeTextTertiary: Color {
        if isStocks { return BullseyeTheme.textTertiary }
        if let assetPlatform { return assetPlatform.textTertiary }
        return eventPlatform?.textTertiary ?? BullseyeBlueTheme.textTertiary
    }

    var body: some View {
        ZStack {
            background.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    alertToggle
                    if isLoading && feed == nil {
                        ProgressView().tint(accent).frame(maxWidth: .infinity).padding(.vertical, 40)
                    }
                    if let feed {
                        if !feed.topPicks.isEmpty { topPicksSection(feed.topPicks) }
                        liveFeedSection(feed)
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Live Trades")
        .refreshable { await reload() }
        .task {
            await reload()
            startAutoRefresh()
        }
        .onDisappear { pollTask?.cancel() }
    }

    @ViewBuilder
    private var background: some View {
        if isStocks {
            BullseyeTheme.backgroundGradient
        } else if let assetPlatform {
            assetPlatform.backgroundGradient
        } else if let eventPlatform {
            eventPlatform.backgroundGradient
        } else {
            BullseyeBlueTheme.backgroundGradient
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(headerTitle)
                .font(.title2.bold())
                .foregroundStyle(themeTextPrimary)
            Text(feed?.disclaimer ?? "Near real-time activity from politicians, whales, and hot markets.")
                .font(.caption2)
                .foregroundStyle(themeTextSecondary)
            if let updated = feed?.updatedAt {
                Text("Updated \(updated.prefix(19).replacingOccurrences(of: "T", with: " "))")
                    .font(.caption2)
                    .foregroundStyle(themeTextTertiary)
            }
        }
    }

    private var headerTitle: String {
        switch market {
        case "stocks": "Congress & Insider Live"
        case "polymarket": "Polymarket Whale Feed"
        case "kalshi": "Kalshi Hot Markets"
        case "futures": "Futures Movers"
        case "crypto": "Crypto Movers"
        case "forex": "Forex Movers"
        default: "Live Trades"
        }
    }

    private var alertToggle: some View {
        Toggle(isOn: $alerts.alertsEnabled) {
            Label("Trade alerts", systemImage: "bell.badge")
                .font(.subheadline.bold())
                .foregroundStyle(themeTextPrimary)
        }
        .tint(accent)
        .padding(12)
        .modifier(glassModifier(cornerRadius: 12))
    }

    private func topPicksSection(_ picks: [LiveTrade]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Best picks right now", systemImage: "star.fill")
                .font(.headline)
                .foregroundStyle(accent)
            ForEach(picks) { pick in
                liveTradeRow(pick, highlighted: true)
            }
        }
    }

    private func liveFeedSection(_ feed: LiveTradesFeed) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Live activity")
                .font(.headline)
                .foregroundStyle(themeTextPrimary)
            ForEach(feed.trades) { trade in
                liveTradeRow(trade, highlighted: trade.isTopPick)
            }
        }
    }

    private func liveTradeRow(_ trade: LiveTrade, highlighted: Bool) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                actorBadge(trade)
                Spacer()
                if let side = trade.side {
                    Text(side)
                        .font(.caption2.bold())
                        .foregroundStyle(accent)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(accent.opacity(0.15))
                        .clipShape(Capsule())
                }
            }
            Text(trade.title)
                .font(.subheadline.bold())
                .foregroundStyle(themeTextPrimary)
            if let sub = trade.subtitle {
                Text(sub)
                    .font(.caption)
                    .foregroundStyle(themeTextSecondary)
            }
            HStack(spacing: 10) {
                if trade.pickScore > 0 {
                    Label(String(format: "%.0f score", trade.pickScore), systemImage: "chart.bar.fill")
                        .font(.caption2.bold())
                        .foregroundStyle(accent)
                }
                if let reason = trade.pickReason {
                    Text(reason)
                        .font(.caption2)
                        .foregroundStyle(themeTextTertiary)
                        .lineLimit(1)
                }
                if let outcome = trade.tradeOutcome {
                    TradeOutcomeBadge(outcome: outcome, compact: true)
                }
            }
            if let ticker = trade.ticker, isStocks {
                HStack(spacing: 12) {
                    Button {
                        Task { await paperBet(trade: trade) }
                    } label: {
                        Label("Bet \(ticker)", systemImage: "banknote")
                            .font(.caption.bold())
                            .foregroundStyle(accent)
                    }
                    if let url = BrokerLinkService.tradeURL(for: ticker) {
                        Link(destination: url) {
                            Label("Trade", systemImage: "arrow.up.right.circle")
                                .font(.caption.bold())
                                .foregroundStyle(accent)
                        }
                    }
                }
            } else if let ticker = trade.ticker, let url = BrokerLinkService.tradeURL(for: ticker) {
                Link(destination: url) {
                    Label("Trade \(ticker)", systemImage: "arrow.up.right.circle")
                        .font(.caption.bold())
                        .foregroundStyle(accent)
                }
            }
        }
        .padding(14)
        .modifier(glassModifier(cornerRadius: 14))
        .overlay {
            if highlighted {
                RoundedRectangle(cornerRadius: 14)
                    .strokeBorder(accent.opacity(0.45), lineWidth: 1)
            }
        }
    }

    private func actorBadge(_ trade: LiveTrade) -> some View {
        HStack(spacing: 6) {
            Image(systemName: actorIcon(trade.actorType))
                .font(.caption)
                .foregroundStyle(accent)
            Text(trade.actorName)
                .font(.caption.bold())
                .foregroundStyle(accent)
            Text(trade.marketType.uppercased())
                .font(.caption2)
                .foregroundStyle(themeTextTertiary)
        }
    }

    private func actorIcon(_ type: String) -> String {
        switch type {
        case "politician": "building.columns"
        case "whale": "person.fill.checkmark"
        case "insider": "briefcase.fill"
        default: "flame.fill"
        }
    }

    private func glassModifier(cornerRadius: CGFloat) -> some ViewModifier {
        if isStocks {
            return AnyGlass(GlassCard(cornerRadius: cornerRadius))
        }
        if let assetPlatform {
            switch assetPlatform {
            case .futures: return AnyGlass(GoldGlassCard(cornerRadius: cornerRadius))
            case .crypto: return AnyGlass(PurpleGlassCard(cornerRadius: cornerRadius))
            case .forex: return AnyGlass(TealGlassCard(cornerRadius: cornerRadius))
            }
        }
        if let eventPlatform {
            switch eventPlatform {
            case .polymarket: return AnyGlass(BlueGlassCard(cornerRadius: cornerRadius))
            case .kalshi: return AnyGlass(RedGlassCard(cornerRadius: cornerRadius))
            }
        }
        return AnyGlass(BlueGlassCard(cornerRadius: cornerRadius))
    }

    private func paperBet(trade: LiveTrade) async {
        guard let ticker = trade.ticker else { return }
        let side = trade.side ?? "BUY"
        let notional = PortfolioView.defaultBetAmount
        do {
            _ = try await APIService.shared.openPaperLive(
                ticker: ticker,
                side: side,
                liveTradeId: trade.id,
                notional: notional
            )
        } catch {
            // silent — user can check portfolio
        }
    }

    private func reload() async {
        isLoading = true
        defer { isLoading = false }
        feed = try? await APIService.shared.fetchLiveTrades(market: market)
    }

    private func startAutoRefresh() {
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(90))
                guard !Task.isCancelled else { return }
                await reload()
            }
        }
    }
}

private struct AnyGlass: ViewModifier {
    private let _body: (Content) -> AnyView

    init<M: ViewModifier>(_ modifier: M) {
        _body = { content in AnyView(content.modifier(modifier)) }
    }

    func body(content: Content) -> some View {
        _body(content)
    }
}
