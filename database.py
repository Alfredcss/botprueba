from supabase import create_client, Client
import config
import utils
from datetime import datetime, timezone, timedelta
import random
import whatsapp_notifier

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
COLUMNAS_PERMITIDAS = "id,clave,nombre,municipio,colonia,precio,subtipoPropiedad,tipoOperacion,descripcion,m2T," \
                        "m2C,recamaras,banios,institucionHipotecaria,mapa_url,latitud,longitud,url_ficha"

# ==============================================================================
# FUNCIONES DE CLIENTES (CRM)
# ==============================================================================
def obtener_cliente(telefono: str):
    try:
        res = supabase.table("clientes").select("*").eq("telefono", telefono).execute()
        if res.data: return res.data[0]
        return None
    except Exception as e:
        print(f"[ERROR DB OBTENER CLIENTE] {e}")
        return None

async def guardar_cliente(mensaje_usuario, respuesta_bot, telefono, datos_extraidos, cliente_existente=None, asesor_asignado_nombre=None):
    try:
        observaciones_actuales = cliente_existente.get("observaciones_generales", "") if cliente_existente else ""
        
        # Generar hora y fecha
        ahora = datetime.now()
        sello = ahora.strftime("%d/%m %H:%M")

        observaciones_actuales = observaciones_actuales or ""
        prefijo = "\n" if observaciones_actuales else ""

        nuevo_historial = (
            f"{observaciones_actuales}{prefijo}[{sello}] Cliente: {mensaje_usuario}"
            f"\n[{sello}] Bot: {respuesta_bot}"
        )

        ahora = datetime.now(timezone.utc)
        tz_mx = timezone(timedelta(hours=-6))
        ahora_mx = ahora.astimezone(tz_mx)
        datos_guardar = {
            "telefono": telefono,
            "observaciones_generales": nuevo_historial,
            "fecha_contacto": ahora_mx.strftime("%Y-%m-%d"),
            "hora_contacto": ahora_mx.strftime("%H:%M:%S"),
            "last_activity": ahora.isoformat(),
            "followup_sent_at": None
        }

        if datos_extraidos.get("nombre_cliente"): datos_guardar["nombre_cliente"] = datos_extraidos["nombre_cliente"]
        
        if datos_extraidos.get("tipo_inmueble"): datos_guardar["tipo_inmueble"] = datos_extraidos["tipo_inmueble"]
        if datos_extraidos.get("zona_municipio"): datos_guardar["zona_municipio"] = datos_extraidos["zona_municipio"]
        if datos_extraidos.get("presupuesto"): datos_guardar["presupuesto"] = str(datos_extraidos["presupuesto"])
        # Solo guardar origen si el cliente aún no tiene uno registrado (preservar la fuente original)
        origen_existente = cliente_existente.get("origen") if cliente_existente else None
        if datos_extraidos.get("origen") and not origen_existente:
            datos_guardar["origen"] = datos_extraidos["origen"]
        if datos_extraidos.get("clave_propiedad"): datos_guardar["id_propiedad_opcional"] = datos_extraidos["clave_propiedad"]

        if asesor_asignado_nombre: datos_guardar["seguimiento"] = asesor_asignado_nombre

        if cliente_existente:
            supabase.table("clientes").update(datos_guardar).eq("telefono", telefono).execute()
        else:
            supabase.table("clientes").insert(datos_guardar).execute()
    except Exception as e:
        print(f"[ERROR DB GUARDAR CLIENTE] {e}")

# ==============================================================================
# FUNCIONES DE PROPIEDADES (INVENTARIO Y MAPAS)
# ==============================================================================
def buscar_por_clave(clave):
    try:
        clave_limpia = str(clave).strip()
        res = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS).or_(f"clave.eq.{clave_limpia},id.eq.{utils.limpiar_numero(clave_limpia)}").execute()
        return res.data
    except Exception as e:
        print(f"[ERROR BUSQUEDA CLAVE] {e}")
        return []

