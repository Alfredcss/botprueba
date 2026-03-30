import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'

/**
 * Extracts the last non-empty message line from the raw conversation log.
 * Used to display the preview snippet in the sidebar.
 */
function extractLastMessage(observaciones) {
  if (!observaciones) return 'Sin mensajes'
  const lines = String(observaciones)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  const last = lines[lines.length - 1] || ''
  // Strip the role prefix (e.g. "Bot: texto" → "texto")
  return last.replace(/^\[\d{2}:\d{2}\]\s*(Bot:|Cliente:|Asesor:)\s*/, '').trim() || 'Sin mensajes'
}

/**
 * Shapes a raw Supabase 'Clientes' row into the format the UI expects.
 */
function mapCliente(row) {
  return {
    telefono: row.telefono,
    display: row.nombre_cliente || row.telefono,
    ultimo_mensaje: extractLastMessage(row.observaciones_generales),
    bot_encendido: row.bot_encendido !== false,
    leido: row.leido !== false,
    seguimiento: row.seguimiento || null,          // assigned advisor name
    id_propiedad: row.id_propiedad_opcional || null,
    _raw: row,
  }
}

/**
 * Manages the full list of conversations by reading directly from Supabase.
 * Subscribes to UPDATE events on 'Clientes' to auto-refresh on any change.
 *
 * TABLE: Clientes
 * COLUMNS USED: id, telefono, nombre_cliente, observaciones_generales,
 *               bot_encendido, leido, created_at
 */
export function useConversations() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchConversations = useCallback(async () => {
    const { data, error } = await supabase
      .from('clientes')
      .select('id, telefono, nombre_cliente, observaciones_generales, bot_encendido, leido, created_at, seguimiento, id_propiedad_opcional')
      .order('created_at', { ascending: false })

    // ── DEBUG ──────────────────────────────────────────────────────────────
    console.log('[useConversations] Respuesta Supabase:', data, 'Error:', error)
    // ──────────────────────────────────────────────────────────────────────

    if (error) {
      console.error('[useConversations] Error de Supabase:', error.message)
      return
    }

    if (Array.isArray(data)) {
      setConversations(data.map(mapCliente))
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchConversations()

    // -----------------------------------------------------------------------
    // Supabase Realtime: re-fetch whenever ANY row in 'Clientes' is updated
    // (new message received, bot toggled, leido changed, etc.).
    // CRITICAL: cleanup cancels this subscription on unmount to avoid
    // exhausting the concurrent connection limit of the Supabase Free Tier.
    // -----------------------------------------------------------------------
    const channel = supabase
      .channel('clientes-list-changes')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'clientes' },
        (payload) => {
          console.log('[useConversations] Realtime UPDATE recibido, refetching...')
          fetchConversations()
        }
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'clientes' },
        (payload) => {
          console.log('[useConversations] Realtime INSERT recibido:', payload)
          setConversations((prev) => [mapCliente(payload.new), ...prev])
        }
      )
      .subscribe((status) => {
        console.log('[useConversations] Estado Realtime:', status)
      })

    // Cleanup: cancel subscription when component unmounts
    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchConversations])

  /**
   * Marks a conversation as read — updates the 'leido' column in Supabase
   * AND optimistically updates local state.
   */
  const markAsRead = useCallback(async (telefono) => {
    const { error } = await supabase
      .from('clientes')
      .update({ leido: true })
      .eq('telefono', telefono)

    console.log('[markAsRead] telefono:', telefono, '| Error:', error)

    if (!error) {
      setConversations((prev) =>
        prev.map((c) => (c.telefono === telefono ? { ...c, leido: true } : c))
      )
    }
  }, [])

  /**
   * Toggles the bot_encendido flag in Supabase AND updates local state.
   */
  const toggleBot = useCallback(async (telefono, newState) => {
    const { error } = await supabase
      .from('clientes')
      .update({ bot_encendido: newState })
      .eq('telefono', telefono)

    console.log('[toggleBot] telefono:', telefono, '| newState:', newState, '| Error:', error)

    if (!error) {
      setConversations((prev) =>
        prev.map((c) =>
          c.telefono === telefono ? { ...c, bot_encendido: newState } : c
        )
      )
    }
    return !error
  }, [])

  return {
    conversations,
    setConversations,
    loading,
    refetch: fetchConversations,
    markAsRead,
    toggleBot,
  }
}
