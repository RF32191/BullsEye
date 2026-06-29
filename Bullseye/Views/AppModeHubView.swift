//
//  AppModeHubView.swift
//  Bullseye
//

import SwiftUI

enum AppProductMode: String, Identifiable {
    case stocks
    case futures
    case crypto
    case forex
    case polymarket
    case kalshi

    var id: String { rawValue }
}

struct AppModeHubView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var activeMode: AppProductMode?
    @State private var showUpgradeStore = false

    var body: some View {
        NavigationStack {
            ZStack {
                BullseyeTheme.backgroundGradient.ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 24) {
                        header
                        folderGrid
                    }
                    .padding(20)
                    .padding(.top, 24)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    CrownStoreButton {
                        showUpgradeStore = true
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
        .upgradeStoreSheet(isPresented: $showUpgradeStore)
        .fullScreenCover(item: $activeMode) { mode in
            switch mode {
            case .stocks:
                MainTabView(onSwitchMode: { activeMode = nil })
            case .futures:
                AssetMarketMainTabView(platform: .futures, onSwitchMode: { activeMode = nil })
            case .crypto:
                AssetMarketMainTabView(platform: .crypto, onSwitchMode: { activeMode = nil })
            case .forex:
                AssetMarketMainTabView(platform: .forex, onSwitchMode: { activeMode = nil })
            case .polymarket:
                MarketsMainTabView(platform: .polymarket, onSwitchMode: { activeMode = nil })
            case .kalshi:
                MarketsMainTabView(platform: .kalshi, onSwitchMode: { activeMode = nil })
            }
        }
    }

    private var header: some View {
        VStack(spacing: 10) {
            Text("Bullseye")
                .font(.system(size: 36, weight: .bold, design: .rounded))
                .foregroundStyle(BullseyeTheme.accentGradient)
            Text("Choose your prediction system")
                .font(.subheadline)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    private var folderGrid: some View {
        VStack(spacing: 16) {
            modeFolder(title: "Stocks", subtitle: "AI · Congress · Insider live trades", icon: "chart.line.uptrend.xyaxis", gradient: BullseyeTheme.accentGradient, tint: BullseyeTheme.neonGreen) { activeMode = .stocks }
            modeFolder(title: "Futures", subtitle: "ES · NQ · CL · GC · Rates", icon: "chart.line.uptrend.xyaxis.circle", gradient: BullseyeGoldTheme.accentGradient, tint: BullseyeGoldTheme.neonGold) { activeMode = .futures }
            modeFolder(title: "Crypto", subtitle: "BTC · ETH · SOL · 24/7 movers", icon: "bitcoinsign.circle", gradient: BullseyePurpleTheme.accentGradient, tint: BullseyePurpleTheme.neonPurple) { activeMode = .crypto }
            modeFolder(title: "Forex", subtitle: "EUR/USD · GBP/USD · Major pairs", icon: "dollarsign.arrow.circlepath", gradient: BullseyeTealTheme.accentGradient, tint: BullseyeTealTheme.neonTeal) { activeMode = .forex }
            modeFolder(title: "Polymarket", subtitle: "Whale trades · AI · Blue", icon: "chart.bar.doc.horizontal", gradient: BullseyeBlueTheme.accentGradient, tint: BullseyeBlueTheme.neonBlue) { activeMode = .polymarket }
            modeFolder(title: "Kalshi", subtitle: "Hot markets · Economics · Red", icon: "flame.fill", gradient: BullseyeRedTheme.accentGradient, tint: BullseyeRedTheme.neonRed) { activeMode = .kalshi }
        }
    }

    private func modeFolder(title: String, subtitle: String, icon: String, gradient: LinearGradient, tint: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 16) {
                ZStack {
                    RoundedRectangle(cornerRadius: 18, style: .continuous).fill(tint.opacity(0.15)).frame(width: 64, height: 64)
                    Image(systemName: icon).font(.title2).foregroundStyle(gradient)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text(title).font(.title3.bold()).foregroundStyle(BullseyeTheme.textPrimary)
                    Text(subtitle).font(.caption).foregroundStyle(BullseyeTheme.textSecondary).multilineTextAlignment(.leading)
                }
                Spacer()
                Image(systemName: "chevron.right.circle.fill").font(.title2).foregroundStyle(tint)
            }
            .padding(18)
            .glassCard(cornerRadius: 18)
            .overlay { RoundedRectangle(cornerRadius: 18, style: .continuous).strokeBorder(tint.opacity(0.35), lineWidth: 1) }
        }
    }
}
