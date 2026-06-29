//
//  CategoryWalletView.swift
//  Bullseye
//

import SwiftUI

struct CategoryWalletView: View {
    let category: String
    var title: String?
    var accent: Color = BullseyeTheme.neonGreen

    @State private var portfolio: CategoryPaperPortfolioResponse?
    @State private var allWallets: [CategoryPaperWallet] = []
    @State private var depositAmount = "5000"
    @State private var betAmount = "1000"
    @State private var buySymbol = ""
    @State private var buyDirection = "bullish"
    @State private var showError = false
    @State private var errorMessage: String?
    @State private var showSuccess = false
    @State private var successMessage: String?

    private var displayTitle: String {
        title ?? CategoryPaperWallet.displayNames[category] ?? category.capitalized
    }

    private var isEventMarket: Bool {
        category == "polymarket" || category == "kalshi"
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                header
                if !allWallets.isEmpty { walletsHub }
                walletSection
                manualBuySection
                openPositionsSection
                closedHistorySection
            }
            .padding(20)
        }
        .navigationTitle("\(displayTitle) Wallet")
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
            Text("Fake Money — \(displayTitle)")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text(isEventMarket
                 ? "Buy YES/NO contracts at live odds. P/L tracks probability moves — not real money."
                 : "Practice with virtual cash using live market prices. Track theoretical wins and losses.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    private var walletsHub: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("All category wallets")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(allWallets) { w in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(w.displayName)
                                .font(.caption.bold())
                                .foregroundStyle(w.category == category ? accent : BullseyeTheme.textSecondary)
                            Text(String(format: "$%.0f", w.equity))
                                .font(.subheadline.bold())
                                .foregroundStyle(BullseyeTheme.textPrimary)
                            Text(String(format: "%+.1f%%", w.totalReturnPct))
                                .font(.caption2)
                                .foregroundStyle(w.totalReturnPct >= 0 ? BullseyeTheme.neonGreen : .orange)
                        }
                        .padding(12)
                        .frame(width: 110, alignment: .leading)
                        .background(w.category == category ? accent.opacity(0.12) : BullseyeTheme.glassFill)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(w.category == category ? accent.opacity(0.4) : Color.clear, lineWidth: 1)
                        )
                    }
                }
            }
        }
        .padding(16)
        .glassCard()
    }

    @ViewBuilder
    private var walletSection: some View {
        if let account = portfolio?.account {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Available cash")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                        Text(String(format: "$%.2f", account.cashBalance))
                            .font(.title.bold())
                            .foregroundStyle(accent)
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
                        .foregroundStyle(accent)
                }

                Button("Reset $10k") { Task { await resetWallet() } }
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
            .padding(16)
            .glassCard()
        }
    }

    private var manualBuySection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Manual fake buy")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            TextField(isEventMarket ? "Market ID or slug" : "Symbol", text: $buySymbol)
                .textInputAutocapitalization(.characters)
                .autocorrectionDisabled()
                .padding(10)
                .background(BullseyeTheme.glassFill)
                .clipShape(RoundedRectangle(cornerRadius: 10))

            Picker("Direction", selection: $buyDirection) {
                if isEventMarket {
                    Text("YES").tag("yes")
                    Text("NO").tag("no")
                } else {
                    Text("Long / Bullish").tag("bullish")
                    Text("Short / Bearish").tag("bearish")
                }
            }
            .pickerStyle(.segmented)

            HStack {
                TextField("Bet $", text: $betAmount)
                    .keyboardType(.decimalPad)
                    .padding(10)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Buy") { Task { await manualBuy() } }
                    .font(.caption.bold())
                    .foregroundStyle(accent)
            }
        }
        .padding(16)
        .glassCard()
    }

    @ViewBuilder
    private var openPositionsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Open positions")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            let open = portfolio?.positions.filter(\.isOpen) ?? []
            if open.isEmpty {
                Text("Open bets from Predict/Live tabs or use manual buy above.")
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
        let closed = portfolio?.positions.filter { !$0.isOpen }.prefix(10) ?? []
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

    private func positionRow(_ pos: PaperPosition, showClose: Bool) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(pos.ticker).font(.headline).foregroundStyle(BullseyeTheme.textPrimary)
                Text("\(pos.direction.capitalized) · $\(Int(pos.notional)) · entry \(formatPrice(pos.entryPrice))")
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
                    Button("Sell") { Task { await sellPosition(pos.id) } }
                        .font(.caption.bold())
                        .foregroundStyle(.orange)
                }
            }
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    private func formatPrice(_ price: Double) -> String {
        if isEventMarket {
            return String(format: "%.1f¢", price * 100)
        }
        return Formatters.currency(price)
    }

    private func load() async {
        portfolio = try? await APIService.shared.fetchCategoryPortfolio(category: category)
        allWallets = (try? await APIService.shared.fetchCategoryWallets())?.wallets ?? []
    }

    private func deposit() async {
        guard let amount = Double(depositAmount), amount > 0 else { return }
        do {
            _ = try await APIService.shared.depositCategoryPaper(category: category, amount: amount)
            successMessage = String(format: "Added $%.0f fake cash", amount)
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func resetWallet() async {
        do {
            _ = try await APIService.shared.resetCategoryPaper(category: category)
            successMessage = "Wallet reset to $10,000"
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func manualBuy() async {
        let sym = buySymbol.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !sym.isEmpty, let notional = Double(betAmount), notional >= 50 else { return }
        do {
            _ = try await APIService.shared.buyCategoryPaper(
                category: category, symbol: sym, direction: buyDirection, notional: notional
            )
            successMessage = String(format: "Opened $%.0f fake position", notional)
            showSuccess = true
            buySymbol = ""
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func sellPosition(_ id: String) async {
        do {
            _ = try await APIService.shared.sellCategoryPaper(category: category, positionId: id)
            successMessage = "Sold — P/L added to wallet cash"
            showSuccess = true
            await load()
        } catch { errorMessage = error.localizedDescription; showError = true }
    }
}
