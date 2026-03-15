import json
import re
import io
import csv
from datetime import datetime
from fastapi import FastAPI, Form, Response
from fastapi.responses import StreamingResponse
import database
import agent
import utils
import mailer

app = FastAPI()
@app.post("/whatsapp")
async def whatsapp_reply(
    From: str = Form(...),
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default="")
):

    # ================= AUDIO =================
    if NumMedia != "0" and "audio" in MediaContentType0:
        texto_transcrito = utils.descargar_y_transcribir_audio(MediaUrl0)
        Body = texto_transcrito

    print(f"\n[MENSAJE] {From} → {Body}")
    body_lower = Body.lower()

    # ================= CRM =================
    cliente_db = database.obtener_cliente(From)
    historial = (cliente_db.get("observaciones_generales") or "")[-4000:] if cliente_db else ""

    datos_msg = {}
    try:
        resp = (agent.prompt_analista | agent.llm_analista).invoke({
            "mensaje": Body,
            "historial_chat": historial
        })
        raw = resp.content.replace("```json", "").replace("```", "")
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            datos_msg = json.loads(match.group())
    except Exception as e:
        print(f"[ERROR ANALISTA] {e}")

    def fusionar(campo, es_numero=False):
        val_msg = utils.limpiar_numero(datos_msg.get(campo)) if es_numero else utils.limpiar_texto(datos_msg.get(campo))
        val_db = (
            utils.limpiar_numero(cliente_db.get(campo))
            if es_numero else utils.limpiar_texto(cliente_db.get(campo))
        ) if cliente_db else None
        return val_msg if val_msg else val_db

    datos_finales = {
        "nombre_cliente": fusionar("nombre_cliente"),
        "zona_municipio": fusionar("zona_municipio"),
        "tipo_inmueble": fusionar("tipo_inmueble"),
        "tipo_operacion": fusionar("tipo_operacion"),
        "presupuesto": fusionar("presupuesto", es_numero=True),
        "clave_propiedad": datos_msg.get("clave_propiedad"),
        "origen_campana": datos_msg.get("origen_campana"),
        "orden_precio": datos_msg.get("orden_precio")
    }

    inventario = ""
    propiedades = []

    quiere_ver = utils.detectar_intencion_ver_propiedades(Body)

    tipo_credito_detectado = None
    if "infonavit" in body_lower:
        tipo_credito_detectado = "infonavit"
    elif "fovissste" in body_lower:
        tipo_credito_detectado = "fovissste"
    elif "bancario" in body_lower:
        tipo_credito_detectado = "bancario"
    elif "credito" in body_lower or "crédito" in body_lower:
        tipo_credito_detectado = "general"

    hacer_busqueda = bool(
        quiere_ver
        or datos_finales["zona_municipio"]
        or datos_finales["tipo_inmueble"]
        or datos_finales["presupuesto"]
        or tipo_credito_detectado
    )

    if datos_finales["clave_propiedad"]:
        propiedades = database.buscar_por_clave(datos_finales["clave_propiedad"])
    elif hacer_busqueda:
        propiedades = database.buscar_propiedades(
            datos_finales["tipo_inmueble"],
            datos_finales["tipo_operacion"],
            datos_finales["zona_municipio"],
            datos_finales["presupuesto"],
            mostrar_mix_general=False,
            tipo_credito=tipo_credito_detectado,
            orden_precio=datos_finales["orden_precio"]
        )

    # ================= RESPUESTA IA =================
    try:
        respuesta = (agent.prompt_vendedor | agent.llm_vendedor).invoke({
            "mensaje": Body,
            "nombre_final": datos_finales["nombre_cliente"],
            "zona_final": datos_finales["zona_municipio"],
            "presupuesto_final": datos_finales["presupuesto"],
            "operacion_final": datos_finales["tipo_operacion"],
            "inventario": inventario,
            "historial_chat": historial
        }).content
    except Exception as e:
        print(f"[ERROR GENERACION] {e}")
        respuesta = "Dame un momento, estoy consultando el inventario."

    print(f"[BOT] {respuesta}")

    await database.guardar_cliente(Body, respuesta, From, datos_msg, cliente_existente=cliente_db)

    # ==============================================================================
    # MODULO NOTIFICACIONES (REPARADO PARA MÚLTIPLES ASESORES)
    # ==============================================================================
    # 🚨 Esto DEBE ir antes del return para que no se ponga gris
    valor_asesor = str(datos_msg.get("quiere_asesor", "")).lower()
    correo_ya_enviado = cliente_db.get("correo_enviado", False) if cliente_db else False
    
    if valor_asesor == "true" and not correo_ya_enviado:
        historial_para_correo = (cliente_db.get("observaciones_generales") or "") if cliente_db else f"Cliente: {Body}\nBot: {respuesta}"
        nombre_seguro = datos_finales.get("nombre_cliente") or f"Nuevo Prospecto ({From})"
        
        try:
            print("[IA] Generando resumen ejecutivo para el asesor...")
            resumen_ejecutivo = (agent.prompt_resumen | agent.llm_analista).invoke({
                "historial": historial_para_correo,
                "nombre": nombre_seguro,
                "telefono": From
            }).content
        except Exception as e:
            resumen_ejecutivo = historial_para_correo 

        info_lead = {
            "nombre": nombre_seguro,
            "telefono": From,
            "zona": datos_finales.get("zona_municipio") or "No especificada",
            "presupuesto": datos_finales.get("presupuesto") or "No especificado"
        }
        
        asesor_asignado = database.obtener_asesor_aleatorio()
        
        if asesor_asignado:
            correo_destino = asesor_asignado.get("correo") or "alfredoferrusca885@gmail.com"
            nombre_asesor = asesor_asignado.get("nombre") or "Asesor C21"
            
            # 📱 FORMATEO INTELIGENTE DE TELÉFONO PARA TWILIO
            tel_bd = str(asesor_asignado.get("telefono", "")).strip()
            if tel_bd:
                # Si el asesor solo puso "4271234567" en la BD, se lo reparamos a Twilio
                if not tel_bd.startswith("whatsapp:"):
                    if not tel_bd.startswith("+"):
                        # Si tiene 10 digitos le agregamos el +521 de México
                        tel_bd = f"+521{tel_bd}" if len(tel_bd) == 10 else f"+{tel_bd}"
                    tel_bd = f"whatsapp:{tel_bd}"
                telefono_asesor = tel_bd
            else:
                telefono_asesor = "whatsapp:+5214272786799" # Respaldo
        else:
            correo_destino = "alfredoferrusca885@gmail.com"
            nombre_asesor = "Administrador"
            telefono_asesor = "whatsapp:+5214272786799"
        
        print(f"[ENVIANDO LEAD] Destino: {nombre_asesor} | Correo: {correo_destino} | WA: {telefono_asesor}")

        # MANDAMOS CORREO
        try:
            mailer.enviar_notificacion_asesor(info_lead, resumen_ejecutivo, correo_destino, nombre_asesor)
        except Exception as e: print(f"[ERROR CORREO] {e}")
        
        # MANDAMOS WHATSAPP
        try:
            import whatsapp_notifier
            whatsapp_notifier.enviar_alerta_asesor(telefono_asesor, info_lead, resumen_ejecutivo)
        except ImportError:
            print("[SISTEMA] No se encontró módulo whatsapp_notifier. Solo se envió correo.")
        except Exception as e:
            print(f"[ERROR WA NOTIFICADOR] {e}")
        
        # ACTUALIZAMOS LA BASE DE DATOS
        try:
            database.supabase.table("clientes").update({"correo_enviado": True}).eq("telefono", From).execute()
        except Exception: pass

    # ================= RESPUESTA TWILIO =================
    # 🚨 El return siempre es lo ÚLTIMO que hace la función. También arreglé el cierre de la etiqueta XML.
    xml_respuesta = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Message>{respuesta}</Message>
    </Response>"""

    return Response(content=xml_respuesta.strip(), media_type="text/xml")