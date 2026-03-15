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
    # 1. Procesamiento de Audio
    if NumMedia != "0" and "audio" in MediaContentType0:
        texto_transcrito = utils.descargar_y_transcribir_audio(MediaUrl0)
        Body = texto_transcrito

    print(f"\n[MENSAJE] {From} → {Body}")
    body_lower = Body.lower()

    # ==============================================================================
    # MODULO CLIENTES (RAG Y CRM)
    # ==============================================================================
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
        if match: datos_msg = json.loads(match.group())
    except Exception as e:
        print(f"[ERROR ANALISTA] {e}")

    def fusionar(campo, es_numero=False):
        val_msg = utils.limpiar_numero(datos_msg.get(campo)) if es_numero else utils.limpiar_texto(datos_msg.get(campo))
        val_db = (utils.limpiar_numero(cliente_db.get(campo)) if es_numero else utils.limpiar_texto(cliente_db.get(campo))) if cliente_db else None
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

    if datos_finales["origen_campana"]: datos_msg["origen"] = datos_finales["origen_campana"]

    inventario = ""
    propiedades = []
    quiere_ver = utils.detectar_intencion_ver_propiedades(Body)

    # 🔍 DETECCIÓN DE INTENCIÓN DE CRÉDITO
    tipo_credito_detectado = None
    if "infonavit" in body_lower: tipo_credito_detectado = "infonavit"
    elif "fovissste" in body_lower: tipo_credito_detectado = "fovissste"
    elif "bancario" in body_lower: tipo_credito_detectado = "bancario"
    elif "credito" in body_lower or "crédito" in body_lower: tipo_credito_detectado = "general"

    # 🔥 BÚSQUEDA DESBLOQUEADA: Buscamos siempre que tengamos la más mínima intención o dato
    hacer_busqueda = bool(quiere_ver or datos_finales["zona_municipio"] or datos_finales["tipo_inmueble"] or datos_finales["presupuesto"] or tipo_credito_detectado)

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

    es_busqueda_especifica = bool(datos_finales.get("clave_propiedad"))

    if propiedades:
        for p in propiedades:
            pre = p.get('precio', 0)
            desc_texto = p.get('descripcion', 'Sin descripción adicional.')
            desc_lower = desc_texto.lower()
            
            # 🧹 LIMPIEZA DEL GUION
            clave_limpia = str(p.get('clave', 'S/N')).strip('-')
            
            acepta = {
                "Infonavit": "infonavit" in desc_lower,
                "Fovissste": "fovissste" in desc_lower,
                "Bancario": "bancario" in desc_lower or "crédito" in desc_lower or "credito" in desc_lower
            }
            creditos_aceptados = [nombre for nombre, lo_acepta in acepta.items() if lo_acepta]
            status_credito = f"✅ Acepta: {', '.join(creditos_aceptados)}" if creditos_aceptados else "❌ Contado/A consultar"

            if es_busqueda_especifica:
                # VERSIÓN DETALLADA
                m2t = p.get('m2T') or 0
                m2c = p.get('m2C') or 0
                habs = p.get('recamaras') or p.get('ambientes') or 0
                banos = p.get('banios') or 0
                
                inventario += f"""
                ---
                *🆔 Referencia: {clave_limpia}*
                🏠 {p.get('subtipoPropiedad')} en {p.get('tipoOperacion')} - {p.get('municipio')} ({p.get('colonia', '')})
                💰 Precio: ${pre:,.0f}
                📏 Terreno: {m2t}m2 | Construcción: {m2c}m2
                🛏️ Habitaciones: {habs} | 🛁 Baños: {banos}
                💳 Créditos: {status_credito}
                📍 Ubicación: {p.get('mapa_url')}
                📸 Ficha y Fotos: {p.get('url_ficha')}
                📝 Descripción extra: {desc_texto}
                ---
                """
            else:
                # VERSIÓN CORTA
                col_texto = p.get('colonia', '')
                colonia_display = f" ({col_texto})" if col_texto else ""
                
                inventario += f"""
                ---
                *🆔 Referencia: {clave_limpia}*
                🏠 {p.get('subtipoPropiedad', 'Propiedad')} en {p.get('tipoOperacion', 'Venta')} - {p.get('municipio', 'Zona C21')}{colonia_display}
                💰 Precio: ${pre:,.0f}
                💳 Créditos: {status_credito}
                📍 Ubicación: {p.get('mapa_url') or 'Consultar asesor'}
                📸 Ficha: {p.get('url_ficha') or 'Consultar asesor'}
                ---
                """
    elif hacer_busqueda:
        # 🚨 CANDADO ANTI-ALUCINACIÓN
        inventario = "[SISTEMA: 0 RESULTADOS EN BASE DE DATOS. TIENES ESTRICTAMENTE PROHIBIDO INVENTAR CASAS. DILE AL CLIENTE LA VERDAD: QUE NO HAY OPCIONES EXACTAS Y OFRECE AYUDA DE UN ASESOR HUMANO.]"

    try:
        respuesta = (agent.prompt_vendedor | agent.llm_vendedor).invoke({
            "mensaje": Body, 
            "nombre_final": datos_finales["nombre_cliente"],
            "zona_final": datos_finales["zona_municipio"], 
            "presupuesto_final": datos_finales["presupuesto"],
            "operacion_final": datos_finales["tipo_operacion"],
            "dato_faltante_prioritario": "", # Ya no obligamos a interrogar
            "inventario": inventario, 
            "historial_chat": historial
        }).content
    except Exception as e:
        print(f"[ERROR GENERACION] {e}")
        respuesta = "Dame un momento, estoy consultando el inventario."

    print(f"[BOT] {respuesta}")

    await database.guardar_cliente(Body, respuesta, From, datos_msg, cliente_existente=cliente_db)

    # ==============================================================================
    # MODULO NOTIFICACIONES (DESBLOQUEADO TOTALMENTE)
    # ==============================================================================
    valor_asesor = str(datos_msg.get("quiere_asesor", "")).lower()
    correo_ya_enviado = cliente_db.get("correo_enviado", False) if cliente_db else False
    
    # 🚨 Se eliminó el candado del nombre
    if valor_asesor == "true" and not correo_ya_enviado:
        historial_para_correo = (cliente_db.get("observaciones_generales") or "") if cliente_db else f"Cliente: {Body}\nBot: {respuesta}"
        
        # Generamos un nombre temporal si el cliente aún no nos lo ha dado
        nombre_seguro = datos_finales.get("nombre_cliente") or f"Nuevo Prospecto ({From})"
        
        try:
            print("[IA] Generando resumen ejecutivo para el asesor...")
            resumen_ejecutivo = (agent.prompt_resumen | agent.llm_analista).invoke({
                "historial": historial_para_correo,
                "nombre": nombre_seguro,
                "telefono": From
            }).content
        except Exception as e:
            print(f"[ERROR RESUMEN] {e}")
            resumen_ejecutivo = historial_para_correo 

        info_lead = {
            "nombre": nombre_seguro,
            "telefono": From,
            "zona": datos_finales.get("zona_municipio") or "No especificada",
            "presupuesto": datos_finales.get("presupuesto") or "No especificado"
        }
        
        asesor_asignado = database.obtener_asesor_aleatorio()
        
        correo_destino = asesor_asignado["correo"] if asesor_asignado else "alfredoferrusca885@gmail.com"
        nombre_asesor = asesor_asignado["nombre"] if asesor_asignado else "Administrador"
        
        # MANDAMOS CORREO
        mailer.enviar_notificacion_asesor(info_lead, resumen_ejecutivo, correo_destino, nombre_asesor)
        
        # MANDAMOS WHATSAPP (Solo si tienes importado whatsapp_notifier, como lo tenías en los archivos anteriores)
        try:
            import whatsapp_notifier
            telefono_asesor = asesor_asignado.get("telefono") if asesor_asignado else "whatsapp:+5214272786799"
            whatsapp_notifier.enviar_alerta_asesor(telefono_asesor, info_lead, resumen_ejecutivo)
        except ImportError:
            print("[SISTEMA] No se encontró módulo whatsapp_notifier. Solo se envió correo.")
        
        # ACTUALIZAMOS LA BASE DE DATOS
        try:
            database.supabase.table("clientes").update({"correo_enviado": True}).eq("telefono", From).execute()
        except Exception as e:
            print(f"[ERROR DB ACTUALIZANDO CANDADO CORREO] {e}")
            
    # Respuesta XML Final
    xml = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Message>{respuesta.replace('&','y')}</Message></Response>"""
    return Response(content=xml.strip(), media_type="text/xml")