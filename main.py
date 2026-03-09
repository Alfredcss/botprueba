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
import whatsapp_notifier

app = FastAPI()

@app.post("/whatsapp")
async def whatsapp_reply(
    From: str = Form(...),
    Body: str = Form(default=""),               
    NumMedia: str = Form(default="0"),          
    MediaUrl0: str = Form(default=""),          
    MediaContentType0: str = Form(default="")   
):
    if NumMedia != "0" and "audio" in MediaContentType0:
        texto_transcrito = utils.descargar_y_transcribir_audio(MediaUrl0)
        Body = texto_transcrito

    print(f"\n[MENSAJE] {From} → {Body}")

    # ==============================================================================
    # MODULO VIP 
    # ==============================================================================
    nombre_asesor_auth = database.obtener_asesor_por_telefono(From)
    if nombre_asesor_auth:
        body_lower = Body.lower()
        
        # Comandos secretos estrictos para evitar falsos positivos
        comandos_vip = ["/reporte", "/exclusivas", "/inventario", "#reporte", "#inventario"]
        if any(comando in body_lower for comando in comandos_vip):
            
            # Buscamos si pidió el reporte de alguien más (ej. "asesor alfredo")
            # Buscamos de forma inteligente el nombre ignorando "de", "la", "el", "asesor" o "asesora"
            patron = r'(?:/reporte|/exclusivas|/inventario)\s+(?:de\s+|del\s+)?(?:la\s+|el\s+)?(?:asesora\s+|asesor\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)'
            match = re.search(patron, body_lower)
            
            if match:
                asesor_objetivo = match.group(1).capitalize() 
            else:
                asesor_objetivo = nombre_asesor_auth # Si solo pone "/reporte", saca el suyo
            
            # OJO: Mientras estés en local, pon aquí tu URL actual de Ngrok
            base_url = "https://perceivable-mi-nonadjacently.ngrok-free.dev" 
            link_descarga = f"{base_url}/descargar/{asesor_objetivo.replace(' ', '%20')}"
            
            mensaje_vip = (
                f"🛡️ *Acceso Autorizado*\n"
                f"Hola {nombre_asesor_auth}.\n\n"
                f"Aquí tienes el reporte de exclusivas de *{asesor_objetivo}*:\n"
                f"📄 {link_descarga}\n\n"
                f"¡Éxito en tus cierres! 🤝"
            )
            
            print(f"\n[🔒 SEGURIDAD] Número autorizado perteneciente a: {nombre_asesor_auth}")
            print(f"[VIP MODO ACTIVADO] Generando reporte para: {asesor_objetivo}")
            print(f"[BOT VIP] {mensaje_vip}\n")
            
            xml = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Message>{mensaje_vip}</Message></Response>"""
            return Response(content=xml.strip(), media_type="text/xml")

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
        "origen_campana": datos_msg.get("origen_campana")
    }

    if datos_finales["origen_campana"]: datos_msg["origen"] = datos_finales["origen_campana"]

    inventario = ""
    propiedades = []
    faltante = "Ninguno"
    

    quiere_ver = utils.detectar_intencion_ver_propiedades(Body)

    if datos_finales["clave_propiedad"]:
        propiedades = database.buscar_por_clave(datos_finales["clave_propiedad"])
    else:
        
        if not datos_finales["zona_municipio"]: 
            faltante = "ZONA"
        elif not datos_finales["presupuesto"]: 
            faltante = "PRESUPUESTO"
        elif not datos_finales["nombre_cliente"]: 
            faltante = "NOMBRE_SOLO_SI_HAY_CITA"

        # 2. BÚSQUEDA LIBERADA: Buscamos siempre que tengamos zona, presupuesto o intención, sin importar el nombre
        if faltante in ["Ninguno", "NOMBRE_SOLO_SI_HAY_CITA"] or quiere_ver or datos_finales["zona_municipio"] or datos_finales["tipo_inmueble"]:
            propiedades = database.buscar_propiedades(
                datos_finales["tipo_inmueble"], 
                datos_finales["tipo_operacion"],
                datos_finales["zona_municipio"],
                datos_finales["presupuesto"], 
                mostrar_mix_general=(quiere_ver and not datos_finales["zona_municipio"])
            )

    if propiedades:
        for p in propiedades:
            id_prop = p.get('id') 
            clave = p.get('clave', 'S/N')
            tipo = p.get('subtipoPropiedad') or 'Propiedad'
            operacion = p.get('tipoOperacion') or 'Venta'
            mun = p.get('municipio', 'Zona C21')
            col = p.get('colonia', '')
            pre = p.get('precio', 0)
            desc = p.get('descripcion', 'Sin descripción detallada.')
            m2t = p.get('m2T') or 0      
            m2c = p.get('m2C') or 0      
            banos = p.get('banios') or 0 
            habs = p.get('recamaras') or p.get('ambientes') or 0 
            link_mapa = p.get('mapa_url')
            lat, lon = p.get('latitud'), p.get('longitud')
            if not link_mapa and lat and lon:
                link_mapa = f"https://maps.google.com/?q={lat},{lon}"
                if id_prop: database.guardar_mapa_generado(id_prop, link_mapa)
            if not link_mapa: link_mapa = "Solicita ubicación a tu asesor."
            link_ficha = p.get('url_ficha') or "Solicita el enlace con fotos a tu asesor"

            inventario += f"""
            ---
            🆔 Referencia: {clave}
            🏠 {tipo} en {operacion} - {mun} ({col})
            💰 Precio: ${pre:,.0f}
            📏 Terreno: {m2t}m² | Constr: {m2c}m²
            🛏️ Habitaciones: {habs} | 🛁 Baños: {banos}
            📍 Ubicación: {link_mapa}
            📸 Fotos y Ficha Técnica: {link_ficha}
            📝 Detalle: {desc}
            ---
            """
    elif quiere_ver and not datos_finales["clave_propiedad"]:
        inventario = "No encontré coincidencias exactas."

    if inventario and ("Referencia:" in inventario or "ID:" in inventario):
        faltante = "Ninguno"

    try:
        respuesta = (agent.prompt_vendedor | agent.llm_vendedor).invoke({
            "mensaje": Body, 
            "nombre_final": datos_finales["nombre_cliente"],
            "zona_final": datos_finales["zona_municipio"], 
            "presupuesto_final": datos_finales["presupuesto"],
            "operacion_final": datos_finales["tipo_operacion"],
            "dato_faltante_prioritario": faltante, 
            "inventario": inventario, 
            "historial_chat": historial
        }).content
    except Exception as e:
        print(f"[ERROR GENERACION] {e}")
        respuesta = "Dame un momento, estoy consultando el inventario."

    print(f"[BOT] {respuesta}")

    await database.guardar_cliente(Body, respuesta, From, datos_msg, cliente_existente=cliente_db)

    # ==============================================================================
    # MODULO NOTIFICACIONES (MAILER)
    # ==============================================================================
    valor_asesor = str(datos_msg.get("quiere_asesor", "")).lower()
    nombre_lead = datos_finales.get("nombre_cliente")
    
    # Revisamos si la base de datos ya tiene la bandera de que se envió el correo
    correo_ya_enviado = cliente_db.get("correo_enviado", False) if cliente_db else False
    
    # CANDADO: Solo enviamos si quiere asesor, SI YA TENEMOS SU NOMBRE, y si NO hemos enviado correo antes.
    if valor_asesor == "true" and nombre_lead and not correo_ya_enviado:
        # 1. DEFINIMOS EL HISTORIAL ANTES DE CUALQUIER OTRA COSA
        historial_actualizado = f"{(cliente_db.get('observaciones_generales') or '')}\nCliente: {Body}\nBot: {respuesta}"
        
        # 2. GENERAMOS EL RESUMEN
        try:
            print("[IA] Generando resumen ejecutivo para el asesor...")
            resumen_ejecutivo = (agent.prompt_resumen | agent.llm_analista).invoke({
                "historial": historial_actualizado,
                "nombre": datos_finales.get("nombre_cliente") or "Cliente sin nombre",
                "telefono": From
            }).content
        except Exception as e:
            print(f"[ERROR RESUMEN] {e}")
            resumen_ejecutivo = historial_actualizado 

        info_lead = {
            "nombre": datos_finales.get("nombre_cliente") or "Cliente",
            "telefono": From,
            "zona": datos_finales.get("zona_municipio") or "No especificada",
            "presupuesto": datos_finales.get("presupuesto") or "No especificado"
        }
        
        # --- 🎲 INICIA LA RULETA DE ASESORES ---
        asesor_asignado = database.obtener_asesor_aleatorio()
        
        # 1. Sacamos el nombre y el WhatsApp del ganador
        if asesor_asignado:
            telefono_asesor = asesor_asignado.get("telefono") or "whatsapp:+5214272786799"
            nombre_asesor = asesor_asignado.get("nombre") or "Administrador"
        else:
            telefono_asesor = "whatsapp:+5214272786799"
            nombre_asesor = "Administrador"
            
        # 🚨 2. EL CORREO MAESTRO: Aquí pones el correo único donde quieren que llegue todo
        correo_destino = "richardRI1690@gmail.com" # <--- CÁMBIALO POR EL CORREO REAL
            
        # 🚀 DISPARAMOS AMBAS NOTIFICACIONES
        # El correo se va al buzón maestro, pero lleva impreso el nombre del ganador
        mailer.enviar_notificacion_asesor(info_lead, resumen_ejecutivo, correo_destino, nombre_asesor)
        
        # El WhatsApp sí se va directo al celular del ganador
        whatsapp_notifier.enviar_alerta_asesor(telefono_asesor, info_lead, resumen_ejecutivo)
        
        # 5. ACTUALIZAMOS EL CANDADO EN LA BASE DE DATOS
        try:
            database.supabase.table("clientes").update({"correo_enviado": True}).eq("telefono", From).execute()
        except Exception as e:
            print(f"[ERROR DB ACTUALIZANDO CANDADO] {e}")
            
    elif valor_asesor == "true" and not nombre_lead:
        print("[SISTEMA] Intención detectada, pero esperando nombre del cliente para enviar correo.")

@app.get("/descargar/{nombre_asesor}")
async def descargar_reporte_asesor(nombre_asesor: str):
    datos = database.obtener_propiedades_por_asesor(nombre_asesor)
    if not datos: return Response(content="No se encontraron propiedades.", media_type="text/plain")

    stream = io.StringIO()
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL)
    writer.writerow(list(datos[0].keys()))
    
    for fila in datos:
        writer.writerow([str(valor) if valor is not None else "" for valor in fila.values()])

    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Inventario_{nombre_asesor}.csv"}
    )