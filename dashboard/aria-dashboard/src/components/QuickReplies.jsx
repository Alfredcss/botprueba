import React from 'react'

const TEMPLATES = [
  {
    label: 'Saludo y Cita',
    text: '¡Hola! Soy tu asesor asignado de Century 21. ¿A qué hora prefieres que te llame?',
  },
  {
    label: 'Pedir Detalles',
    text: 'Para darte un mejor servicio, ¿buscas comprar o rentar?',
  },
  {
    label: 'En espera',
    text: 'Dame un momento, estoy revisando nuestro inventario para enviarte las mejores opciones.',
  },
]

/**
 * Quick-reply template buttons bar above the input.
 */
export default function QuickReplies({ onUseTemplate }) {
  return (
    <div className="quick-replies">
      <span className="quick-replies__icon">
        <i className="fa-solid fa-bolt" />
      </span>
      {TEMPLATES.map((t) => (
        <button
          key={t.label}
          className="quick-reply-btn"
          onClick={() => onUseTemplate(t.text)}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}
