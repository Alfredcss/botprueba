import React, { useState, useRef } from 'react'

/**
 * Message input bar for the advisor to send messages.
 */
export default function ChatInput({ clientPhone, onMessageSent }) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const inputRef = useRef(null)

  // Called externally via ref or prop from QuickReplies
  function applyTemplate(tmpl) {
    setText(tmpl)
    inputRef.current?.focus()
  }

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || !clientPhone || sending) return

    setText('')
    setSending(true)

    try {
      const API_URL = import.meta.env.VITE_API_URL || ''
      await fetch(`${API_URL}/api/enviar_mensaje/${encodeURIComponent(clientPhone)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: trimmed }),
      })
      onMessageSent?.()
    } catch (err) {
      console.error('Error enviando mensaje:', err)
    } finally {
      setSending(false)
    }
  }

  function handleKeyPress(e) {
    if (e.key === 'Enter') handleSend()
  }

  // Expose applyTemplate so parent can call it
  ChatInput.applyTemplate = applyTemplate

  return (
    <div className="chat-input-area">
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Escribe un mensaje..."
        className="chat-input"
        disabled={sending}
      />
      <button
        className="send-btn"
        onClick={handleSend}
        disabled={sending || !text.trim()}
        title="Enviar"
      >
        {sending ? (
          <i className="fa-solid fa-spinner fa-spin" />
        ) : (
          <i className="fa-solid fa-paper-plane" />
        )}
      </button>
    </div>
  )
}
