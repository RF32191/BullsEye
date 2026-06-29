//
//  PredictionEngine.swift
//  Bullseye
//

import SwiftUI

enum PredictionEngine: String, CaseIterable, Identifiable {
    case ai
    case technical

    var id: String { rawValue }

    var title: String {
        switch self {
        case .ai: "AI Model"
        case .technical: "Technical Bot"
        }
    }

    var subtitle: String {
        switch self {
        case .ai: "150–250 tokens · GPT analysis with bull/bear cases"
        case .technical: "Free · RSI, MACD, momentum from live data"
        }
    }

    var icon: String {
        switch self {
        case .ai: "brain.head.profile"
        case .technical: "waveform.path.ecg"
        }
    }
}
