//
//  SuggestionDisclosure.swift
//  Bullseye
//

import SwiftUI

struct SuggestionHeader: View {
    let kind: String
    let subtitle: String
    let direction: String?
    let confidence: Double?
    let horizon: String?
    var accent: Color = BullseyeTheme.neonGreen

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label(kind, systemImage: "lightbulb.fill")
                    .font(.headline)
                    .foregroundStyle(accent)
                Spacer()
                Text("NOT ADVICE")
                    .font(.caption2.bold())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.2))
                    .foregroundStyle(.orange)
                    .clipShape(Capsule())
            }

            Text(subtitle)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            if direction != nil || confidence != nil || horizon != nil {
                HStack(spacing: 8) {
                    if let direction {
                        chip("View: \(direction.capitalized)", accent)
                    }
                    if let confidence {
                        chip("Confidence \(Int(confidence))%", BullseyeTheme.textPrimary)
                    }
                    if let horizon {
                        chip("Horizon \(horizon)", BullseyeTheme.textSecondary)
                    }
                }
            }

            Text("This is an algorithmic opinion based on available data — not a guarantee. Verify prices and do your own research before trading.")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .padding(12)
        .background(accent.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(accent.opacity(0.25), lineWidth: 1)
        )
    }

    private func chip(_ text: String, _ color: Color) -> some View {
        Text(text)
            .font(.caption2.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .foregroundStyle(color)
            .background(BullseyeTheme.glassFill)
            .clipShape(Capsule())
    }
}

struct EventMarketSuggestionHeader: View {
    let platform: String
    let question: String
    let predictedSide: String
    let confidence: Double
    let yesPrice: Double?
    var accent: Color

    var body: some View {
        SuggestionHeader(
            kind: "\(platform.capitalized) suggestion",
            subtitle: question,
            direction: predictedSide == "yes" ? "Bullish on Yes" : "Bullish on No",
            confidence: confidence,
            horizon: yesPrice.map { "Yes now \(Int($0 * 100))%" },
            accent: accent
        )
    }
}

struct AnalyticsExplainer: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("How to read this dashboard")
                .font(.subheadline.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            explainerRow("Win rate", "Percent of resolved predictions that hit target before stop-loss within the stated horizon.")
            explainerRow("Calibration", "Compares AI-stated confidence to actual outcomes. Well-calibrated means 70% confidence ≈ 70% wins.")
            explainerRow("AI vs Technical", "AI uses news, fundamentals, and macro context. Technical uses RSI, MACD, and price action only (free).")
            explainerRow("Local log", "On-device copy of your predictions; server ledger is the verified source of truth.")
        }
        .padding(14)
        .glassCard(cornerRadius: 12)
    }

    private func explainerRow(_ title: String, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(detail)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }
}

struct CategoryWatchlistSection: View {
    let category: WatchlistCategory
    var accent: Color = BullseyeTheme.neonGreen

    @State private var items: [WatchlistItem] = []
    @State private var addText = ""
    @State private var errorMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("\(category.displayName) watchlist")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            Text(category.hint)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)

            HStack {
                TextField(category.placeholder, text: $addText)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                Button("Add") { Task { await add() } }
                    .font(.caption.bold())
                    .foregroundStyle(accent)
            }

            if items.isEmpty {
                Text("No symbols saved yet — add tickers you follow in this category.")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            ForEach(items) { item in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.ticker).font(.subheadline.bold())
                        Text(item.companyName).font(.caption2).foregroundStyle(BullseyeTheme.textSecondary)
                    }
                    Spacer()
                    Button(role: .destructive) {
                        Task { await remove(item.ticker) }
                    } label: {
                        Image(systemName: "trash")
                    }
                }
                .padding(10)
                .glassCard(cornerRadius: 10)
            }

            if let errorMessage {
                Text(errorMessage).font(.caption2).foregroundStyle(.orange)
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 12)
        .task { await load() }
    }

    private func load() async {
        items = (try? await APIService.shared.getWatchlist(category: category.rawValue)) ?? []
    }

    private func add() async {
        let t = addText.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !t.isEmpty else { return }
        do {
            _ = try await APIService.shared.postWatchlist(ticker: t, companyName: nil, category: category.rawValue)
            addText = ""
            await load()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func remove(_ ticker: String) async {
        try? await APIService.shared.deleteWatchlist(ticker: ticker, category: category.rawValue)
        await load()
    }
}

enum WatchlistCategory: String, CaseIterable, Identifiable {
    case stocks
    case crypto
    case futures
    case forex
    case polymarket
    case kalshi

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .stocks: "Stocks"
        case .crypto: "Crypto"
        case .futures: "Futures"
        case .forex: "Forex"
        case .polymarket: "Polymarket"
        case .kalshi: "Kalshi"
        }
    }

    var placeholder: String {
        switch self {
        case .stocks: "NVDA"
        case .crypto: "BTC"
        case .futures: "ES=F"
        case .forex: "EURUSD"
        case .polymarket, .kalshi: "Market ID"
        }
    }

    var hint: String {
        switch self {
        case .stocks: "Track equities for flow alerts and quick access."
        case .crypto: "Saved per crypto mode — prices refresh from live feeds when tapped."
        case .futures: "Futures symbols like ES=F, NQ=F."
        case .forex: "Pairs like EURUSD or EURUSD=X."
        case .polymarket, .kalshi: "Save market external IDs or short slugs from search."
        }
    }
}
