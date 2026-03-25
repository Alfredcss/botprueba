import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'

/**
 * Loads the full conversation log for one contact.
 * Reads the `observaciones_generales` column from the 'Clientes' table.
 *
 * TABLE: Clientes
 * COLUMNS USED: telefono, observaciones_generales
 *
 * @param {string|null} telefono - The selected contact's phone number.
 */
export function useChat(telefono) {
  const [rawLog, setRawLog] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchChat = useCallback(async () => {
    if (!telefono) return
    setLoading(true)

    const { data, error } = await supabase
      .from('clientes')
      .select('observaciones_generales')
      .eq('telefono', telefono)
      .maybeSingle() // returns null (not an error) if no row found

    // ── DEBUG ──────────────────────────────────────────────────────────────
    console.log('[useChat] telefono:', telefono, '| Respuesta Supabase:', data, '| Error:', error)
    // ──────────────────────────────────────────────────────────────────────

    if (error) {
      console.error('[useChat] Error de Supabase:', error.message)
      setLoading(false)
      return
    }

    setRawLog(data?.observaciones_generales ?? '')
    setLoading(false)
  }, [telefono])

  useEffect(() => {
    if (!telefono) {
      setRawLog('')
      return
    }

    fetchChat()

    // -----------------------------------------------------------------------
    // Supabase Realtime: listen for updates to THIS specific contact's row.
    // When the Python backend appends a new message, it updates the
    // 'observaciones_generales' column → triggers this handler.
    //
    // CRITICAL: cleanup cancels the channel whenever the selected contact
    // changes or the component unmounts — avoids Free Tier connection limits.
    // -----------------------------------------------------------------------
    const channelName = `chat-${telefono.replace(/\W/g, '_')}`

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'clientes',
          filter: `telefono=eq.${telefono}`,
        },
        (payload) => {
          console.log('[useChat] Realtime UPDATE para', telefono, payload)
          // Directly update from payload — no extra fetch needed
          setRawLog(payload.new?.observaciones_generales ?? '')
        }
      )
      .subscribe((status) => {
        console.log(`[useChat] Estado Realtime canal "${channelName}":`, status)
      })

    // Cleanup: cancel subscription when contact changes or component unmounts
    return () => {
      supabase.removeChannel(channel)
    }
  }, [telefono, fetchChat])

  return { rawLog, loading, refetch: fetchChat }
}
