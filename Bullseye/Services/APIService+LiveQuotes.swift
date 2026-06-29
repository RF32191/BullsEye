//
//  APIService+LiveQuotes.swift
//  Bullseye
//

import Foundation

struct LiveStockQuoteResponse: Codable, Sendable {
    let symbol: String
    let name: String
    let price: Double
    let change: Double
    let changePct: Double
    let source: String?
    let isLive: Bool?
    let fetchedAt: String?
    let priceNote: String?
}

struct LiveAssetQuoteResponse: Codable, Sendable {
    let assetClass: String
    let symbol: String
    let name: String
    let category: String
    let price: Double?
    let changePct: Double?
    let volume: Double?
    let source: String?
    let isLive: Bool?
    let fetchedAt: String?
    let priceNote: String?
}

extension APIService {
    func fetchLiveStockQuote(ticker: String) async throws -> LiveStockQuoteResponse {
        try await get("/stocks/\(ticker.uppercased())/quote", query: ["fresh": "true"])
    }

    func fetchLiveAssetQuote(assetClass: String, symbol: String) async throws -> LiveAssetQuoteResponse {
        try await get(
            "/asset-markets/\(assetClass)/quote",
            query: ["symbol": symbol.uppercased(), "fresh": "true"]
        )
    }
}
