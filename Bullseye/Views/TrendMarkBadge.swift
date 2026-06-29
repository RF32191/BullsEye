//
//  TrendMarkBadge.swift
//  Bullseye
//

import SwiftUI

struct TrendMarkBadge: View {
    let label: String?
    let arrow: String?
    let strength: Double?
    let summary: String?
    var accent: Color = BullseyeTheme.neonGreen

    var body: some View {
        if label != nil || summary != nil {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    if let arrow, !arrow.isEmpty {
                        Text(arrow)
                            .font(.title3.bold())
                            .foregroundStyle(trendColor)
                    }
                    if let label, !label.isEmpty {
                        Text(readableLabel(label))
                            .font(.caption.bold())
                            .foregroundStyle(trendColor)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(trendColor.opacity(0.15))
                            .clipShape(Capsule())
                    }
                    if let strength {
                        Text(String(format: "%.0f%% strength", strength))
                            .font(.caption2)
                            .foregroundStyle(BullseyeTheme.textTertiary)
                    }
                }
                if let summary, !summary.isEmpty {
                    Text(summary)
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }
            }
        }
    }

    private var trendColor: Color {
        guard let label else { return accent }
        if label.contains("up") { return BullseyeTheme.neonGreen }
        if label.contains("down") { return .orange }
        return BullseyeTheme.textSecondary
    }

    private func readableLabel(_ raw: String) -> String {
        raw.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

extension TechnicalAnalysis {
    var trendMarkBadge: TrendMarkBadge {
        TrendMarkBadge(
            label: trendLabel,
            arrow: trendArrow,
            strength: trendStrength,
            summary: trendSummary
        )
    }
}
