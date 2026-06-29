//
//  TokenBalanceBanner.swift
//  Bullseye
//

import SwiftUI

struct TokenBalanceBanner: View {
    @Bindable var appModel: AppViewModel
    @State private var showUpgradeStore = false

    var body: some View {
        Button {
            showUpgradeStore = true
        } label: {
            HStack {
                Image(systemName: "crown.fill")
                    .foregroundStyle(BullseyeTheme.neonGreen)
                Text("\(appModel.tokenBalance?.balance ?? appModel.user?.tokenBalance ?? 0) tokens")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(BullseyeTheme.textPrimary)
                Spacer()
                Text("\(appModel.tokenBalance?.costPerPrediction ?? 250) / prediction")
                    .font(.caption)
                    .foregroundStyle(BullseyeTheme.textSecondary)
                Image(systemName: "chevron.right")
                    .font(.caption2)
                    .foregroundStyle(BullseyeTheme.textTertiary)
            }
            .padding(14)
            .glassCard(cornerRadius: 12)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Buy tokens or upgrade")
        .upgradeStoreSheet(isPresented: $showUpgradeStore)
    }
}
