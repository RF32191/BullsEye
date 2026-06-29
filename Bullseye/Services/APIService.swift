//
//  APIService.swift
//  Bullseye
//

import Foundation

actor APIService {
    static let shared = APIService()

    private var deviceID: String { DeviceIDManager.deviceID }

    func register() async throws -> UserProfile {
        struct Body: Encodable { let deviceId: String }
        return try await post("/auth/register", body: Body(deviceId: deviceID))
    }

    func tokenBalance() async throws -> TokenBalance {
        try await get("/auth/tokens")
    }

    func searchStocks(query: String) async throws -> [StockSearchResult] {
        try await get("/stocks/search", query: ["q": query])
    }

    func quote(ticker: String) async throws -> StockQuote {
        try await get("/stocks/\(ticker.uppercased())/quote")
    }

    func analyze(ticker: String, horizon: PredictionHorizonOption) async throws -> Prediction {
        struct Body: Encodable {
            let ticker: String
            let horizonValue: Int
            let horizonUnit: String
        }
        do {
            return try await post("/predictions/analyze", body: Body(ticker: ticker, horizonValue: horizon.value, horizonUnit: horizon.unit))
        } catch APIError.server(let msg) where msg.lowercased().contains("insufficient") {
            throw APIError.insufficientTokens
        }
    }

    func analyze(ticker: String, horizonDays: Int) async throws -> Prediction {
        try await analyze(ticker: ticker, horizon: PredictionHorizonOption(id: "\(horizonDays)d", label: "\(horizonDays)d", value: horizonDays, unit: "days"))
    }

    func analyzeTechnical(ticker: String, horizon: PredictionHorizonOption) async throws -> Prediction {
        struct Body: Encodable {
            let ticker: String
            let horizonValue: Int
            let horizonUnit: String
        }
        return try await post("/predictions/analyze-technical", body: Body(ticker: ticker, horizonValue: horizon.value, horizonUnit: horizon.unit))
    }

    func analyzeTechnical(ticker: String, horizonDays: Int) async throws -> Prediction {
        try await analyzeTechnical(ticker: ticker, horizon: PredictionHorizonOption(id: "\(horizonDays)d", label: "\(horizonDays)d", value: horizonDays, unit: "days"))
    }

    func fetchFlowAnalysis(ticker: String, horizon: PredictionHorizonOption) async throws -> FlowAnalysis {
        try await get(
            "/flow/\(ticker.uppercased())",
            query: ["horizon_value": String(horizon.value), "horizon_unit": horizon.unit]
        )
    }

    func predictFlow(ticker: String, horizon: PredictionHorizonOption, engine: PredictionEngine) async throws -> Prediction {
        struct Body: Encodable {
            let horizonValue: Int
            let horizonUnit: String
            let engine: String
        }
        let engineKey = engine == .ai ? "ai" : "technical"
        return try await post(
            "/flow/\(ticker.uppercased())/predict",
            body: Body(horizonValue: horizon.value, horizonUnit: horizon.unit, engine: engineKey)
        )
    }

    func fetchMacroDashboard() async throws -> MacroDashboard {
        try await get("/intelligence/macro")
    }

    func fetchCrossMarketLinks(ticker: String) async throws -> CrossMarketLinks {
        try await get("/intelligence/cross-market/\(ticker.uppercased())")
    }

    func fetchConflicts(limit: Int = 15) async throws -> ConflictsFeed {
        try await get("/intelligence/conflicts", query: ["limit": String(limit)])
    }

    func fetchUserWatches() async throws -> UserWatches {
        try await get("/intelligence/watches")
    }

    func updateUserWatches(_ watches: UserWatchesUpdate) async throws -> UserWatches {
        try await put("/intelligence/watches", body: watches)
    }

    func openPaperFromFlow(ticker: String, direction: String, notional: Double = 1000) async throws -> PaperPosition {
        struct Body: Encodable {
            let ticker: String
            let direction: String
            let notional: Double
        }
        return try await post("/paper/open-flow", body: Body(ticker: ticker.uppercased(), direction: direction, notional: notional))
    }

    func openPaperLive(ticker: String, side: String, liveTradeId: String, notional: Double = 500) async throws -> PaperPosition {
        struct Body: Encodable {
            let ticker: String
            let side: String
            let notional: Double
            let liveTradeId: String
        }
        return try await post("/paper/open-live", body: Body(ticker: ticker.uppercased(), side: side, notional: notional, liveTradeId: liveTradeId))
    }

    func closePaperPosition(id: String) async throws -> PaperPosition {
        try await post("/paper/close/\(id)", body: EmptyBody())
    }

    func depositPaperCash(amount: Double) async throws -> PaperAccount {
        struct Body: Encodable { let amount: Double }
        return try await post("/paper/deposit", body: Body(amount: amount))
    }

    func resetPaperWallet(amount: Double = 10_000) async throws -> PaperAccount {
        struct Body: Encodable { let amount: Double }
        return try await post("/paper/reset", body: Body(amount: amount))
    }

    func fetchPaperAccount() async throws -> PaperAccount {
        try await get("/paper/account")
    }

    func fetchSmartMoney(limit: Int = 50) async throws -> LiveTradesFeed {
        try await get("/alerts/smart-money", query: ["limit": String(limit)])
    }

    private struct EmptyBody: Encodable {}

    func fetchTracker(limit: Int = 50) async throws -> [Prediction] {
        try await get("/predictions/tracker", query: ["limit": String(limit)])
    }

    func fetchTrackerStats() async throws -> TrackerStats {
        try await get("/predictions/tracker/stats")
    }

    func fetchAccuracyTrend(ticker: String? = nil) async throws -> [DailyAccuracyPoint] {
        if let ticker {
            return try await get("/predictions/accuracy-trend", query: ["ticker": ticker.uppercased()])
        }
        return try await get("/predictions/accuracy-trend")
    }

    func fetchSubscription() async throws -> SubscriptionInfo {
        try await get("/subscription")
    }

    func updateSubscription(tier: SubscriptionTier) async throws -> SubscriptionInfo {
        struct Body: Encodable { let tier: String }
        return try await put("/subscription", body: Body(tier: tier.rawValue))
    }

    func fetchPurchaseCatalog() async throws -> PurchaseCatalog {
        try await get("/subscription/catalog")
    }

    func purchaseTokenPack(
        packId: String,
        productId: String,
        transactionId: String?,
        source: String
    ) async throws -> TokenPurchaseResponse {
        struct Body: Encodable {
            let packId: String
            let productId: String
            let transactionId: String?
            let source: String
        }
        return try await post(
            "/subscription/purchase-tokens",
            body: Body(packId: packId, productId: productId, transactionId: transactionId, source: source)
        )
    }

    func purchaseSubscription(
        productId: String,
        tier: SubscriptionTier?,
        transactionId: String?,
        source: String
    ) async throws -> SubscriptionInfo {
        struct Body: Encodable {
            let productId: String
            let tier: String?
            let transactionId: String?
            let source: String
        }
        return try await post(
            "/subscription/purchase-subscription",
            body: Body(productId: productId, tier: tier?.rawValue, transactionId: transactionId, source: source)
        )
    }

    func fetchTrend(ticker: String, days: Int = 90) async throws -> TrendResponse {
        try await get("/stocks/\(ticker.uppercased())/trend", query: ["days": String(days)])
    }

    func fetchTechnicals(ticker: String) async throws -> TechnicalAnalysis {
        try await get("/stocks/\(ticker.uppercased())/technicals")
    }

    func fetchCongressTrades(
        ticker: String? = nil,
        type: String? = nil,
        party: String? = nil,
        politician: String? = nil,
        page: Int = 1,
        perPage: Int = 30
    ) async throws -> CongressTradesResponse {
        var query: [String: String] = [
            "page": String(page),
            "per_page": String(perPage),
        ]
        if let ticker, !ticker.isEmpty { query["ticker"] = ticker.uppercased() }
        if let type { query["type"] = type }
        if let party { query["party"] = party }
        if let politician, !politician.isEmpty { query["politician"] = politician }
        return try await get("/congress/trades", query: query)
    }

    func fetchInsiderTrades(ticker: String? = nil, page: Int = 1) async throws -> InsiderTradesResponse {
        var query = ["page": String(page), "per_page": "30"]
        if let ticker, !ticker.isEmpty { query["ticker"] = ticker.uppercased() }
        return try await get("/insider/trades", query: query)
    }

    func fetchWatchlist() async throws -> [WatchlistItem] {
        try await get("/watchlist")
    }

    func addToWatchlist(ticker: String, companyName: String?) async throws -> WatchlistItem {
        struct Body: Encodable {
            let ticker: String
            let companyName: String?
        }
        return try await post("/watchlist", body: Body(ticker: ticker.uppercased(), companyName: companyName))
    }

    func removeFromWatchlist(ticker: String) async throws {
        struct OkResponse: Decodable { let ok: Bool }
        let _: OkResponse = try await delete("/watchlist/\(ticker.uppercased())")
    }

    func fetchPaperPortfolio() async throws -> PaperPortfolioResponse {
        try await get("/paper/portfolio")
    }

    func openPaperPosition(predictionId: UUID, notional: Double = 1000) async throws -> PaperPosition {
        struct Body: Encodable {
            let predictionId: UUID
            let notional: Double
        }
        return try await post("/paper/open", body: Body(predictionId: predictionId, notional: notional))
    }

    func fetchAccuracyDashboard() async throws -> AccuracyDashboard {
        try await get("/predictions/accuracy-dashboard")
    }

    func fetchUsageLimits() async throws -> UsageLimits {
        try await get("/predictions/usage")
    }

    func fetchPublicStats() async throws -> PublicStats {
        try await get("/predictions/public-stats")
    }

    func fetchTrendingEventMarkets(platform: String? = nil) async throws -> [EventMarket] {
        var query: [String: String] = [:]
        if let platform { query["platform"] = platform }
        return try await get("/event-markets/trending", query: query)
    }

    func searchEventMarkets(query q: String, platform: String? = nil) async throws -> [EventMarket] {
        var query = ["q": q]
        if let platform { query["platform"] = platform }
        return try await get("/event-markets/search", query: query)
    }

    func fetchEventCategories() async throws -> [EventCategory] {
        try await get("/event-markets/categories")
    }

    func fetchCategoryMarkets(slug: String, platform: String) async throws -> [EventMarket] {
        try await get("/event-markets/categories/\(slug)/markets", query: ["platform": platform])
    }

    func fetchEventTraders(platform: String? = nil, category: String? = nil) async throws -> [EventTrader] {
        var query: [String: String] = [:]
        if let platform { query["platform"] = platform }
        if let category { query["category"] = category }
        return try await get("/event-markets/traders", query: query)
    }

    func fetchEventTraderDetail(id: String) async throws -> EventTraderDetail {
        try await get("/event-markets/traders/\(id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? id)")
    }

    func fetchTopPoliticians(limit: Int = 15) async throws -> [PoliticianSummary] {
        try await get("/congress/politicians/top", query: ["limit": String(limit)])
    }

    func fetchPoliticianProfile(slug: String) async throws -> PoliticianProfile {
        try await get("/congress/politicians/\(slug)")
    }

    func fetchLiveTrades(market: String = "all", limit: Int = 40) async throws -> LiveTradesFeed {
        try await get("/alerts/live-trades", query: ["market": market, "limit": String(limit)])
    }

    func fetchAssetTrending(assetClass: String) async throws -> [AssetMarketQuote] {
        try await get("/asset-markets/\(assetClass)/trending")
    }

    func searchAssetMarkets(assetClass: String, query: String) async throws -> [AssetMarketQuote] {
        try await get("/asset-markets/\(assetClass)/search", query: ["q": query])
    }

    func fetchAssetCategories(assetClass: String) async throws -> [AssetMarketCategory] {
        try await get("/asset-markets/\(assetClass)/categories")
    }

    func fetchAssetCategoryMarkets(assetClass: String, slug: String) async throws -> [AssetMarketQuote] {
        try await get("/asset-markets/\(assetClass)/categories/\(slug)/markets")
    }

    func predictAssetMarket(assetClass: String, symbol: String, horizonDays: Int = 30) async throws -> AssetMarketPrediction {
        struct Body: Encodable {
            let symbol: String
            let horizonDays: Int
        }
        return try await post("/asset-markets/\(assetClass)/predict", body: Body(symbol: symbol, horizonDays: horizonDays))
    }

    func predictAssetMarketTechnical(assetClass: String, symbol: String, horizonDays: Int = 30) async throws -> AssetMarketPrediction {
        struct Body: Encodable {
            let symbol: String
            let horizonDays: Int
        }
        return try await post("/asset-markets/\(assetClass)/predict-technical", body: Body(symbol: symbol, horizonDays: horizonDays))
    }

    func fetchAssetQuote(assetClass: String, symbol: String) async throws -> AssetMarketQuote {
        try await get("/asset-markets/\(assetClass)/quote", query: ["symbol": symbol])
    }

    func fetchAssetTechnicals(assetClass: String, symbol: String) async throws -> TechnicalAnalysis {
        try await get("/asset-markets/\(assetClass)/technicals", query: ["symbol": symbol])
    }

    func fetchAssetComparison(assetClass: String, symbol: String, aiDirection: String, aiConfidence: Double) async throws -> ComparisonAnalysis {
        try await get(
            "/asset-markets/\(assetClass)/compare",
            query: ["symbol": symbol, "ai_direction": aiDirection, "ai_confidence": String(aiConfidence)]
        )
    }

    func fetchEventMarketAnalytics(platform: String, externalId: String) async throws -> EventMarketAnalytics {
        try await get("/event-markets/analytics", query: ["platform": platform, "external_id": externalId])
    }

    func fetchEventMarketComparison(platform: String, externalId: String, aiSide: String, aiConfidence: Double) async throws -> EventMarketCompare {
        try await get(
            "/event-markets/compare",
            query: ["platform": platform, "external_id": externalId, "ai_side": aiSide, "ai_confidence": String(aiConfidence)]
        )
    }

    func predictEventMarketTechnical(platform: String, externalId: String, horizonDays: Int = 30) async throws -> EventMarketPrediction {
        struct Body: Encodable {
            let platform: String
            let externalId: String
            let horizonDays: Int
        }
        return try await post("/event-markets/predict-technical", body: Body(platform: platform, externalId: externalId, horizonDays: horizonDays))
    }

    func fetchAssetTracker(assetClass: String) async throws -> [AssetMarketPrediction] {
        try await get("/asset-markets/\(assetClass)/tracker")
    }

    func fetchAssetTrackerStats(assetClass: String) async throws -> AssetMarketStats {
        try await get("/asset-markets/\(assetClass)/tracker/stats")
    }

    func fetchCategoryWatches() async throws -> [CategoryWatch] {
        try await get("/event-markets/watches")
    }

    func addCategoryWatch(platform: String, slug: String, label: String) async throws -> CategoryWatch {
        struct Body: Encodable {
            let platform: String
            let categorySlug: String
            let categoryLabel: String
        }
        return try await post("/event-markets/watches", body: Body(platform: platform, categorySlug: slug, categoryLabel: label))
    }

    func removeCategoryWatch(id: UUID) async throws {
        struct Ok: Decodable { let ok: Bool }
        let _: Ok = try await delete("/event-markets/watches/\(id.uuidString)")
    }

    func predictEventMarket(platform: String, externalId: String, horizonDays: Int = 30) async throws -> EventMarketPrediction {
        struct Body: Encodable {
            let platform: String
            let externalId: String
            let horizonDays: Int
        }
        return try await post("/event-markets/predict", body: Body(platform: platform, externalId: externalId, horizonDays: horizonDays))
    }

    func fetchEventTracker() async throws -> [EventMarketPrediction] {
        try await get("/event-markets/tracker")
    }

    func fetchEventTrackerStats() async throws -> EventMarketStats {
        try await get("/event-markets/tracker/stats")
    }

    func fetchComparison(ticker: String, aiDirection: String, aiConfidence: Double) async throws -> ComparisonAnalysis {
        try await get(
            "/stocks/\(ticker.uppercased())/compare",
            query: [
                "ai_direction": aiDirection,
                "ai_confidence": String(aiConfidence),
            ]
        )
    }

    func healthCheck() async throws -> HealthResponse {
        var request = URLRequest(url: APIConfig.baseURL.appending(path: "/health"))
        request.httpMethod = "GET"
        request.cachePolicy = .reloadIgnoringLocalCacheData
        return try await perform(request)
    }

    func ping() async throws -> PingResponse {
        try await get("/ping")
    }

    func fetchChatSessions() async throws -> [ChatSession] {
        try await get("/chat/sessions")
    }

    func fetchChatMessages(sessionId: UUID) async throws -> [ChatMessage] {
        try await get("/chat/sessions/\(sessionId.uuidString)/messages")
    }

    func sendChat(message: String, sessionId: UUID? = nil) async throws -> SendChatResponse {
        struct Body: Encodable {
            let message: String
            let sessionId: UUID?
        }
        do {
            return try await post("/chat/send", body: Body(message: message, sessionId: sessionId))
        } catch APIError.insufficientTokens {
            throw APIError.insufficientTokens
        }
    }

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        guard let url = apiURL(path: path, query: query) else { throw APIError.invalidResponse }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue(deviceID, forHTTPHeaderField: "X-Device-ID")
        request.cachePolicy = .reloadIgnoringLocalCacheData
        return try await perform(request)
    }

    func apiURL(path: String, query: [String: String] = [:]) -> URL? {
        var components = URLComponents()
        components.scheme = APIConfig.baseURL.scheme
        components.host = APIConfig.baseURL.host
        components.port = APIConfig.baseURL.port

        let basePath = APIConfig.baseURL.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let prefix = APIConfig.apiPrefix.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let resource = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let joined = [basePath, prefix, resource].filter { !$0.isEmpty }.joined(separator: "/")
        components.path = "/" + joined

        if !query.isEmpty {
            components.queryItems = query
                .sorted { $0.key < $1.key }
                .map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        return components.url
    }

    func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        guard let url = apiURL(path: path) else { throw APIError.invalidResponse }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceID, forHTTPHeaderField: "X-Device-ID")
        request.httpBody = try JSONCoding.encoder.encode(body)
        return try await perform(request)
    }

    func put<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        guard let url = apiURL(path: path) else { throw APIError.invalidResponse }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceID, forHTTPHeaderField: "X-Device-ID")
        request.httpBody = try JSONCoding.encoder.encode(body)
        return try await perform(request)
    }

    func delete<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        guard let url = apiURL(path: path, query: query) else { throw APIError.invalidResponse }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue(deviceID, forHTTPHeaderField: "X-Device-ID")
        return try await perform(request)
    }

    func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await NetworkSession.shared.data(for: request)
        } catch let error as URLError {
            throw mapURLError(error, host: request.url?.host)
        }

        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        if http.statusCode == 402 { throw APIError.insufficientTokens }

        if !(200...299).contains(http.statusCode) {
            throw APIError.server(parseErrorDetail(from: data, status: http.statusCode))
        }

        do {
            return try JSONCoding.decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(JSONCoding.decodeErrorMessage(error))
        }
    }

    private func parseErrorDetail(from data: Data, status: Int) -> String {
        if let decoded = try? JSONCoding.decoder.decode(APIErrorResponse.self, from: data) {
            let detail = decoded.detail
            if detail == "Not Found" {
                return "API endpoint not found. The server may need an update — try again after restarting the app."
            }
            return detail
        }
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let detail = json["detail"] as? String {
            return detail
        }
        if let body = String(data: data, encoding: .utf8), !body.isEmpty {
            return "Request failed (\(status)): \(body.prefix(200))"
        }
        return "Request failed (\(status))"
    }

    private func mapURLError(_ error: URLError, host: String?) -> APIError {
        switch error.code {
        case .cannotFindHost, .dnsLookupFailed:
            return .unreachable("Cannot find server. Check internet and API URL: \(APIConfig.displayURL)")
        case .notConnectedToInternet, .networkConnectionLost:
            return .unreachable("No internet connection.")
        case .timedOut:
            return .unreachable("Connection timed out to \(APIConfig.displayHost)")
        case .cannotConnectToHost:
            return .unreachable("Cannot connect to \(APIConfig.displayHost)")
        default:
            return .unreachable(error.localizedDescription)
        }
    }
}

struct PingResponse: Codable, Sendable {
    let ok: Bool
    let service: String
}
