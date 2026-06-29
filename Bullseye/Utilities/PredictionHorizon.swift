//
//  PredictionHorizon.swift
//  Bullseye
//

import SwiftUI

struct PredictionHorizonOption: Identifiable, Equatable {
    let id: String
    let label: String
    let value: Int
    let unit: String

    static let stockOptions: [PredictionHorizonOption] = [
        .init(id: "15m", label: "15m", value: 15, unit: "minutes"),
        .init(id: "30m", label: "30m", value: 30, unit: "minutes"),
        .init(id: "1h", label: "1h", value: 1, unit: "hours"),
        .init(id: "4h", label: "4h", value: 4, unit: "hours"),
        .init(id: "1d", label: "1d", value: 1, unit: "days"),
        .init(id: "7d", label: "7d", value: 7, unit: "days"),
        .init(id: "30d", label: "30d", value: 30, unit: "days"),
        .init(id: "90d", label: "90d", value: 90, unit: "days"),
    ]

    static let dayOnlyOptions: [PredictionHorizonOption] = [
        .init(id: "7d", label: "7d", value: 7, unit: "days"),
        .init(id: "30d", label: "30d", value: 30, unit: "days"),
        .init(id: "90d", label: "90d", value: 90, unit: "days"),
    ]

    static let defaultStock = stockOptions.first(where: { $0.id == "30d" })!
}

struct PredictionHorizonPicker: View {
    @Binding var selection: PredictionHorizonOption
    let options: [PredictionHorizonOption]
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Horizon")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BullseyeTheme.textPrimary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(options) { option in
                        Button { selection = option } label: {
                            Text(option.label)
                                .font(.caption.bold())
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(selection == option ? accent.opacity(0.2) : Color.clear)
                                .foregroundStyle(selection == option ? accent : BullseyeTheme.textSecondary)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 10)
                                        .strokeBorder(selection == option ? accent : BullseyeTheme.glassBorder, lineWidth: 1)
                                )
                        }
                    }
                }
            }
        }
    }
}

enum AlertFrequency: String, CaseIterable, Identifiable {
    case realtime
    case fast
    case normal
    case slow
    case hourly
    case digest

    var id: String { rawValue }

    var label: String {
        switch self {
        case .realtime: "Real-time (1 min)"
        case .fast: "Fast (5 min)"
        case .normal: "Normal (15 min)"
        case .slow: "Slow (30 min)"
        case .hourly: "Hourly"
        case .digest: "Daily digest (batch)"
        }
    }

    var intervalNanoseconds: UInt64 {
        switch self {
        case .realtime: 60_000_000_000
        case .fast: 300_000_000_000
        case .normal: 900_000_000_000
        case .slow: 1_800_000_000_000
        case .hourly: 3_600_000_000_000
        case .digest: 86_400_000_000_000
        }
    }
}

struct AlertFrequencyPicker: View {
    @Binding var selection: AlertFrequency
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Notification frequency")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BullseyeTheme.textPrimary)
            ForEach(AlertFrequency.allCases) { freq in
                Button {
                    selection = freq
                } label: {
                    HStack {
                        Text(freq.label)
                            .foregroundStyle(BullseyeTheme.textPrimary)
                        Spacer()
                        if selection == freq {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(accent)
                        }
                    }
                    .padding(12)
                    .background(BullseyeTheme.glassFill)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .strokeBorder(selection == freq ? accent.opacity(0.5) : BullseyeTheme.glassBorder, lineWidth: 1)
                    )
                }
            }
        }
    }
}
