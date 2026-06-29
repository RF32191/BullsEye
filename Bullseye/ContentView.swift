//
//  ContentView.swift
//  Bullseye
//

import SwiftUI

struct ContentView: View {
    @State private var session = AppSession.shared
    @State private var publicStats: PublicStats?
    @State private var logoScale: CGFloat = 0.85
    @State private var logoOpacity: Double = 0
    @State private var contentOpacity: Double = 0
    @State private var glowPulse = false
    @State private var showMainApp = false
    @State private var showUpgradeStore = false

    var body: some View {
        ZStack {
            BullseyeTheme.backgroundGradient
                .ignoresSafeArea()

            RadialGradient(
                colors: [
                    BullseyeTheme.neonGreen.opacity(glowPulse ? 0.14 : 0.08),
                    Color.clear
                ],
                center: .top,
                startRadius: 40,
                endRadius: 420
            )
            .ignoresSafeArea()
            .animation(.easeInOut(duration: 3).repeatForever(autoreverses: true), value: glowPulse)

            ScrollView(showsIndicators: false) {
                VStack(spacing: 28) {
                    headerSection
                    apiStatusSection
                    metricsSection
                    featuresSection
                    actionSection
                }
                .padding(.horizontal, 20)
                .padding(.top, 48)
                .padding(.bottom, 40)
            }
            .opacity(contentOpacity)

            VStack {
                HStack {
                    Spacer()
                    CrownStoreButton {
                        showUpgradeStore = true
                    }
                    .padding(.trailing, 20)
                    .padding(.top, 12)
                }
                Spacer()
            }
        }
        .upgradeStoreSheet(isPresented: $showUpgradeStore)
        .preferredColorScheme(.dark)
        #if os(iOS)
        .fullScreenCover(isPresented: $showMainApp) {
            AppModeHubView()
        }
        #else
        .sheet(isPresented: $showMainApp) {
            AppModeHubView()
                .frame(minWidth: 900, minHeight: 640)
        }
        #endif
        .task {
            await session.bootstrapIfNeeded()
        }
        .onAppear {
            glowPulse = true
            withAnimation(.spring(response: 0.9, dampingFraction: 0.75)) {
                logoScale = 1.0
                logoOpacity = 1.0
            }
            withAnimation(.easeOut(duration: 0.8).delay(0.3)) {
                contentOpacity = 1.0
            }
            Task { publicStats = try? await APIService.shared.fetchPublicStats() }
        }
    }

    private var headerSection: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(BullseyeTheme.radialGlow)
                    .frame(width: 200, height: 200)
                    .blur(radius: 20)

                Image("AppLogo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 120, height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
                    .shadow(color: BullseyeTheme.neonGreen.opacity(0.45), radius: 24, y: 8)
            }
            .scaleEffect(logoScale)
            .opacity(logoOpacity)

            VStack(spacing: 8) {
                Text("Bullseye AI")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundStyle(BullseyeTheme.accentGradient)

                Text("Institutional-grade stock analysis,\npowered by AI")
                    .font(.subheadline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
        }
    }

    private var apiStatusSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Circle()
                    .fill(session.connection.isConnected ? BullseyeTheme.neonGreen : Color.red)
                    .frame(width: 10, height: 10)
                Text(session.connection.isConnected ? "API online" : "API offline")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(session.connection.isConnected ? BullseyeTheme.neonGreen : .red)
                Spacer()
                if session.appModel.isLoading {
                    ProgressView().tint(BullseyeTheme.neonGreen)
                }
            }

            if session.connection.isConnected {
                Button {
                    showUpgradeStore = true
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "crown.fill")
                            .font(.caption2)
                        Text("\(session.appModel.tokenBalance?.balance ?? session.appModel.user?.tokenBalance ?? 0) tokens — tap to buy more")
                            .font(.caption2)
                    }
                    .foregroundStyle(BullseyeTheme.textSecondary)
                }
                .buttonStyle(.plain)
            } else if let error = session.connection.lastError ?? session.appModel.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
                Button("Retry connection") {
                    Task { await session.retryConnection() }
                }
                .font(.caption.bold())
                .foregroundStyle(BullseyeTheme.neonGreen)
            } else {
                Text("Connecting to \(APIConfig.displayHost)…")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
    }

    private var metricsSection: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                MetricCard(
                    title: "Predictions",
                    value: publicStats.map { "\($0.totalPredictions)" } ?? "—",
                    change: "Locked ledger",
                    isPositive: true
                )
                MetricCard(
                    title: "Win Rate",
                    value: publicStats?.overallWinRatePct.map { String(format: "%.0f%%", $0) } ?? "—",
                    change: "Verified",
                    isPositive: true
                )
            }

            HStack(spacing: 12) {
                MetricCard(
                    title: "AI Engine",
                    value: publicStats?.aiWinRatePct.map { String(format: "%.0f%%", $0) } ?? "—",
                    change: "Resolved",
                    isPositive: true
                )
                MetricCard(
                    title: "Technical Bot",
                    value: publicStats?.technicalWinRatePct.map { String(format: "%.0f%%", $0) } ?? "—",
                    change: "Free tier",
                    isPositive: true
                )
            }
        }
    }

    private var featuresSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Platform Highlights")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            VStack(spacing: 10) {
                FeatureRow(icon: "chart.bar.doc.horizontal", title: "Event Markets", subtitle: "Polymarket + Kalshi predictions in a dedicated blue mode")
                FeatureRow(icon: "chart.line.uptrend.xyaxis", title: "AI Stock Analysis", subtitle: "Explainable bull & bear cases with citations")
                FeatureRow(icon: "building.columns", title: "Congress & Insider Tracking", subtitle: "STOCK Act + Form 4 filings with post-trade performance")
                FeatureRow(icon: "lock.shield", title: "Paper Trading First", subtitle: "Live trading only with explicit authorization")
            }
        }
        .padding(20)
        .glassCard()
    }

    private var actionSection: some View {
        Button {
            showMainApp = true
        } label: {
            HStack(spacing: 10) {
                Image(systemName: "arrow.right.circle.fill")
                    .font(.title3)
                Text("Get Started")
                    .font(.headline)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .foregroundStyle(.black)
            .background(BullseyeTheme.accentGradient)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .shadow(color: BullseyeTheme.neonGreen.opacity(0.35), radius: 12, y: 4)
        }
    }
}

private struct MetricCard: View {
    let title: String
    let value: String
    let change: String
    let isPositive: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textTertiary)

            Text(value)
                .font(.title3.weight(.bold))
                .foregroundStyle(BullseyeTheme.textPrimary)

            Text(change)
                .font(.caption.weight(.semibold))
                .foregroundStyle(isPositive ? BullseyeTheme.neonGreen : Color.red)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .glassCard(cornerRadius: 14)
    }
}

private struct FeatureRow: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(BullseyeTheme.neonGreen)
                .frame(width: 36, height: 36)
                .background(BullseyeTheme.neonGreen.opacity(0.12))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }

            Spacer(minLength: 0)
        }
    }
}

#Preview {
    ContentView()
}
