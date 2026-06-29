//
//  BrokerLinkService+Assets.swift
//  Bullseye
//

import Foundation

extension BrokerLinkService {
    static func tradeURL(for symbol: String, assetClass: String? = nil) -> URL? {
        let upper = symbol.uppercased()
        let base = upper
            .replacingOccurrences(of: "-USD", with: "")
            .replacingOccurrences(of: "=X", with: "")
            .replacingOccurrences(of: "=F", with: "")

        if assetClass == "crypto" || upper.contains("-USD") {
            switch preferredBroker {
            case .robinhood:
                return URL(string: "https://robinhood.com/crypto/\(base)")
            case .webull:
                return URL(string: "https://www.webull.com/quote/crypto/\(base)")
            case .none:
                return URL(string: "https://robinhood.com/crypto/\(base)")
            }
        }

        if assetClass == "forex" || upper.contains("=X") {
            return URL(string: "https://www.tradingview.com/symbols/\(base)/")
        }

        if assetClass == "futures" || upper.contains("=F") {
            return URL(string: "https://www.tradingview.com/symbols/\(upper)/")
        }

        return tradeURL(for: upper)
    }
}
