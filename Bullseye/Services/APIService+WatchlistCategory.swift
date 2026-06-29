//
//  APIService+WatchlistCategory.swift
//  Bullseye
//

import Foundation

extension APIService {
    func getWatchlist(category: String) async throws -> [WatchlistItem] {
        try await get("/watchlist", query: ["category": category])
    }

    func postWatchlist(ticker: String, companyName: String?, category: String) async throws -> WatchlistItem {
        struct Body: Encodable {
            let ticker: String
            let companyName: String?
            let category: String
        }
        return try await post(
            "/watchlist",
            body: Body(ticker: ticker.uppercased(), companyName: companyName, category: category)
        )
    }

    func deleteWatchlist(ticker: String, category: String) async throws {
        struct OkResponse: Decodable { let ok: Bool }
        let _: OkResponse = try await delete(
            "/watchlist/\(ticker.uppercased())",
            query: ["category": category]
        )
    }
}
