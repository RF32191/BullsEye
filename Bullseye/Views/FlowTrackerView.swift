//
//  FlowTrackerView.swift
//  Bullseye
//

import SwiftUI

struct FlowTrackerView: View {
    @Bindable var appModel: AppViewModel
    @ObservedObject private var alerts = TradeAlertManager.shared

    @FocusState private var searchFocused: Bool
    @State private var query = ""
    @State private var results: [StockSearchResult] = []
    @State private var selected: StockSearchResult?
    @State private var horizon = PredictionHorizonOption.defaultStock
    @State private var engine: PredictionEngine = .technical
    @State private var flow: FlowAnalysis?
    @State private var prediction: Prediction?
    @State private var isSearching = false
    @State private var isLoading = false
    @State private var isPredicting = false
    @State private var showError = false
    @State private var errorMessage: String?
    @State private var successMessage: String?
    @State private var showSuccess = false
    @State private var searchTask: Task<Void, Never>?
    @State private var betAmount = String(format: "%.0f", PortfolioView.defaultBetAmount)
    @State private var politicianSlug = ""

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                introBanner
                searchSection
                if let selected {
                    selectedCard(selected)
                }
                PredictionHorizonPicker(selection: $horizon, options: PredictionHorizonOption.stockOptions, accent: BullseyeTheme.neonGreen)
                HStack {
                    Text("Bet amount $")
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                    TextField("1000", text: $betAmount)
                        .keyboardType(.decimalPad)
                        .padding(8)
                        .background(BullseyeTheme.glassFill)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                enginePicker
                analyzeFlowButton
                if let flow {
                    flowResult(flow)
                }
                if let prediction {
                    predictionCard(prediction)
                }
                alertSettingsSection
            }
            .padding(20)
        }
        .navigationTitle("Money Flow")
        .onChange(of: horizon) { _, _ in
            if selected != nil { Task { await loadFlow() } }
        }
        .onChange(of: betAmount) { _, v in
            if let n = Double(v) { PortfolioView.saveDefaultBet(n) }
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
        .alert("Paper trade", isPresented: $showSuccess) {
            Button("OK") { successMessage = nil }
        } message: {
            Text(successMessage ?? "")
        }
    }

    private var introBanner: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Track inflows & timing", systemImage: "arrow.left.arrow.right.circle.fill")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text("Combines congress/insider money, volume, and technicals to suggest when to push in, hold, or pull out.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(BullseyeTheme.glassBorder, lineWidth: 1))
    }

    private var searchSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Stock")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BullseyeTheme.textPrimary)
            HStack {
                TextField("Search ticker (e.g. NVDA)", text: $query)
                    .focused($searchFocused)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .onChange(of: query) { _, newValue in
                        searchTask?.cancel()
                        searchTask = Task {
                            try? await Task.sleep(nanoseconds: 350_000_000)
                            guard !Task.isCancelled else { return }
                            await search(query: newValue)
                        }
                    }
                if isSearching {
                    ProgressView().tint(BullseyeTheme.neonGreen)
                }
            }
            .padding(12)
            .background(BullseyeTheme.glassFill)
            .clipShape(RoundedRectangle(cornerRadius: 12))

            if !results.isEmpty && selected == nil {
                ForEach(results.prefix(6)) { item in
                    Button {
                        selected = item
                        query = item.symbol
                        results = []
                        searchFocused = false
                        Task { await loadFlow() }
                    } label: {
                        HStack {
                            Text(item.symbol).font(.headline).foregroundStyle(BullseyeTheme.neonGreen)
                            Text(item.name).font(.caption).foregroundStyle(BullseyeTheme.textSecondary).lineLimit(1)
                            Spacer()
                        }
                        .padding(.vertical, 8)
                    }
                }
            }
        }
    }

    private func selectedCard(_ item: StockSearchResult) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(item.symbol).font(.title2.bold()).foregroundStyle(BullseyeTheme.textPrimary)
                Text(item.name).font(.caption).foregroundStyle(BullseyeTheme.textSecondary)
            }
            Spacer()
            if alerts.isWatchingFlow(ticker: item.symbol) {
                Label("Alerts on", systemImage: "bell.fill")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            Button {
                alerts.toggleFlowWatch(ticker: item.symbol)
            } label: {
                Image(systemName: alerts.isWatchingFlow(ticker: item.symbol) ? "bell.fill" : "bell")
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        .padding(14)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var enginePicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Prediction engine")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BullseyeTheme.textPrimary)
            Picker("Engine", selection: $engine) {
                ForEach(PredictionEngine.allCases, id: \.self) { e in
                    Text(e.title).tag(e)
                }
            }
            .pickerStyle(.segmented)
        }
    }

    private var analyzeFlowButton: some View {
        VStack(spacing: 10) {
            Button {
                Task { await loadFlow() }
            } label: {
                HStack {
                    if isLoading { ProgressView().tint(.black) }
                    else { Image(systemName: "waveform.path.ecg") }
                    Text("Analyze money flow")
                        .font(.headline)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .foregroundStyle(.black)
                .background(BullseyeTheme.neonGreen)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .disabled(selected == nil || isLoading)

            Button {
                Task { await runPrediction() }
            } label: {
                HStack {
                    if isPredicting { ProgressView().tint(BullseyeTheme.neonGreen) }
                    else { Image(systemName: engine.icon) }
                    Text("Lock \(horizon.label) prediction")
                        .font(.subheadline.weight(.semibold))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .foregroundStyle(BullseyeTheme.neonGreen)
                .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(BullseyeTheme.neonGreen, lineWidth: 1))
            }
            .disabled(selected == nil || isPredicting)
        }
    }

    private func flowResult(_ flow: FlowAnalysis) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                actionBadge(flow.action)
                Spacer()
                Text("Score \(Int(flow.flowScore))")
                    .font(.caption.bold())
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            Text(flow.timingNote)
                .font(.subheadline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            Text(flow.reasoning)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            HStack(spacing: 12) {
                flowMetric("Congress", formatUsd(flow.congressNetUsd))
                flowMetric("Insider", formatUsd(flow.insiderNetUsd))
                if let vol = flow.volumeRatio {
                    flowMetric("Volume", String(format: "%.1fx", vol))
                }
            }

            HStack(spacing: 12) {
                flowMetric("Target", String(format: "$%.2f", flow.suggestedTarget))
                flowMetric("Stop", String(format: "$%.2f", flow.suggestedStop))
            }

            ForEach(flow.components) { component in
                HStack {
                    Text(component.label).font(.caption).foregroundStyle(BullseyeTheme.textSecondary)
                    Spacer()
                    Text(component.value).font(.caption.bold()).foregroundStyle(impactColor(component.impact))
                }
            }

            if let enhanced = flow.enhancedSignals {
                enhancedSignalsSection(enhanced)
            }

            Button {
                Task { await openPaperTrade(flow: flow) }
            } label: {
                Label("Simulate $\(betAmount) paper trade", systemImage: "banknote")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .foregroundStyle(BullseyeTheme.neonGreen)
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(BullseyeTheme.neonGreen, lineWidth: 1))
            }

            Text(flow.disclaimer)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary.opacity(0.8))
        }
        .padding(16)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(BullseyeTheme.glassBorder, lineWidth: 1))
    }

    private func predictionCard(_ pred: Prediction) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Locked prediction")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("\(pred.direction.rawValue.capitalized) · \(pred.horizonLabel ?? "\(pred.horizonDays)d")")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text(pred.reasoning)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
        .padding(14)
        .background(BullseyeTheme.neonGreen.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var alertSettingsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle(isOn: $alerts.alertsEnabled) {
                Text("Live trade alerts")
                    .foregroundStyle(BullseyeTheme.textPrimary)
            }
            .tint(BullseyeTheme.neonGreen)

            Toggle(isOn: $alerts.flowAlertsEnabled) {
                Text("Money flow alerts (watched tickers)")
                    .foregroundStyle(BullseyeTheme.textPrimary)
            }
            .tint(BullseyeTheme.neonGreen)

            AlertFrequencyPicker(selection: $alerts.alertFrequency, accent: BullseyeTheme.neonGreen)

            if !alerts.flowWatchedTickers.isEmpty {
                Text("Flow watching: \(alerts.flowWatchedTickers.joined(separator: ", "))")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            HStack {
                TextField("Politician slug (e.g. nancy-pelosi)", text: $politicianSlug)
                    .font(.caption)
                    .padding(8)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                Button("Watch") {
                    Task { await addPoliticianWatch() }
                }
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        .padding(16)
        .background(BullseyeTheme.glassFill)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private func actionBadge(_ action: String) -> some View {
        let (label, color, icon) = actionStyle(action)
        return Label(label, systemImage: icon)
            .font(.headline)
            .foregroundStyle(color)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
    }

    private func actionStyle(_ action: String) -> (String, Color, String) {
        switch action.lowercased() {
        case "push": return ("PUSH IN", BullseyeTheme.neonGreen, "arrow.up.circle.fill")
        case "pull": return ("PULL OUT", .red, "arrow.down.circle.fill")
        default: return ("HOLD", .orange, "pause.circle.fill")
        }
    }

    private func flowMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).font(.caption2).foregroundStyle(BullseyeTheme.textSecondary)
            Text(value).font(.caption.bold()).foregroundStyle(BullseyeTheme.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func impactColor(_ impact: String) -> Color {
        switch impact {
        case "positive": BullseyeTheme.neonGreen
        case "negative": .red
        default: BullseyeTheme.textPrimary
        }
    }

    private func enhancedSignalsSection(_ s: EnhancedFlowSignals) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Enhanced signals")
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.neonGreen)
            if let si = s.shortInterestPct { signalLine("Short interest", String(format: "%.1f%%", si)) }
            if let bias = s.analystGradeBias { signalLine("Analyst bias", bias) }
            if let inst = s.institutionalNetChangePct { signalLine("Institutional Δ", String(format: "%+.1f%%", inst)) }
            if let cluster = s.insiderClusterBuys, cluster > 0 { signalLine("Insider cluster", "\(cluster) buyers") }
            if let rs = s.sectorRelativeStrengthPct { signalLine("vs sector", String(format: "%+.1f%%", rs)) }
            if let earn = s.nextEarningsDate { signalLine("Next earnings", earn) }
            if let intra = s.intraday, intra.available == true {
                signalLine("VWAP", intra.aboveVwap == true ? "Above" : "Below")
                if let chg = intra.sessionChangePct { signalLine("Session", String(format: "%+.1f%%", chg)) }
            }
            if let sources = s.dataSources?.joined(separator: ", ") {
                Text("Sources: \(sources)").font(.caption2).foregroundStyle(BullseyeTheme.textTertiary)
            }
        }
        .padding(.top, 6)
    }

    private func signalLine(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).font(.caption2).foregroundStyle(BullseyeTheme.textSecondary)
            Spacer()
            Text(value).font(.caption2.bold()).foregroundStyle(BullseyeTheme.textPrimary)
        }
    }

    private func openPaperTrade(flow: FlowAnalysis) async {
        let dir = flow.action == "pull" ? "pull" : "push"
        let notional = Double(betAmount) ?? PortfolioView.defaultBetAmount
        PortfolioView.saveDefaultBet(notional)
        do {
            _ = try await APIService.shared.openPaperFromFlow(ticker: flow.ticker, direction: dir, notional: notional)
            successMessage = String(format: "Opened $%.0f paper bet on %@", notional, flow.ticker)
            showSuccess = true
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func formatUsd(_ value: Double) -> String {
        let prefix = value >= 0 ? "+" : ""
        if abs(value) >= 1_000_000 { return "\(prefix)$\(String(format: "%.1fM", value / 1_000_000))" }
        if abs(value) >= 1_000 { return "\(prefix)$\(String(format: "%.0fK", value / 1_000))" }
        return "\(prefix)$\(String(format: "%.0f", value))"
    }

    private func addPoliticianWatch() async {
        let slug = politicianSlug.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !slug.isEmpty else { return }
        do {
            var watches = try await APIService.shared.fetchUserWatches()
            var slugs = watches.politicianSlugs
            if !slugs.contains(slug) { slugs.append(slug) }
            _ = try await APIService.shared.updateUserWatches(UserWatchesUpdate(politicianSlugs: slugs))
            politicianSlug = ""
            successMessage = "Watching politician: \(slug)"
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func search(query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 1 else { results = []; return }
        isSearching = true
        defer { isSearching = false }
        do {
            results = try await APIService.shared.searchStocks(query: trimmed)
        } catch {
            results = []
        }
    }

    private func loadFlow() async {
        guard let ticker = selected?.symbol else { return }
        isLoading = true
        prediction = nil
        defer { isLoading = false }
        do {
            flow = try await APIService.shared.fetchFlowAnalysis(ticker: ticker, horizon: horizon)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func runPrediction() async {
        guard let ticker = selected?.symbol else { return }
        isPredicting = true
        defer { isPredicting = false }
        do {
            prediction = try await APIService.shared.predictFlow(ticker: ticker, horizon: horizon, engine: engine)
            await appModel.refreshTokens()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}
