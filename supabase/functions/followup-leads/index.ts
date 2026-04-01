import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// =========================================================
// CONFIGURACIÓN — Variables de entorno de Supabase
// =========================================================
const TWILIO_ACCOUNT_SID = Deno.env.get('TWILIO_ACCOUNT_SID')!
const TWILIO_AUTH_TOKEN   = Deno.env.get('TWILIO_AUTH_TOKEN')!
const TWILIO_FROM         = 'whatsapp:+5214271097523' // Número de Aria

// =========================================================
// HANDLER PRINCIPAL
// =========================================================
Deno.serve(async () => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  // Calcular ventana de tiempo: entre hace 2 horas y hace 24 horas
  const ahora   = new Date()
  const hace2h  = new Date(ahora.getTime() - 2  * 60 * 60 * 1000).toISOString()
  const hace24h = new Date(ahora.getTime() - 24 * 60 * 60 * 1000).toISOString()

  // Buscar leads inactivos que cumplan TODAS las condiciones
  const { data: leads, error } = await supabase
    .from('clientes')
    .select('telefono, nombre_cliente')
    .eq('bot_encendido', true)   // El bot aún está activo (no hay asesor)
    .eq('followup_sent', false)  // No se le ha mandado ya el followup
    .lt('last_activity', hace2h) // Llevan más de 2 horas sin responder
    .gt('last_activity', hace24h)// Pero menos de 24 horas (sesión Twilio activa)

  if (error) {
    console.error('[FOLLOWUP ERROR] Consulta Supabase:', error.message)
    return new Response(JSON.stringify({ error: error.message }), { status: 500 })
  }

  if (!leads || leads.length === 0) {
    console.log('[FOLLOWUP] Sin leads inactivos en este momento.')
    return new Response(JSON.stringify({ enviados: 0 }), { status: 200 })
  }

  console.log(`[FOLLOWUP] Leads inactivos encontrados: ${leads.length}`)
  let enviados = 0

  for (const lead of leads) {
    const nombre  = lead.nombre_cliente || ''
    const saludo  = nombre ? `¡Hola ${nombre}!` : '¡Hola!'
    const mensaje = `${saludo} 👋 Seguimos aquí para ayudarte.\n¿Deseas continuar con el proceso? Puedo mostrarte más opciones o conectarte con un asesor. 😊\n\n— Aria, Century 21 Diamante`

    // Asegurar formato correcto del número
    const telefonoLimpio = lead.telefono.replace('whatsapp:', '').replace('WHATSAPP:', '')
    const toNumber = `whatsapp:${telefonoLimpio}`

    const bodyParams = new URLSearchParams()
    bodyParams.set('From', TWILIO_FROM)
    bodyParams.set('To',   toNumber)
    bodyParams.set('Body', mensaje)

    try {
      const res = await fetch(
        `https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json`,
        {
          method: 'POST',
          headers: {
            'Authorization': 'Basic ' + btoa(`${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}`),
            'Content-Type':  'application/x-www-form-urlencoded',
          },
          body: bodyParams.toString(),
        }
      )

      if (res.ok) {
        // Marcar como enviado para no mandar doble
        await supabase
          .from('clientes')
          .update({ followup_sent: true })
          .eq('telefono', lead.telefono)

        console.log(`[FOLLOWUP] ✅ Enviado a ${lead.telefono}`)
        enviados++
      } else {
        const errText = await res.text()
        console.error(`[FOLLOWUP] ❌ Error Twilio para ${lead.telefono}: ${errText}`)
      }
    } catch (e) {
      console.error(`[FOLLOWUP] ❌ Error de red para ${lead.telefono}:`, e)
    }
  }

  return new Response(JSON.stringify({ enviados, total: leads.length }), { status: 200 })
})
