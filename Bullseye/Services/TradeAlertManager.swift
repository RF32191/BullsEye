//
//  TradeAlertManager.swift
//  Bullseye
//

import Combine
import Foundation
import UserNotifications

@MainActor
final class TradeAlertManager: ObservableObject {
    static let shared = TradeAlertManager()

    @Published var alertsEnabled: Bool {
        didSet {
            UserDefaults.standard.set(alertsEnabled, forKey: Self.enabledKey)
            restartPollingIfNeeded()
        }
    }

    @Published var flowAlertsEnabled: Bool {
        didSet {
            UserDefaults.standard.set(flowAlertsEnabled, forKey: Self.flowEnabledKey)
        }
    }

    @Published var alertFrequency: AlertFrequency {
        didSet {
            UserDefaults.standard.set(alertFrequency.rawValue, forKey: Self.frequencyKey)
            restartPollingIfNeeded()
        }
    }

    @Published private(set) var flowWatchedTickers: [String] = []

    @Published var flowScorePushThreshold: Double {
        didSet { UserDefaults.standard.set(flowScorePushThreshold, forKey: Self.pushThresholdKey) }
    }

    @Published var flowScorePullThreshold: Double {
        didSet { UserDefaults.standard.set(flowScorePullThreshold, forKey: Self.pullThresholdKey) }
    }

    private static let enabledKey = "tradeAlertsEnabled"
    private static let flowEnabledKey = "flowAlertsEnabled"
    private static let frequencyKey = "alertFrequency"
    private static let seenKey = "seenLiveTradeIds"
    private static let flowWatchKey = "flowWatchedTickers"
    private static let flowActionKey = "lastFlowActions"
    private static let pushThresholdKey = "flowScorePushThreshold"
    private static let pullThresholdKey = "flowScorePullThreshold"
    private static let lastFlowScoresKey = "lastFlowScores"

    private var pollTask: Task<Void, Never>?
    private var lastFlowActions: [String: String] = [:]
    private var lastFlowScores: [String: Double] = [:]

    private init() {
        alertsEnabled = UserDefaults.standard.object(forKey: Self.enabledKey) as? Bool ?? true
        flowAlertsEnabled = UserDefaults.standard.object(forKey: Self.flowEnabledKey) as? Bool ?? true
        flowScorePushThreshold = UserDefaults.standard.object(forKey: Self.pushThresholdKey) as? Double ?? 62
        flowScorePullThreshold = UserDefaults.standard.object(forKey: Self.pullThresholdKey) as? Double ?? 38
        let freqRaw = UserDefaults.standard.string(forKey: Self.frequencyKey) ?? AlertFrequency.normal.rawValue
        alertFrequency = AlertFrequency(rawValue: freqRaw) ?? .normal
        flowWatchedTickers = UserDefaults.standard.stringArray(forKey: Self.flowWatchKey) ?? []
        lastFlowActions = (UserDefaults.standard.dictionary(forKey: Self.flowActionKey) as? [String: String]) ?? [:]
        if let scores = UserDefaults.standard.dictionary(forKey: Self.lastFlowScoresKey) as? [String: Double] {
            lastFlowScores = scores
        }
    }

