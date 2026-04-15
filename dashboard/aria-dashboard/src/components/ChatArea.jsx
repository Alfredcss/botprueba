import React, { useEffect, useRef } from 'react'
import ChatHeader from './ChatHeader'
import MessageBubble from './MessageBubble'
import QuickReplies from './QuickReplies'
import ChatInput from './ChatInput'
import { useChat } from '../hooks/useChat'
import { parseMessages } from '../lib/utils'

/**
 * Right panel — shows the conversation for the selected client.
 */
export default function ChatArea({
  selectedClient,
  botActive,
  onToggleBot,
  onBack,
  onConversationsRefetch,
}) {
  const telefono = selectedClient?.telefono ?? null
  const { rawLog, loading, refetch } = useChat(telefono)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Fallback date for legacy messages that only have [HH:MM] timestamps
  const rawFecha = selectedClient?._raw?.fecha_contacto || selectedClient?._raw?.created_at || null
  let fallbackDate = ''
  if (rawFecha) {
    // fecha_contacto is "YYYY-MM-DD", created_at is ISO string
    const d = new Date(rawFecha)
    if (!isNaN(d)) {
      const dd = String(d.getUTCDate()).padStart(2, '0')
      const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
      fallbackDate = `${dd}/${mm}`
    }
  }

  const messages = parseMessages(rawLog, fallbackDate)

  // Scroll to bottom whenever messages update
  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length])

  const clientName = selectedClient?.display || selectedClient?.telefono || 'Cliente'
  const clientPhone = selectedClient?.telefono
    ? String(selectedClient.telefono).replace('whatsapp:', '')
    : ''

  function handleMessageSent() {
    refetch()
    onConversationsRefetch?.()
  }

  function handleTemplate(text) {
    // Pass the template text down to ChatInput via a shared ref
    if (inputRef.current?.applyTemplate) {
      inputRef.current.applyTemplate(text)
    } else {
      // Fallback: dispatch a custom event
      window.__ariaTemplate = text
    }
  }

  // Empty state
  if (!selectedClient) {
    return (
      <div id="panel-chat" className="chat-panel chat-panel--empty">
        <div className="empty-state">
          <i className="fa-solid fa-gem empty-state__icon" />
          <h3 className="empty-state__text">Selecciona un prospecto</h3>
        </div>
      </div>
    )
  }

  // Build list with date separators injected between messages of different dates
  const renderedMessages = []
  let lastDate = null
  messages.forEach((msg, i) => {
    const currentDate = msg.date || null
    if (currentDate && currentDate !== lastDate) {
      renderedMessages.push(
        <div key={`date-${currentDate}-${i}`} className="date-separator">
          <span className="date-separator__pill">{currentDate}</span>
        </div>
      )
      lastDate = currentDate
    }
    renderedMessages.push(
      <MessageBubble key={i} role={msg.role} text={msg.text} time={msg.time} date={msg.date} />
    )
  })

  return (
    <div id="panel-chat" className="chat-panel">
      <ChatHeader
        clientName={clientName}
        clientPhone={clientPhone}
        botActive={botActive}
        onToggleBot={onToggleBot}
        onBack={onBack}
      />

      {/* Messages */}
      <div className="chat-messages">
        {loading && messages.length === 0 ? (
          <p className="empty-msg">Cargando mensajes...</p>
        ) : messages.length === 0 ? (
          <p className="empty-msg">Aún no hay mensajes.</p>
        ) : (
          renderedMessages
        )}
        <div ref={bottomRef} />
      </div>

      <QuickReplies onUseTemplate={handleTemplate} />
      <ChatInput
        clientPhone={telefono}
        onMessageSent={handleMessageSent}
      />
    </div>
  )
}
