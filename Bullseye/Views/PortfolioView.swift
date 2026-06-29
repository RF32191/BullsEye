//
//  PortfolioView.swift
//  Bullseye
//

import SwiftUI

struct PortfolioView: View {
    @State private var watchlist: [WatchlistItem] = []
    @State private var paper: PaperPortfolioResponse?
    @State private var usage: UsageLimits?
    @State private var addTicker = ""
    @State private var depositAmount = "5000"
    @State private var betAmount = String(format: "%.0f", PortfolioView.defaultBetAmount)
    @State private var autoFlowWatch = UserDefaults.standard.bool(forKey: "autoFlowWatchlist")
    @State private var showError = false
    @State private var errorMessage: String?
    @State private var showSuccess = false
    @State private var successMessage: String?
    @State private var broker = BrokerLinkService.preferredBroker

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                header
                walletSection
                brokerSection
                openPositionsSection
                closedHistorySection
                watchlistSection
            }
            .padding(20)
        }
        .navigationTitle("Portfolio")
        .refreshable { await load() }
        .task { await load() }
        .alert("Error", isPresented: $showError) {
            Button("OK") { errorMessage = nil }
        } message: { Text(errorMessage ?? "") }
        .alert("Success", isPresented: $showSuccess) {
            Button("OK") { successMessage = nil }
        } message: { Text(successMessage ?? "") }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Fake Money Portfolio")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Practice with virtual cash — track wins and losses from real market prices.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    @ViewBuilder
    private var walletSection: some View {
        if let account = paper?.account {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Available cash")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                        Text(String(format: "$%.2f", account.cashBalance))
                            .font(.title.bold())
                            .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Total equity")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                        Text(String(format: "$%.0f", account.equity))
                            .font(.headline)
                            .foregroundStyle(BullseyeTheme.textPrimary)
                    }
                }

                HStack(spacing: 10) {
                    walletStat("Total P/L", String(format: "$%+.0f", account.totalPnlUsd), account.totalPnlUsd >= 0)
                    walletStat("Return", String(format: "%+.1f%%", account.totalReturnPct), account.totalReturnPct >= 0)
                    walletStat("Win rate", account.closedWinRatePct.map { String(format: "%.0f%%", $0) } ?? "—", true)
                }

                HStack(spacing: 8) {
                    TextField("Deposit $", text: $depositAmount)
                        .keyboardType(.decimalPad)
                        .padding(10)
                        .background(BullseyeTheme.glassFill)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    Button("Add cash") { Task { await deposit() } }
                        .font(.caption.bold())
                        .foregroundStyle(BullseyeTheme.neonGreen)
                }

                HStack(spacing: 8) {
                    Text("Default bet:")
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                    TextField("$", text: $betAmount)
                        .keyboardType(.decimalPad)
                        .frame(width: 90)
                        .padding(8)
                        .background(BullseyeTheme.glassFill)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    Spacer()
                    Button("Reset $10k") { Task { await resetWallet() } }
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
            .padding(16)
            .glassCard()
        }
    }

    private func walletStat(_ label: String, _ value: String, _ positive: Bool) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.subheadline.bold())
                .foregroundStyle(positive ? BullseyeTheme.neonGreen : .orange)
            Text(label)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .glassCard(cornerRadius: 10)
    }

    private var brokerSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Preferred Broker")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Picker("Broker", selection: $broker) {
                ForEach(PreferredBroker.allCases) { b in
                    Text(b.displayName).tag(b)
                }
            }
            .pickerStyle(.segmented)
            .onChange(of: broker) { _, new in BrokerLinkService.preferredBroker = new }
        }
        .padding(16)
        .glassCard()
    }

    @ViewBuilder
    private var openPositionsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Open bets")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            let open = paper?.positions.filter(\.isOpen) ?? []
            if open.isEmpty {
                Text("Bet from Predict, Flow, or Live tabs. Cash is deducted when you open; returned with P/L when you close.")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }

            ForEach(open) { pos in
                positionRow(pos, showClose: true)
            }
        }
        .padding(16)
        .glassCard()
    }

    @ViewBuilder
    private var closedHistorySection: some View {
        let closed = paper?.positions.filter { !$0.isOpen }.prefix(10) ?? []
        if !closed.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                Text("Closed — realized P/L")
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                ForEach(Array(closed)) { pos in
                    positionRow(pos, showClose: false)
                }
            }
            .padding(16)
            .glassCard()
        }
    }

    private func positionRow(_ pos: PaperPosition, showClose: Bool) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(pos.ticker).font(.headline).foregroundStyle(BullseyeTheme.textPrimary)
                    if let src = pos.source {
                        Text(src)
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(BullseyeTheme.neonGreen.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }
                Text("\(pos.direction.capitalized) · $\(Int(pos.notional)) bet · entry \(Formatters.currency(pos.entryPrice))")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text(String(format: "%+.1f%%", pos.pnlPct))
                    .font(.headline)
                    .foregroundStyle(pos.pnlPct >= 0 ? BullseyeTheme.neonGreen : .orange)
                Text(String(format: "$%+.0f", pos.pnlUsd))
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
                if showClose {
                    Button("Close") { Task { await closePosition(pos.id) } }
                        .font(.caption.bold())
                        .foregroundStyle(.orange)
                }
            }
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    private var watchlistSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Watchlist")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            Toggle(isOn: $autoFlowWatch) {
                Text("Auto flow-watch watchlist tickers")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textPrimary)
            }
            .tint(BullseyeTheme.neonGreen)
            .onChange(of: autoFlowWatch) { _, v in
                UserDefaults.standard.set(v, forKey: "autoFlowWatchlist")
                if v { syncFlowWatchlist() }
            }

            HStack {
                TextField("Add ticker", text: $addTicker)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                Button("Add") { Task { await addItem() } }
                    .font(.caption.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }

            ForEach(watchlist) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(item.ticker).font(.headline)
                        Text(item.companyName).font(.caption).foregroundStyle(BullseyeTheme.textSecondary)
                    }
                    Spacer()
                    Button {
                        TradeAlertManager.shared.toggleFlowWatch(ticker: item.ticker)
                    } label: {
                        Image(systemName: TradeAlertManager.shared.isWatchingFlow(ticker: item.ticker) ? "bell.fill" : "bell")
                            .foregroundStyle(BullseyeTheme.neonGreen)
                    }
                    Button(role: .destructive) { Task { await removeItem(item.ticker) } } label: {
                        Image(systemName: "trash").foregroundStyle(.red.opacity(0.8))
                    }
                }
                .padding(12)
                .glassCard(cornerRadius: 12)
            }
        }
    }

    private func load() async {
        watchlist = (try? await APIService.shared.fetchWatchlist()) ?? []
        paper = try? await APIService.shared.fetchPaperPortfolio()
        usage = try? await APIService.shared.fetchUsageLimits()
        if autoFlowWatch { syncFlowWatchlist() }
    }

    private func syncFlowWatchlist() {
        for item in watchlist where !TradeAlertManager.shared.isWatchingFlow(ticker: item.ticker) {
            TradeAlertManager.shared.toggleFlowWatch(ticker: item.ticker)
        }
    }

    private func deposit() async {
        guard let amount = Double(depositAmount), amount > 0 else { return }
        do {
            _ = try await APIService.shared.depositPaperCash(amount: amount)
            successMessage = String(format: "Added $%.0f fake cash", amount)
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func resetWallet() async {
        do {
            _ = try await APIService.shared.resetPaperWallet()
            successMessage = "Wallet reset to $10,000"
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func closePosition(_ id: String) async {
        do {
            _ = try await APIService.shared.closePaperPosition(id: id)
            successMessage = "Position closed — P/L added to cash"
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func addItem() async {
        let t = addTicker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !t.isEmpty else { return }
        do {
            _ = try await APIService.shared.addToWatchlist(ticker: t, companyName: nil)
            addTicker = ""
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func removeItem(_ ticker: String) async {
        do {
            try await APIService.shared.removeFromWatchlist(ticker: ticker)
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    static var defaultBetAmount: Double {
        Double(UserDefaults.standard.string(forKey: "defaultBetAmount") ?? "1000") ?? 1000
    }

    static func saveDefaultBet(_ amount: Double) {
        UserDefaults.standard.set(String(format: "%.0f", amount), forKey: "defaultBetAmount")
    }
}
