//
//  PredictView.swift
//  Bullseye
//

import SwiftUI

struct PredictView: View {
    @Bindable var appModel: AppViewModel

    @FocusState private var searchFocused: Bool
    @State private var query = ""
    @State private var results: [StockSearchResult] = []
    @State private var selected: StockSearchResult?
    @State private var quote: StockQuote?
    @State private var horizon = PredictionHorizonOption.defaultStock
    @State private var engine: PredictionEngine = .ai
    @State private var prediction: Prediction?
    @State private var comparison: ComparisonAnalysis?
    @State private var isSearching = false
    @State private var isAnalyzing = false
    @State private var showError = false
    @State private var errorMessage: String?
    @State private var searchTask: Task<Void, Never>?
    @State private var hasSearched = false

    @State private var paperMessage: String?
    @State private var betAmount = String(format: "%.0f", PortfolioView.defaultBetAmount)

    private let horizons = PredictionHorizonOption.stockOptions

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                tokenBanner
                searchSection
                if let selected {
                    selectedStockCard(selected)
                }
                enginePicker
                PredictionHorizonPicker(selection: $horizon, options: horizons, accent: BullseyeTheme.neonGreen)
                analyzeButton
                if let prediction {
                    predictionResult(prediction)
                }
                if let comparison {
                    comparisonSection(comparison)
                }
            }
            .padding(20)
        }
        .scrollDismissesKeyboard(.interactively)
        #if os(iOS)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { dismissKeyboard() }
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        #endif
        .navigationTitle("Predict")
        .alert("Error", isPresented: $showError) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var tokenBanner: some View {
        TokenBalanceBanner(appModel: appModel)
    }

    private var searchSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Select Stock")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(BullseyeTheme.textTertiary)
                TextField("Search ticker or company", text: $query)
                    .focused($searchFocused)
                    #if os(iOS)
                    .textInputAutocapitalization(.characters)
                    .submitLabel(.search)
                    #endif
                    .autocorrectionDisabled()
                    .foregroundStyle(BullseyeTheme.textPrimary)
                    .onSubmit { Task { await search() } }
                Button("Search") { Task { await search() } }
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            .padding(12)
            .glassCard(cornerRadius: 12)
            .onChange(of: query) { _, newValue in
                searchTask?.cancel()
                let trimmed = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                guard trimmed.count >= 1 else {
                    results = []
                    hasSearched = false
                    return
                }
                searchTask = Task {
                    try? await Task.sleep(nanoseconds: 500_000_000)
                    guard !Task.isCancelled else { return }
                    await search()
                }
            }

            if isSearching {
                ProgressView().tint(BullseyeTheme.neonGreen)
            } else if hasSearched && results.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("No matches for \"\(query.uppercased())\"")
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                    if isLikelyTicker(query) {
                        Button("Use \"\(query.uppercased())\" anyway") {
                            Task { await selectDirectTicker(query.uppercased()) }
                        }
                        .font(.caption.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                }
            }

            ForEach(results) { stock in
                Button {
                    selected = stock
                    query = stock.symbol
                    results = []
                    hasSearched = false
                    Task { await loadQuote(stock.symbol) }
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(stock.symbol)
                                .font(.headline)
                                .foregroundStyle(BullseyeTheme.textPrimary)
                            Text(stock.name)
                                .font(.caption)
                                .foregroundStyle(BullseyeTheme.textSecondary)
                        }
                        Spacer()
                        if selected?.symbol == stock.symbol {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(BullseyeTheme.neonGreen)
                        }
                    }
                    .padding(12)
                    .glassCard(cornerRadius: 10)
                }
            }
        }
    }

    private func selectedStockCard(_ stock: StockSearchResult) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(stock.symbol)
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.accentGradient)
            Text(stock.name)
                .foregroundStyle(BullseyeTheme.textSecondary)
            if let quote {
                HStack {
                    Text(Formatters.currency(quote.price))
                        .font(.title3.bold())
                    Text("\(quote.changePct >= 0 ? "+" : "")\(Formatters.percent(quote.changePct))")
                        .foregroundStyle(quote.changePct >= 0 ? BullseyeTheme.neonGreen : .red)
                }
            }
            Text("Data: Yahoo Finance")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .glassCard()
    }

    private var enginePicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Prediction Engine")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            ForEach(PredictionEngine.allCases) { option in
                Button {
                    engine = option
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: option.icon)
                            .font(.title3)
                            .foregroundStyle(engine == option ? BullseyeTheme.neonGreen : BullseyeTheme.textTertiary)
                            .frame(width: 32)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(option.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(BullseyeTheme.textPrimary)
                            Text(option.subtitle)
                                .font(.caption)
                                .foregroundStyle(BullseyeTheme.textSecondary)
                        }
                        Spacer()
                        if engine == option {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(BullseyeTheme.neonGreen)
                        }
                    }
                    .padding(12)
                    .background(engine == option ? BullseyeTheme.neonGreen.opacity(0.12) : Color.clear)
                    .glassCard(cornerRadius: 12)
                    .overlay {
                        if engine == option {
                            RoundedRectangle(cornerRadius: 12)
                                .strokeBorder(BullseyeTheme.neonGreen.opacity(0.4), lineWidth: 1)
                        }
                    }
                }
            }
        }
    }

    private var analyzeButton: some View {
        Button {
            Task { await runAnalysis() }
        } label: {
            HStack {
                if isAnalyzing {
                    ProgressView().tint(.black)
                } else {
                    Image(systemName: engine.icon)
                    Text(engine == .ai ? "Run AI Prediction" : "Run Technical Bot")
                        .font(.headline)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .foregroundStyle(.black)
            .background(selected == nil ? Color.gray : BullseyeTheme.neonGreen)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .disabled(selected == nil || isAnalyzing)
    }

    private func predictionResult(_ p: Prediction) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                directionBadge(p.direction)
                if p.aiModel == "technical-bot" {
                    Text("TECHNICAL BOT")
                        .font(.caption2.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(BullseyeTheme.neonGreen.opacity(0.15))
                        .clipShape(Capsule())
                }
                Spacer()
                Text("\(Int(p.confidence))% confidence")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }

            Text("Saved locally + locked on Railway")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)

            gridRow("Target", Formatters.currency(p.targetPrice))
            gridRow("Stop Loss", Formatters.currency(p.stopLoss))
            gridRow("Take Profit", Formatters.currency(p.takeProfit))

            Text("Why")
                .font(.headline)
            Text(p.reasoning)
                .font(.subheadline)
                .foregroundStyle(BullseyeTheme.textSecondary)

            Text("Bull Case")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(p.bullCase)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            Text("Bear Case")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.orange)
            Text(p.bearCase)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            if let factors = p.analysisFactors, !factors.isEmpty {
                factorsSection(factors)
            }

            actionButtons(for: p)
        }
        .padding(16)
        .glassCard()
    }

    private func actionButtons(for p: Prediction) -> some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Text("Bet $")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
                TextField("1000", text: $betAmount)
                    .keyboardType(.decimalPad)
                    .padding(8)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .onChange(of: betAmount) { _, v in
                if let n = Double(v) { PortfolioView.saveDefaultBet(n) }
            }

            HStack(spacing: 10) {
                Button {
                    Task { await followPaper(p) }
                } label: {
                    Label("Follow with Paper $", systemImage: "dollarsign.circle")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .foregroundStyle(BullseyeTheme.backgroundDeep)
                .background(BullseyeTheme.neonGreen)
                .clipShape(RoundedRectangle(cornerRadius: 10))

                Button {
                    Task { await addWatchlist(p.ticker, p.companyName) }
                } label: {
                    Label("Watchlist", systemImage: "star")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .foregroundStyle(BullseyeTheme.neonGreen)
                .background(BullseyeTheme.glassFill)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }

            if let url = BrokerLinkService.tradeURL(for: p.ticker) {
                Link(destination: url) {
                    Label("Open in \(BrokerLinkService.preferredBroker.displayName)", systemImage: "arrow.up.right.circle")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .foregroundStyle(BullseyeTheme.textPrimary)
                .background(BullseyeTheme.glassFill)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }

            if let paperMessage {
                Text(paperMessage)
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
    }

    private func followPaper(_ p: Prediction) async {
        let notional = Double(betAmount) ?? PortfolioView.defaultBetAmount
        PortfolioView.saveDefaultBet(notional)
        do {
            _ = try await APIService.shared.openPaperPosition(predictionId: p.id, notional: notional)
            paperMessage = String(format: "Opened $%.0f paper bet — see Portfolio tab", notional)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func addWatchlist(_ ticker: String, _ name: String) async {
        do {
            _ = try await APIService.shared.addToWatchlist(ticker: ticker, companyName: name)
            paperMessage = "\(ticker) added to watchlist"
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func factorsSection(_ factors: [AnalysisFactor]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("What the model considered")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Each factor below was fed into the analysis from Yahoo Finance live data.")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)

            ForEach(factors) { factor in
                HStack(alignment: .top, spacing: 10) {
                    Circle()
                        .fill(impactColor(factor.impact))
                        .frame(width: 8, height: 8)
                        .padding(.top, 5)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(factor.category) · \(factor.label)")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(BullseyeTheme.textPrimary)
                        Text(factor.value)
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                    Spacer()
                    Text(factor.impact.uppercased())
                        .font(.caption2.bold())
                        .foregroundStyle(impactColor(factor.impact))
                }
            }
        }
    }

    private func impactColor(_ impact: String) -> Color {
        switch impact.lowercased() {
        case "bullish": BullseyeTheme.neonGreen
        case "bearish": .red
        default: .yellow
        }
    }

    private func comparisonSection(_ c: ComparisonAnalysis) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("AI vs Technical Bot")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            HStack {
                signalPill("Technical", c.technicalSignal.uppercased())
                signalPill("AI", c.aiDirection.uppercased())
                signalPill("Combined", String(format: "%.0f", c.combinedScore))
            }

            Text(c.summary)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            Text(c.agreement ? "Signals aligned ✓" : "Signals diverge — review both models")
                .font(.caption.bold())
                .foregroundStyle(c.agreement ? BullseyeTheme.neonGreen : .orange)
        }
        .padding(16)
        .glassCard()
    }

    private func signalPill(_ title: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.caption.bold()).foregroundStyle(BullseyeTheme.neonGreen)
            Text(title).font(.caption2).foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
    }

    private func directionBadge(_ direction: PredictionDirection) -> some View {
        Text(direction.rawValue.uppercased())
            .font(.caption.bold())
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(directionColor(direction).opacity(0.2))
            .foregroundStyle(directionColor(direction))
            .clipShape(Capsule())
    }

    private func directionColor(_ direction: PredictionDirection) -> Color {
        switch direction {
        case .bullish: BullseyeTheme.neonGreen
        case .bearish: .red
        case .neutral: .yellow
        }
    }

    private func gridRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(BullseyeTheme.textTertiary)
            Spacer()
            Text(value).foregroundStyle(BullseyeTheme.textPrimary)
        }
        .font(.subheadline)
    }

    private func isLikelyTicker(_ text: String) -> Bool {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        return t.count >= 1 && t.count <= 5 && t.allSatisfy(\.isLetter)
    }

    private func selectDirectTicker(_ symbol: String) async {
        query = symbol
        results = []
        hasSearched = false
        searchFocused = false
        selected = StockSearchResult(symbol: symbol, name: symbol, exchange: nil, currency: "USD")
        await loadQuote(symbol)
    }

    private func search() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 1 else { return }
        isSearching = true
        defer {
            isSearching = false
            hasSearched = true
        }
        do {
            results = try await APIService.shared.searchStocks(query: trimmed)
            searchFocused = false
        } catch {
            results = []
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func loadQuote(_ ticker: String) async {
        do {
            quote = try await APIService.shared.quote(ticker: ticker)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func runAnalysis() async {
        guard let ticker = selected?.symbol else { return }
        searchFocused = false
        isAnalyzing = true
        comparison = nil
        defer { isAnalyzing = false }
        do {
            let technicals = try await APIService.shared.fetchTechnicals(ticker: ticker)
            let result: Prediction
            switch engine {
            case .ai:
                result = try await APIService.shared.analyze(ticker: ticker, horizon: horizon)
                comparison = try await APIService.shared.fetchComparison(
                    ticker: ticker,
                    aiDirection: result.direction.rawValue,
                    aiConfidence: result.confidence
                )
                LocalAnalyticsStore.shared.ingest(result, technicals: technicals, source: "ai")
            case .technical:
                result = try await APIService.shared.analyzeTechnical(ticker: ticker, horizon: horizon)
                LocalAnalyticsStore.shared.ingest(result, technicals: technicals, source: "technical")
            }
            prediction = result
            await appModel.refreshTokens()
            await LocalAnalyticsStore.shared.syncFromRailway()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}
