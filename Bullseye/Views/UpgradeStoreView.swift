//
//  UpgradeStoreView.swift
//  Bullseye
//

import SwiftUI

struct UpgradeStoreView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var appModel: AppViewModel
    @Bindable var subscription: SubscriptionManager
    @Bindable var store: StorePurchaseManager

    @State private var catalog: PurchaseCatalog?
    @State private var usage: UsageLimits?
    @State private var errorMessage: String?
    @State private var successMessage: String?
    @State private var showError = false
    @State private var showSuccess = false

    init(
        appModel: AppViewModel,
        subscription: SubscriptionManager = .shared,
        store: StorePurchaseManager = .shared
    ) {
        self.appModel = appModel
        self.subscription = subscription
        self.store = store
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 24) {
                headerSection
                balanceSection
                if let usage { usageSection(usage) }
                subscriptionSection
                tokenPacksSection
                footerNote
            }
            .padding(20)
        }
        .navigationTitle("Upgrade")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Done") { dismiss() }
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        .refreshable { await reload() }
        .task { await reload() }
        .alert("Error", isPresented: $showError) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
        .alert("Success", isPresented: $showSuccess) {
            Button("OK") { successMessage = nil }
        } message: {
            Text(successMessage ?? "")
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Bullseye Pro", systemImage: "crown.fill")
                .font(.title2.bold())
                .foregroundStyle(BullseyeTheme.accentGradient)
            Text("Unlock unlimited AI, buy token packs, and track smart money like the pros.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
    }

    private var balanceSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(appModel.tokenBalance?.balance ?? appModel.user?.tokenBalance ?? 0)")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(BullseyeTheme.accentGradient)
                Text("tokens available")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text(subscription.tier.displayName)
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.neonGreen)
                Text("current plan")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
        }
        .padding(16)
        .glassCard()
    }

    private func usageSection(_ usage: UsageLimits) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Today's usage")
                .font(.subheadline.bold())
                .foregroundStyle(BullseyeTheme.textPrimary)
            if let aiLimit = usage.dailyAiLimit {
                usageRow("AI analyses", used: usage.dailyAiUsed, limit: aiLimit)
            } else {
                Text("AI analyses: unlimited")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            if let chatLimit = usage.dailyChatLimit {
                usageRow("Chat messages", used: usage.dailyChatUsed, limit: chatLimit)
            } else {
                Text("Chat messages: unlimited")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 12)
    }

    private func usageRow(_ label: String, used: Int, limit: Int) -> some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)
            Spacer()
            Text("\(used)/\(limit)")
                .font(.caption.bold())
                .foregroundStyle(used >= limit ? .orange : BullseyeTheme.textPrimary)
        }
    }

    private var subscriptionSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Subscription tiers")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)

            tierCard(.free, catalogSub: nil)

            if let subs = catalog?.subscriptions {
                ForEach(subs) { sub in
                    subscriptionProductCard(sub)
                }
            } else {
                tierCard(.pro, catalogSub: nil)
                tierCard(.elite, catalogSub: nil)
            }
        }
    }

    private func tierCard(_ tier: SubscriptionTier, catalogSub: SubscriptionCatalogItem?) -> some View {
        let isCurrent = subscription.tier == tier
        let price = catalogSub.map { store.displayPrice(for: $0.productId, fallback: tier.monthlyPriceLabel) } ?? tier.monthlyPriceLabel

        return VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(tier.displayName)
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Spacer()
                Text(price)
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
                if isCurrent {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(BullseyeTheme.neonGreen)
                }
            }
            ForEach(tier.features, id: \.self) { feature in
                Label(feature, systemImage: "checkmark")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
            if tier == .free && isCurrent {
                Text("Your current plan")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
        .overlay {
            if isCurrent {
                RoundedRectangle(cornerRadius: 14)
                    .strokeBorder(BullseyeTheme.neonGreen.opacity(0.5), lineWidth: 1)
            }
        }
    }

    private func subscriptionProductCard(_ sub: SubscriptionCatalogItem) -> some View {
        let tier = SubscriptionTier(rawValue: sub.tier) ?? .pro
        let isCurrent = subscription.tier == tier
        let price = store.displayPrice(for: sub.productId, fallback: String(format: "$%.2f/mo", sub.priceUsd))

        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(sub.label)
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Spacer()
                Text(price)
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
            ForEach(tier.features, id: \.self) { feature in
                Label(feature, systemImage: "checkmark")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
            if isCurrent {
                Text("Active plan")
                    .font(.caption.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
            } else {
                Button {
                    Task { await buySubscription(sub) }
                } label: {
                    Label("Subscribe to \(sub.label)", systemImage: "crown.fill")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .foregroundStyle(BullseyeTheme.backgroundDeep)
                .background(BullseyeTheme.accentGradient)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .disabled(store.isPurchasing)
            }
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
        .overlay {
            if isCurrent {
                RoundedRectangle(cornerRadius: 14)
                    .strokeBorder(BullseyeTheme.neonGreen.opacity(0.5), lineWidth: 1)
            }
        }
    }

    private var tokenPacksSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Token packs")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("AI predictions cost \(appModel.tokenBalance?.costPerPrediction ?? 250) tokens each. Technical analysis is free.")
                .font(.caption)
                .foregroundStyle(BullseyeTheme.textSecondary)

            if let packs = catalog?.tokenPacks, !packs.isEmpty {
                ForEach(packs) { pack in
                    tokenPackCard(pack)
                }
            } else {
                Text("Loading packs…")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
        }
    }

    private func tokenPackCard(_ pack: TokenPackCatalogItem) -> some View {
        let price = store.displayPrice(for: pack.productId, fallback: String(format: "$%.2f", pack.priceUsd))

        return HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(pack.label)
                    .font(.headline)
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Text("\(pack.tokens.formatted()) tokens")
                    .font(.subheadline.bold())
                    .foregroundStyle(BullseyeTheme.neonGreen)
                Text(pack.subtitle)
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textSecondary)
            }
            Spacer()
            Button(price) {
                Task { await buyTokenPack(pack) }
            }
            .font(.subheadline.bold())
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .foregroundStyle(BullseyeTheme.backgroundDeep)
            .background(BullseyeTheme.accentGradient)
            .clipShape(Capsule())
            .disabled(store.isPurchasing)
        }
        .padding(14)
        .glassCard(cornerRadius: 12)
    }

    private var footerNote: some View {
        VStack(alignment: .leading, spacing: 6) {
            if store.isPurchasing {
                HStack {
                    ProgressView().tint(BullseyeTheme.neonGreen)
                    Text("Processing purchase…")
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }
            }
            if let note = store.lastError {
                Text(note)
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
            Text("No login required — purchases are tied to your device. Restore via the same device ID.")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
    }

    private func reload() async {
        catalog = try? await APIService.shared.fetchPurchaseCatalog()
        usage = try? await APIService.shared.fetchUsageLimits()
        await appModel.refreshTokens()
        await subscription.loadFromBackend()
        await store.loadStoreProducts(catalog: catalog)
    }

    private func buyTokenPack(_ pack: TokenPackCatalogItem) async {
        do {
            successMessage = try await store.purchaseTokenPack(pack, appModel: appModel)
            showSuccess = true
            await reload()
        } catch StorePurchaseError.cancelled {
            return
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func buySubscription(_ sub: SubscriptionCatalogItem) async {
        do {
            successMessage = try await store.purchaseSubscription(sub, appModel: appModel)
            showSuccess = true
            await reload()
        } catch StorePurchaseError.cancelled {
            return
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}

struct CrownStoreButton: View {
    var accent: Color = BullseyeTheme.neonGreen
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "crown.fill")
                .foregroundStyle(accent)
        }
        .accessibilityLabel("Upgrade and buy tokens")
    }
}

struct UpgradeStoreSheetModifier: ViewModifier {
    @Binding var isPresented: Bool
    var accent: Color

    func body(content: Content) -> some View {
        content
            .sheet(isPresented: $isPresented) {
                NavigationStack {
                    UpgradeStoreView(appModel: AppSession.shared.appModel)
                }
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
    }
}

extension View {
    func upgradeStoreSheet(isPresented: Binding<Bool>) -> some View {
        modifier(UpgradeStoreSheetModifier(isPresented: isPresented, accent: BullseyeTheme.neonGreen))
    }
}
