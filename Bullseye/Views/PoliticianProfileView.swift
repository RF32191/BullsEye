//
//  PoliticianProfileView.swift
//  Bullseye
//

import SwiftUI

struct PoliticianProfileView: View {
    let slug: String
    let initialName: String

    @State private var profile: PoliticianProfile?
    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 16) {
                if isLoading {
                    ProgressView()
                        .tint(BullseyeTheme.neonGreen)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else if let profile {
                    statsSection(profile)
                    disclaimerBanner(profile.disclaimer)
                    Text("Trade history")
                        .font(.headline)
                        .foregroundStyle(BullseyeTheme.textPrimary)
                    ForEach(profile.trades) { trade in
                        CongressTradeRow(trade: trade)
                    }
                } else {
                    Text(errorMessage ?? "Could not load profile")
                        .foregroundStyle(BullseyeTheme.textSecondary)
                }
            }
            .padding(20)
        }
        .navigationTitle(profile?.memberName ?? initialName)
        .navigationBarTitleDisplayMode(.inline)
        .withModeHomeButton(accent: BullseyeTheme.neonGreen)
        .task { await load() }
        .refreshable { await load() }
    }

    private func statsSection(_ profile: PoliticianProfile) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                if let party = profile.party {
                    Text(partyLabel(party))
                        .font(.caption.bold())
                        .foregroundStyle(partyColor(party))
                }
                if let chamber = profile.chamber {
                    Text(chamber)
                        .font(.caption)
                        .foregroundStyle(BullseyeTheme.textTertiary)
                }
            }

            HStack(spacing: 12) {
                statTile(
                    title: "Win rate",
                    value: profile.winRatePct.map { String(format: "%.0f%%", $0) } ?? "—",
                    accent: BullseyeTheme.neonGreen
                )
                statTile(
                    title: "Record",
                    value: "\(profile.wins)W · \(profile.losses)L",
                    accent: BullseyeTheme.textPrimary
                )
                statTile(
                    title: "Avg return",
                    value: profile.avgReturnSinceTradePct.map { String(format: "%+.1f%%", $0) } ?? "—",
                    accent: (profile.avgReturnSinceTradePct ?? 0) >= 0 ? BullseyeTheme.neonGreen : .orange
                )
            }

            Text("\(profile.totalTrades) disclosed trades tracked")
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }

    private func statTile(title: String, value: String, accent: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textTertiary)
            Text(value)
                .font(.subheadline.bold())
                .foregroundStyle(accent)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func disclaimerBanner(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(BullseyeTheme.neonGreenMuted)
            Text(text)
                .font(.caption2)
                .foregroundStyle(BullseyeTheme.textSecondary)
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    private func partyLabel(_ party: String) -> String {
        switch party.uppercased() {
        case "D": "Democrat"
        case "R": "Republican"
        case "I": "Independent"
        default: party
        }
    }

    private func partyColor(_ party: String) -> Color {
        switch party.uppercased() {
        case "D": Color.blue.opacity(0.9)
        case "R": Color.red.opacity(0.9)
        default: BullseyeTheme.textSecondary
        }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            profile = try await APIService.shared.fetchPoliticianProfile(slug: slug)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
