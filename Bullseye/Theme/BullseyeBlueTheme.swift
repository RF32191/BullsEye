//
//  BullseyeBlueTheme.swift
//  Bullseye
//

import SwiftUI

enum BullseyeBlueTheme {
    static let background = Color(red: 0.02, green: 0.05, blue: 0.10)
    static let backgroundDeep = Color(red: 0.01, green: 0.03, blue: 0.08)

    static let navy = Color(red: 0.05, green: 0.12, blue: 0.22)
    static let slate = Color(red: 0.08, green: 0.18, blue: 0.32)

    static let neonBlue = Color(red: 0.35, green: 0.75, blue: 1.0)
    static let neonBlueBright = Color(red: 0.55, green: 0.85, blue: 1.0)
    static let neonBlueMuted = Color(red: 0.25, green: 0.55, blue: 0.95)

    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.68)
    static let textTertiary = Color.white.opacity(0.42)

    static let glassFill = Color.white.opacity(0.07)
    static let glassBorder = Color(red: 0.35, green: 0.75, blue: 1.0).opacity(0.28)
    static let glassHighlight = Color.white.opacity(0.14)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [backgroundDeep, navy, background],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static var accentGradient: LinearGradient {
        LinearGradient(
            colors: [neonBlueBright, neonBlue, neonBlueMuted],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

struct BlueGlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(BullseyeBlueTheme.glassFill)
                    .background {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .fill(.ultraThinMaterial.opacity(0.25))
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        BullseyeBlueTheme.glassHighlight,
                                        BullseyeBlueTheme.glassBorder,
                                        BullseyeBlueTheme.glassBorder.opacity(0.3),
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 1
                            )
                    }
            }
    }
}

extension View {
    func blueGlassCard(cornerRadius: CGFloat = 16) -> some View {
        modifier(BlueGlassCard(cornerRadius: cornerRadius))
    }
}
