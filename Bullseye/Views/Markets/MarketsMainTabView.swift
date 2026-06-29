//
//  MarketsMainTabView.swift
//  Bullseye
//

import SwiftUI

struct MarketsMainTabView: View {
    let platform: EventMarketPlatform
    var onSwitchMode: (() -> Void)? = nil
    @State private var session = AppSession.shared

    var body: some View {
        TabView {
            NavigationStack { MarketsPredictView(platform: platform, appModel: session.appModel).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Predict", systemImage: "brain.head.profile") }

            NavigationStack { LiveTradesView(market: platform.rawValue, eventPlatform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Live", systemImage: "bolt.fill") }

            NavigationStack { MarketsCategoriesView(platform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Categories", systemImage: "square.grid.2x2") }

            NavigationStack { MarketsTradersView(platform: platform).withModeHomeButton(accent: platform.accent) }
                .tabItem { Label("Traders", systemImage: "person.3.fill") }

            NavigationStack { MarketsTrackerView(platform: platform).withModeHomeButton(accent: platform.accent) }
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
            marketsConnectionBanner
        }
        .task { await session.bootstrapIfNeeded() }
    }

    private var marketsConnectionBanner: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(session.connection.isConnected ? platform.accent : Color.red)
                .frame(width: 8, height: 8)
            Text(session.connection.isConnected ? "\(platform.title) API online" : "Offline")
                .font(.caption2)
                .foregroundStyle(platform.textSecondary)
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(platform.accent.opacity(0.12))
    }
}
