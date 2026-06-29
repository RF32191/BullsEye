//
//  BrokerLinkService.swift
//  Bullseye
//

import Foundation

enum PreferredBroker: String, CaseIterable, Identifiable, Codable {
    case robinhood
    case webull
    case none

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .robinhood: "Robinhood"
        case .webull: "Webull"
        case .none: "None"
        }
    }
}

enum BrokerLinkService {
    private static let brokerKey = "bullseye.preferred.broker"

    static var preferredBroker: PreferredBroker {
        get {
            guard let raw = UserDefaults.standard.string(forKey: brokerKey),
                  let value = PreferredBroker(rawValue: raw) else { return .none }
            return value
        }
        set {
            UserDefaults.standard.set(newValue.rawValue, forKey: brokerKey)
        }
    }

    static func tradeURL(for ticker: String) -> URL? {
        let symbol = ticker.uppercased()
        switch preferredBroker {
        case .robinhood:
            return URL(string: "https://robinhood.com/stocks/\(symbol)")
        case .webull:
            return URL(string: "https://www.webull.com/quote/us/\(symbol)")
        case .none:
            return URL(string: "https://robinhood.com/stocks/\(symbol)")
        }
    }
}
