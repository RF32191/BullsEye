//
//  TrendView.swift
//  Bullseye
//

import Charts
import SwiftUI

struct TrendView: View {
    @FocusState private var searchFocused: Bool
    @State private var query = ""
    @State private var ticker = "NVDA"
    @State private var trend: TrendResponse?
    @State private var isLoading = false
    @State private var showError = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                searchBar
                if isLoading {
                    ProgressView().tint(BullseyeTheme.neonGreen).frame(maxWidth: .infinity)
                }
                if let trend {
                    liveHeader(trend)
                    priceChart(trend)
                    rsiChart(trend)
                    macdChart(trend)
                    allVariablesSection(trend.technicals)
                    eventsSection(trend.events ?? [])
                    educationSection
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
        .navigationTitle("Live Trends")
        .task { await loadTrend() }
        .alert("Error", isPresented: $showError) {
            Button("OK") {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var searchBar: some View {
        HStack {
            TextField("Import ticker (e.g. AAPL)", text: $query)
                .focused($searchFocused)
                #if os(iOS)
                .textInputAutocapitalization(.characters)
                .submitLabel(.search)
                #endif
                .autocorrectionDisabled()
                .onSubmit { importTicker() }
                .foregroundStyle(BullseyeTheme.textPrimary)
            Button("Load") { importTicker() }
                .foregroundStyle(BullseyeTheme.neonGreen)
                .fontWeight(.semibold)
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    private func liveHeader(_ trend: TrendResponse) -> some View {
        HStack {
            VStack(alignment: .leading) {
                Text(trend.symbol).font(.title.bold()).foregroundStyle(BullseyeTheme.accentGradient)
                Text(Formatters.currency(trend.technicals.price))
                    .font(.title3)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text("Signal: \(trend.technicals.signal.uppercased()) · Score \(Int(trend.technicals.technicalScore ?? 0))/100")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.neonGreen)
                TrendMarkBadge(
                    label: trend.technicals.trendLabel,
                    arrow: trend.technicals.trendArrow,
                    strength: trend.technicals.trendStrength,
                    summary: trend.technicals.trendSummary
                )
            }
            Spacer()
            if let pct = trend.technicals.trendPct30d {
                Text(Formatters.percent(pct, signed: true))
                    .font(.headline)
                    .foregroundStyle(pct >= 0 ? BullseyeTheme.neonGreen : .red)
            }
        }
    }

    private func priceChart(_ trend: TrendResponse) -> some View {
        chartCard(title: "Price Trend (90d)", subtitle: "Closing price each session") {
            Chart(trend.points) { point in
                LineMark(
                    x: .value("Date", point.date),
                    y: .value("Close", point.close)
                )
                .foregroundStyle(BullseyeTheme.neonGreen.gradient)
                .interpolationMethod(.catmullRom)
            }
            .frame(height: 200)
            .chartYAxisLabel("USD")
        }
    }

    private func rsiChart(_ trend: TrendResponse) -> some View {
        let series = (trend.indicators ?? []).compactMap { point -> (String, Double)? in
            guard let rsi = point.rsi else { return nil }
            return (point.date, rsi)
        }
        return chartCard(title: "RSI (14)", subtitle: "Above 70 = overbought · Below 30 = oversold") {
            Chart {
                ForEach(series, id: \.0) { item in
                    LineMark(x: .value("Date", item.0), y: .value("RSI", item.1))
                        .foregroundStyle(Color.orange.gradient)
                }
                RuleMark(y: .value("Overbought", 70))
                    .foregroundStyle(.red.opacity(0.4))
                    .lineStyle(StrokeStyle(dash: [4, 4]))
                RuleMark(y: .value("Oversold", 30))
                    .foregroundStyle(BullseyeTheme.neonGreen.opacity(0.4))
                    .lineStyle(StrokeStyle(dash: [4, 4]))
            }
            .frame(height: 160)
            .chartYScale(domain: 0...100)
        }
    }

    private func macdChart(_ trend: TrendResponse) -> some View {
        let series = (trend.indicators ?? []).compactMap { point -> (String, Double)? in
            guard let hist = point.macdHist else { return nil }
            return (point.date, hist)
        }
        return chartCard(title: "MACD Histogram", subtitle: "Positive = bullish momentum · Negative = bearish") {
            Chart(series, id: \.0) { item in
                BarMark(
                    x: .value("Date", item.0),
                    y: .value("Hist", item.1)
                )
                .foregroundStyle(item.1 >= 0 ? BullseyeTheme.neonGreen : Color.red)
            }
            .frame(height: 160)
        }
    }

    private func allVariablesSection(_ tech: TechnicalAnalysis) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("All Technical Variables")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                variableCell("RSI", String(format: "%.1f", tech.rsi), hint: "Relative strength")
                variableCell("MACD", String(format: "%.3f", tech.macd), hint: "Trend momentum")
                variableCell("MACD Signal", String(format: "%.3f", tech.macdSignal), hint: "Signal line")
                variableCell("MACD Hist", String(format: "%.3f", tech.macdHist), hint: "Histogram")
                variableCell("EMA 12", Formatters.currency(tech.ema12), hint: "Short EMA")
                variableCell("EMA 26", Formatters.currency(tech.ema26), hint: "Long EMA")
                variableCell("SMA 50", tech.sma50.map { Formatters.currency($0) } ?? "—", hint: "50-day avg")
                variableCell("SMA 200", tech.sma200.map { Formatters.currency($0) } ?? "—", hint: "200-day avg")
                variableCell("P/E", tech.peRatio.map { String(format: "%.1f", $0) } ?? "—", hint: "Trailing P/E")
                variableCell("Forward P/E", tech.forwardPe.map { String(format: "%.1f", $0) } ?? "—", hint: "Forward P/E")
                variableCell("Beta", tech.beta.map { String(format: "%.2f", $0) } ?? "—", hint: "Market sensitivity")
                variableCell("EPS", tech.eps.map { String(format: "%.2f", $0) } ?? "—", hint: "Earnings/share")
                variableCell("52w High", tech.fiftyTwoWeekHigh.map { Formatters.currency($0) } ?? "—", hint: "Year high")
                variableCell("52w Low", tech.fiftyTwoWeekLow.map { Formatters.currency($0) } ?? "—", hint: "Year low")
                variableCell("From 52w High", tech.pctFrom52wHigh.map { Formatters.percent($0, signed: true) } ?? "—", hint: "Distance")
                variableCell("Volume", tech.volume.map { formatVolume($0) } ?? "—", hint: "Today")
                variableCell("Avg Volume", tech.avgVolume.map { formatVolume($0) } ?? "—", hint: "30-day avg")
                variableCell("Market Cap", tech.marketCap.map { formatMarketCap($0) } ?? "—", hint: "Total value")
                variableCell("30d Trend", tech.trendPct30d.map { Formatters.percent($0, signed: true) } ?? "—", hint: "Price change")
                variableCell("Bot Score", String(format: "%.0f", tech.technicalScore ?? 0), hint: "Combined score")
            }

            if let source = tech.dataSource {
                Text("Data: \(source)")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
        }
        .padding(16)
        .glassCard()
    }

    private func formatVolume(_ v: Double) -> String {
        if v >= 1_000_000 { return String(format: "%.1fM", v / 1_000_000) }
        if v >= 1_000 { return String(format: "%.0fK", v / 1_000) }
        return String(format: "%.0f", v)
    }

    private func formatMarketCap(_ v: Double) -> String {
        if v >= 1_000_000_000_000 { return String(format: "$%.2fT", v / 1_000_000_000_000) }
        if v >= 1_000_000_000 { return String(format: "$%.1fB", v / 1_000_000_000) }
        return String(format: "$%.0fM", v / 1_000_000)
    }

    private func variableCell(_ title: String, _ value: String, hint: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption2).foregroundStyle(BullseyeTheme.textTertiary)
            Text(value).font(.subheadline.bold()).foregroundStyle(BullseyeTheme.neonGreen)
            Text(hint).font(.caption2).foregroundStyle(BullseyeTheme.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(BullseyeTheme.chatAssistantFill)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func eventsSection(_ events: [UpcomingEvent]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Upcoming Events")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Plan around catalysts — volatility often rises into these dates.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            ForEach(events) { event in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(event.type.uppercased())
                            .font(.caption2.bold())
                            .foregroundStyle(.black)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(BullseyeTheme.neonGreen)
                            .clipShape(Capsule())
                        Text(event.date)
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                    Text(event.title)
                        .font(.subheadline.bold())
                        .foregroundStyle(BullseyeTheme.textPrimary)
                    Text(event.description)
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(12)
                .glassCard(cornerRadius: 12)
            }
        }
    }

    private var educationSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("How to read these charts")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("RSI measures speed of price moves. MACD histogram shows whether bullish momentum is strengthening or fading. EMA crossovers help confirm trend direction. Always combine charts with earnings dates and your locked predictions in the Tracker tab.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .glassCard()
    }

    private func chartCard<Content: View>(title: String, subtitle: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline).foregroundStyle(BullseyeTheme.textPrimary)
            Text(subtitle).font(.caption).foregroundStyle(BullseyeTheme.textSecondary)
            content()
        }
        .padding(16)
        .glassCard()
    }

    private func importTicker() {
        let symbol = query.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !symbol.isEmpty else { return }
        ticker = symbol
        query = symbol
        searchFocused = false
        Task { await loadTrend() }
    }

    private func loadTrend() async {
        isLoading = true
        defer { isLoading = false }
        do {
            trend = try await APIService.shared.fetchTrend(ticker: ticker)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}
