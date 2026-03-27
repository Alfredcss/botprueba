import config
from twilio.rest import Client

# =========================================================
# CONFIGURACIÓN DE TWILIO
# =========================================================
# Inicializamos el cliente de Twilio una sola vez
client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Tus números oficiales
NUMERO_TWILIO = "whatsapp:+5214271097523" #chip de Aria
NUMERO_OFICINA = "whatsapp:+5214276880588" #numero de la oficina

def enviar_alerta_asesor(numero_asesor, datos_cliente, resumen_ai, nombre_asesor):
    # 1. Extraemos y LIMPIAMOS los datos del cliente
    cliente_nombre = str(datos_cliente.get('nombre', 'Cliente sin nombre')).strip()
    cliente_telefono = str(datos_cliente.get('telefono', 'Sin teléfono')).strip()
    zona = str(datos_cliente.get('zona', 'No especificada')).strip()
    presupuesto = str(datos_cliente.get('presupuesto', 'No especificado')).strip()
    zona_presupuesto = f"{zona} / {presupuesto}"

    # Limpiamos rigurosamente el resumen de la IA
    resumen_limpio = str(resumen_ai).strip()

    # 2. CONSTRUIMOS LA PLANTILLA EXACTA
    mensaje_plantilla = f"""🚨 NUEVO LEAD CENTURY 21 DIAMANTE 🚨

Hola {nombre_asesor}, el asistente virtual te ha asignado un nuevo prospecto.

👤 Cliente: {cliente_nombre}
📱 Teléfono: {cliente_telefono}
📍 Zona/Presupuesto: {zona_presupuesto}

📝 Resumen de la solicitud:
{resumen_limpio}

Por favor, contacta a este prospecto lo antes posible. ¡Mucho éxito!"""

    try:
        # Variable para controlar si el envío al asesor fue exitoso y a qué número
        numero_formateado = ""
        
        # 3. Enviar mensaje al Asesor
        if numero_asesor:
            # 🛡️ BLINDAJE: Limpiamos el número para evitar errores de mayúsculas ("WhatsApp:") o espacios
            numero_limpio = numero_asesor.lower().replace("whatsapp:", "").strip()
            numero_formateado = f"whatsapp:{numero_limpio}"
            
            client.messages.create(
                from_=NUMERO_TWILIO,
                body=mensaje_plantilla,
                to=numero_formateado
            )
            print(f"[ALERTA ENVIADA] Lead enviado a {nombre_asesor} con plantilla oficial.")
        
        # 4. Enviar copia de respaldo a la Oficina
        mensaje_oficina = f"📋 *COPIA DE RESPALDO*\nAsesor asignado: *{nombre_asesor}*\n\n{mensaje_plantilla}"
        
        # Solo enviamos la copia si el número del asesor NO es el mismo de la oficina
        if numero_formateado != NUMERO_OFICINA:
            client.messages.create(
                from_=NUMERO_TWILIO,
                body=mensaje_oficina,
                to=NUMERO_OFICINA
            )
            print("[ALERTA ENVIADA] Copia de respaldo enviada a la oficina.")
        
    except Exception as e:
        print(f"[ERROR TWILIO PLANTILLA] {e}")