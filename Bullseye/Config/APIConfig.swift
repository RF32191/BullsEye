//
//  APIConfig.swift
//  Bullseye
//

import Foundation

enum APIConfig {
    /// Hardcoded production API — always used unless Xcode scheme env override is set.
    static let productionURL = URL(string: "https://bullseye-api-production-f8ac.up.railway.app")!

    static var baseURL: URL {
        if let override = ProcessInfo.processInfo.environment["BULLSEYE_API_URL"],
           let url = URL(string: override.trimmingCharacters(in: .whitespacesAndNewlines)),
           url.scheme?.hasPrefix("http") == true {
            return url
        }
        return productionURL
    }

    static let apiPrefix = "/api/v1"

    static var displayURL: String {
        baseURL.absoluteString
    }

    static var displayHost: String {
        baseURL.host ?? displayURL
    }

    static var isUsingRailway: Bool {
        baseURL.host?.contains("railway.app") == true
    }
}