def buscar_propiedades(tipo_inmueble, tipo_operacion, zona, presupuesto, recamaras=None, banios=None, caracteristica=None, mostrar_mix_general=False, tipo_credito=None):
    try:
        if not presupuesto:
            presupuesto_busqueda = 1000000000
            orden_descendente = False  
        else:
            presupuesto_busqueda = presupuesto * 1.2 
            orden_descendente = True   

        query = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)
        
        if tipo_operacion: query = query.ilike("tipoOperacion", f"%{tipo_operacion}%")
        if tipo_inmueble:
            # Agrupar Local, Oficina y Consultorio para mayor flexibilidad comercial
            tipo_prefix = tipo_inmueble[:3].lower()
            if tipo_prefix in ["loca", "ofic", "cons"]:
                query = query.or_("subtipoPropiedad.ilike.%loca%,subtipoPropiedad.ilike.%ofic%,subtipoPropiedad.ilike.%cons%")
            else:
                query = query.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%")
        
        # Filtro de Crédito
        if tipo_credito == "infonavit": query = query.or_('descripcion.ilike.%infonavit%,institucionHipotecaria.cs.{"INFONAVIT"}')
        elif tipo_credito == "fovissste": query = query.or_('descripcion.ilike.%fovissste%,descripcion.ilike.%fovisste%,descripcion.ilike.%foviste%,institucionHipotecaria.cs.{"FOVISSSTE"}')
        elif tipo_credito == "bancario": query = query.or_('descripcion.ilike.%bancario%,descripcion.ilike.%credito%,descripcion.ilike.%crédito%,institucionHipotecaria.cs.{"BANCARIO"}')
        elif tipo_credito == "general": query = query.or_('descripcion.ilike.%infonavit%,descripcion.ilike.%fovissste%,descripcion.ilike.%bancario%,institucionHipotecaria.cs.{"INFONAVIT"},institucionHipotecaria.cs.{"FOVISSSTE"},institucionHipotecaria.cs.{"BANCARIO"}')

        # 🌟 NUEVO: Filtro de Características (Múltiples palabras separadas por coma)
        if caracteristica:
            # Dividimos las palabras por comas y limpiamos los espacios
            lista_palabras = [c.strip().lower() for c in str(caracteristica).split(",") if c.strip()]
            
            # Aplicamos un filtro independiente por cada amenidad (Funciona como AND)
            for palabra in lista_palabras:
                query = query.ilike("descripcion", f"%{palabra}%")

        # Filtro de Zona
        if zona and zona.lower() != "sugerencias":
            zona_limpia = str(zona).strip()
            zona_busqueda = f"municipio.ilike.%{zona_limpia}%,colonia.ilike.%{zona_limpia}%,nombre.ilike.%{zona_limpia}%,descripcion.ilike.%{zona_limpia}%"
            query = query.or_(zona_busqueda)

        if recamaras is not None:
            query = query.or_(f"recamaras.gte.{recamaras},recamaras.is.null")
        if banios is not None:
            query = query.or_(f"banios.gte.{banios},banios.is.null")

        query = query.lte("precio", presupuesto_busqueda).order("precio", desc=orden_descendente)
        res = query.execute()
        propiedades = res.data
        
        # 🎲 Mezclamos las propiedades para que Aria no muestre siempre las mismas 4
        if propiedades:
            random.shuffle(propiedades)
            
        alerta_fase_2 = False # Bandera para avisarle a Aria

        # FASE 2: BÚSQUEDA FLEXIBLE
        if not propiedades:
            print("[DB] Búsqueda 1 vacía. Intentando Fase 2 (Sin Zona)...")
            alerta_fase_2 = True # Encendemos la bandera
            query_f2 = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)
            
            if tipo_operacion: query_f2 = query_f2.ilike("tipoOperacion", f"%{tipo_operacion}%")
            if tipo_inmueble:
                tipo_prefix_f2 = tipo_inmueble[:3].lower()
                if tipo_prefix_f2 in ["loca", "ofic", "cons"]:
                    query_f2 = query_f2.or_("subtipoPropiedad.ilike.%loca%,subtipoPropiedad.ilike.%ofic%,subtipoPropiedad.ilike.%cons%")
                else:
                    query_f2 = query_f2.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%")
            
            if tipo_credito == "infonavit": query_f2 = query_f2.or_('descripcion.ilike.%infonavit%,institucionHipotecaria.cs.{"INFONAVIT"}')
            elif tipo_credito == "fovissste": query_f2 = query_f2.or_('descripcion.ilike.%fovissste%,descripcion.ilike.%fovisste%,descripcion.ilike.%foviste%,institucionHipotecaria.cs.{"FOVISSSTE"}')
            elif tipo_credito == "bancario": query_f2 = query_f2.or_('descripcion.ilike.%bancario%,descripcion.ilike.%credito%,descripcion.ilike.%crédito%,institucionHipotecaria.cs.{"BANCARIO"}')
            elif tipo_credito == "general": query_f2 = query_f2.or_('descripcion.ilike.%infonavit%,descripcion.ilike.%fovissste%,descripcion.ilike.%bancario%,institucionHipotecaria.cs.{"INFONAVIT"},institucionHipotecaria.cs.{"FOVISSSTE"},institucionHipotecaria.cs.{"BANCARIO"}')
            
            # 🌟 NUEVO: Aplicamos la misma lógica de lista para las características en Fase 2
            if caracteristica:
                lista_palabras = [c.strip().lower() for c in str(caracteristica).split(",") if c.strip()]
                for palabra in lista_palabras:
                    query_f2 = query_f2.ilike("descripcion", f"%{palabra}%")
            
            if recamaras is not None:
                query_f2 = query_f2.or_(f"recamaras.gte.{recamaras},recamaras.is.null")
            if banios is not None:
                query_f2 = query_f2.or_(f"banios.gte.{banios},banios.is.null")
                
            query_f2 = query_f2.lte("precio", presupuesto_busqueda).order("precio", desc=orden_descendente)
            res_f2 = query_f2.execute()
            propiedades = res_f2.data
            
            if propiedades:
                random.shuffle(propiedades)

        # Devolvemos las propiedades Y la bandera de alerta
        return (propiedades[:4] if propiedades else []), alerta_fase_2
    
    except Exception as e:
        print(f"[ERROR DB BUSQUEDA] {e}")
        return [], False

