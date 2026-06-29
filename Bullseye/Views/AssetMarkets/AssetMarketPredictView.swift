//
//  AssetMarketPredictView.swift
//  Bullseye
//

import SwiftUI

struct AssetMarketPredictView: View {
    let platform: AssetMarketPlatform
    @Bindable var appModel: AppViewModel

    @FocusState private var searchFocused: Bool
    @State private var query = ""
    @State private var results: [AssetMarketQuote] = []
    @State private var selected: AssetMarketQuote?
    @State private var horizonDays = 30
    @State private var engine: PredictionEngine = .ai
    @State private var prediction: AssetMarketPrediction?
    @State private var comparison: ComparisonAnalysis?
    @State private var technicals: TechnicalAnalysis?
    @State private var isSearching = false
    @State private var isAnalyzing = false
    @State private var errorMessage: String?
    @State private var searchTask: Task<Void, Never>?
    @State private var hasSearched = false

    private let horizons = [7, 30, 90]

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    tokenBanner
                    searchSection
                    if let selected { selectedCard(selected) }
                    if let technicals { technicalsStrip(technicals) }
                    enginePicker
                    horizonPicker
                    analyzeButton
                    if let prediction { predictionCard(prediction) }
                    if let comparison { comparisonSection(comparison) }
                }
                .padding(20)
            }
        }
        .navigationTitle("\(platform.title) Predict")
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { searchFocused = false }
                    .foregroundStyle(platform.accent)
            }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: { Text(errorMessage ?? "") }
    }

    private var tokenBanner: some View {
        TokenBalanceBanner(appModel: appModel)
    }

    private var searchSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Search \(platform.title)")
                .font(.headline).foregroundStyle(platform.textPrimary)

            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(platform.textTertiary)
                TextField(searchPlaceholder, text: $query)
                    .focused($searchFocused)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .foregroundStyle(platform.textPrimary)
                    .onSubmit { Task { await search() } }
                Button("Search") { Task { await search() } }
                    .font(.caption.bold()).foregroundStyle(platform.accent)
            }
            .padding(12).assetGlassCard(platform: platform, cornerRadius: 12)
            .onChange(of: query) { _, newValue in
                searchTask?.cancel()
                let trimmed = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                guard trimmed.count >= 1 else { results = []; hasSearched = false; return }
                searchTask = Task {
                    try? await Task.sleep(for: .milliseconds(500))
                    guard !Task.isCancelled else { return }
                    await search()
                }
            }

            if isSearching { ProgressView().tint(platform.accent) }
            else if hasSearched && results.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("No matches for \"\(query)\"")
                        .font(.caption).foregroundStyle(platform.textSecondary)
                    Button("Use \"\(query.uppercased())\" anyway") {
                        Task { await selectDirect(query.uppercased()) }
                    }
                    .font(.caption.bold()).foregroundStyle(platform.accent)
                }
            }

            ForEach(results) { item in
                Button {
                    selected = item
                    query = item.symbol
                    results = []
                    hasSearched = false
                    Task { await loadTechnicals(item.symbol) }
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(item.symbol).font(.headline).foregroundStyle(platform.textPrimary)
                            Text(item.name).font(.caption).foregroundStyle(platform.textSecondary)
                        }
                        Spacer()
                        if selected?.symbol == item.symbol {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(platform.accent)
                        }
                    }
                    .padding(12).assetGlassCard(platform: platform, cornerRadius: 10)
                }
            }
        }
    }

    private var searchPlaceholder: String {
        switch platform {
        case .futures: "ES, NQ, CL, GC…"
        case .crypto: "BTC, ETH, SOL…"
        case .forex: "EURUSD, GBPUSD…"
        }
    }

    private func selectedCard(_ item: AssetMarketQuote) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(item.symbol).font(.title2.bold()).foregroundStyle(platform.accentGradient)
            Text(item.name).foregroundStyle(platform.textSecondary)
            if let price = item.price {
                HStack {
                    Text(Formatters.currency(price)).font(.title3.bold())
                    if let chg = item.changePct {
                        Text(String(format: "%+.2f%%", chg))
                            .foregroundStyle(chg >= 0 ? platform.accent : .orange)
                    }
                }
            }
            Text("Data: Yahoo Finance").font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16).assetGlassCard(platform: platform)
    }

    private func technicalsStrip(_ t: TechnicalAnalysis) -> some View {
        HStack(spacing: 12) {
            pill("RSI", String(format: "%.0f", t.rsi))
            pill("Signal", t.signal.uppercased())
            pill("Score", String(format: "%.0f", t.technicalScore ?? 0))
        }
    }

    private func pill(_ label: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.caption.bold()).foregroundStyle(platform.accent)
            Text(label).font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .frame(maxWidth: .infinity).padding(8).assetGlassCard(platform: platform, cornerRadius: 8)
    }

    private var enginePicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Prediction Engine").font(.headline).foregroundStyle(platform.textPrimary)
            ForEach(PredictionEngine.allCases) { option in
                Button { engine = option } label: {
                    HStack(spacing: 12) {
                        Image(systemName: option.icon)
                            .foregroundStyle(engine == option ? platform.accent : platform.textTertiary)
                        VStack(alignment: .leading) {
                            Text(option.title).font(.subheadline.bold()).foregroundStyle(platform.textPrimary)
                            Text(option.subtitle).font(.caption).foregroundStyle(platform.textSecondary)
                        }
                        Spacer()
                        if engine == option {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(platform.accent)
                        }
                    }
                    .padding(12).assetGlassCard(platform: platform, cornerRadius: 12)
                }
            }
        }
    }

    private var horizonPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Horizon").font(.headline).foregroundStyle(platform.textPrimary)
            HStack {
                ForEach(horizons, id: \.self) { days in
                    Button { horizonDays = days } label: {
                        Text("\(days)d")
                            .font(.caption.bold())
                            .frame(maxWidth: .infinity).padding(.vertical, 8)
                            .background(horizonDays == days ? platform.accent.opacity(0.2) : Color.clear)
                            .foregroundStyle(horizonDays == days ? platform.accent : platform.textSecondary)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
        }
    }

    private var analyzeButton: some View {
        Button { Task { await runAnalysis() } } label: {
            HStack {
                if isAnalyzing { ProgressView().tint(.black) }
                else {
                    Image(systemName: engine.icon)
                    Text(engine == .ai ? "Run AI Prediction" : "Run Technical Bot").font(.headline)
                }
            }
            .frame(maxWidth: .infinity).padding(.vertical, 16)
            .foregroundStyle(platform.backgroundDeep)
            .background(selected == nil ? Color.gray : platform.accent)
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .disabled(selected == nil || isAnalyzing)
    }

    private func predictionCard(_ p: AssetMarketPrediction) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(p.direction.uppercased()).font(.caption.bold())
                    .foregroundStyle(platform.backgroundDeep)
                    .padding(.horizontal, 10).padding(.vertical, 4)
                    .background(platform.accent).clipShape(Capsule())
                if p.aiModel == "technical-bot" {
                    Text("TECH BOT").font(.caption2.bold()).foregroundStyle(platform.accent)
                }
                Spacer()
                Text("\(Int(p.confidence))%").font(.caption.bold()).foregroundStyle(platform.accent)
            }
            Text(p.reasoning).font(.caption).foregroundStyle(platform.textSecondary)
            Text("Target \(Formatters.currency(p.targetPrice)) · Stop \(Formatters.currency(p.stopLoss))")
                .font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .padding(16).assetGlassCard(platform: platform)
    }

    private func comparisonSection(_ c: ComparisonAnalysis) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("AI vs Technical Bot").font(.headline).foregroundStyle(platform.textPrimary)
            Text(c.summary).font(.caption).foregroundStyle(platform.textSecondary)
            Text(c.agreement ? "Signals aligned ✓" : "Signals diverge")
                .font(.caption.bold()).foregroundStyle(c.agreement ? platform.accent : .orange)
        }
        .padding(16).assetGlassCard(platform: platform)
    }

    private func search() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        isSearching = true
        defer { isSearching = false; hasSearched = true }
        results = (try? await APIService.shared.searchAssetMarkets(assetClass: platform.rawValue, query: trimmed)) ?? []
        searchFocused = false
    }

    private func selectDirect(_ symbol: String) async {
        query = symbol
        results = []
        if let row = try? await APIService.shared.fetchAssetQuote(assetClass: platform.rawValue, symbol: symbol) {
            selected = row
            await loadTechnicals(symbol)
        }
    }

    private func loadTechnicals(_ symbol: String) async {
        technicals = try? await APIService.shared.fetchAssetTechnicals(assetClass: platform.rawValue, symbol: symbol)
    }

    private func runAnalysis() async {
        guard let symbol = selected?.symbol else { return }
        isAnalyzing = true
        comparison = nil
        defer { isAnalyzing = false }
        do {
            switch engine {
            case .ai:
                let result = try await APIService.shared.predictAssetMarket(
                    assetClass: platform.rawValue, symbol: symbol, horizonDays: horizonDays
                )
                prediction = result
                comparison = try await APIService.shared.fetchAssetComparison(
                    assetClass: platform.rawValue,
                    symbol: symbol,
                    aiDirection: result.direction,
                    aiConfidence: result.confidence
                )
            case .technical:
                prediction = try await APIService.shared.predictAssetMarketTechnical(
                    assetClass: platform.rawValue, symbol: symbol, horizonDays: horizonDays
                )
            }
            await loadTechnicals(symbol)
            await appModel.refreshTokens()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
