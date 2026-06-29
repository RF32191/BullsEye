//
//  StorePurchaseManager.swift
//  Bullseye
//

import Foundation
import StoreKit

@MainActor
@Observable
final class StorePurchaseManager {
    static let shared = StorePurchaseManager()

    private(set) var storeProducts: [Product] = []
    private(set) var isLoadingProducts = false
    private(set) var isPurchasing = false
    private(set) var lastError: String?

    private var updateListenerTask: Task<Void, Never>?

    private init() {
        updateListenerTask = listenForTransactions()
    }

    func loadStoreProducts(catalog: PurchaseCatalog?) async {
        guard !isLoadingProducts else { return }
        isLoadingProducts = true
        defer { isLoadingProducts = false }

        var ids = Set<String>()
        catalog?.tokenPacks.forEach { ids.insert($0.productId) }
        catalog?.subscriptions.forEach { ids.insert($0.productId) }

        if ids.isEmpty {
            ids = [
                "Fermoselle.Bullseye.tokens.2500",
                "Fermoselle.Bullseye.tokens.10000",
                "Fermoselle.Bullseye.tokens.50000",
                "Fermoselle.Bullseye.pro.monthly",
                "Fermoselle.Bullseye.elite.monthly",
            ]
        }

        do {
            storeProducts = try await Product.products(for: Array(ids))
            lastError = storeProducts.isEmpty ? "App Store products not configured yet — dev purchase available." : nil
        } catch {
            storeProducts = []
            lastError = error.localizedDescription
        }
    }

    func displayPrice(for productId: String, fallback: String) -> String {
        storeProducts.first(where: { $0.id == productId })?.displayPrice ?? fallback
    }

    func purchaseTokenPack(_ pack: TokenPackCatalogItem, appModel: AppViewModel) async throws -> String {
        isPurchasing = true
        lastError = nil
        defer { isPurchasing = false }

        if let product = storeProducts.first(where: { $0.id == pack.productId }) {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                let transaction = try checkVerified(verification)
                let response = try await APIService.shared.purchaseTokenPack(
                    packId: pack.id,
                    productId: pack.productId,
                    transactionId: String(transaction.id),
                    source: "app_store"
                )
                await transaction.finish()
                await appModel.refreshTokens()
                return response.message
            case .userCancelled:
                throw StorePurchaseError.cancelled
            case .pending:
                throw StorePurchaseError.pending
            @unknown default:
                throw StorePurchaseError.failed
            }
        }

        let response = try await APIService.shared.purchaseTokenPack(
            packId: pack.id,
            productId: pack.productId,
            transactionId: nil,
            source: "dev"
        )
        await appModel.refreshTokens()
        return response.message
    }

    func purchaseSubscription(_ sub: SubscriptionCatalogItem, appModel: AppViewModel) async throws -> String {
        isPurchasing = true
        lastError = nil
        defer { isPurchasing = false }

        if let product = storeProducts.first(where: { $0.id == sub.productId }) {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                let transaction = try checkVerified(verification)
                _ = try await APIService.shared.purchaseSubscription(
                    productId: sub.productId,
                    tier: SubscriptionTier(rawValue: sub.tier),
                    transactionId: String(transaction.id),
                    source: "app_store"
                )
                await transaction.finish()
                await SubscriptionManager.shared.loadFromBackend()
                await appModel.refreshTokens()
                return "Welcome to \(sub.label)!"
            case .userCancelled:
                throw StorePurchaseError.cancelled
            case .pending:
                throw StorePurchaseError.pending
            @unknown default:
                throw StorePurchaseError.failed
            }
        }

        _ = try await APIService.shared.purchaseSubscription(
            productId: sub.productId,
            tier: SubscriptionTier(rawValue: sub.tier),
            transactionId: nil,
            source: "dev"
        )
        await SubscriptionManager.shared.loadFromBackend()
        await appModel.refreshTokens()
        return "Welcome to \(sub.label)!"
    }

    private func listenForTransactions() -> Task<Void, Never> {
        Task.detached {
            for await result in Transaction.updates {
                if case .verified(let transaction) = result {
                    await transaction.finish()
                }
            }
        }
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw StorePurchaseError.failed
        case .verified(let safe):
            return safe
        }
    }
}

enum StorePurchaseError: LocalizedError {
    case cancelled
    case pending
    case failed

    var errorDescription: String? {
        switch self {
        case .cancelled: "Purchase cancelled"
        case .pending: "Purchase pending approval"
        case .failed: "Purchase could not be completed"
        }
    }
}
