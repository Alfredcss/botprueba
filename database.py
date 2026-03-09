from supabase import create_client, Client
import config
import utils
from datetime import datetime
import random
import whatsapp_notifier

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
COLUMNAS_PERMITIDAS = "id,clave,nombre,municipio,colonia,precio,subtipoPropiedad,tipoOperacion,descripcion,m2T,m2C,recamaras,banios,mapa_url,latitud,longitud,url_ficha"

# ==============================================================================
# FUNCIONES VIP (ASESORES)
# ==============================================================================
def obtener_asesor_por_telefono(telefono: str):
    try:
        res = supabase.table("asesores").select("id, nombre, correo, telefono").eq("activo", True).execute()
        if res.data: return res.data[0]["nombre"]
        return None
    except Exception as e:
        print(f"[ERROR CHECK ASESOR] {e}")
        return None

def obtener_propiedades_por_asesor(nombre_asesor: str):
    try:
        print(f"\n[DB REPORTES] 1. Buscando ID para el asesor: '{nombre_asesor}'")
        
        # PASO 1: Buscar al asesor en su tabla
        asesor_res = supabase.table("asesores").select("id, nombre").ilike("nombre", f"%{nombre_asesor}%").execute()
        
        if not asesor_res.data:
            print(f"[DB REPORTES] ❌ ERROR: No existe ningún asesor llamado '{nombre_asesor}' en la tabla 'asesores'.")
            return []
            
        # Extraemos el ID
        id_del_asesor = asesor_res.data[0]["id"]
        nombre_real = asesor_res.data[0]["nombre"]
        print(f"[DB REPORTES] ✅ Asesor encontrado: {nombre_real} (ID: {id_del_asesor})")
        
        # PASO 2: Buscar las propiedades usando ese ID
        print(f"[DB REPORTES] 2. Buscando casas donde asesor_id == {id_del_asesor}")
        res = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS).eq("asesor_id", id_del_asesor).execute()
        
        if not res.data:
            print(f"[DB REPORTES] ❌ ERROR: El ID {id_del_asesor} no tiene casas asignadas en la tabla propiedades (Revisa si en Supabase la celda dice NULL).")
            return []
            
        print(f"[DB REPORTES] ✅ ÉXITO: Se encontraron {len(res.data)} propiedades para {nombre_real}.")
        return res.data
        
    except Exception as e:
        print(f"[ERROR REPORTES OCURRIDO] {e}")
        return []

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

async def guardar_cliente(mensaje_usuario, respuesta_bot, telefono, datos_extraidos, cliente_existente=None):
    try:
        observaciones_actuales = cliente_existente.get("observaciones_generales", "") if cliente_existente else ""
        nuevo_historial = f"{observaciones_actuales}\nCliente: {mensaje_usuario}\nBot: {respuesta_bot}"
        
        # 1. Obtenemos el momento actual
        ahora = datetime.now()
        
        # 2. Formateamos exactamente como lo piden tus columnas en Supabase
        fecha_str = ahora.strftime("%Y-%m-%d") # Formato para columna 'date' (Ej: 2026-03-03)
        hora_str = ahora.strftime("%H:%M:%S")  # Formato para columna 'time' (Ej: 14:30:00)
        
        # 3. Lo inyectamos en los datos a guardar
        datos_guardar = {
            "telefono": telefono, 
            "observaciones_generales": nuevo_historial,
            "fecha_contacto": fecha_str,
            "hora_contacto": hora_str
        }

        # Continúa tu código normal...
        if datos_extraidos.get("nombre_cliente"): datos_guardar["nombre_cliente"] = datos_extraidos["nombre_cliente"]
        
        if datos_extraidos.get("tipo_inmueble"): datos_guardar["tipo_inmueble"] = datos_extraidos["tipo_inmueble"]
        if datos_extraidos.get("zona_municipio"): datos_guardar["zona_municipio"] = datos_extraidos["zona_municipio"]
        if datos_extraidos.get("presupuesto"): datos_guardar["presupuesto"] = str(datos_extraidos["presupuesto"])
        if datos_extraidos.get("origen"): datos_guardar["origen"] = datos_extraidos["origen"]
        if datos_extraidos.get("clave_propiedad"): datos_guardar["id_propiedad_opcional"] = datos_extraidos["clave_propiedad"]

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

