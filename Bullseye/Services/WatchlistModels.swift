//
//  WatchlistModels.swift
//  Bullseye
//

import Foundation

enum CategoryWatchlistAPI {
    static func fetch(category: String) async throws -> [WatchlistItem] {
        try await APIService.shared.getWatchlist(category: category)
    }

    static func add(ticker: String, name: String?, category: String) async throws -> WatchlistItem {
        try await APIService.shared.postWatchlist(ticker: ticker, companyName: name, category: category)
    }

    static func remove(ticker: String, category: String) async throws {
        try await APIService.shared.deleteWatchlist(ticker: ticker, category: category)
    }
}
