//
//  CongressTradesView.swift
//  Bullseye
//

import SwiftUI

private enum TradeFilter: String, CaseIterable, Identifiable {
    case all, purchase, sale

    var id: String { rawValue }

    var label: String {
        switch self {
        case .all: "All"
        case .purchase: "Buys"
        case .sale: "Sells"
        }
    }

    var apiValue: String? {
        switch self {
        case .all: nil
        case .purchase: "purchase"
        case .sale: "sale"
        }
    }
}

private enum PartyFilter: String, CaseIterable, Identifiable {
    case all, D, R, I

    var id: String { rawValue }
    var label: String {
        switch self {
        case .all: "All"
        case .D: "Dem"
        case .R: "Rep"
        case .I: "Ind"
        }
    }
    var apiValue: String? { self == .all ? nil : rawValue }
}

private enum DataFeed: String, CaseIterable, Identifiable {
    case congress, insider
    var id: String { rawValue }
    var label: String { self == .congress ? "Congress" : "Insider" }
}

struct CongressTradesView: View {
    @State private var feed: DataFeed = .congress
    @State private var trades: [CongressTrade] = []
    @State private var insiderTrades: [InsiderTrade] = []
    @State private var total = 0
    @State private var page = 1
    @State private var hasMore = false
    @State private var dataSource = ""
    @State private var disclaimer = ""
    @State private var isMock = false
    @State private var tickerQuery = ""
    @State private var politicianQuery = ""
    @State private var tradeFilter: TradeFilter = .all
    @State private var partyFilter: PartyFilter = .all
    @State private var isLoading = false
    @State private var isLoadingMore = false
    @State private var errorMessage: String?
    @State private var searchTask: Task<Void, Never>?
    @State private var topPoliticians: [PoliticianSummary] = []
    @State private var isLoadingPoliticians = false

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 16) {
                headerSection
                feedPicker
                if isMock { mockBanner }
                disclaimerBanner
                if feed == .congress { filterSection }
                if feed == .congress { partyFilterSection }
                if feed == .congress && politicianQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    politicianLeaderboard
                }
                searchSection

                if isLoading && trades.isEmpty && insiderTrades.isEmpty {
                    ProgressView()
                        .tint(BullseyeTheme.neonGreen)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else if feed == .congress && trades.isEmpty {
                    emptyState
                } else if feed == .insider && insiderTrades.isEmpty {
                    emptyState
                } else if feed == .congress {
                    resultsHeader
                    ForEach(trades) { trade in
                        CongressTradeRow(trade: trade)
                    }
                    if hasMore { loadMoreButton }
                } else {
                    resultsHeader
                    ForEach(insiderTrades) { trade in
                        InsiderTradeRow(trade: trade)
                    }
                    if hasMore { loadMoreButton }
                }
            }
            .padding(20)
        }
        .navigationTitle("Political Trades")
        .refreshable { await reload() }
        .task {
            await reload()
            await loadPoliticians()
        }
        .onChange(of: feed) { _, newFeed in
            Task {
                await reload()
                if newFeed == .congress { await loadPoliticians() }
            }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Political Trade Tracker")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("STOCK Act disclosures from the U.S. House and Senate — updated as filings are published.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    private var feedPicker: some View {
        Picker("Feed", selection: $feed) {
            ForEach(DataFeed.allCases) { f in
                Text(f.label).tag(f)
            }
        }
        .pickerStyle(.segmented)
    }

    private var mockBanner: some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text("Sample data — live API unavailable or mock mode enabled on server.")
                .font(.caption2)
                .foregroundStyle(.orange)
        }
        .padding(10)
        .background(Color.orange.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private var partyFilterSection: some View {
        HStack(spacing: 8) {
            ForEach(PartyFilter.allCases) { filter in
                Button {
                    partyFilter = filter
                    Task { await reload() }
                } label: {
                    Text(filter.label)
                        .font(.caption.bold())
                        .foregroundStyle(partyFilter == filter ? BullseyeTheme.backgroundDeep : BullseyeTheme.textPrimary)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background {
                            Capsule()
                                .fill(partyFilter == filter ? BullseyeTheme.neonGreen : BullseyeTheme.glassFill)
                        }
                }
            }
            Spacer()
        }
    }

    private var disclaimerBanner: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(BullseyeTheme.neonGreenMuted)
            Text(disclaimer.isEmpty
                 ? "Filings may lag the actual trade by up to 45 days per federal law."
                 : disclaimer)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    private var filterSection: some View {
        HStack(spacing: 8) {
            ForEach(TradeFilter.allCases) { filter in
                Button {
                    tradeFilter = filter
                    Task { await reload() }
                } label: {
                    Text(filter.label)
                        .font(.caption.bold())
                        .foregroundStyle(tradeFilter == filter ? BullseyeTheme.backgroundDeep : BullseyeTheme.textPrimary)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background {
                            Capsule()
                                .fill(tradeFilter == filter ? BullseyeTheme.neonGreen : BullseyeTheme.glassFill)
                        }
                }
            }
            Spacer()
        }
    }

    private var searchSection: some View {
        VStack(spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(BullseyeTheme.textTertiary)
                TextField("Ticker (e.g. NVDA)", text: $tickerQuery)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .foregroundStyle(BullseyeTheme.textPrimary)
                    .onChange(of: tickerQuery) { _, _ in scheduleSearch() }
            }
            .padding(12)
            .glassCard(cornerRadius: 12)

            HStack(spacing: 10) {
                Image(systemName: "person.crop.circle")
                    .foregroundStyle(BullseyeTheme.textTertiary)
                TextField("Politician name", text: $politicianQuery)
                    .autocorrectionDisabled()
                    .foregroundStyle(BullseyeTheme.textPrimary)
                    .onChange(of: politicianQuery) { _, _ in scheduleSearch() }
            }
            .padding(12)
            .glassCard(cornerRadius: 12)
        }
    }

    private var politicianLeaderboard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Top performers")
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Spacer()
                if isLoadingPoliticians {
                    ProgressView().scaleEffect(0.8).tint(BullseyeTheme.neonGreen)
                }
            }
            Text("Win rate based on direction-aware returns since each trade date (buys win if stock rose, sells if it fell).")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)

            if topPoliticians.isEmpty && !isLoadingPoliticians {
                Text("No politician stats yet")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            } else {
                ForEach(topPoliticians) { politician in
                    NavigationLink {
                        PoliticianProfileView(slug: politician.memberSlug, initialName: politician.memberName)
                    } label: {
                        PoliticianLeaderboardRow(politician: politician)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func loadPoliticians() async {
        isLoadingPoliticians = true
        defer { isLoadingPoliticians = false }
        topPoliticians = (try? await APIService.shared.fetchTopPoliticians()) ?? []
    }

    private var resultsHeader: some View {
        HStack {
            Text("\(total) filing\(total == 1 ? "" : "s")")
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.textSecondary)
            Spacer()
            if !dataSource.isEmpty {
                Text(dataSource)
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
                    .lineLimit(1)
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "building.columns")
                .font(.largeTitle)
                .foregroundStyle(BullseyeTheme.neonGreenMuted)
            Text("No trades found")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Try clearing filters or search a different ticker.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 32)
    }

    private var loadMoreButton: some View {
        Button {
            Task { await loadMore() }
        } label: {
            HStack {
                if isLoadingMore {
                    ProgressView().tint(BullseyeTheme.neonGreen)
                }
                Text(isLoadingMore ? "Loading…" : "Load more")
                    .font(.caption.bold())
            }
            .foregroundStyle(BullseyeTheme.neonGreen)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .glassCard(cornerRadius: 12)
        }
        .disabled(isLoadingMore)
    }

    private func scheduleSearch() {
        searchTask?.cancel()
        searchTask = Task {
            try? await Task.sleep(for: .milliseconds(450))
            guard !Task.isCancelled else { return }
            await reload()
        }
    }

    private func reload() async {
        page = 1
        isLoading = true
        defer { isLoading = false }
        await fetch(page: 1, append: false)
    }

    private func loadMore() async {
        guard hasMore, !isLoadingMore else { return }
        isLoadingMore = true
        defer { isLoadingMore = false }
        await fetch(page: page + 1, append: true)
    }

    private func fetch(page: Int, append: Bool) async {
        let ticker = tickerQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        let politician = politicianQuery.trimmingCharacters(in: .whitespacesAndNewlines)

        do {
            if feed == .insider {
                let response = try await APIService.shared.fetchInsiderTrades(
                    ticker: ticker.isEmpty ? nil : ticker,
                    page: page
                )
                if append { insiderTrades.append(contentsOf: response.trades) }
                else { insiderTrades = response.trades }
                total = response.total
                self.page = response.page
                hasMore = response.hasMore
                dataSource = response.dataSource
                disclaimer = response.disclaimer
                isMock = response.isMock
                return
            }

            let response = try await APIService.shared.fetchCongressTrades(
                ticker: ticker.isEmpty ? nil : ticker,
                type: tradeFilter.apiValue,
                party: partyFilter.apiValue,
                politician: politician.isEmpty ? nil : politician,
                page: page
            )
            if append {
                trades.append(contentsOf: response.trades)
            } else {
                trades = response.trades
            }
            total = response.total
            self.page = response.page
            hasMore = response.hasMore
            dataSource = response.dataSource
            disclaimer = response.disclaimer
            isMock = response.isMock
        } catch {
            if !append {
                trades = []
                insiderTrades = []
            }
            errorMessage = error.localizedDescription
        }
    }
}

private struct PoliticianLeaderboardRow: View {
    let politician: PoliticianSummary

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(politician.memberName)
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.textPrimary)
                HStack(spacing: 6) {
                    if let party = politician.party {
                        Text(party)
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                    Text("\(politician.trackedTrades) tracked")
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textTertiary)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                if let winRate = politician.winRatePct {
                    Text(String(format: "%.0f%% win", winRate))
                        .font(.caption.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                }
                if let avg = politician.avgReturnSinceTradePct {
                    Text(String(format: "%+.1f%% avg", avg))
                        .font(.caption2)
                        .foregroundStyle(avg >= 0 ? BullseyeTheme.neonGreenMuted : .orange)
                }
            }
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }
}

