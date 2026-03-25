import React from 'react'
import { formatearEnlaces } from '../lib/utils'

/**
 * Renders a single chat message bubble.
 * @param {{ role: 'Bot'|'Cliente'|'Asesor', text: string, time: string }} props
 */
export default function MessageBubble({ role, text, time }) {
  const botName = import.meta.env.VITE_BOT_NAME || 'IA'

  const timeHtml = time
    ? `<span class="msg-time">${time}</span>`
    : ''

  const linkedText = formatearEnlaces(text)

  if (role === 'Cliente') {
    return (
      <div className="msg-row msg-row--left">
        <div className="bubble bubble--client">
          <p
            className="bubble__text"
            dangerouslySetInnerHTML={{ __html: linkedText + timeHtml }}
          />
        </div>
      </div>
    )
  }

  if (role === 'Bot') {
    return (
      <div className="msg-row msg-row--right">
        <div className="bubble bubble--bot">
          <span className="bubble__label">
            <i className="fa-solid fa-robot" style={{ marginRight: 4 }} />
            {botName}
          </span>
          <p
            className="bubble__text"
            dangerouslySetInnerHTML={{ __html: linkedText + timeHtml }}
          />
        </div>
      </div>
    )
  }

  if (role === 'Asesor') {
    return (
      <div className="msg-row msg-row--right">
        <div className="bubble bubble--advisor">
          <span className="bubble__label">
            <i className="fa-solid fa-user-tie" style={{ marginRight: 4 }} />
            Tú
          </span>
          <p
            className="bubble__text"
            dangerouslySetInnerHTML={{ __html: linkedText + timeHtml }}
          />
        </div>
      </div>
    )
  }

  return null
}
