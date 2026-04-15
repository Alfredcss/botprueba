import os
import json
import re
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Response
from twilio.rest import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config
import database
import agent
import utils
import whatsapp_notifier
import mailer

# 1. IMPORTAMOS EL MÓDULO DEL DASHBOARD (Tu código)
from fastapi.middleware.cors import CORSMiddleware
from dashboard.routes import router as dashboard_router

# ==============================================================================
# SCHEDULER — Follow-up de Leads Inactivos
# ==============================================================================
async def check_followup_leads():
    """Corre cada hora. Detecta leads sin respuesta (2-24h) y manda mensaje de seguimiento."""
    print("[FOLLOWUP] Revisando leads inactivos...")
    try:
        ahora  = datetime.now(timezone.utc)
        hace2h  = (ahora - timedelta(hours=2)).isoformat()
        hace24h = (ahora - timedelta(hours=24)).isoformat()

        res = database.supabase.table("clientes") \
            .select("telefono, nombre_cliente") \
            .eq("bot_encendido", True) \
            .eq("followup_sent", False) \
            .lt("last_activity", hace2h) \
            .gt("last_activity", hace24h) \
            .execute()

        leads = res.data or []
        if not leads:
            print("[FOLLOWUP] Sin leads inactivos en este momento.")
            return

        print(f"[FOLLOWUP] {len(leads)} lead(s) inactivo(s) encontrado(s).")
        for lead in leads:
            nombre = lead.get("nombre_cliente") or ""
            saludo = f"\u00a1Hola {nombre}!" if nombre else "\u00a1Hola!"
            mensaje = (
                f"{saludo} \U0001f44b Seguimos aqu\u00ed para ayudarte.\n"
                f"\u00bfDeseas continuar con el proceso? "
                f"Puedo mostrarte m\u00e1s opciones o conectarte con un asesor. \U0001f60a"
            )
            try:
                whatsapp_notifier.client.messages.create(
                    from_=whatsapp_notifier.NUMERO_TWILIO,
                    body=mensaje,
                    to=lead["telefono"]
                )
                database.supabase.table("clientes") \
                    .update({"followup_sent": True}) \
                    .eq("telefono", lead["telefono"]) \
                    .execute()
                print(f"[FOLLOWUP] \u2705 Mensaje enviado a {lead['telefono']}")
            except Exception as e:
                print(f"[FOLLOWUP] \u274c Error con {lead['telefono']}: {e}")
    except Exception as e:
        print(f"[FOLLOWUP ERROR] {e}")

# ==============================================================================
# SCHEDULER RAPIDO — Follow-up en 5 min, 20 min + Auto-asignación en 25 min
# ==============================================================================
# │ AQUÍ SE CAMBIAN LOS TIEMPOS │
# ╟─────────────────────────────────────────└
MINUTOS_FOLLOWUP_ETAPA0 = 5   # Minutos sin respuesta para mandar PRIMER aviso
MINUTOS_FOLLOWUP_ETAPA1 = 20  # Minutos sin respuesta para mandar SEGUNDO aviso
MINUTOS_FOLLOWUP_ETAPA2 = 25  # Minutos desde el SEGUNDO aviso para auto-asignar asesor (O bien minutos totales, ver logica)
MINUTOS_INTERVALO_SCHEDULER = 5  # Con qué frecuencia corre el scheduler
# └─────────────────────────────────────────┘

