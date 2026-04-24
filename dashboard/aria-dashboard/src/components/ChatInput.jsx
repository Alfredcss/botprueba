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
      const res = await fetch(`${API_URL}/api/enviar_mensaje/${encodeURIComponent(clientPhone)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: trimmed }),
      })

      if (!res.ok) {
        console.error(`[ChatInput] Error del servidor: ${res.status} ${res.statusText}`)
        // Refetch de todas formas por si el mensaje se guardó parcialmente
        setTimeout(() => onMessageSent?.(), 1000)
        return
      }

      // Parsear JSON de forma segura — el servidor podría devolver cuerpo vacío en error
      let data = {}
      try {
        data = await res.json()
      } catch {
        console.warn('[ChatInput] La respuesta del servidor no era JSON válido.')
      }

      if (data.status === 'error') {
        console.error('[ChatInput] El backend reportó un error al guardar el mensaje:', data.detalle)
      }
      // Refetch primario a 800ms — da tiempo al backend Railway de escribir en Supabase
      setTimeout(() => onMessageSent?.(), 800)
      // Refetch secundario a 2.5s — red de seguridad por si la primera llega antes que la escritura
      setTimeout(() => onMessageSent?.(), 2500)
    } catch (err) {
      console.error('[ChatInput] No se pudo conectar con el servidor. ¿Está el backend corriendo?', err)
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
