import React from 'react'
import { formatearEnlaces } from '../lib/utils'

/**
 * Renders a single chat message bubble.
 * @param {{ role: 'Bot'|'Cliente'|'Asesor', text: string, time: string, date: string }} props
 */
export default function MessageBubble({ role, text, time, date }) {
  const botName = import.meta.env.VITE_BOT_NAME || 'IA'

  // Combine date + time: "14/04 · 21:08" or just "21:08" for legacy messages
  const timeLabel = [date, time].filter(Boolean).join(' · ')
  const timeHtml = timeLabel
    ? `<span class="msg-time">${timeLabel}</span>`
    : ''

  const linkedText = formatearEnlaces(text)
  const fullHtml = `<span class="msg-body">${linkedText}</span>${timeHtml}`

  if (role === 'Cliente') {
    return (
      <div className="msg-row msg-row--left">
        <div className="bubble bubble--client">
          <p
            className="bubble__text"
            dangerouslySetInnerHTML={{ __html: fullHtml }}
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
            dangerouslySetInnerHTML={{ __html: fullHtml }}
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
            dangerouslySetInnerHTML={{ __html: fullHtml }}
          />
        </div>
      </div>
    )
  }

  return null
}
