//
//  IntelligenceHubView.swift
//  Bullseye
//

import SwiftUI

struct IntelligenceHubView: View {
    @State private var segment = 0
    @State private var macro: MacroDashboard?
    @State private var conflicts: ConflictsFeed?
    @State private var crossTicker = "NVDA"
    @State private var crossLinks: CrossMarketLinks?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                Picker("Section", selection: $segment) {
                    Text("Macro").tag(0)
                    Text("Conflicts").tag(1)
                    Text("Cross-Market").tag(2)
                }
                .pickerStyle(.segmented)

                if isLoading {
                    ProgressView().tint(BullseyeTheme.neonGreen).frame(maxWidth: .infinity)
                }

                switch segment {
                case 0: macroSection
                case 1: conflictsSection
                default: crossMarketSection
                }
            }
            .padding(20)
        }
        .navigationTitle("Intelligence")
        .task { await loadMacro() }
        .onChange(of: segment) { _, new in
            Task {
                if new == 0 { await loadMacro() }
                else if new == 1 { await loadConflicts() }
                else { await loadCrossMarket() }
            }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var macroSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let macro {
                Text("Macro pulse")
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(Array(macro.macroQuotes.keys.sorted()), id: \.self) { key in
                        if let q = macro.macroQuotes[key] {
                            macroTile(key: key, quote: q)
                        }
                    }
                }
                sectionTitle("Hot Polymarket")
                ForEach(macro.polymarketHot.prefix(5)) { m in
                    eventRow(m)
                }
                sectionTitle("Hot Kalshi")
                ForEach(macro.kalshiHot.prefix(5)) { m in
                    eventRow(m)
                }
            }
        }
    }

    private var conflictsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Politician ↔ ticker conflicts")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            if let conflicts {
                ForEach(conflicts.conflicts) { c in
                    VStack(alignment: .leading, spacing: 4) {
                        Text("\(c.memberName ?? "Member") · \(c.ticker)")
                            .font(.subheadline.bold())
                            .foregroundStyle(BullseyeTheme.neonGreen)
                        Text("\(c.transactionType?.capitalized ?? "Trade") · \(c.amountLabel ?? "")")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                        Text(c.note)
                            .font(.caption2)
                            .foregroundStyle(.orange)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private var crossMarketSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                TextField("Ticker", text: $crossTicker)
                    .textInputAutocapitalization(.characters)
                    .padding(10)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Link") { Task { await loadCrossMarket() } }
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            if let crossLinks {
                sectionTitle("Linked event markets")
                ForEach(crossLinks.linkedMarkets.prefix(8)) { m in
                    eventRow(m)
                }
                sectionTitle("Theme matches")
                ForEach(crossLinks.themeMatches.prefix(6)) { t in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(t.keyword.uppercased())
                            .font(.caption.bold())
                            .foregroundStyle(BullseyeTheme.neonGreen)
                        Text(t.event.question ?? "Event")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                        Text("Tickers: \(t.relatedTickers.joined(separator: ", "))")
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                    .padding(10)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                }
            }
        }
    }

    private func macroTile(key: String, quote: MacroQuote) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(key.replacingOccurrences(of: "_", with: " ").uppercased())
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary)
            Text(quote.symbol)
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            if let price = quote.price {
                Text(String(format: "$%.2f", price))
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            if let chg = quote.changePct {
                Text(String(format: "%+.2f%%", chg))
                    .font(.caption2)
                    .foregroundStyle(chg >= 0 ? BullseyeTheme.neonGreen : .red)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func eventRow(_ m: EventMarketCard) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(m.question ?? "Market")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textPrimary)
                .lineLimit(2)
            HStack {
                if let p = m.platform { Text(p).font(.caption2).foregroundStyle(BullseyeTheme.textSecondary) }
                if let y = m.yesPrice { Text(String(format: "Yes %.0f%%", y * 100)).font(.caption2) }
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func sectionTitle(_ text: String) -> some View {
        Text(text)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(BullseyeTheme.textPrimary)
            .padding(.top, 8)
    }

    private func loadMacro() async {
        isLoading = true
        defer { isLoading = false }
        do { macro = try await APIService.shared.fetchMacroDashboard() }
        catch { errorMessage = error.localizedDescription }
    }

    private func loadConflicts() async {
        isLoading = true
        defer { isLoading = false }
        do { conflicts = try await APIService.shared.fetchConflicts() }
        catch { errorMessage = error.localizedDescription }
    }

    private func loadCrossMarket() async {
        isLoading = true
        defer { isLoading = false }
        do { crossLinks = try await APIService.shared.fetchCrossMarketLinks(ticker: crossTicker) }
        catch { errorMessage = error.localizedDescription }
    }
}