async def check_quick_followup():
    """Corre cada MINUTOS_INTERVALO_SCHEDULER minutos.
    Etapa 0: si el cliente no responde en MINUTOS_FOLLOWUP_ETAPA0 min → mensaje amigable.
    Etapa 1: si no responde en MINUTOS_FOLLOWUP_ETAPA1 min → segundo mensaje de seguimiento.
    Etapa 2: si aún no responde en MINUTOS_FOLLOWUP_ETAPA2 min después del último aviso → auto-asignar asesor.
    """
    try:
        ahora          = datetime.now(timezone.utc)
        umbral_etapa0  = (ahora - timedelta(minutes=MINUTOS_FOLLOWUP_ETAPA0))
        umbral_etapa1  = (ahora - timedelta(minutes=MINUTOS_FOLLOWUP_ETAPA1))
        umbral_etapa2  = (ahora - timedelta(minutes=MINUTOS_FOLLOWUP_ETAPA2)).isoformat()

        # ── ETAPAS 0 y 1: Mensajes de seguimiento ──────────────────────────────
        # Consultamos todos los que no han llegado a Etapa 1 completa y no están asignados
        res1 = database.supabase.table("clientes") \
            .select("telefono, nombre_cliente, last_activity, observaciones_generales") \
            .eq("bot_encendido", True) \
            .eq("followup_sent", False) \
            .eq("auto_asignado", False) \
            .execute()

        for lead in (res1.data or []):
            try:
                last_activity_str = lead.get("last_activity")
                if not last_activity_str:
                    continue
                last_activity = datetime.fromisoformat(last_activity_str.replace("Z", "+00:00"))
                observaciones = lead.get("observaciones_generales") or ""
                nombre = lead.get("nombre_cliente") or ""
                saludo = f"\u00a1Hola {nombre}!" if nombre else "\u00a1Hola!"

                # Verificamos si ya enviamos el de 5 min (Etapa 0) revisando el historial oculto o parseando
                ya_envio_5m = "[FW-5M]" in observaciones

                if not ya_envio_5m and last_activity < umbral_etapa0:
                    # ETAPA 0: 5 minutos
                    mensaje_5m = (
                        f"{saludo} \U0001f44b ¿Sigues por ahí?\n"
                        f"Acabo de encontrar unas opciones más que podrían interesarte. "
                        f"¿Te gustaría que te las mande? \U0001f60a"
                    )
                    whatsapp_notifier.client.messages.create(
                        from_=whatsapp_notifier.NUMERO_TWILIO,
                        body=mensaje_5m,
                        to=lead["telefono"]
                    )
                    nuevo_obs = observaciones + "\n[FW-5M]"
                    database.supabase.table("clientes").update({
                        "observaciones_generales": nuevo_obs
                    }).eq("telefono", lead["telefono"]).execute()
                    print(f"[QUICK-FU] \u2705 Etapa 0 (5m) enviada a {lead['telefono']}")

                elif ya_envio_5m and last_activity < umbral_etapa1:
                    # ETAPA 1: 20 minutos
                    mensaje_20m = (
                        f"{saludo} Seguimos aqu\u00ed para ayudarte.\n"
                        f"\u00bfDeseas continuar con el proceso? "
                        f"Puedo mostrarte m\u00e1s opciones o conectarte con un asesor."
                    )
                    whatsapp_notifier.client.messages.create(
                        from_=whatsapp_notifier.NUMERO_TWILIO,
                        body=mensaje_20m,
                        to=lead["telefono"]
                    )
                    database.supabase.table("clientes").update({
                        "followup_sent":    True,
                        "followup_sent_at": ahora.isoformat()
                    }).eq("telefono", lead["telefono"]).execute()
                    print(f"[QUICK-FU] \u2705 Etapa 1 (20m) enviada a {lead['telefono']}")
            except Exception as e:
                print(f"[QUICK-FU] \u274c Error Etapas 0/1 con {lead['telefono']}: {e}")

        # ── ETAPA 2: Auto-asignar asesor ────────────────────────────────────────
        res2 = database.supabase.table("clientes") \
            .select("telefono, nombre_cliente, zona_municipio, presupuesto, observaciones_generales") \
            .eq("bot_encendido", True) \
            .eq("followup_sent", True) \
            .eq("auto_asignado", False) \
            .lt("followup_sent_at", umbral_etapa2) \
            .execute()

        for lead in (res2.data or []):
            try:
                asesor = database.obtener_asesor_aleatorio()
                if not asesor:
                    print("[QUICK-FU] Sin asesores activos para auto-asignar.")
                    continue

                nombre_lead = lead.get("nombre_cliente") or "Cliente Interesado"
                info_lead = {
                    "nombre":      nombre_lead,
                    "telefono":    lead["telefono"],
                    "zona":        lead.get("zona_municipio") or "No especificada",
                    "presupuesto": lead.get("presupuesto")   or "No especificado"
                }
                historial   = lead.get("observaciones_generales") or ""
                nombre_asesor = asesor["nombre"]
                tel_asesor    = asesor["telefono"]
                correo_destino = whatsapp_notifier.CORREO_OFICINA if hasattr(whatsapp_notifier, "CORREO_OFICINA") else "asesores@c21diamante.com"
                if asesor.get("recibir_correo") and asesor.get("correo"):
                    correo_destino += f", {asesor['correo']}"

                # Generar resumen ejecutivo del historial con IA
                resumen_ia = await (agent.prompt_resumen | agent.llm_analista).ainvoke({
                    "historial": historial,
                    "nombre":    nombre_lead,
                    "telefono":  lead["telefono"]
                })

                # Notificar al asesor por WhatsApp y correo
                whatsapp_notifier.enviar_alerta_asesor(
                    numero_asesor=tel_asesor,
                    datos_cliente=info_lead,
                    resumen_ai=resumen_ia.content,
                    nombre_asesor=nombre_asesor
                )
                mailer.enviar_notificacion_asesor(
                    datos_cliente=info_lead,
                    historial_completo=historial,
                    correo_destino=correo_destino,
                    nombre_asesor=nombre_asesor
                )

                # Actualizar cliente: pausar bot y marcar como asignado
                database.supabase.table("clientes").update({
                    "auto_asignado": True,
                    "correo_enviado": True,
                    "seguimiento":   nombre_asesor,
                    "bot_encendido": False
                }).eq("telefono", lead["telefono"]).execute()

                print(f"[QUICK-FU] \u2705 Etapa 2: {lead['telefono']} auto-asignado a {nombre_asesor}")
            except Exception as e:
                print(f"[QUICK-FU] \u274c Etapa 2 error con {lead['telefono']}: {e}")

    except Exception as e:
        print(f"[QUICK-FU ERROR] {e}")


scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduler lento: follow-up a leads fríos (2-24h)
    scheduler.add_job(check_followup_leads, "interval", hours=1, id="followup_leads")
    # Scheduler rápido: Etapa 1 + Etapa 2 auto-asignación (tiempos en constantes arriba)
    scheduler.add_job(check_quick_followup, "interval", minutes=MINUTOS_INTERVALO_SCHEDULER, id="quick_followup")
    scheduler.start()
    print(f"[SCHEDULER] ✅ Schedulers iniciados (follow-up 1h + quick cada {MINUTOS_INTERVALO_SCHEDULER} min | Etapa1={MINUTOS_FOLLOWUP_ETAPA1}min, Etapa2={MINUTOS_FOLLOWUP_ETAPA2}min).")
    yield
    scheduler.shutdown()
    print("[SCHEDULER] Schedulers detenidos.")

app = FastAPI(lifespan=lifespan)

# Permitir conexiones desde cualquier dominio (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CONECTAMOS EL DASHBOARD A LA APP PRINCIPAL
app.include_router(dashboard_router)

# ==============================================================================
# ENDPOINT PRINCIPAL: WHATSAPP BOT (Lógica intacta de tu compañero)
# ==============================================================================
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

    print(f"\n[MENSAJE] {From} -> {Body}")
    body_lower = Body.lower()

    # ==============================================================================
    # SILENCIADOR MANUAL DEL BOT (HUMAN IN THE LOOP)
    # ==============================================================================
    cliente_db = database.obtener_cliente(From)
    bot_activo = cliente_db.get("bot_encendido", True) if cliente_db else True

    if not bot_activo:
        print(f"[BOT PAUSADO] Mensaje recibido de {From}. Esperando intervención humana.")
        
        ahora = datetime.now()
        sello = ahora.strftime("%d/%m %H:%M")
        historial_actual = cliente_db.get("observaciones_generales") or ""
        prefijo = "\n" if historial_actual else ""
        nuevo_historial = f"{historial_actual}{prefijo}[{sello}] Cliente: {Body}"
        
        try:
            database.supabase.table("clientes").update({
                "observaciones_generales": nuevo_historial,
                "leido": False,
                "fecha_contacto": ahora_mx.strftime("%Y-%m-%d"),
                "hora_contacto": ahora_mx.strftime("%H:%M:%S"),
                "last_activity": ahora_utc.isoformat(),  # Resetear ventana de follow-up
                "followup_sent": False               # El asesor está activo, no mandar followup
            }).eq("telefono", From).execute()
        except Exception as e:
            print(f"[ERROR ACTUALIZAR SILENCIO] {e}")
            
        return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="text/xml")

    # ==============================================================================
    # DETECCIÓN DE ASESOR — Si el número pertenece a un asesor, NO correr flujo de ventas
    # ==============================================================================
    asesor_remitente = database.obtener_asesor_por_telefono(From)
    if asesor_remitente:
        nombre_asesor_rem = asesor_remitente.get("nombre", "Asesor")
        print(f"[ASESOR] Mensaje recibido de asesor: {nombre_asesor_rem} ({From})")

        # Actualizar last_keepalive en la tabla asesores para saber que está activo
        try:
            ahora_utc = datetime.now(timezone.utc).isoformat()
            database.supabase.table("asesores").update({
                "last_keepalive": ahora_utc
            }).eq("id", asesor_remitente["id"]).execute()
        except Exception as e:
            print(f"[ASESOR] Error actualizando keepalive: {e}")

        # Respuesta de confirmación al asesor (no es un cliente)
        msg_asesor = (
            f"✅ ¡Hola {nombre_asesor_rem}!\n"
            f"Tu conexión está activa. Los nuevos leads te llegarán directamente aquí. 📲\n\n"
            f"_Este canal es exclusivo para notificaciones de Century 21 Diamante._"
        )
        xml_asesor = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Message>{msg_asesor}</Message></Response>"""
        return Response(content=xml_asesor.strip(), media_type="text/xml")

    # ==============================================================================
    # MODULO CLIENTES (RAG Y CRM)
    # ==============================================================================
    historial = (cliente_db.get("observaciones_generales") or "")[-4000:] if cliente_db else ""

    datos_msg = {}
    try:
        resp = await (agent.prompt_analista | agent.llm_analista).ainvoke({
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
        if campo == "presupuesto" and datos_msg.get("zona_municipio") and not datos_msg.get("presupuesto"):
            return None
        return val_msg if val_msg else val_db

    datos_finales = {
        "nombre_cliente": fusionar("nombre_cliente"),
        "zona_municipio": fusionar("zona_municipio"),
        "tipo_inmueble": fusionar("tipo_inmueble"),
        "tipo_operacion": fusionar("tipo_operacion"),
        "presupuesto": fusionar("presupuesto", es_numero=True),
        "clave_propiedad": datos_msg.get("clave_propiedad"),
        "recamaras": fusionar("recamaras", es_numero=True),
        "banios": fusionar("banios", es_numero=True),
        "caracteristica": fusionar("caracteristica"),
        "origen_campana": datos_msg.get("origen_campana")
    }

    if datos_finales["origen_campana"]: datos_msg["origen"] = datos_finales["origen_campana"]

    # Limpiar caracteristicas de terminos de credito y verbos filtro para evitar choques en busqueda exacta
    if datos_finales["caracteristica"]:
        c_limpia = datos_finales["caracteristica"].lower()
        stopwords_pattern = r"\b(infonavit|fovissste|bancario|credito|crédito|creditos|créditos|recursos propios|acepta|acepte|acepten|con|que|tenga|para)\b"
        c_limpia = re.sub(stopwords_pattern, "", c_limpia)
        datos_finales["caracteristica"] = c_limpia.strip(" ,.-")

    inventario = ""
    propiedades = []
    faltante = "Ninguno"
    alerta_fase_2 = False
    quiere_ver = utils.detectar_intencion_ver_propiedades(Body)

    # 🔍 DETECCIÓN DE INTENCIÓN DE CRÉDITO
    tipo_credito_detectado = None
    if "infonavit" in body_lower: tipo_credito_detectado = "infonavit"
    elif "fovissste" in body_lower: tipo_credito_detectado = "fovissste"
    elif "bancario" in body_lower: tipo_credito_detectado = "bancario"
    elif "credito" in body_lower or "crédito" in body_lower: tipo_credito_detectado = "general"

    if datos_finales["clave_propiedad"]:
        propiedades = database.buscar_por_clave(datos_finales["clave_propiedad"])
    else:
        if not datos_finales["zona_municipio"]: faltante = "ZONA"
        elif not datos_finales["presupuesto"]: faltante = "PRESUPUESTO"
        
        if faltante in ["Ninguno", "NOMBRE_SOLO_SI_HAY_CITA"] or quiere_ver or datos_finales["zona_municipio"] or datos_finales["tipo_inmueble"]:
            # 2. Ahora esperamos DOS valores de la base de datos y pasamos la caracteristica
            propiedades, alerta_fase_2 = database.buscar_propiedades(
                datos_finales["tipo_inmueble"], 
                datos_finales["tipo_operacion"],
                datos_finales["zona_municipio"],
                datos_finales["presupuesto"], 
                recamaras=datos_finales["recamaras"],
                banios=datos_finales["banios"],
                caracteristica=datos_finales["caracteristica"], # <--- ESTO ESTÁ PERFECTO
                mostrar_mix_general=(quiere_ver and not datos_finales["zona_municipio"]),
                tipo_credito=tipo_credito_detectado
            )

    # 3. Inyectamos la alerta si se activó la Fase 2 (Esto cura la alucinación de Praderas)
    if alerta_fase_2:
        inventario += f"\n\n🚨 IMPORTANTE PARA ARIA: No encontraste propiedades en la zona exacta ({datos_finales['zona_municipio']}), estas opciones son cercanas/sugerencias. Pide disculpas e indícalo al cliente."
    if propiedades:
        for p in propiedades:
            if p is None:
                continue
            pre = p.get('precio', 0)

            desc = p.get('descripcion', '') or ''
            desc = desc.lower()
            
            institucion_raw = p.get('institucionHipotecaria') or ''
            if isinstance(institucion_raw, list):
                institucion = " ".join([str(i).lower() for i in institucion_raw])
            else:
                institucion = str(institucion_raw).lower()
        
            acepta = {
                "Infonavit": "infonavit" in desc or "infonavit" in institucion,
                "Fovissste": "fovissste" in desc or "fovissste" in institucion or "fovisste" in desc or "fovisste" in institucion or "foviste" in desc or "foviste" in institucion,
                "Bancario": "bancario" in desc or "crédito" in desc or "credito" in desc or "bancario" in institucion,
                "Banjercito": "banjercito" in desc or "banjercito" in institucion
            }
            creditos_aceptados = [nombre for nombre, lo_acepta in acepta.items() if lo_acepta]
            status_credito = f"✅ Acepta: {', '.join(creditos_aceptados)}" if creditos_aceptados else "❌ NO acepta créditos, solo pago con recursos propios"

            inventario += f"""
                ---
                🆔 Referencia: {p.get('clave', 'S/N')}
                🏠 {p.get('subtipoPropiedad', 'Propiedad')} en {p.get('tipoOperacion', 'Venta')} - {p.get('municipio', 'Zona C21')}
                💰 Precio: ${pre:,.0f}
                💳 Créditos: {status_credito}
                📝 Detalles: {p.get('descripcion', 'Sin descripción detallada.')}
                📸 Ficha: {p.get('url_ficha') or 'Consultar asesor'}
                ---
                """
        inventario += "\n\n📋 Recuerda que los gastos notariales son independientes al precio publicado."
    elif quiere_ver and not datos_finales["clave_propiedad"]:
        inventario = "No encontré coincidencias exactas."

    # === DETERMINAR ASIGNACIÓN ANTES DE RESPONDER ===
    estado_asignacion_prompt = "No se ha solicitado asesor en este mensaje o ya se envio alerta antes."
    
    # Variables de asignación retenidas para despues de responder
    asignacion_lista = False
    info_lead_retenida = None
    nombre_final_asesor_retenido = "Oficina"
    telefono_final_asesor_retenido = whatsapp_notifier.NUMERO_OFICINA
    correos_destino_final_retenido = "asesores@c21diamante.com"
    
    valor_asesor = str(datos_msg.get("quiere_asesor", "")).lower()
    nombre_lead = datos_finales.get("nombre_cliente")
    alerta_ya_enviada = cliente_db.get("correo_enviado", False) if cliente_db else False

    if valor_asesor == "true" and not alerta_ya_enviada:
        asignacion_lista = True
        nombre_seguro = nombre_lead if nombre_lead and nombre_lead != "Cliente Interesado" else "Cliente Interesado"
        info_lead_retenida = {
            "nombre": nombre_seguro,
            "telefono": From,
            "zona": datos_finales.get("zona_municipio") or "No especificada",
            "presupuesto": datos_finales.get("presupuesto") or "No especificado"
        }
        
        nombre_solicitado = datos_msg.get("asesor_solicitado")
        if nombre_solicitado:
            asesor_asignado = database.obtener_asesor_por_nombre(nombre_solicitado)
            if asesor_asignado:
                print(f"[ASIGNACIÓN] El cliente pidió a {asesor_asignado['nombre']} y está ACTIVO.")
                nombre_final_asesor_retenido = asesor_asignado['nombre']
                telefono_final_asesor_retenido = asesor_asignado['telefono']
                if asesor_asignado.get('recibir_correo') and asesor_asignado.get('correo'):
                    correos_destino_final_retenido += f", {asesor_asignado['correo']}"
                estado_asignacion_prompt = f"Se asignó con éxito a {nombre_final_asesor_retenido}"
            else:
                print(f"[ASIGNACIÓN] Pidió a '{nombre_solicitado}' pero está inactivo/no existe. Va a ruleta.")
                asesor_asignado = database.obtener_asesor_aleatorio()
                if asesor_asignado:
                    nombre_final_asesor_retenido = asesor_asignado['nombre']
                    telefono_final_asesor_retenido = asesor_asignado['telefono']
                    if asesor_asignado.get('recibir_correo') and asesor_asignado.get('correo'):
                        correos_destino_final_retenido += f", {asesor_asignado['correo']}"
                estado_asignacion_prompt = f"El cliente pidió a {nombre_solicitado} pero NO está disponible. Se asignó a {nombre_final_asesor_retenido}"
        else:
            asesor_asignado = database.obtener_asesor_aleatorio()
            if asesor_asignado:
                print(f"[ASIGNACIÓN] La ruleta eligió a: {asesor_asignado['nombre']}")
                nombre_final_asesor_retenido = asesor_asignado['nombre']
                telefono_final_asesor_retenido = asesor_asignado['telefono']
                if asesor_asignado.get('recibir_correo') and asesor_asignado.get('correo'):
                    correos_destino_final_retenido += f", {asesor_asignado['correo']}"
            estado_asignacion_prompt = f"Se asignó con éxito a {nombre_final_asesor_retenido}"

    try:
        respuesta_ia = await (agent.prompt_vendedor | agent.llm_vendedor).ainvoke({
            "mensaje": Body, 
            "nombre_final": datos_finales["nombre_cliente"],
            "zona_final": datos_finales["zona_municipio"], 
            "presupuesto_final": datos_finales["presupuesto"],
            "operacion_final": datos_finales["tipo_operacion"],
            "dato_faltante_prioritario": faltante, 
            "inventario": inventario, 
            "historial_chat": historial,
            "estado_asignacion": estado_asignacion_prompt
        })
        respuesta = respuesta_ia.content 
    except Exception as e:
        print(f"[ERROR GENERACION] {e}")
        respuesta = "Dame un momento, estoy consultando el inventario."

    # 💡 FORZAR EL TEXTO DE GASTOS NOTARIALES SI SE MOSTRARON PROPIEDADES
    if "referencia:" in respuesta.lower() and "gastos notariales" not in respuesta.lower():
        respuesta += "\n\n📋 Recuerda que los gastos notariales son independientes al precio publicado."

    # 🛡️ GUARDIA DE FICHA TÉCNICA: inyectar fichas que el LLM haya omitido
    if propiedades:
        for p in propiedades:
            if p is None:
                continue
            clave = str(p.get('clave', '') or '')
            url_ficha = p.get('url_ficha') or ''
            texto_ficha = url_ficha if url_ficha else 'Consultar asesor'
            # Si la propiedad está referenciada en la respuesta pero su ficha no aparece
            if clave and clave in respuesta and texto_ficha not in respuesta:
                respuesta += f"\n\n📸 Ficha propiedad {clave}: {texto_ficha}"

    print(f"[BOT] {respuesta}")

    # Guardar primera interacción en DB
    await database.guardar_cliente(Body, respuesta, From, datos_msg, cliente_existente=cliente_db)

    # ==============================================================================
    # MODULO NOTIFICACIONES (Ejecución Post-Captura)
    # ==============================================================================
    if asignacion_lista:
        obs_previas = cliente_db.get('observaciones_generales', '') if cliente_db else ''
        historial_actualizado = f"{obs_previas}\nCliente: {Body}\nBot: {respuesta}"

        # 1. Generar resumen IA
        resumen_ejecutivo = "Sin resumen disponible."
        try:
            resumen_ia = await (agent.prompt_resumen | agent.llm_analista).ainvoke({
                "historial": historial_actualizado,
                "nombre": info_lead_retenida["nombre"],
                "telefono": From
            })
            resumen_ejecutivo = resumen_ia.content
        except Exception as e:
            print(f"[ERROR RESUMEN IA] {e}")

        # 2. Enviar alerta WhatsApp al asesor (independiente)
        try:
            whatsapp_notifier.enviar_alerta_asesor(
                numero_asesor=telefono_final_asesor_retenido,
                datos_cliente=info_lead_retenida,
                resumen_ai=resumen_ejecutivo,
                nombre_asesor=nombre_final_asesor_retenido
            )
        except Exception as e:
            print(f"[ERROR WHATSAPP ASESOR] {e}")

        # 3. Enviar correo (independiente — un fallo de Gmail NO bloquea el resto)
        try:
            mailer.enviar_notificacion_asesor(
                datos_cliente=info_lead_retenida,
                historial_completo=historial_actualizado,
                correo_destino=correos_destino_final_retenido,
                nombre_asesor=nombre_final_asesor_retenido
            )
        except Exception as e:
            print(f"[ERROR CORREO ASESOR] {e}")

        # 4. Actualizar Supabase SIEMPRE, sin importar si el correo falló
        try:
            database.supabase.table("clientes").update({
                "correo_enviado": True,
                "seguimiento": nombre_final_asesor_retenido
            }).eq("telefono", From).execute()
            print(f"[DB] ✅ Seguimiento actualizado → {nombre_final_asesor_retenido}")
        except Exception as e:
            print(f"[ERROR DB SEGUIMIENTO] {e}")

    # Respuesta XML Segura
    xml = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Message>{respuesta.replace('&','y')}</Message></Response>"""
    return Response(content=xml.strip(), media_type="text/xml")