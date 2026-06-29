//
//  AppSession.swift
//  Bullseye
//

import Foundation
import Observation

@MainActor
@Observable
final class AppSession {
    static let shared = AppSession()

    var appModel = AppViewModel()
    var connection = ConnectionService.shared
    var hasBootstrapped = false

    private init() {}

    func bootstrapIfNeeded() async {
        guard !hasBootstrapped else { return }
        await appModel.bootstrap()
        hasBootstrapped = true
    }

    func retryConnection() async {
        await connection.checkConnection()
        if connection.isConnected {
            await appModel.bootstrap()
            hasBootstrapped = true
        }
    }
}