def buscar_propiedades(tipo_inmueble, tipo_operacion, zona, presupuesto, mostrar_mix_general=False):
    """Búsqueda estricta y lógica: Respeta siempre el tipo de inmueble y la operación."""
    try:
        # 🚨 1. EL FILTRO ANTI-MEZCLAS (NUEVO)
        # Si la IA no supo si es Venta o Renta, usamos el sentido común financiero
        if not tipo_operacion:
            if presupuesto and presupuesto > 150000:
                tipo_operacion = "Venta"  # Nadie paga 150 mil de renta mensual
            elif presupuesto and presupuesto <= 150000:
                tipo_operacion = "Renta"  # Nadie compra una casa en 150 mil
            else:
                tipo_operacion = "Venta"  # Por defecto, asumimos Venta si no hay datos

        # 2. MANEJO INTELIGENTE DEL PRESUPUESTO Y EL ORDEN
        if not presupuesto:
            presupuesto_busqueda = 1000000000
            orden_descendente = False  # Si no hay presupuesto, mostramos de la más barata a la más cara
        else:
            presupuesto_busqueda = presupuesto * 1.2 # Margen del 20%
            orden_descendente = True   # Si dio presupuesto, mostramos lo más top que le alcanza

        # FASE 1: BÚSQUEDA IDEAL (Todo estricto)
        query = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)
        
        # 🚨 CANDADOS INQUEBRANTABLES: Nunca soltamos la Operación ni el Tipo
        if tipo_operacion: query = query.ilike("tipoOperacion", f"%{tipo_operacion}%")
        if tipo_inmueble: query = query.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%") 
        
        if zona and zona.lower() != "sugerencias":
            zona_busqueda = f"municipio.ilike.*{zona}*,colonia.ilike.*{zona}*,nombre.ilike.*{zona}*"
            query = query.or_(zona_busqueda)

        query = query.lte("precio", presupuesto_busqueda).order("precio", desc=orden_descendente)
        res = query.execute()
        propiedades = res.data

        # FASE 2: BÚSQUEDA FLEXIBLE (Mismos candados, pero le perdonamos la Zona)
        if not propiedades:
            print("[DB] Búsqueda 1 vacía. Intentando Fase 2 (Sin Zona)...")
            query_f2 = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)
            
            # Mantenemos los candados inquebrantables
            if tipo_operacion: query_f2 = query_f2.ilike("tipoOperacion", f"%{tipo_operacion}%")
            if tipo_inmueble: query_f2 = query_f2.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%")
            
            query_f2 = query_f2.lte("precio", presupuesto_busqueda).order("precio", desc=orden_descendente)
            res_f2 = query_f2.execute()
            propiedades = res_f2.data

        # ELIMINAMOS LA FASE 3 (Modo Supervivencia). 
        # Si después de quitar la zona sigue sin haber casas de ese precio, 
        # es mejor devolver vacío para que el bot diga la verdad.
        
        return propiedades[:4] if propiedades else []
    except Exception as e:
        print(f"[ERROR DB BUSQUEDA] {e}")
        return []

def guardar_mapa_generado(id_propiedad, url_mapa):
    try:
        supabase.table("propiedades").update({"mapa_url": url_mapa}).eq("id", id_propiedad).execute()
    except Exception as e:
        print(f"[ERROR GUARDANDO MAPA] {e}")

def obtener_asesor_aleatorio():
    try:
        # 🚨 CORRECCIÓN: Agregamos 'telefono' al select para que Twilio pueda usarlo
        res = supabase.table("asesores").select("id, nombre, correo, telefono").eq("activo", True).execute()
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