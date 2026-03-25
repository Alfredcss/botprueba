import React from 'react'

/**
 * Individual client row in the sidebar list.
 * Shows: name, phone, seguimiento (assigned advisor), last message, IA/HUMANO badge.
 */
export default function ClientItem({ client, isActive, onClick }) {
  const isBotOn = client.bot_encendido !== false
  const isUnread = !isBotOn && client.leido === false

  const safeTelefono = client.telefono
    ? String(client.telefono).replace('whatsapp:', '')
    : 'Desconocido'
  const safeDisplay = client.display ? String(client.display) : safeTelefono
  const safeMsg = client.ultimo_mensaje ? String(client.ultimo_mensaje) : 'Sin mensajes'
  const asesor = client.seguimiento ? String(client.seguimiento) : null

  return (
    <div
      className={`client-item ${isActive ? 'client-item--active' : ''} ${isUnread ? 'client-item--unread' : ''}`}
      onClick={onClick}
    >
      <div className="client-item__info">
        {/* Name + unread dot */}
        <div className="client-item__name-row">
          <p className={`client-item__name ${isUnread ? 'client-item__name--unread' : isActive ? 'client-item__name--active' : ''}`}>
            {safeDisplay}
          </p>
          {isUnread && <span className="unread-dot" />}
        </div>

        {/* Phone */}
        <p className="client-item__phone">{safeTelefono}</p>

        {/* Assigned advisor — only shown when set */}
        {asesor && (
          <p className="client-item__advisor">
            <i className="fa-solid fa-id-badge" style={{ marginRight: 4, opacity: .7 }} />
            {asesor}
          </p>
        )}

        {/* Last message preview */}
        <p className={`client-item__last-msg ${isUnread ? 'client-item__last-msg--unread' : ''}`}>
          {safeMsg}
        </p>
      </div>

      {/* IA / HUMANO badge */}
      <div className="client-item__badge">
        {isBotOn ? (
          <span className="badge badge--ia">
            <i className="fa-solid fa-robot" /> IA
          </span>
        ) : (
          <span className="badge badge--human">
            <i className="fa-solid fa-user" /> HUMANO
          </span>
        )}
      </div>
    </div>
  )
}
