//
//  AppViewModel.swift
//  Bullseye
//

import Foundation
import Observation

@Observable
@MainActor
final class AppViewModel {
    var user: UserProfile?
    var tokenBalance: TokenBalance?
    var isLoading = false
    var errorMessage: String?

    func bootstrap() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        LocalAnalyticsStore.shared.load()
        UserDefaults.standard.removeObject(forKey: "bullseye.railway.baseURL")

        let connected = await ConnectionService.shared.checkConnection()
        if !connected {
            errorMessage = ConnectionService.shared.lastError
        }

        do {
            user = try await APIService.shared.register()
            tokenBalance = try await APIService.shared.tokenBalance()
            ConnectionService.shared.isConnected = true
            ConnectionService.shared.lastError = nil
            errorMessage = nil
            await SubscriptionManager.shared.loadFromBackend()
            await LocalAnalyticsStore.shared.syncFromRailway()
        } catch {
            if errorMessage == nil {
                errorMessage = error.localizedDescription
            }
        }
    }

    func refreshTokens() async {
        do {
            user = try await APIService.shared.register()
            tokenBalance = try await APIService.shared.tokenBalance()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
