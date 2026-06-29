//
//  ConnectionService.swift
//  Bullseye
//

import Foundation
import Observation

@Observable
@MainActor
final class ConnectionService {
    static let shared = ConnectionService()

    var isConnected = false
    var lastError: String?
    var lastChecked: Date?

    func checkConnection() async -> Bool {
        do {
            let health = try await APIService.shared.healthCheck()
            guard health.status == "ok" else { throw URLError(.badServerResponse) }
            isConnected = true
            lastError = nil
            lastChecked = Date()
            return true
        } catch let apiError as APIError {
            isConnected = false
            lastError = apiError.localizedDescription
            lastChecked = Date()
            return false
        } catch {
            isConnected = false
            lastError = friendlyMessage(for: error)
            lastChecked = Date()
            return false
        }
    }

    private func friendlyMessage(for error: Error) -> String {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .cannotFindHost, .dnsLookupFailed:
                return "Cannot find server at \(APIConfig.displayURL)"
            case .notConnectedToInternet, .networkConnectionLost:
                return "No internet connection"
            case .timedOut:
                return "Connection timed out"
            case .cannotConnectToHost:
                return "Cannot connect to \(APIConfig.displayURL)"
            default:
                return urlError.localizedDescription
            }
        }
        return error.localizedDescription
    }
}
