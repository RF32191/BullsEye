//
//  AssetMarketCategoriesView.swift
//  Bullseye
//

import SwiftUI

struct AssetMarketCategoriesView: View {
    let platform: AssetMarketPlatform

    @State private var categories: [AssetMarketCategory] = []
    @State private var selected: AssetMarketCategory?
    @State private var markets: [AssetMarketQuote] = []
    @State private var isLoading = false

    var body: some View {
        ZStack {
            platform.backgroundGradient.ignoresSafeArea()
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("\(platform.title) Categories")
                        .font(.title2.bold())
                        .foregroundStyle(platform.textPrimary)

                    if isLoading { ProgressView().tint(platform.accent) }

                    ForEach(categories) { cat in
                        Button {
                            selected = cat
                            Task { await loadMarkets(cat) }
                        } label: {
                            HStack {
                                Text(cat.label)
                                    .font(.subheadline.bold())
                                    .foregroundStyle(platform.textPrimary)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(platform.textTertiary)
                            }
                            .padding(12)
                            .assetGlassCard(platform: platform, cornerRadius: 12)
                        }
                    }

                    if let selected, !markets.isEmpty {
                        Text("Markets in \(selected.label)")
                            .font(.headline)
                            .foregroundStyle(platform.accent)
                        ForEach(markets) { m in
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(m.name).font(.caption.bold()).foregroundStyle(platform.textPrimary)
                                    Text(m.symbol).font(.caption2).foregroundStyle(platform.textTertiary)
                                }
                                Spacer()
                                if let chg = m.changePct {
                                    Text(String(format: "%+.2f%%", chg))
                                        .font(.caption.bold())
                                        .foregroundStyle(chg >= 0 ? platform.accent : .orange)
                                }
                            }
                            .padding(10)
                            .assetGlassCard(platform: platform, cornerRadius: 10)
                        }
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Categories")
        .task { await reload() }
        .refreshable { await reload() }
    }

    private func reload() async {
        isLoading = true
        defer { isLoading = false }
        categories = (try? await APIService.shared.fetchAssetCategories(assetClass: platform.rawValue)) ?? []
    }

    private func loadMarkets(_ cat: AssetMarketCategory) async {
        markets = (try? await APIService.shared.fetchAssetCategoryMarkets(assetClass: platform.rawValue, slug: cat.slug)) ?? []
    }
}
