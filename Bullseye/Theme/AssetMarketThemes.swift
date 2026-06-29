//
//  BullseyeGoldTheme.swift
//  Bullseye — Futures
//

import SwiftUI

enum BullseyeGoldTheme {
    static let background = Color(red: 0.10, green: 0.08, blue: 0.02)
    static let backgroundDeep = Color(red: 0.08, green: 0.06, blue: 0.01)
    static let bronze = Color(red: 0.18, green: 0.14, blue: 0.04)
    static let amber = Color(red: 0.28, green: 0.20, blue: 0.05)
    static let neonGold = Color(red: 1.0, green: 0.78, blue: 0.12)
    static let neonGoldBright = Color(red: 1.0, green: 0.88, blue: 0.35)
    static let neonGoldMuted = Color(red: 0.85, green: 0.65, blue: 0.15)
    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.68)
    static let textTertiary = Color.white.opacity(0.42)
    static let glassFill = Color.white.opacity(0.07)
    static let glassBorder = Color(red: 1.0, green: 0.78, blue: 0.12).opacity(0.28)
    static let glassHighlight = Color.white.opacity(0.14)

    static var backgroundGradient: LinearGradient {
        LinearGradient(colors: [backgroundDeep, bronze, background], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
    static var accentGradient: LinearGradient {
        LinearGradient(colors: [neonGoldBright, neonGold, neonGoldMuted], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
}

enum BullseyePurpleTheme {
    static let background = Color(red: 0.06, green: 0.03, blue: 0.12)
    static let backgroundDeep = Color(red: 0.04, green: 0.02, blue: 0.08)
    static let violet = Color(red: 0.14, green: 0.08, blue: 0.22)
    static let neonPurple = Color(red: 0.75, green: 0.35, blue: 1.0)
    static let neonPurpleBright = Color(red: 0.85, green: 0.55, blue: 1.0)
    static let neonPurpleMuted = Color(red: 0.55, green: 0.25, blue: 0.85)
    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.68)
    static let textTertiary = Color.white.opacity(0.42)
    static let glassFill = Color.white.opacity(0.07)
    static let glassBorder = Color(red: 0.75, green: 0.35, blue: 1.0).opacity(0.28)
    static let glassHighlight = Color.white.opacity(0.14)

    static var backgroundGradient: LinearGradient {
        LinearGradient(colors: [backgroundDeep, violet, background], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
    static var accentGradient: LinearGradient {
        LinearGradient(colors: [neonPurpleBright, neonPurple, neonPurpleMuted], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
}

enum BullseyeTealTheme {
    static let background = Color(red: 0.02, green: 0.08, blue: 0.09)
    static let backgroundDeep = Color(red: 0.01, green: 0.06, blue: 0.07)
    static let slate = Color(red: 0.05, green: 0.16, blue: 0.18)
    static let neonTeal = Color(red: 0.25, green: 0.85, blue: 0.82)
    static let neonTealBright = Color(red: 0.45, green: 0.95, blue: 0.92)
    static let neonTealMuted = Color(red: 0.18, green: 0.65, blue: 0.68)
    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.68)
    static let textTertiary = Color.white.opacity(0.42)
    static let glassFill = Color.white.opacity(0.07)
    static let glassBorder = Color(red: 0.25, green: 0.85, blue: 0.82).opacity(0.28)
    static let glassHighlight = Color.white.opacity(0.14)

    static var backgroundGradient: LinearGradient {
        LinearGradient(colors: [backgroundDeep, slate, background], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
    static var accentGradient: LinearGradient {
        LinearGradient(colors: [neonTealBright, neonTeal, neonTealMuted], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
}

enum AssetMarketPlatform: String, Identifiable, CaseIterable {
    case futures, crypto, forex

    var id: String { rawValue }

    var title: String {
        switch self {
        case .futures: "Futures"
        case .crypto: "Crypto"
        case .forex: "Forex"
        }
    }

    var subtitle: String {
        switch self {
        case .futures: "Index · Energy · Metals · Rates"
        case .crypto: "BTC · ETH · SOL · Alts"
        case .forex: "Major pairs · Cross rates"
        }
    }

    var icon: String {
        switch self {
        case .futures: "chart.line.uptrend.xyaxis.circle"
        case .crypto: "bitcoinsign.circle"
        case .forex: "dollarsign.arrow.circlepath"
        }
    }

    var accent: Color {
        switch self {
        case .futures: BullseyeGoldTheme.neonGold
        case .crypto: BullseyePurpleTheme.neonPurple
        case .forex: BullseyeTealTheme.neonTeal
        }
    }

    var accentBright: Color {
        switch self {
        case .futures: BullseyeGoldTheme.neonGoldBright
        case .crypto: BullseyePurpleTheme.neonPurpleBright
        case .forex: BullseyeTealTheme.neonTealBright
        }
    }

    var accentMuted: Color {
        switch self {
        case .futures: BullseyeGoldTheme.neonGoldMuted
        case .crypto: BullseyePurpleTheme.neonPurpleMuted
        case .forex: BullseyeTealTheme.neonTealMuted
        }
    }

    var backgroundGradient: LinearGradient {
        switch self {
        case .futures: BullseyeGoldTheme.backgroundGradient
        case .crypto: BullseyePurpleTheme.backgroundGradient
        case .forex: BullseyeTealTheme.backgroundGradient
        }
    }

    var accentGradient: LinearGradient {
        switch self {
        case .futures: BullseyeGoldTheme.accentGradient
        case .crypto: BullseyePurpleTheme.accentGradient
        case .forex: BullseyeTealTheme.accentGradient
        }
    }

    var textPrimary: Color {
        switch self {
        case .futures: BullseyeGoldTheme.textPrimary
        case .crypto: BullseyePurpleTheme.textPrimary
        case .forex: BullseyeTealTheme.textPrimary
        }
    }

    var textSecondary: Color {
        switch self {
        case .futures: BullseyeGoldTheme.textSecondary
        case .crypto: BullseyePurpleTheme.textSecondary
        case .forex: BullseyeTealTheme.textSecondary
        }
    }

    var textTertiary: Color {
        switch self {
        case .futures: BullseyeGoldTheme.textTertiary
        case .crypto: BullseyePurpleTheme.textTertiary
        case .forex: BullseyeTealTheme.textTertiary
        }
    }

    var backgroundDeep: Color {
        switch self {
        case .futures: BullseyeGoldTheme.backgroundDeep
        case .crypto: BullseyePurpleTheme.backgroundDeep
        case .forex: BullseyeTealTheme.backgroundDeep
        }
    }
}

struct GoldGlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16
    func body(content: Content) -> some View {
        content.background {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(BullseyeGoldTheme.glassFill)
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(BullseyeGoldTheme.glassBorder, lineWidth: 1)
                }
        }
    }
}

struct PurpleGlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16
    func body(content: Content) -> some View {
        content.background {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(BullseyePurpleTheme.glassFill)
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(BullseyePurpleTheme.glassBorder, lineWidth: 1)
                }
        }
    }
}

struct TealGlassCard: ViewModifier {
    var cornerRadius: CGFloat = 16
    func body(content: Content) -> some View {
        content.background {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(BullseyeTealTheme.glassFill)
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(BullseyeTealTheme.glassBorder, lineWidth: 1)
                }
        }
    }
}

extension View {
    func goldGlassCard(cornerRadius: CGFloat = 16) -> some View { modifier(GoldGlassCard(cornerRadius: cornerRadius)) }
    func purpleGlassCard(cornerRadius: CGFloat = 16) -> some View { modifier(PurpleGlassCard(cornerRadius: cornerRadius)) }
    func tealGlassCard(cornerRadius: CGFloat = 16) -> some View { modifier(TealGlassCard(cornerRadius: cornerRadius)) }

    @ViewBuilder
    func assetGlassCard(platform: AssetMarketPlatform, cornerRadius: CGFloat = 16) -> some View {
        switch platform {
        case .futures: goldGlassCard(cornerRadius: cornerRadius)
        case .crypto: purpleGlassCard(cornerRadius: cornerRadius)
        case .forex: tealGlassCard(cornerRadius: cornerRadius)
        }
    }
}