    func requestPermissionIfNeeded() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .notDetermined else { return }
        _ = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
    }

    private var digestQueue: [String] = []

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                await pollAllMarkets()
                await pollFlowWatches()
                try? await Task.sleep(nanoseconds: alertFrequency.intervalNanoseconds)
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }

    func isWatchingFlow(ticker: String) -> Bool {
        flowWatchedTickers.contains(ticker.uppercased())
    }

    func toggleFlowWatch(ticker: String) {
        let symbol = ticker.uppercased()
        if let idx = flowWatchedTickers.firstIndex(of: symbol) {
            flowWatchedTickers.remove(at: idx)
            lastFlowActions.removeValue(forKey: symbol)
        } else {
            flowWatchedTickers.append(symbol)
        }
        persistFlowWatchlist()
        persistFlowActions()
    }

    func pollAllMarkets() async {
        guard alertsEnabled else { return }
        digestQueue.removeAll()
        for market in ["stocks", "polymarket", "kalshi", "futures", "crypto", "forex"] {
            await checkMarket(market)
        }
        if alertFrequency == .digest, !digestQueue.isEmpty {
            await notify(
                title: "Bullseye daily digest",
                body: digestQueue.prefix(5).joined(separator: " · "),
                id: "digest-\(Int(Date().timeIntervalSince1970))"
            )
            digestQueue.removeAll()
        }
    }

    func pollFlowWatches() async {
        guard flowAlertsEnabled, !flowWatchedTickers.isEmpty else { return }
        for ticker in flowWatchedTickers {
            await checkFlow(ticker: ticker)
        }
    }

    private func restartPollingIfNeeded() {
        guard pollTask != nil else { return }
        startPolling()
    }

    private func persistFlowWatchlist() {
        UserDefaults.standard.set(flowWatchedTickers, forKey: Self.flowWatchKey)
    }

    private func persistFlowActions() {
        UserDefaults.standard.set(lastFlowActions, forKey: Self.flowActionKey)
    }

    private func checkFlow(ticker: String) async {
        guard let analysis = try? await APIService.shared.fetchFlowAnalysis(
            ticker: ticker,
            horizon: PredictionHorizonOption.defaultStock
        ) else { return }

        let symbol = ticker.uppercased()
        let previous = lastFlowActions[symbol]
        let prevScore = lastFlowScores[symbol]
        lastFlowActions[symbol] = analysis.action
        lastFlowScores[symbol] = analysis.flowScore
        persistFlowActions()
        UserDefaults.standard.set(lastFlowScores, forKey: Self.lastFlowScoresKey)

        if let previous, previous != analysis.action {
            let title: String
            switch analysis.action.lowercased() {
            case "push": title = "Push in · \(symbol)"
            case "pull": title = "Pull out · \(symbol)"
            default: title = "Hold · \(symbol)"
            }
            await notify(title: title, body: analysis.timingNote, id: "flow-\(symbol)-\(analysis.action)-\(Int(Date().timeIntervalSince1970))")
        }

        if let prevScore {
            if prevScore < flowScorePushThreshold && analysis.flowScore >= flowScorePushThreshold {
                await notify(
                    title: "Flow score high · \(symbol)",
                    body: "Score crossed \(Int(flowScorePushThreshold))+ (\(Int(analysis.flowScore))) — \(analysis.timingNote)",
                    id: "flow-score-push-\(symbol)-\(Int(Date().timeIntervalSince1970))"
                )
            }
            if prevScore > flowScorePullThreshold && analysis.flowScore <= flowScorePullThreshold {
                await notify(
                    title: "Flow score low · \(symbol)",
                    body: "Score fell below \(Int(flowScorePullThreshold)) (\(Int(analysis.flowScore))) — consider reducing exposure.",
                    id: "flow-score-pull-\(symbol)-\(Int(Date().timeIntervalSince1970))"
                )
            }
        }
    }

    private func checkMarket(_ market: String) async {
        guard let feed = try? await APIService.shared.fetchLiveTrades(market: market, limit: 30) else { return }
        var seen = Set(UserDefaults.standard.stringArray(forKey: Self.seenKey) ?? [])
        let isFirstRun = seen.isEmpty

        for trade in feed.trades {
            seen.insert(trade.id)
        }
        for pick in feed.topPicks {
            seen.insert(pick.id)
        }

        if isFirstRun {
            UserDefaults.standard.set(Array(seen.prefix(200)), forKey: Self.seenKey)
            return
        }

        let previousSeen = Set(UserDefaults.standard.stringArray(forKey: Self.seenKey) ?? [])
        let newTrades = feed.trades.filter { !previousSeen.contains($0.id) }
        let newPicks = feed.topPicks.filter { !previousSeen.contains($0.id) }

        for trade in newTrades.prefix(3) {
            let title = liveTitle(for: trade)
            let body = trade.subtitle ?? trade.title
            if alertFrequency == .digest {
                digestQueue.append(title)
            } else {
                await notify(title: title, body: body, id: trade.id)
            }
        }

        for pick in newPicks.prefix(2) {
            let title = "Top pick · \(marketLabel(pick.marketType))"
            let body = "\(pick.title) — \(pick.pickReason ?? "High score")"
            if alertFrequency == .digest {
                digestQueue.append(title)
            } else {
                await notify(title: title, body: body, id: "pick-\(pick.id)")
            }
        }

        UserDefaults.standard.set(Array(seen.prefix(200)), forKey: Self.seenKey)
    }

    private func notify(title: String, body: String, id: String) async {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: id,
            content: content,
            trigger: nil
        )
        try? await UNUserNotificationCenter.current().add(request)
    }

    private func liveTitle(for trade: LiveTrade) -> String {
        switch trade.actorType {
        case "politician": "Congress trade · \(trade.actorName)"
        case "whale": "Whale trade · \(trade.actorName)"
        case "insider": "Insider trade · \(trade.actorName)"
        default: "Live · \(marketLabel(trade.marketType))"
        }
    }

    private func marketLabel(_ market: String) -> String {
        switch market {
        case "stocks": "Stocks"
        case "polymarket": "Polymarket"
        case "kalshi": "Kalshi"
        case "futures": "Futures"
        case "crypto": "Crypto"
        case "forex": "Forex"
        default: market.capitalized
        }
    }
}
