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

  async function fetchAdvisors() {
    setLoading(true)
    const { data, error } = await supabase
      .from('asesores')
      .select('id, nombre, telefono, activo')
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
    const { error } = await supabase
      .from('asesores')
      .insert([{ nombre: newName.trim(), telefono: newPhone.trim(), activo: true }])

    console.log('[AdvisorsModal] INSERT error:', error)
    if (!error) {
      setNewName('')
      setNewPhone('')
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
          <div className="modal__add-row">
            <input
              type="text"
              placeholder="Nombre completo"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="modal__input"
              onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
            />
            <input
              type="text"
              placeholder="Ej. +52427..."
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              className="modal__input"
              onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
            />
            <button className="modal__btn-add" onClick={handleAdd}>
              <i className="fa-solid fa-plus" />
            </button>
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
                    <p className="advisor-row__phone">{displayTel}</p>
                    <p className={`advisor-row__status ${a.activo ? 'advisor-row__status--active' : ''}`}>
                      {a.activo ? '● En Guardia' : '○ Fuera de Turno'}
                    </p>
                  </div>
                  <div className="advisor-row__actions">
                    <button
                      className={`advisor-toggle ${a.activo ? 'advisor-toggle--on' : 'advisor-toggle--off'}`}
                      onClick={() => handleToggle(a.id, a.activo)}
                      title={a.activo ? 'Desactivar' : 'Activar'}
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