struct CongressTradeRow: View {
    let trade: CongressTrade

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    NavigationLink {
                        PoliticianProfileView(slug: trade.memberSlug, initialName: trade.memberName)
                    } label: {
                        Text(trade.memberName)
                            .font(.headline)
                            .foregroundStyle(BullseyeTheme.textPrimary)
                    }
                    .buttonStyle(.plain)
                    HStack(spacing: 6) {
                        if let party = trade.partyLabel {
                            Text(party)
                                .font(.caption2.bold())
                                .foregroundStyle(partyColor(trade.party))
                        }
                        if let chamber = trade.chamber {
                            Text(chamber)
                                .font(.caption2)
                                .foregroundStyle(BullseyeTheme.textTertiary)
                        }
                        if let owner = trade.owner, owner != "self" {
                            Text("· \(owner.capitalized)")
                                .font(.caption2)
                                .foregroundStyle(BullseyeTheme.textTertiary)
                        }
                    }
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text(trade.ticker)
                        .font(.title3.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                    HStack(spacing: 6) {
                        if let outcome = trade.tradeOutcome {
                            TradeOutcomeBadge(outcome: outcome, compact: true)
                        }
                        tradeTypeBadge
                    }
                }
            }

            Text(trade.amountLabel)
                .font(.subheadline.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)

            HStack {
                if let txDate = trade.transactionDate {
                    Label("Traded \(txDate)", systemImage: "calendar")
                }
                if let filed = trade.disclosureDate {
                    Label("Filed \(filed)", systemImage: "doc.text")
                }
            }
            .font(.caption2)
            .foregroundStyle(BullseyeTheme.textSecondary)

            if trade.conflictScore > 0.4 {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                    Text("Conflict score \(Int(trade.conflictScore * 100))%")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }
            }

            ReturnSinceTradeRow(
                returnPct: trade.returnSinceTradePct,
                outcome: trade.tradeOutcome,
                label: "since trade",
                currentPrice: trade.currentPrice
            )

            if let ret = trade.returnSinceDisclosurePct {
                HStack(spacing: 6) {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                        .foregroundStyle(ret >= 0 ? BullseyeTheme.neonGreen : .orange)
                    Text(String(format: "%+.1f%% since filing", ret))
                        .font(.caption.bold())
                        .foregroundStyle(ret >= 0 ? BullseyeTheme.neonGreen : .orange)
                }
            }

            if let dir = trade.latestPredictionDirection {
                HStack(spacing: 6) {
                    Image(systemName: "brain.head.profile")
                        .foregroundStyle(BullseyeTheme.neonGreenMuted)
                    Text("Your prediction: \(dir.capitalized)")
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                    if let conf = trade.latestPredictionConfidence {
                        Text("(\(Int(conf))%)")
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                }
            }

            HStack(spacing: 12) {
                if let url = BrokerLinkService.tradeURL(for: trade.ticker) {
                    Link(destination: url) {
                        Label("Trade \(trade.ticker)", systemImage: "arrow.up.right.circle")
                            .font(.caption.bold())
                            .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                }
                if let urlString = trade.sourceUrl, let url = URL(string: urlString) {
                    Link(destination: url) {
                        Label("Filing", systemImage: "doc.text")
                            .font(.caption.bold())
                            .foregroundStyle(BullseyeTheme.neonGreenMuted)
                    }
                }
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }

    private var tradeTypeBadge: some View {
        Text(trade.isPurchase ? "BUY" : trade.isSale ? "SELL" : trade.transactionType.uppercased())
            .font(.caption2.bold())
            .foregroundStyle(trade.isPurchase ? BullseyeTheme.neonGreen : .orange)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background {
                Capsule()
                    .fill((trade.isPurchase ? BullseyeTheme.neonGreen : Color.orange).opacity(0.15))
            }
    }

    private func partyColor(_ party: String?) -> Color {
        switch party?.uppercased() {
        case "D": Color.blue.opacity(0.9)
        case "R": Color.red.opacity(0.9)
        default: BullseyeTheme.textSecondary
        }
    }
}

private struct InsiderTradeRow: View {
    let trade: InsiderTrade

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(trade.reportingName)
                        .font(.headline)
                        .foregroundStyle(BullseyeTheme.textPrimary)
                    if let title = trade.reportingTitle {
                        Text(title)
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                }
                Spacer()
                Text(trade.symbol)
                    .font(.title3.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            Text(trade.transactionType)
                .font(.caption.bold())
                .foregroundStyle(.orange)
            if let qty = trade.securitiesTransacted, let price = trade.price {
                Text("\(Int(qty)) shares @ \(Formatters.currency(price))")
                    .font(.subheadline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
            }
            if let tx = trade.transactionDate {
                Text("Traded \(tx) · Filed \(trade.filingDate ?? "—")")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            ReturnSinceTradeRow(
                returnPct: trade.returnSinceTradePct,
                outcome: trade.tradeOutcome,
                label: "since trade",
                currentPrice: trade.currentPrice
            )

            if let url = BrokerLinkService.tradeURL(for: trade.symbol) {
                Link(destination: url) {
                    Label("Trade \(trade.symbol)", systemImage: "arrow.up.right.circle")
                        .font(.caption.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                }
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }
}
