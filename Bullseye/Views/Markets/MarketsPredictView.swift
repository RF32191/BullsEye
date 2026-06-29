//
//  MarketsPredictView.swift
//  Bullseye
//

import SwiftUI

struct MarketsPredictView: View {
    let platform: EventMarketPlatform
    @Bindable var appModel: AppViewModel

    @FocusState private var searchFocused: Bool
    @State private var query = ""
    @State private var markets: [EventMarket] = []
    @State private var selected: EventMarket?
    @State private var horizonDays = 30
    @State private var engine: PredictionEngine = .ai
    @State private var prediction: EventMarketPrediction?
    @State private var analytics: EventMarketAnalytics?
    @State private var eventComparison: EventMarketCompare?
    @State private var isLoading = false
    @State private var isPredicting = false
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
                    if let selected { selectedMarketCard(selected) }
                    if let analytics { analyticsStrip(analytics) }
                    enginePicker
                    horizonPicker
                    analyzeButton
                    if let prediction { predictionCard(prediction) }
                    if let eventComparison { comparisonSection(eventComparison) }
                    if markets.isEmpty && !isLoading && !hasSearched { trendingHint }
                    ForEach(markets.filter { selected == nil || $0.id != selected?.id }) { market in
                        marketPickRow(market)
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("\(platform.title) Predict")
        .task { await loadTrending() }
        .scrollDismissesKeyboard(.interactively)
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: { Text(errorMessage ?? "") }
    }

    private var tokenBanner: some View {
        TokenBalanceBanner(appModel: appModel)
    }

    private var searchSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Search \(platform.title) markets")
                .font(.headline).foregroundStyle(platform.textPrimary)
            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(platform.textTertiary)
                TextField("Politics, CPI, election…", text: $query)
                    .focused($searchFocused)
                    .autocorrectionDisabled()
                    .foregroundStyle(platform.textPrimary)
                    .onSubmit { Task { await search() } }
                Button("Search") { Task { await search() } }
                    .font(.caption.bold()).foregroundStyle(platform.accent)
            }
            .padding(12).eventGlassCard(platform: platform, cornerRadius: 12)
            .onChange(of: query) { _, newValue in
                searchTask?.cancel()
                let trimmed = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                guard trimmed.count >= 2 else { return }
                searchTask = Task {
                    try? await Task.sleep(for: .milliseconds(500))
                    guard !Task.isCancelled else { return }
                    await search()
                }
            }
            if isLoading { ProgressView().tint(platform.accent) }
            else if hasSearched && markets.isEmpty {
                Text("No markets found — try a broader term")
                    .font(.caption).foregroundStyle(platform.textSecondary)
            }
        }
    }

    private var trendingHint: some View {
        Text("Trending markets load on open — search above or pick from the list.")
            .font(.caption).foregroundStyle(platform.textTertiary)
    }

    private func selectedMarketCard(_ market: EventMarket) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(platform.title.uppercased())
                .font(.caption2.bold()).foregroundStyle(platform.accent)
            Text(market.question)
                .font(.subheadline.bold()).foregroundStyle(platform.textPrimary)
            if let yes = market.yesPrice {
                Text("Yes \(Int(yes * 100))% · Vol \(Formatters.compactNumber(market.volume))")
                    .font(.caption).foregroundStyle(platform.textSecondary)
            }
        }
        .padding(16).eventGlassCard(platform: platform)
    }

    private func analyticsStrip(_ a: EventMarketAnalytics) -> some View {
        HStack(spacing: 12) {
            pill("Tech", a.technicalSignal.uppercased())
            pill("Score", String(format: "%.0f", a.technicalScore))
            pill("Vol", Formatters.compactNumber(a.volume))
        }
    }

    private func pill(_ label: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.caption.bold()).foregroundStyle(platform.accent)
            Text(label).font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .frame(maxWidth: .infinity).padding(8).eventGlassCard(platform: platform, cornerRadius: 8)
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
                    .padding(12).eventGlassCard(platform: platform, cornerRadius: 12)
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
                if isPredicting { ProgressView().tint(.black) }
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
        .disabled(selected == nil || isPredicting)
    }

    private func marketPickRow(_ market: EventMarket) -> some View {
        Button {
            selected = market
            prediction = nil
            eventComparison = nil
            Task { await loadAnalytics(market) }
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                Text(market.question)
                    .font(.caption.bold())
                    .foregroundStyle(platform.textPrimary)
                    .multilineTextAlignment(.leading)
                if let yes = market.yesPrice {
                    Text("Yes \(Int(yes * 100))%")
                        .font(.caption2).foregroundStyle(platform.accent)
                }
            }
            .padding(12).eventGlassCard(platform: platform, cornerRadius: 12)
            .overlay {
                if selected?.id == market.id {
                    RoundedRectangle(cornerRadius: 12).strokeBorder(platform.accent.opacity(0.5), lineWidth: 1)
                }
            }
        }
    }

    private func predictionCard(_ p: EventMarketPrediction) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(p.predictedSide.uppercased()).font(.caption.bold())
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
            Text("Target Yes: \(Int(p.targetYesPrice * 100))% · Locked to tracker")
                .font(.caption2).foregroundStyle(platform.textTertiary)
        }
        .padding(16).eventGlassCard(platform: platform)
    }

    private func comparisonSection(_ c: EventMarketCompare) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("AI vs Technical Analytics").font(.headline).foregroundStyle(platform.textPrimary)
            Text(c.comparisonSummary).font(.caption).foregroundStyle(platform.textSecondary)
            Text(c.agreement ? "Signals aligned ✓" : "Signals diverge")
                .font(.caption.bold()).foregroundStyle(c.agreement ? platform.accent : .orange)
        }
        .padding(16).eventGlassCard(platform: platform)
    }

    private func loadTrending() async {
        isLoading = true
        defer { isLoading = false }
        markets = (try? await APIService.shared.fetchTrendingEventMarkets(platform: platform.rawValue)) ?? []
    }

    private func search() async {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard q.count >= 2 else { await loadTrending(); return }
        isLoading = true
        defer { isLoading = false; hasSearched = true }
        markets = (try? await APIService.shared.searchEventMarkets(query: q, platform: platform.rawValue)) ?? []
    }

    private func loadAnalytics(_ market: EventMarket) async {
        analytics = try? await APIService.shared.fetchEventMarketAnalytics(
            platform: market.platform, externalId: market.externalId
        )
    }

    private func runAnalysis() async {
        guard let market = selected else { return }
        isPredicting = true
        eventComparison = nil
        defer { isPredicting = false }
        do {
            switch engine {
            case .ai:
                let result = try await APIService.shared.predictEventMarket(
                    platform: market.platform, externalId: market.externalId, horizonDays: horizonDays
                )
                prediction = result
                eventComparison = try await APIService.shared.fetchEventMarketComparison(
                    platform: market.platform,
                    externalId: market.externalId,
                    aiSide: result.predictedSide,
                    aiConfidence: result.confidence
                )
            case .technical:
                prediction = try await APIService.shared.predictEventMarketTechnical(
                    platform: market.platform, externalId: market.externalId, horizonDays: horizonDays
                )
            }
            await loadAnalytics(market)
            await appModel.refreshTokens()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
