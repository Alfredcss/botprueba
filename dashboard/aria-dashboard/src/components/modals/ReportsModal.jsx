import React, { useState, useEffect } from 'react'
import { supabase } from '../../lib/supabase'
import * as XLSX from 'xlsx'

/**
 * Modal for viewing and downloading property interest reports.
 * Derives data directly from the 'clientes' table using id_propiedad_opcional.
 *
 * TABLE: clientes
 * COLUMNS USED: id_propiedad_opcional, nombre_cliente, telefono,
 *               fecha_contacto, hora_contacto, observaciones_generales
 */
export default function ReportsModal({ isOpen, onClose }) {
  // { clave: string, interesados: number, rows: [] }[]
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(false)

  async function fetchReport() {
    setLoading(true)
    const { data, error } = await supabase
      .from('clientes')
      .select(
        'id, id_propiedad_opcional, nombre_cliente, telefono, fecha_contacto, hora_contacto, observaciones_generales'
      )
      .not('id_propiedad_opcional', 'is', null)   // only rows with a property assigned
      .order('id_propiedad_opcional', { ascending: true })

    console.log('[ReportsModal] Respuesta Supabase:', data, 'Error:', error)

    if (error) {
      console.error('[ReportsModal] Error:', error.message)
      alert('Error al cargar el reporte: ' + error.message)
      setLoading(false)
      return
    }

    // Group by id_propiedad_opcional
    const grouped = {}
    ;(data || []).forEach((row) => {
      const clave = String(row.id_propiedad_opcional).trim()
      if (!grouped[clave]) grouped[clave] = []
      grouped[clave].push(row)
    })

    const result = Object.entries(grouped).map(([clave, rows]) => ({
      clave,
      interesados: rows.length,
      rows,
    }))

    setProperties(result)
    setLoading(false)
  }

  useEffect(() => {
    if (isOpen) fetchReport()
  }, [isOpen])

  function handleDownload(item) {
    const rows = item.rows.map((c) => ({
      'ID Prospecto': c.id || 'S/N',
      'Nombre de Cliente': c.nombre_cliente || 'Desconocido',
      Teléfono: String(c.telefono || 'S/N').replace('whatsapp:', ''),
      'Fecha de Contacto': c.fecha_contacto || '',
      'Hora de Contacto': c.hora_contacto || '',
      'Historial de Chat': String(c.observaciones_generales || '').replace(/\n/g, '  •  '),
    }))

    const ws = XLSX.utils.json_to_sheet(rows)
    ws['!cols'] = [
      { wch: 15 }, { wch: 30 }, { wch: 20 },
      { wch: 18 }, { wch: 18 }, { wch: 120 },
    ]
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Prospectos')
    XLSX.writeFile(wb, `Reporte_Propiedad_${item.clave}.xlsx`)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ width: 'min(92vw, 520px)' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal__header">
          <h3 className="modal__title">
            <i className="fa-solid fa-building-circle-check" style={{ marginRight: 8 }} />
            Propiedades Consultadas
          </h3>
          <button className="modal__close" onClick={onClose}>
            <i className="fa-solid fa-times" />
          </button>
        </div>

        <div className="modal__subtitle">
          Prospectos agrupados por propiedad de interés · Descarga en Excel
        </div>

        {/* Content */}
        <div className="modal__list">
          {loading ? (
            <div className="report-loader">
              <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 28, color: 'var(--primary)' }} />
              <p>Consultando base de datos...</p>
            </div>
          ) : properties.length === 0 ? (
            <p className="empty-msg" style={{ padding: '2.5rem', textAlign: 'center' }}>
              Ningún prospecto tiene una propiedad específica asignada todavía.
            </p>
          ) : (
            properties.map((item) => (
              <div key={item.clave} className="report-row">
                <div>
                  <p className="report-row__title">
                    Propiedad:{' '}
                    <span style={{ color: 'var(--primary)', fontWeight: 800 }}>
                      {item.clave}
                    </span>
                  </p>
                  <p className="report-row__count">
                    <i className="fa-solid fa-users" style={{ marginRight: 4 }} />
                    {item.interesados} prospecto{item.interesados !== 1 ? 's' : ''} interesado{item.interesados !== 1 ? 's' : ''}
                  </p>
                </div>
                <button className="report-download-btn" onClick={() => handleDownload(item)}>
                  <i className="fa-solid fa-file-excel" style={{ marginRight: 6 }} />
                  Descargar
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
