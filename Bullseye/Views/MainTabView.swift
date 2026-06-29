//
//  MainTabView.swift
//  Bullseye
//

import SwiftUI

struct MainTabView: View {
    var onSwitchMode: (() -> Void)? = nil
    @State private var session = AppSession.shared

    var body: some View {
        TabView {
            NavigationStack { PredictView(appModel: session.appModel).withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Predict", systemImage: "brain.head.profile") }

            NavigationStack { ChatView(appModel: session.appModel).withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Chat", systemImage: "bubble.left.and.text.bubble.right") }

            NavigationStack { TrendView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Trends", systemImage: "chart.xyaxis.line") }

            NavigationStack { CongressTradesView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Congress", systemImage: "building.columns") }

            NavigationStack { LiveTradesView(market: "stocks").withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Live", systemImage: "bolt.fill") }

            NavigationStack { IntelligenceHubView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Intel", systemImage: "globe.americas.fill") }

            NavigationStack { FlowTrackerView(appModel: session.appModel).withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Flow", systemImage: "arrow.left.arrow.right.circle") }

            NavigationStack { CategoryWalletView(category: "stocks", accent: BullseyeTheme.neonGreen).withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Wallet", systemImage: "dollarsign.circle") }

            NavigationStack { PortfolioView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Portfolio", systemImage: "briefcase") }

            NavigationStack { AnalyticsView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Analytics", systemImage: "chart.bar.doc.horizontal") }

            NavigationStack { TrackerView().withModeHomeButton(accent: BullseyeTheme.neonGreen) }
                .tabItem { Label("Tracker", systemImage: "lock.doc") }

            NavigationStack {
                UpgradeStoreView(appModel: session.appModel, subscription: SubscriptionManager.shared)
                    .withModeHomeButton(accent: BullseyeTheme.neonGreen, showCrown: false)
            }
                .tabItem { Label("Plan", systemImage: "crown") }
        }
        .tint(BullseyeTheme.neonGreen)
        .environment(\.switchMode, onSwitchMode)
        .environment(\.modeHomeAccent, BullseyeTheme.neonGreen)
        .safeAreaInset(edge: .top) {
            if session.connection.isConnected {
                HStack(spacing: 8) {
                    Circle()
                        .fill(BullseyeTheme.neonGreen)
                        .frame(width: 8, height: 8)
                    Text("API online · \(session.appModel.tokenBalance?.balance ?? session.appModel.user?.tokenBalance ?? 0) tokens")
                        .font(.caption2)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(BullseyeTheme.neonGreen.opacity(0.12))
            } else {
                HStack {
                    Image(systemName: "wifi.exclamationmark")
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Cannot reach server")
                            .font(.caption.bold())
                        Text(session.connection.lastError ?? session.appModel.errorMessage ?? APIConfig.displayURL)
                            .font(.caption2)
                            .lineLimit(2)
                    }
                    Spacer()
                    Button("Retry") {
                        Task { await session.retryConnection() }
                    }
                    .font(.caption.bold())
                }
                .foregroundStyle(.white)
                .padding(10)
                .background(Color.red.opacity(0.85))
            }
        }
        .task {
            await session.bootstrapIfNeeded()
        }
    }
}

#Preview {
    MainTabView()
}
