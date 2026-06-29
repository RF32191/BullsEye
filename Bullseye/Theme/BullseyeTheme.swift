//
//  BullseyeTheme.swift
//  Bullseye
//

import SwiftUI

enum BullseyeTheme {
    static let background = Color(red: 0.02, green: 0.04, blue: 0.02)
    static let backgroundDeep = Color.black

    static let forestGreen = Color(red: 0.05, green: 0.15, blue: 0.06)
    static let emerald = Color(red: 0.08, green: 0.28, blue: 0.12)
    static let deepGreen = Color(red: 0.04, green: 0.12, blue: 0.05)

    static let neonGreen = Color(red: 0.0, green: 1.0, blue: 0.4)
    static let neonGreenBright = Color(red: 0.22, green: 1.0, blue: 0.08)
    static let neonGreenMuted = Color(red: 0.0, green: 0.75, blue: 0.35)

    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.65)
    static let textTertiary = Color.white.opacity(0.4)

    static let glassFill = Color.white.opacity(0.06)
    static let glassBorder = Color(red: 0.0, green: 0.9, blue: 0.4).opacity(0.25)
    static let glassHighlight = Color.white.opacity(0.12)

    static let chatAssistantFill = Color(red: 0.07, green: 0.17, blue: 0.09)
    static let chatCitationFill = Color(red: 0.05, green: 0.12, blue: 0.07)
    static let chatInputFill = Color(red: 0.10, green: 0.14, blue: 0.11)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [backgroundDeep, forestGreen, background],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static var accentGradient: LinearGradient {
        LinearGradient(
            colors: [neonGreenBright, neonGreen, neonGreenMuted],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static var radialGlow: RadialGradient {
        RadialGradient(
            colors: [neonGreen.opacity(0.18), Color.clear],
            center: .center,
            startRadius: 20,
            endRadius: 220
        )
    }
}

struct GlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(BullseyeTheme.glassFill)
                    .background {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .fill(.ultraThinMaterial.opacity(0.3))
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        BullseyeTheme.glassHighlight,
                                        BullseyeTheme.glassBorder,
                                        BullseyeTheme.glassBorder.opacity(0.3)
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
    func glassCard(cornerRadius: CGFloat = 16) -> some View {
        modifier(GlassCard(cornerRadius: cornerRadius))
    }
}
