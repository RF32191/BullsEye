//
//  BackendSettings.swift
//  Bullseye
//

import Foundation

enum BackendSettings {
    private static let railwayURLKey = "bullseye.railway.baseURL"

    static let defaultProductionURL = "https://bullseye-api-production-f8ac.up.railway.app"

    static var railwayBaseURL: String? {
        get {
            if let saved = UserDefaults.standard.string(forKey: railwayURLKey),
               let valid = sanitize(saved) {
                return valid
            }
            if let bundled = Bundle.main.object(forInfoDictionaryKey: "RailwayBaseURL") as? String,
               let valid = sanitize(bundled) {
                return valid
            }
            return defaultProductionURL
        }
        set {
            if let newValue, let valid = sanitize(newValue) {
                UserDefaults.standard.set(valid, forKey: railwayURLKey)
            } else {
                UserDefaults.standard.removeObject(forKey: railwayURLKey)
            }
        }
    }

    static var isRailwayConfigured: Bool {
        railwayBaseURL != nil
    }

    /// Clears invalid saved URLs (e.g. placeholder text) that cause "server not found".
    static func repairStoredURLIfNeeded() {
        guard let saved = UserDefaults.standard.string(forKey: railwayURLKey) else { return }
        if sanitize(saved) == nil {
            UserDefaults.standard.removeObject(forKey: railwayURLKey)
        }
    }

    private static func sanitize(_ raw: String) -> String? {
        let value = normalized(raw)
        guard let url = URL(string: value), let host = url.host, !host.isEmpty else { return nil }

        let blocked = ["your-app", "your_app", "localhost", "127.0.0.1", "example.com"]
        if blocked.contains(where: { host.contains($0) }) { return nil }

        return value
    }

    private static func normalized(_ url: String) -> String {
        var value = url.trimmingCharacters(in: .whitespacesAndNewlines)
        if !value.hasPrefix("http://") && !value.hasPrefix("https://") {
            value = "https://\(value)"
        }
        if value.hasSuffix("/") {
            value.removeLast()
        }
        return value
    }
}
