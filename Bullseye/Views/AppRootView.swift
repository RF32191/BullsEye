//
//  AppRootView.swift
//  Bullseye
//

import SwiftUI

/// Entry wrapper — use in BullseyeApp instead of ContentView directly for terms gating.
struct AppRootView: View {
    @State private var termsAccepted = LegalTermsManager.hasAcceptedCurrentTerms

    var body: some View {
        Group {
            if termsAccepted {
                ContentView()
                    .preferredColorScheme(.dark)
                    .task {
                        await AppSession.shared.bootstrapIfNeeded()
                        await TradeAlertManager.shared.requestPermissionIfNeeded()
                        TradeAlertManager.shared.startPolling()
                    }
            } else {
                TermsAcceptanceView {
                    termsAccepted = true
                }
            }
        }
    }
}
