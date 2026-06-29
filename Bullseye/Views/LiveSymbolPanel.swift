//
//  LiveSymbolPanel.swift
//  Bullseye
//

import SwiftUI

/// Drop-in live price panel when a symbol is selected — embed in Predict / Asset views.
struct LiveSymbolPanel: View {
    let symbol: String
    let name: String
    let kind: QuoteMarketKind
    let watchlistCategory: WatchlistCategory
    var accent: Color = BullseyeTheme.neonGreen

    @State private var isWatchlisted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            LiveQuoteCard(
                symbol: symbol,
                name: name,
                kind: kind,
                accent: accent,
                onWatchlistToggle: { Task { await toggleWatch() } },
                isWatchlisted: isWatchlisted
            )
            CategoryWatchlistSection(category: watchlistCategory, accent: accent)
        }
        .task { await refreshWatchState() }
    }

    private func refreshWatchState() async {
        let items = (try? await APIService.shared.getWatchlist(category: watchlistCategory.rawValue)) ?? []
        isWatchlisted = items.contains { $0.ticker.uppercased() == symbol.uppercased() }
    }

    private func toggleWatch() async {
        if isWatchlisted {
            try? await APIService.shared.deleteWatchlist(ticker: symbol, category: watchlistCategory.rawValue)
        } else {
            _ = try? await APIService.shared.postWatchlist(ticker: symbol, companyName: name, category: watchlistCategory.rawValue)
        }
        await refreshWatchState()
    }
}
