//
//  BullseyeApp.swift
//  Bullseye
//

import SwiftUI

@main
struct BullseyeApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .preferredColorScheme(.dark)
                .task {
                    await AppSession.shared.bootstrapIfNeeded()
                    await TradeAlertManager.shared.requestPermissionIfNeeded()
                    TradeAlertManager.shared.startPolling()
                }
        }
    }
}
