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

  const messages = parseMessages(rawLog)

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
          messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} text={msg.text} time={msg.time} />
          ))
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
