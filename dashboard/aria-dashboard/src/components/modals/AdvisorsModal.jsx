import React, { useState, useEffect } from 'react'
import { supabase } from '../../lib/supabase'

/**
 * Modal for CRUD operations on advisors.
 * Reads/writes directly from the Supabase 'asesores' table.
 *
 * TABLE: asesores
 * EXPECTED COLUMNS: id, nombre, telefono, activo
 */
export default function AdvisorsModal({ isOpen, onClose }) {
  const [advisors, setAdvisors] = useState([])
  const [loading, setLoading] = useState(false)
  const [newName, setNewName] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newRecibirCorreo, setNewRecibirCorreo] = useState(false)

  async function fetchAdvisors() {
    setLoading(true)
    const { data, error } = await supabase
      .from('asesores')
      .select('id, nombre, telefono, activo, correo, recibir_correo')
      .order('nombre', { ascending: true })

    console.log('[AdvisorsModal] Respuesta Supabase:', data, 'Error:', error)

    if (!error && Array.isArray(data)) {
      setAdvisors(data)
    } else if (error) {
      console.error('[AdvisorsModal] Error:', error.message)
    }
    setLoading(false)
  }

  useEffect(() => {
    if (isOpen) fetchAdvisors()
  }, [isOpen])

  async function handleAdd() {
    if (!newName.trim() || !newPhone.trim()) {
      alert('Por favor, ingresa el nombre y el número de teléfono del asesor.')
      return
    }
    const payload = { 
      nombre: newName.trim(), 
      telefono: newPhone.trim(), 
      activo: true 
    }
    if (newEmail.trim()) {
      payload.correo = newEmail.trim()
      payload.recibir_correo = newRecibirCorreo
    }

    const { error } = await supabase
      .from('asesores')
      .insert([payload])

    console.log('[AdvisorsModal] INSERT error:', error)
    if (!error) {
      setNewName('')
      setNewPhone('')
      setNewEmail('')
      setNewRecibirCorreo(false)
      fetchAdvisors()
    } else {
      alert('Error al guardar el asesor: ' + error.message)
    }
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar permanentemente a este asesor?')) return
    const { error } = await supabase.from('asesores').delete().eq('id', id)
    console.log('[AdvisorsModal] DELETE error:', error)
    if (!error) {
      fetchAdvisors()
    } else {
      alert('No se pudo eliminar: ' + error.message)
    }
  }

  async function handleToggle(id, currentState) {
    const { error } = await supabase
      .from('asesores')
      .update({ activo: !currentState })
      .eq('id', id)
    console.log('[AdvisorsModal] TOGGLE error:', error)
    if (!error) fetchAdvisors()
  }

  async function handleToggleEmail(id, currentState, hasEmail) {
    if (!hasEmail) {
      alert('Este asesor no tiene un correo registrado. Actualiza su registro en la base de datos primero.')
      return
    }
    const { error } = await supabase
      .from('asesores')
      .update({ recibir_correo: !currentState })
      .eq('id', id)
    console.log('[AdvisorsModal] TOGGLE EMAIL error:', error)
    if (!error) fetchAdvisors()
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal__header">
          <h3 className="modal__title">
            <i className="fa-solid fa-users" style={{ marginRight: 8 }} />
            Gestión de Asesores
          </h3>
          <button className="modal__close" onClick={onClose}>
            <i className="fa-solid fa-times" />
          </button>
        </div>

        {/* Add advisor form */}
        <div className="modal__add-form">
          <p className="modal__section-label">Añadir Nuevo Asesor</p>
          <div className="modal__add-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <input
              type="text"
              placeholder="Nombre completo"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="modal__input"
            />
            <input
              type="text"
              placeholder="Teléfono (Ej. +52427...)"
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              className="modal__input"
            />
            <input
              type="email"
              placeholder="Correo electrónico (Opcional)"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="modal__input"
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label style={{ fontSize: '0.9rem', color: '#666', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <input 
                  type="checkbox" 
                  checked={newRecibirCorreo} 
                  onChange={(e) => setNewRecibirCorreo(e.target.checked)}
                  disabled={!newEmail.trim()}
                />
                Activar envío de correos
              </label>
              <button className="modal__btn-add" onClick={handleAdd} style={{ marginLeft: 'auto' }}>
                <i className="fa-solid fa-plus" />
              </button>
            </div>
          </div>
        </div>

        {/* List */}
        <div className="modal__list">
          {loading ? (
            <p className="empty-msg" style={{ padding: '2rem' }}>
              <i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 6 }} />
              Cargando red de asesores...
            </p>
          ) : advisors.length === 0 ? (
            <p className="empty-msg" style={{ padding: '2rem' }}>
              No hay asesores registrados aún.
            </p>
          ) : (
            advisors.map((a) => {
              const displayTel = (a.telefono || 'Sin número').replace('whatsapp:', '')
              return (
                <div key={a.id} className="advisor-row">
                  <div className="advisor-row__avatar">
                    <i className="fa-solid fa-user" />
                  </div>
                  <div className="advisor-row__info">
                    <p className="advisor-row__name">{a.nombre}</p>
                    <p className="advisor-row__phone">{displayTel} {a.correo ? `• ${a.correo}` : ''}</p>
                    <p className={`advisor-row__status ${a.activo ? 'advisor-row__status--active' : ''}`}>
                      {a.activo ? '● En Guardia' : '○ Fuera de Turno'}
                    </p>
                  </div>
                  <div className="advisor-row__actions" style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="advisor-toggle"
                      style={{ 
                        background: a.recibir_correo ? 'rgba(212, 175, 55, 0.2)' : 'rgba(0,0,0,0.05)', 
                        color: a.recibir_correo ? '#d4af37' : '#999',
                        width: '32px', height: '32px', borderRadius: '50%', border: 'none', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}
                      onClick={() => handleToggleEmail(a.id, a.recibir_correo, !!a.correo)}
                      title={a.recibir_correo ? 'Desactivar notificaciones por correo' : 'Activar notificaciones por correo'}
                    >
                      <i className="fa-solid fa-envelope" />
                    </button>
                    <button
                      className={`advisor-toggle ${a.activo ? 'advisor-toggle--on' : 'advisor-toggle--off'}`}
                      style={{ margin: 0 }}
                      onClick={() => handleToggle(a.id, a.activo)}
                      title={a.activo ? 'Desactivar Asesor' : 'Activar Asesor'}
                    >
                      <span className={`advisor-toggle__knob ${a.activo ? 'advisor-toggle__knob--on' : ''}`} />
                    </button>
                    <button className="advisor-delete" onClick={() => handleDelete(a.id)} title="Eliminar asesor">
                      <i className="fa-solid fa-trash-can" />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
