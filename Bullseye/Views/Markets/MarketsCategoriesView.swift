//
//  MarketsCategoriesView.swift
//  Bullseye
//

import SwiftUI

struct MarketsCategoriesView: View {
    let platform: EventMarketPlatform

    @State private var categories: [EventCategory] = []
    @State private var watches: [CategoryWatch] = []
    @State private var selectedCategory: EventCategory?
    @State private var categoryMarkets: [EventMarket] = []
    @State private var isLoading = false

    private var platformWatches: [CategoryWatch] {
        watches.filter { $0.platform == platform.rawValue }
    }

    private var platformCategories: [EventCategory] {
        categories.filter { $0.platform == platform.rawValue }
    }

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("\(platform.title) Categories")
                        .font(.title2.bold())
                        .foregroundStyle(platform.textPrimary)
                    Text("Follow categories for AI predictions on \(platform.title).")
                        .font(.caption)
                        .foregroundStyle(platform.textSecondary)

                    if !platformWatches.isEmpty {
                        Text("Watching")
                            .font(.headline)
                            .foregroundStyle(platform.accent)
                        ForEach(platformWatches) { w in
                            HStack {
                                Text(w.categoryLabel)
                                    .foregroundStyle(platform.textPrimary)
                                Spacer()
                                Button(role: .destructive) {
                                    Task { await removeWatch(w.id) }
                                } label: {
                                    Image(systemName: "xmark.circle")
                                }
                            }
                            .padding(12)
                            .eventGlassCard(platform: platform, cornerRadius: 12)
                        }
                    }

                    Text("Browse")
                        .font(.headline)
                        .foregroundStyle(platform.textPrimary)

                    if isLoading {
                        ProgressView().tint(platform.accent)
                    }

                    ForEach(platformCategories) { cat in
                        Button {
                            selectedCategory = cat
                            Task { await loadMarkets(cat) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(cat.label)
                                        .font(.subheadline.bold())
                                        .foregroundStyle(platform.textPrimary)
                                }
                                Spacer()
                                Button {
                                    Task { await addWatch(cat) }
                                } label: {
                                    Image(systemName: "star")
                                        .foregroundStyle(platform.accent)
                                }
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(platform.textTertiary)
                            }
                            .padding(12)
                            .eventGlassCard(platform: platform, cornerRadius: 12)
                        }
                    }

                    if let selectedCategory, !categoryMarkets.isEmpty {
                        Text("Markets in \(selectedCategory.label)")
                            .font(.headline)
                            .foregroundStyle(platform.accent)
                        ForEach(categoryMarkets) { m in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(m.question)
                                    .font(.caption)
                                    .foregroundStyle(platform.textPrimary)
                                if let yes = m.yesPrice {
                                    Text("Yes \(Int(yes * 100))%")
                                        .font(.caption2)
                                        .foregroundStyle(platform.accent)
                                }
                            }
                            .padding(10)
                            .eventGlassCard(platform: platform, cornerRadius: 10)
                        }
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Categories")
        .refreshable { await reload() }
        .task { await reload() }
    }

    private func reload() async {
        isLoading = true
        defer { isLoading = false }
        categories = (try? await APIService.shared.fetchEventCategories()) ?? []
        watches = (try? await APIService.shared.fetchCategoryWatches()) ?? []
    }

    private func loadMarkets(_ cat: EventCategory) async {
        categoryMarkets = (try? await APIService.shared.fetchCategoryMarkets(slug: cat.slug, platform: platform.rawValue)) ?? []
    }

    private func addWatch(_ cat: EventCategory) async {
        _ = try? await APIService.shared.addCategoryWatch(platform: platform.rawValue, slug: cat.slug, label: cat.label)
        await reload()
    }

    private func removeWatch(_ id: UUID) async {
        try? await APIService.shared.removeCategoryWatch(id: id)
        await reload()
    }
}
