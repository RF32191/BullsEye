//
//  TermsAcceptanceView.swift
//  Bullseye
//

import SwiftUI

struct TermsAcceptanceView: View {
    @State private var hasReadTerms = false
    @State private var hasAcknowledgedRisk = false
    var onAccepted: () -> Void

    private var canAccept: Bool { hasReadTerms && hasAcknowledgedRisk }

    var body: some View {
        ZStack {
            BullseyeTheme.backgroundGradient.ignoresSafeArea()

            VStack(spacing: 0) {
                VStack(spacing: 8) {
                    Image(systemName: "exclamationmark.shield.fill")
                        .font(.largeTitle)
                        .foregroundStyle(BullseyeTheme.neonGreen)
                    Text(LegalTermsManager.termsTitle)
                        .font(.title3.bold())
                        .foregroundStyle(BullseyeTheme.textPrimary)
                    Text("Required before using Bullseye AI")
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }
                .padding(.top, 24)
                .padding(.horizontal, 20)

                ScrollView {
                    Text(LegalTermsManager.termsBody)
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textSecondary)
                        .padding(20)
                }
                .background(BullseyeTheme.glassFill)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .padding(.horizontal, 16)
                .padding(.vertical, 12)

                VStack(alignment: .leading, spacing: 12) {
                    Toggle(isOn: $hasReadTerms) {
                        Text("I have read and understand the Terms of Use")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textPrimary)
                    }
                    .tint(BullseyeTheme.neonGreen)

                    Toggle(isOn: $hasAcknowledgedRisk) {
                        Text("I understand trading involves risk of loss and Bullseye is not investment advice")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textPrimary)
                    }
                    .tint(BullseyeTheme.neonGreen)

                    Button {
                        LegalTermsManager.acceptCurrentTerms()
                        onAccepted()
                    } label: {
                        Text("I Accept — Continue to Bullseye")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .foregroundStyle(.black)
                    .background(canAccept ? BullseyeTheme.accentGradient : LinearGradient(colors: [.gray], startPoint: .leading, endPoint: .trailing))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .disabled(!canAccept)
                }
                .padding(20)
            }
        }
        .preferredColorScheme(.dark)
        .interactiveDismissDisabled()
    }
}
