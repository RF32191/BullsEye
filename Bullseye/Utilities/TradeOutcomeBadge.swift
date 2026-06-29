//
//  TradeOutcomeBadge.swift
//  Bullseye
//

import SwiftUI

struct TradeOutcomeBadge: View {
    let outcome: String
    var compact = false

    private var isWin: Bool { outcome.lowercased() == "win" }
    private var isLoss: Bool { outcome.lowercased() == "loss" }

    var body: some View {
        if isWin || isLoss {
            Text(compact ? (isWin ? "W" : "L") : (isWin ? "WIN" : "LOSS"))
                .font(.caption2.bold())
                .foregroundStyle(isWin ? BullseyeTheme.neonGreen : .orange)
                .padding(.horizontal, compact ? 6 : 8)
                .padding(.vertical, 4)
                .background {
                    Capsule()
                        .fill((isWin ? BullseyeTheme.neonGreen : Color.orange).opacity(0.15))
                }
        }
    }
}

struct ReturnSinceTradeRow: View {
    let returnPct: Double?
    let outcome: String?
    let label: String
    var currentPrice: Double?

    var body: some View {
        if let ret = returnPct {
            HStack(spacing: 6) {
                if let outcome {
                    TradeOutcomeBadge(outcome: outcome)
                }
                Image(systemName: ret >= 0 ? "arrow.up.right" : "arrow.down.right")
                    .font(.caption2.bold())
                    .foregroundStyle(ret >= 0 ? BullseyeTheme.neonGreen : .orange)
                Text(String(format: "%+.1f%% \(label)", ret))
                    .font(.caption.bold())
                    .foregroundStyle(ret >= 0 ? BullseyeTheme.neonGreen : .orange)
                if let price = currentPrice {
                    Text("· now \(Formatters.currency(price))")
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textTertiary)
                }
            }
        }
    }
}
