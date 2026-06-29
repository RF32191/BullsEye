//
//  ChatInputField.swift
//  Bullseye
//

import SwiftUI

#if canImport(UIKit)
import UIKit

struct ChatInputField: UIViewRepresentable {
    @Binding var text: String
    var placeholder: String
    var onSend: () -> Void

    func makeUIView(context: Context) -> UITextField {
        let field = UITextField()
        field.delegate = context.coordinator
        field.placeholder = placeholder
        field.borderStyle = .none
        field.backgroundColor = UIColor.white.withAlphaComponent(0.06)
        field.textColor = .white
        field.tintColor = UIColor(red: 0, green: 1, blue: 0.4, alpha: 1)
        field.font = .systemFont(ofSize: 16)
        field.autocorrectionType = .no
        field.autocapitalizationType = .sentences
        field.returnKeyType = .send
        field.enablesReturnKeyAutomatically = true
        field.layer.cornerRadius = 12
        field.layer.masksToBounds = true
        field.leftView = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 1))
        field.leftViewMode = .always
        field.rightView = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 1))
        field.rightViewMode = .always
        field.addTarget(context.coordinator, action: #selector(Coordinator.textChanged), for: .editingChanged)
        return field
    }

    func updateUIView(_ uiView: UITextField, context: Context) {
        if uiView.text != text { uiView.text = text }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(text: $text, onSend: onSend)
    }

    final class Coordinator: NSObject, UITextFieldDelegate {
        @Binding var text: String
        let onSend: () -> Void

        init(text: Binding<String>, onSend: @escaping () -> Void) {
            _text = text
            self.onSend = onSend
        }

        @objc func textChanged(_ sender: UITextField) {
            text = sender.text ?? ""
        }

        func textFieldShouldReturn(_ textField: UITextField) -> Bool {
            onSend()
            return true
        }
    }
}

#else

struct ChatInputField: View {
    @Binding var text: String
    var placeholder: String
    var onSend: () -> Void

    var body: some View {
        TextField(placeholder, text: $text)
            .onSubmit(onSend)
            .foregroundStyle(BullseyeTheme.textPrimary)
            .padding(12)
            .background(BullseyeTheme.glassFill)
            .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

#endif
