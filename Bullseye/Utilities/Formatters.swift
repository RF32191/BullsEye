//
//  Formatters.swift
//  Bullseye
//

import Foundation

enum Formatters {
    static func currency(_ value: Double) -> String {
        String(format: "$%.2f", value)
    }

    static func percent(_ value: Double, signed: Bool = false) -> String {
        if signed {
            return String(format: "%+.2f%%", value)
        }
        return String(format: "%.2f%%", value)
    }

    static func compactNumber(_ value: Double) -> String {
        let absVal = abs(value)
        if absVal >= 1_000_000 { return String(format: "$%.1fM", absVal / 1_000_000) }
        if absVal >= 1_000 { return String(format: "$%.0fK", absVal / 1_000) }
        return String(format: "$%.0f", absVal)
    }
}
