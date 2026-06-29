//
//  AssetMarketMainTabView.swift
//  Bullseye
//

import SwiftUI

struct AssetMarketMainTabView: View {
    let platform: AssetMarketPlatform
    var onSwitchMode: (() -> Void)? = nil
    @State private var session = AppSession.shared

    var body: some View {
        TabView {
            NavigationStack { AssetMarketPredictView(platform: platform, appModel: session.appModel).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Predict", systemImage: "brain.head.profile") }

            NavigationStack { LiveTradesView(market: platform.rawValue, assetPlatform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Live", systemImage: "bolt.fill") }

            NavigationStack { AssetMarketCategoriesView(platform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Categories", systemImage: "square.grid.2x2") }

            NavigationStack { AssetMarketTrackerView(platform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Tracker", systemImage: "lock.doc") }

            NavigationStack {
                CategoryWalletView(category: platform.rawValue, accent: platform.accent)
                    .withModeHomeButton(accent: platform.accent)
            }
                .tabItem { Label("Wallet", systemImage: "dollarsign.circle") }
        }
        .tint(platform.accent)
        .environment(\.switchMode, onSwitchMode)
        .environment(\.modeHomeAccent, platform.accent)
        .safeAreaInset(edge: .top) {
            HStack(spacing: 8) {
                Circle().fill(session.connection.isConnected ? platform.accent : .red).frame(width: 8, height: 8)
                Text(session.connection.isConnected ? "\(platform.title) API online" : "Offline")
                    .font(.caption2).foregroundStyle(platform.textSecondary)
                Spacer()
            }
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(platform.accent.opacity(0.12))
        }
        .task { await session.bootstrapIfNeeded() }
    }
}
