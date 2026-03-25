import React from 'react'

/**
 * The top bar of the chat panel.
 * Shows the client name/phone, back button (mobile), and bot toggle.
 */
export default function ChatHeader({ clientName, clientPhone, botActive, onToggleBot, onBack }) {
  const statusLabel = botActive ? 'IA Activa' : 'Humano'

  return (
    <div className="chat-header">
      <div className="chat-header__left">
        <button className="back-btn" onClick={onBack} title="Volver">
          <i className="fa-solid fa-arrow-left" />
        </button>
        <div>
          <h2 className="chat-header__name">{clientName || 'Cliente'}</h2>
          <p className="chat-header__phone">{clientPhone}</p>
        </div>
      </div>

      <div className="bot-toggle">
        <span className={`bot-toggle__label ${botActive ? 'bot-toggle__label--active' : 'bot-toggle__label--off'}`}>
          {statusLabel}
        </span>
        <button
          className={`toggle-switch ${botActive ? 'toggle-switch--on' : 'toggle-switch--off'}`}
          onClick={onToggleBot}
          aria-label="Toggle bot"
        >
          <div className={`toggle-knob ${botActive ? 'toggle-knob--on' : 'toggle-knob--off'}`} />
        </button>
      </div>
    </div>
  )
}