def guardar_mapa_generado(id_propiedad, url_mapa):
    try:
        supabase.table("propiedades").update({"mapa_url": url_mapa}).eq("id", id_propiedad).execute()
    except Exception as e:
        print(f"[ERROR GUARDANDO MAPA] {e}")

def obtener_asesor_aleatorio():
    try:
        res = supabase.table("asesores").select("id, nombre, correo, telefono, recibir_correo").eq("activo", True).execute()
        asesores_activos = res.data

        if not asesores_activos:
            print("[ALERTA] No hay ningún asesor con activo=TRUE en Supabase.")
            return None
        asesor_ganador = random.choice(asesores_activos)
        print(f"[ASIGNACIÓM] La ruleta eligio a: {asesor_ganador['nombre']} ({asesor_ganador['correo']})")

        return asesor_ganador
    except Exception as e:
        print(f"[ERROR DB OBTENER ASESOR] {e}")
    return None

def obtener_asesor_por_nombre(nombre: str):
    """
    Busca un asesor cuyo nombre coincida parcialmente (ilike)
    con el nombre solicitado y que esté activo.
    """
    try:
        res = supabase.table("asesores").select("id, nombre, correo, telefono, recibir_correo").eq("activo", True).ilike("nombre", f"%{nombre}%").execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"[ERROR DB OBTENER ASESOR POR NOMBRE] {e}")
        return None

def obtener_asesor_por_telefono(telefono_raw: str):
    """
    Detecta si el número entrante pertenece a un asesor registrado.
    Normaliza el número quitando 'whatsapp:', '+', y espacios para
    coincidir con el formato que pueda tener la tabla asesores.
    """
    try:
        # Extraer solo dígitos del número entrante (e.g. "whatsapp:+5214271234567" -> "5214271234567")
        solo_digitos = ''.join(filter(str.isdigit, telefono_raw))

        res = supabase.table("asesores").select("id, nombre, correo, telefono, recibir_correo, activo").execute()
        for asesor in (res.data or []):
            tel_asesor = ''.join(filter(str.isdigit, asesor.get("telefono", "")))
            # Coincidencia si los últimos 10 dígitos son iguales (ignora prefijos de país)
            if tel_asesor and tel_asesor[-10:] == solo_digitos[-10:]:
                return asesor
        return None
    except Exception as e:
        print(f"[ERROR DB OBTENER ASESOR POR TELEFONO] {e}")
        return None
