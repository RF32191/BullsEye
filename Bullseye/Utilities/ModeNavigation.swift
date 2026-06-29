//
//  ModeNavigation.swift
//  Bullseye
//

import SwiftUI

private struct SwitchModeKey: EnvironmentKey {
    static let defaultValue: (() -> Void)? = nil
}

private struct ModeHomeAccentKey: EnvironmentKey {
    static let defaultValue: Color = BullseyeTheme.neonGreen
}

extension EnvironmentValues {
    var switchMode: (() -> Void)? {
        get { self[SwitchModeKey.self] }
        set { self[SwitchModeKey.self] = newValue }
    }

    var modeHomeAccent: Color {
        get { self[ModeHomeAccentKey.self] }
        set { self[ModeHomeAccentKey.self] = newValue }
    }
}

struct ModeHomeButtonModifier: ViewModifier {
    @Environment(\.switchMode) private var switchMode
    @State private var showUpgradeStore = false
    var accent: Color?
    var showCrown: Bool

    private var tint: Color {
        accent ?? BullseyeTheme.neonGreen
    }

    func body(content: Content) -> some View {
        content
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 14) {
                        if showCrown {
                            CrownStoreButton(accent: tint) {
                                showUpgradeStore = true
                            }
                        }
                        if let switchMode {
                            Button(action: switchMode) {
                                Image(systemName: "house.fill")
                                    .foregroundStyle(tint)
                            }
                            .accessibilityLabel("Home")
                        }
                    }
                }
            }
            .upgradeStoreSheet(isPresented: $showUpgradeStore)
    }
}

extension View {
    func withModeHomeButton(accent: Color? = nil, showCrown: Bool = true) -> some View {
        modifier(ModeHomeButtonModifier(accent: accent, showCrown: showCrown))
    }
}
