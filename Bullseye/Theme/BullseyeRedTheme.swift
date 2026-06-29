//
//  BullseyeRedTheme.swift
//  Bullseye
//

import SwiftUI

enum BullseyeRedTheme {
    static let background = Color(red: 0.10, green: 0.02, blue: 0.03)
    static let backgroundDeep = Color(red: 0.08, green: 0.01, blue: 0.02)

    static let crimson = Color(red: 0.22, green: 0.05, blue: 0.08)
    static let wine = Color(red: 0.32, green: 0.08, blue: 0.12)

    static let neonRed = Color(red: 1.0, green: 0.28, blue: 0.32)
    static let neonRedBright = Color(red: 1.0, green: 0.45, blue: 0.48)
    static let neonRedMuted = Color(red: 0.85, green: 0.22, blue: 0.28)

    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.68)
    static let textTertiary = Color.white.opacity(0.42)

    static let glassFill = Color.white.opacity(0.07)
    static let glassBorder = Color(red: 1.0, green: 0.28, blue: 0.32).opacity(0.28)
    static let glassHighlight = Color.white.opacity(0.14)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [backgroundDeep, crimson, background],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static var accentGradient: LinearGradient {
        LinearGradient(
            colors: [neonRedBright, neonRed, neonRedMuted],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

struct RedGlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(BullseyeRedTheme.glassFill)
                    .background {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .fill(.ultraThinMaterial.opacity(0.25))
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        BullseyeRedTheme.glassHighlight,
                                        BullseyeRedTheme.glassBorder,
                                        BullseyeRedTheme.glassBorder.opacity(0.3),
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
    func redGlassCard(cornerRadius: CGFloat = 16) -> some View {
        modifier(RedGlassCard(cornerRadius: cornerRadius))
    }

    @ViewBuilder
    func eventGlassCard(platform: EventMarketPlatform, cornerRadius: CGFloat = 16) -> some View {
        switch platform {
        case .polymarket: blueGlassCard(cornerRadius: cornerRadius)
        case .kalshi: redGlassCard(cornerRadius: cornerRadius)
        }
    }
}

enum EventMarketPlatform: String, Identifiable, CaseIterable {
    case polymarket
    case kalshi

    var id: String { rawValue }

    var title: String {
        switch self {
        case .polymarket: "Polymarket"
        case .kalshi: "Kalshi"
        }
    }

    var subtitle: String {
        switch self {
        case .polymarket: "Live whale activity · AI predictions · Blue"
        case .kalshi: "Hot markets · Economics · Red"
        }
    }

    var icon: String {
        switch self {
        case .polymarket: "chart.bar.doc.horizontal"
        case .kalshi: "flame.fill"
        }
    }

    var accent: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.neonBlue
        case .kalshi: BullseyeRedTheme.neonRed
        }
    }

    var accentBright: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.neonBlueBright
        case .kalshi: BullseyeRedTheme.neonRedBright
        }
    }

    var accentMuted: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.neonBlueMuted
        case .kalshi: BullseyeRedTheme.neonRedMuted
        }
    }

    var backgroundGradient: LinearGradient {
        switch self {
        case .polymarket: BullseyeBlueTheme.backgroundGradient
        case .kalshi: BullseyeRedTheme.backgroundGradient
        }
    }

    var accentGradient: LinearGradient {
        switch self {
        case .polymarket: BullseyeBlueTheme.accentGradient
        case .kalshi: BullseyeRedTheme.accentGradient
        }
    }

    var textSecondary: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.textSecondary
        case .kalshi: BullseyeRedTheme.textSecondary
        }
    }

    var textPrimary: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.textPrimary
        case .kalshi: BullseyeRedTheme.textPrimary
        }
    }

    var textTertiary: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.textTertiary
        case .kalshi: BullseyeRedTheme.textTertiary
        }
    }

    var backgroundDeep: Color {
        switch self {
        case .polymarket: BullseyeBlueTheme.backgroundDeep
        case .kalshi: BullseyeRedTheme.backgroundDeep
        }
    }
}
