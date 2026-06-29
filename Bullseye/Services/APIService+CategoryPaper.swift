//
//  APIService+CategoryPaper.swift
//  Bullseye
//

import Foundation

struct CategoryPaperWallet: Codable, Identifiable, Sendable {
    var id: String { category }
    let category: String
    let cashBalance: Double
    let startingBalance: Double
    let investedOpen: Double
    let equity: Double
    let unrealizedPnlUsd: Double
    let realizedPnlUsd: Double
    let totalPnlUsd: Double
    let totalReturnPct: Double
    let openPositions: Int
    let closedPositions: Int
    let closedWinRatePct: Double?
}

struct CategoryWalletsResponse: Codable, Sendable {
    let wallets: [CategoryPaperWallet]
}

struct CategoryPaperPortfolioResponse: Codable, Sendable {
    let category: String
    let account: CategoryPaperWallet
    let positions: [PaperPosition]
    let summary: PaperPortfolioSummary
}

extension APIService {
    func fetchCategoryWallets() async throws -> CategoryWalletsResponse {
        try await get("/paper/wallets")
    }

    func fetchCategoryPortfolio(category: String) async throws -> CategoryPaperPortfolioResponse {
        try await get("/paper/category/\(category.lowercased())/portfolio")
    }

    func buyCategoryPaper(
        category: String,
        symbol: String,
        direction: String,
        notional: Double,
        name: String? = nil
    ) async throws -> PaperPosition {
        struct Body: Encodable {
            let symbol: String
            let direction: String
            let notional: Double
            let name: String?
        }
        return try await post(
            "/paper/category/\(category.lowercased())/buy",
            body: Body(symbol: symbol.uppercased(), direction: direction, notional: notional, name: name)
        )
    }

    func sellCategoryPaper(category: String, positionId: String) async throws -> PaperPosition {
        try await post("/paper/category/\(category.lowercased())/sell/\(positionId)", body: EmptyEncodable())
    }

    func depositCategoryPaper(category: String, amount: Double) async throws -> CategoryPaperWallet {
        struct Body: Encodable { let amount: Double }
        return try await post("/paper/category/\(category.lowercased())/deposit", body: Body(amount: amount))
    }

    func resetCategoryPaper(category: String, amount: Double = 10_000) async throws -> CategoryPaperWallet {
        struct Body: Encodable { let amount: Double }
        return try await post("/paper/category/\(category.lowercased())/reset", body: Body(amount: amount))
    }
}

private struct EmptyEncodable: Encodable {}

extension CategoryPaperWallet {
    static let displayNames: [String: String] = [
        "stocks": "Stocks",
        "crypto": "Crypto",
        "futures": "Futures",
        "forex": "Forex",
        "polymarket": "Polymarket",
        "kalshi": "Kalshi",
    ]

    var displayName: String {
        Self.displayNames[category] ?? category.capitalized
    }

    var isEventMarket: Bool {
        category == "polymarket" || category == "kalshi"
    }
}
