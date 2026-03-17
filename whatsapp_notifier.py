from twilio.rest import Client
import config

# ---------------------------------------------------------
# CONFIGURACIÓN DE TWILIO (Tus credenciales de la consola)
# ---------------------------------------------------------
TWILIO_ACCOUNT_SID = config.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = config.TWILIO_AUTH_TOKEN
TWILIO_NUMERO_BOT = "whatsapp:+5214271097523" # El número de tu Sandbox o el Oficial

# 🚨 PON AQUÍ EL NÚMERO DE RESPALDO DE LA OFICINA
NUMERO_OFICINA = "whatsapp:+5214276880588"

# Inicializamos el cliente de Twilio
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def enviar_alerta_asesor(numero_asesor, datos_cliente, resumen_ejecutivo, nombre_asesor="Asesor Asignado"):
    # Limpiamos el número para generar el enlace clicable de wa.me
    telefono_limpio = datos_cliente['telefono'].replace('whatsapp:+', '')
    
    # --- 1. MENSAJE PARA EL ASESOR ---
    mensaje_asesor = f"""🚨 *¡NUEVO LEAD DE CENTURY 21 Diamante!* 🚨

👤 *Cliente:* {datos_cliente['nombre']}
📞 *Teléfono:* {datos_cliente['telefono']}

📋 *Resumen de la IA:*
{resumen_ejecutivo}

📲 *Contactar ahora:* Haz clic aquí para enviarle un mensaje rápido al cliente: https://wa.me/{telefono_limpio}

¡Éxito en tu cierre! 🤝"""

    # --- 2. MENSAJE PARA LA OFICINA ---
    mensaje_oficina = f"""📋 *RESPALDO OFICINA* 📋
Este lead fue asignado a: *{nombre_asesor}* ({numero_asesor})

👤 *Cliente:* {datos_cliente['nombre']}
📞 *Teléfono:* {datos_cliente['telefono']}

📋 *Resumen de la IA:*
{resumen_ejecutivo}"""

    exito = True

    # Ejecutamos el envío al asesor
    try:
        message_asesor = twilio_client.messages.create(
            from_=TWILIO_NUMERO_BOT,
            body=mensaje_asesor,
            to=numero_asesor
        )
        print(f"[WHATSAPP NOTIFIER] Alerta enviada al asesor. SID: {message_asesor.sid}")
    except Exception as e:
        print(f"[ERROR WHATSAPP NOTIFIER] No se pudo enviar alerta al asesor: {e}")
        exito = False

    # Ejecutamos el envío a la oficina
    try:
        message_oficina = twilio_client.messages.create(
            from_=TWILIO_NUMERO_BOT,
            body=mensaje_oficina,
            to=NUMERO_OFICINA
        )
        print(f"[WHATSAPP NOTIFIER] Copia enviada a la oficina. SID: {message_oficina.sid}")
    except Exception as e:
        print(f"[ERROR WHATSAPP NOTIFIER] No se pudo enviar copia a la oficina: {e}")
        exito = False

    return exito