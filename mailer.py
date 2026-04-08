import os
import re
import json
import requests

# Email del remitente verificado en Brevo (debe coincidir con el sender verificado en tu cuenta)
EMAIL_FROM_ADDR = os.getenv("EMAIL_FROM_ADDR", "sendcenturydiamante@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Aria C21 Diamante")

def enviar_notificacion_asesor(datos_cliente, historial_completo, correo_destino="asesores@c21diamante.com", nombre_asesor="Equipo Century 21"):
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")

    if not BREVO_API_KEY:
        print("[MAILER ERROR] Falta la variable de entorno BREVO_API_KEY.")
        return

    try:
        # Limpiamos el número para el link de WhatsApp
        telefono_raw    = datos_cliente.get('telefono', '')
        telefono_limpio = re.sub(r'\D', '', telefono_raw)

        # Construir lista de destinatarios (soporta múltiples separados por coma)
        destinatarios = [{"email": d.strip()} for d in correo_destino.split(",") if d.strip()]

        cuerpo_html = f"""
        <html>
          <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f5f7; padding: 20px; margin: 0;">
            
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
              
              <div style="background-color: #212121; color: #BE9A5A; padding: 25px; text-align: center; border-bottom: 4px solid #BE9A5A;">
                <h1 style="margin: 0; font-size: 24px; letter-spacing: 1px;">CENTURY 21 Diamante</h1>
                <p style="margin: 5px 0 0 0; color: #ffffff; font-size: 14px; font-weight: 300;">Notificación de Asistente IA</p>
              </div>

              <div style="padding: 30px;">
                <h2 style="color: #333333; margin-top: 0; border-bottom: 2px solid #eeeeee; padding-bottom: 10px; font-size: 18px;">
                  📋 Ficha del Prospecto
                </h2>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #666;"><strong>👔 Asesor Asignado:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #BE9A5A; font-weight: bold; text-align: right; font-size: 16px;">{nombre_asesor}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #666;"><strong>👤 Nombre del cliente:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #222; font-weight: bold; text-align: right;">{datos_cliente.get('nombre', 'Cliente Interesado')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #666;"><strong>📱 Teléfono:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #222; font-weight: bold; text-align: right;">{datos_cliente.get('telefono')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #666;"><strong>📍 Zona de interés:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #222; font-weight: bold; text-align: right;">{datos_cliente.get('zona', 'No especificada')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #666;"><strong>💰 Presupuesto:</strong></td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; color: #222; font-weight: bold; text-align: right;">${datos_cliente.get('presupuesto', 'No especificado')}</td>
                  </tr>
                </table>

                <h2 style="color: #333333; margin-top: 0; border-bottom: 2px solid #eeeeee; padding-bottom: 10px; font-size: 18px;">
                  💬 Historial de Conversación
                </h2>
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #BE9A5A; font-size: 14px; color: #444444; line-height: 1.6; white-space: pre-wrap; border-radius: 0 4px 4px 0;">
{historial_completo}
                </div>

                <div style="text-align: center; margin-top: 35px; margin-bottom: 10px;">
                  <a href="https://wa.me/{telefono_limpio}" style="background-color: #25D366; color: white; padding: 14px 28px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; display: inline-block; box-shadow: 0 2px 5px rgba(37, 211, 102, 0.4);">
                    Abrir chat en WhatsApp
                  </a>
                </div>
                
              </div>
              
              <div style="background-color: #f4f5f7; color: #888888; text-align: center; padding: 15px; font-size: 12px; border-top: 1px solid #eeeeee;">
                Este mensaje fue generado automáticamente por la arquitectura RAG del chatbot.
              </div>

            </div>
          </body>
        </html>
        """

        payload = {
            "sender":      {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM_ADDR},
            "to":          destinatarios,
            "subject":     f"🔴 NUEVO LEAD para {nombre_asesor}: {datos_cliente.get('nombre', 'Cliente Interesado')} 🏠",
            "htmlContent": cuerpo_html
        }

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key":      BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept":       "application/json"
            },
            data=json.dumps(payload),
            timeout=10
        )

        if response.status_code in [200, 201]:
            print(f"[MAILER] ✅ Correo enviado via Brevo a: {correo_destino}")
        else:
            raise Exception(f"Brevo error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[MAILER ERROR] {e}")
        raise  # Re-lanzar para que main.py lo capture en su bloque independiente