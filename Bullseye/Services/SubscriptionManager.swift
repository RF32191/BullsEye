//
//  SubscriptionManager.swift
//  Bullseye
//

import Foundation

enum SubscriptionTier: String, Codable, CaseIterable, Sendable {
    case free
    case pro
    case elite

    var displayName: String {
        switch self {
        case .free: "Free"
        case .pro: "Pro"
        case .elite: "Elite"
        }
    }

    var dailyAIAnalyses: Int? {
        switch self {
        case .free: 5
        case .pro, .elite: nil
        }
    }

    var dailyChatMessages: Int? {
        switch self {
        case .free: 10
        case .pro, .elite: nil
        }
    }

    var features: [String] {
        switch self {
        case .free:
            ["5 AI analyses/day", "10 chat messages/day", "Paper trading", "1 watchlist"]
        case .pro:
            ["Unlimited AI", "Congress tracker", "Advanced indicators", "Unlimited watchlists"]
        case .elite:
            ["Everything in Pro", "Live broker integrations", "Portfolio optimization", "Priority AI"]
        }
    }

    var monthlyPriceLabel: String {
        switch self {
        case .free: "Free"
        case .pro: "$9.99/mo"
        case .elite: "$19.99/mo"
        }
    }
}

@Observable
@MainActor
final class SubscriptionManager {
    static let shared = SubscriptionManager()

    private let tierKey = "bullseye.subscription.tier"

    var tier: SubscriptionTier {
        get {
            guard let raw = UserDefaults.standard.string(forKey: tierKey),
                  let value = SubscriptionTier(rawValue: raw) else { return .free }
            return value
        }
        set {
            UserDefaults.standard.set(newValue.rawValue, forKey: tierKey)
            Task { await syncToBackend() }
        }
    }

    func syncToBackend() async {
        try? await APIService.shared.updateSubscription(tier: tier)
    }

    func loadFromBackend() async {
        if let remote = try? await APIService.shared.fetchSubscription(),
           SubscriptionTier(rawValue: remote.tier) != nil {
            UserDefaults.standard.set(remote.tier, forKey: tierKey)
        }
    }
}
