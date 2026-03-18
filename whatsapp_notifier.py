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

import config
from twilio.rest import Client

client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Asegúrate de poner aquí tu número oficial de Twilio y el de la oficina
NUMERO_TWILIO = "whatsapp:+5214271097523" 
NUMERO_OFICINA = "whatsapp:+5214276880588" 

def enviar_alerta_asesor(numero_asesor, datos_cliente, resumen_ai, nombre_asesor):
    # 1. Extraemos los datos del cliente
    cliente_nombre = datos_cliente.get('nombre', 'Cliente sin nombre')
    cliente_telefono = datos_cliente.get('telefono', 'Sin teléfono')
    zona = datos_cliente.get('zona', 'No especificada')
    presupuesto = datos_cliente.get('presupuesto', 'No especificado')
    zona_presupuesto = f"{zona} / {presupuesto}"

    # 2. CONSTRUIMOS LA PLANTILLA EXACTA (No modifiques espacios ni emojis)
    mensaje_plantilla = f"""🚨 *NUEVO LEAD CENTURY 21 DIAMANTE* 🚨

Hola {nombre_asesor}, el asistente virtual te ha asignado un nuevo prospecto.

👤 *Cliente:* {cliente_nombre}
📱 *Teléfono:* {cliente_telefono}
📍 *Zona/Presupuesto:* {zona_presupuesto}

📝 *Resumen de la solicitud:*
{resumen_ai}

Por favor, contacta a este prospecto lo antes posible. ¡Mucho éxito! 💎"""

    try:
        # 3. Enviar mensaje al Asesor
        if numero_asesor:
            # Nos aseguramos de que el número empiece con "whatsapp:"
            numero_formateado = f"whatsapp:{numero_asesor}" if not numero_asesor.startswith("whatsapp:") else numero_asesor
            
            client.messages.create(
                from_=NUMERO_TWILIO,
                body=mensaje_plantilla,
                to=numero_formateado
            )
            print(f"[ALERTA ENVIADA] Lead enviado a {nombre_asesor} con plantilla oficial.")
        
        # 4. Enviar copia a la Oficina (Opcional, pero recomendado)
        client.messages.create(
            from_=NUMERO_TWILIO,
            body=mensaje_plantilla,
            to=NUMERO_OFICINA
        )
        
    except Exception as e:
        print(f"[ERROR TWILIO PLANTILLA] {e}")