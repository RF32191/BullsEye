//
//  ChatView.swift
//  Bullseye
//

import SwiftUI

struct ChatView: View {
    @Bindable var appModel: AppViewModel

    @State private var sessions: [ChatSession] = []
    @State private var messages: [ChatMessage] = []
    @State private var activeSessionId: UUID?
    @State private var input = ""
    @State private var isLoading = false
    @State private var isSending = false
    @State private var showError = false
    @State private var errorMessage: String?
    @State private var showSessions = false
    @State private var serverOnline = true

    var body: some View {
        VStack(spacing: 0) {
            connectionBanner
            messagesList
            Divider().overlay(BullseyeTheme.glassBorder)
            inputBar
        }
        .background(BullseyeTheme.backgroundGradient.ignoresSafeArea())
        .navigationTitle("AI Chat")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showSessions.toggle() } label: {
                    Image(systemName: "list.bullet")
                        .foregroundStyle(BullseyeTheme.neonGreen)
                }
            }
            ToolbarItem(placement: .topBarLeading) {
                Button("New") {
                    activeSessionId = nil
                    messages = []
                    dismissKeyboard()
                }
                .foregroundStyle(BullseyeTheme.neonGreen)
            }
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { dismissKeyboard() }
                    .foregroundStyle(BullseyeTheme.neonGreen)
            }
        }
        .sheet(isPresented: $showSessions) { sessionPicker }
        .task {
            await checkServer()
            await loadSessions()
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var connectionBanner: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(serverOnline ? BullseyeTheme.neonGreen : .red)
                .frame(width: 8, height: 8)
            Text(serverOnline ? "Connected · \(APIConfig.displayHost)" : "Server offline")
                .font(.caption2)
                .foregroundStyle(serverOnline ? BullseyeTheme.textSecondary : .red)
                .lineLimit(1)
            Spacer()
            Button("Retry") { Task { await checkServer(); await loadSessions() } }
                .font(.caption2.bold())
                .foregroundStyle(BullseyeTheme.neonGreen)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(BullseyeTheme.backgroundDeep.opacity(0.6))
    }

    private var messagesList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 14) {
                    if messages.isEmpty && !isLoading { emptyPrompt }
                    ForEach(messages) { message in
                        ChatBubble(message: message).id(message.id)
                    }
                    if isSending {
                        HStack {
                            ProgressView().tint(BullseyeTheme.neonGreen)
                            Text("Bullseye AI is thinking…")
                                .font(.subheadline)
                                .foregroundStyle(BullseyeTheme.textSecondary)
                            Spacer()
                        }
                        .padding(.horizontal, 16)
                    }
                }
                .padding(.vertical, 12)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: messages.count) { _, _ in
                if let last = messages.last {
                    withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
        }
    }

    private var emptyPrompt: some View {
        VStack(spacing: 12) {
            Image(systemName: "bubble.left.and.text.bubble.right")
                .font(.largeTitle)
                .foregroundStyle(BullseyeTheme.neonGreen)
            Text("Ask Bullseye AI")
                .font(.headline)
                .foregroundStyle(BullseyeTheme.textPrimary)
            Text("Try: \"Should I buy NVDA?\" or \"Compare AAPL vs MSFT\"")
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(BullseyeTheme.textSecondary)
                .padding(.horizontal, 24)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    private var inputBar: some View {
        HStack(spacing: 10) {
            TextField("Ask about any stock…", text: $input, axis: .vertical)
                .lineLimit(1...4)
                .foregroundStyle(.white)
                .tint(BullseyeTheme.neonGreen)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(BullseyeTheme.chatInputFill)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                .onSubmit { Task { await sendMessage() } }

            Button { Task { await sendMessage() } } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(canSend ? BullseyeTheme.neonGreen : Color.gray.opacity(0.5))
            }
            .disabled(!canSend)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(BullseyeTheme.backgroundDeep)
    }

    private var canSend: Bool {
        !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isSending && serverOnline
    }

    private var sessionPicker: some View {
        NavigationStack {
            List(sessions) { session in
                Button {
                    activeSessionId = session.id
                    showSessions = false
                    Task { await loadMessages(sessionId: session.id) }
                } label: {
                    VStack(alignment: .leading) {
                        Text(session.title).foregroundStyle(BullseyeTheme.textPrimary)
                        Text("\(session.messageCount) messages · \(session.updatedAt.formatted(date: .abbreviated, time: .shortened))")
                            .font(.caption)
                            .foregroundStyle(BullseyeTheme.textSecondary)
                    }
                }
            }
            .navigationTitle("Chat History")
            .preferredColorScheme(.dark)
        }
    }

    private func checkServer() async {
        serverOnline = await ConnectionService.shared.checkConnection()
    }

    private func loadSessions() async {
        isLoading = true
        defer { isLoading = false }
        do {
            sessions = try await APIService.shared.fetchChatSessions()
            serverOnline = true
        } catch {
            serverOnline = false
            presentError(error)
        }
    }

    private func loadMessages(sessionId: UUID) async {
        isLoading = true
        defer { isLoading = false }
        do {
            messages = try await APIService.shared.fetchChatMessages(sessionId: sessionId)
        } catch {
            presentError(error)
        }
    }

    private func sendMessage() async {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        isSending = true
        defer { isSending = false }

        do {
            let response = try await APIService.shared.sendChat(message: text, sessionId: activeSessionId)
            input = ""
            dismissKeyboard()
            activeSessionId = response.sessionId
            messages.append(response.userMessage)
            messages.append(response.assistantMessage)
            serverOnline = true
            await appModel.refreshTokens()
            await loadSessions()
        } catch {
            presentError(error)
        }
    }

    private func presentError(_ error: Error) {
        errorMessage = error.localizedDescription
        showError = true
    }
}

private struct ChatBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top) {
            if message.isUser { Spacer(minLength: 28) }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 10) {
                Text(displayText)
                    .font(.body)
                    .lineSpacing(6)
                    .foregroundStyle(message.isUser ? Color.black : Color.white)
                    .multilineTextAlignment(message.isUser ? .trailing : .leading)
                    .textSelection(.enabled)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(message.isUser ? BullseyeTheme.neonGreen : BullseyeTheme.chatAssistantFill)
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay {
                        if !message.isUser {
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .strokeBorder(BullseyeTheme.neonGreen.opacity(0.35), lineWidth: 1)
                        }
                    }

                if let citations = message.citations, !citations.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Sources")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(BullseyeTheme.neonGreen)
                        ForEach(citations) { citation in
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(citation.source) · \(citation.label)")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(citation.detail)
                                    .font(.caption)
                                    .foregroundStyle(Color.white.opacity(0.75))
                            }
                        }
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(BullseyeTheme.chatCitationFill)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
            .frame(maxWidth: 340, alignment: message.isUser ? .trailing : .leading)

            if !message.isUser { Spacer(minLength: 28) }
        }
        .padding(.horizontal, 12)
    }

    private var displayText: String {
        message.content
            .replacingOccurrences(of: "**", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
