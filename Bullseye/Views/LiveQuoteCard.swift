//
//  LiveQuoteCard.swift
//  Bullseye
//

import SwiftUI

enum QuoteMarketKind: String {
    case stocks
    case crypto
    case futures
    case forex

    var pollIntervalSeconds: UInt64 {
        switch self {
        case .crypto: 8
        default: 12
        }
    }
}

struct LiveQuoteCard: View {
    let symbol: String
    let name: String
    let kind: QuoteMarketKind
    var accent: Color = BullseyeTheme.neonGreen
    var onWatchlistToggle: (() -> Void)?
    var isWatchlisted: Bool = false

    @State private var quote: LiveQuoteDisplay?
    @State private var trendLabel: String?
    @State private var trendArrow: String?
    @State private var trendStrength: Double?
    @State private var trendSummary: String?
    @State private var isLoading = true
    @State private var lastError: String?
    @State private var pollTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(symbol)
                        .font(.title2.bold())
                        .foregroundStyle(accent)
                    Text(name)
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }
                Spacer()
                if let onWatchlistToggle {
                    Button(action: onWatchlistToggle) {
                        Image(systemName: isWatchlisted ? "star.fill" : "star")
                            .foregroundStyle(isWatchlisted ? accent : BullseyeTheme.textTertiary)
                    }
                }
                liveBadge
            }

            if isLoading && quote == nil {
                ProgressView().tint(accent)
            } else if let quote {
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text(Formatters.currency(quote.price))
                        .font(.title.bold())
                    Text(String(format: "%+.2f%%", quote.changePct))
                        .font(.headline)
                        .foregroundStyle(quote.changePct >= 0 ? BullseyeTheme.neonGreen : .orange)
                }

                HStack(spacing: 6) {
                    Text("Source: \(quote.source)")
                    if let updated = quote.fetchedAt {
                        Text("· \(updated)")
                    }
                }
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)

                if let note = quote.priceNote {
                    Text(note)
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }

                if !quote.isLive {
                    Label("Delayed or estimated", systemImage: "exclamationmark.triangle")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }

                if let trendLabel {
                    TrendMarkBadge(
                        label: trendLabel,
                        arrow: trendArrow,
                        strength: trendStrength,
                        summary: trendSummary,
                        accent: accent
                    )
                }
            } else if let lastError {
                Text(lastError).font(.caption).foregroundStyle(.orange)
            }

            Button { Task { await refreshQuote() } } label: {
                Label("Refresh live price", systemImage: "arrow.clockwise")
                    .font(.caption.bold())
            }
            .foregroundStyle(accent)
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
        .task(id: symbol) {
            await refreshQuote()
            startPolling()
        }
        .onDisappear { pollTask?.cancel() }
    }

    private var liveBadge: some View {
        HStack(spacing: 4) {
            Circle().fill(BullseyeTheme.neonGreen).frame(width: 6, height: 6)
            Text("LIVE").font(.caption2.bold()).foregroundStyle(BullseyeTheme.neonGreen)
        }
        .padding(.horizontal, 8).padding(.vertical, 4)
        .background(BullseyeTheme.neonGreen.opacity(0.12))
        .clipShape(Capsule())
    }

    private func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: kind.pollIntervalSeconds * 1_000_000_000)
                guard !Task.isCancelled else { return }
                await refreshQuote()
            }
        }
    }

    private func refreshQuote() async {
        isLoading = quote == nil
        defer { isLoading = false }
        do {
            switch kind {
            case .stocks:
                let q = try await APIService.shared.fetchLiveStockQuote(ticker: symbol)
                quote = LiveQuoteDisplay(
                    price: q.price, changePct: q.changePct,
                    source: q.source ?? "Yahoo Finance", fetchedAt: q.fetchedAt,
                    priceNote: q.priceNote, isLive: q.isLive ?? true
                )
            case .crypto, .futures, .forex:
                let q = try await APIService.shared.fetchLiveAssetQuote(assetClass: kind.rawValue, symbol: symbol)
                quote = LiveQuoteDisplay(
                    price: q.price ?? 0, changePct: q.changePct ?? 0,
                    source: q.source ?? "Market data", fetchedAt: q.fetchedAt,
                    priceNote: q.priceNote, isLive: q.isLive ?? true
                )
            }
            lastError = nil
            await loadTrendMarks()
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func loadTrendMarks() async {
        do {
            let tech: TechnicalAnalysis
            switch kind {
            case .stocks:
                tech = try await APIService.shared.fetchTechnicals(ticker: symbol)
            case .crypto, .futures, .forex:
                tech = try await APIService.shared.fetchAssetTechnicals(assetClass: kind.rawValue, symbol: symbol)
            }
            trendLabel = tech.trendLabel
            trendArrow = tech.trendArrow
            trendStrength = tech.trendStrength
            trendSummary = tech.trendSummary
        } catch {
            trendLabel = nil
            trendArrow = nil
            trendStrength = nil
            trendSummary = nil
        }
    }
}

struct LiveQuoteDisplay {
    let price: Double
    let changePct: Double
    let source: String
    let fetchedAt: String?
    let priceNote: String?
    let isLive: Bool
}
