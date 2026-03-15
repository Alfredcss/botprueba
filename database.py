from supabase import create_client, Client
import config
import utils
from datetime import datetime
import random

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
COLUMNAS_PERMITIDAS = "id,clave,nombre,municipio,colonia,precio,subtipoPropiedad,tipoOperacion,descripcion,m2T,m2C,recamaras,banios,mapa_url,latitud,longitud,url_ficha"

def obtener_cliente(telefono: str):
    try:
        res = supabase.table("clientes").select("*").eq("telefono", telefono).execute()
        if res.data: return res.data[0]
        return None
    except Exception as e: return None

async def guardar_cliente(mensaje_usuario, respuesta_bot, telefono, datos_extraidos, cliente_existente=None):
    try:
        observaciones_actuales = cliente_existente.get("observaciones_generales", "") if cliente_existente else ""
        nuevo_historial = f"{observaciones_actuales}\nCliente: {mensaje_usuario}\nBot: {respuesta_bot}"
        
        ahora = datetime.now()
        datos_guardar = {
            "telefono": telefono, 
            "observaciones_generales": nuevo_historial,
            "fecha_contacto": ahora.strftime("%Y-%m-%d"),
            "hora_contacto": ahora.strftime("%H:%M:%S")
        }

        if datos_extraidos.get("nombre_cliente"): datos_guardar["nombre_cliente"] = datos_extraidos["nombre_cliente"]
        if datos_extraidos.get("tipo_inmueble"): datos_guardar["tipo_inmueble"] = datos_extraidos["tipo_inmueble"]
        if datos_extraidos.get("zona_municipio"): datos_guardar["zona_municipio"] = datos_extraidos["zona_municipio"]
        if datos_extraidos.get("presupuesto"): datos_guardar["presupuesto"] = str(datos_extraidos["presupuesto"])
        if datos_extraidos.get("origen"): datos_guardar["origen"] = datos_extraidos["origen"]
        if datos_extraidos.get("clave_propiedad"): datos_guardar["id_propiedad_opcional"] = datos_extraidos["clave_propiedad"]

        if cliente_existente: supabase.table("clientes").update(datos_guardar).eq("telefono", telefono).execute()
        else: supabase.table("clientes").insert(datos_guardar).execute()
    except Exception as e: pass

def buscar_por_clave(clave):
    try:
        clave_limpia = str(clave).strip()
        res = supabase.table("propiedades").select(COLUMNAS_PERMITIDAS).or_(f"clave.eq.{clave_limpia},id.eq.{utils.limpiar_numero(clave_limpia)}").execute()
        return res.data
    except Exception as e: return []

def buscar_propiedades(tipo_inmueble, tipo_operacion, zona, presupuesto, mostrar_mix_general=False, tipo_credito=None, orden_precio=None):
    try:
        presupuesto_busqueda = (presupuesto * 1.2) if presupuesto and presupuesto != 999999999 else 1000000000
        
        def aplicar_filtros_base(q):
            if tipo_operacion: q = q.ilike("tipoOperacion", f"%{tipo_operacion}%")
            if tipo_inmueble: q = q.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%") 
            return q

        def aplicar_zona(q):
            # 💡 Si no hay zona, devolvemos el query sin filtro de lugar para que busque en todo el inventario
            if not zona or zona.lower().strip() == "null" or zona.lower().strip() == "none": 
                return q
            
            z_lower = zona.lower().strip()
            # Filtros de ciudad conocidos
            if z_lower in ["qro", "queretaro", "querétaro"]: return q.or_("municipio.ilike.*queretaro*,municipio.ilike.*querétaro*")
            if z_lower in ["sjr", "san juan"]: return q.ilike("municipio", "%san juan%")
            
            return q.or_(f"municipio.ilike.*{z_lower}*,colonia.ilike.*{z_lower}*,nombre.ilike.*{z_lower}*")

        # FASE 1: BÚSQUEDA
        q1 = aplicar_zona(aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)))
        q1 = q1.lte("precio", presupuesto_busqueda)
        
        propiedades = q1.order("precio", desc=False).limit(4).execute().data

        # FASE 2: RESCATE (Solo si no hay nada en absoluto)
        if not propiedades:
            q_rescate = aplicar_zona(aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)))
            propiedades = q_rescate.order("precio", desc=False).limit(4).execute().data

        return propiedades
    except Exception as e:
        print(f"[ERROR DB] {e}")
        return []

def guardar_mapa_generado(id_propiedad, url_mapa):
    try: supabase.table("propiedades").update({"mapa_url": url_mapa}).eq("id", id_propiedad).execute()
    except Exception: pass

def obtener_asesor_aleatorio():
    try:
        res = supabase.table("asesores").select("id, nombre, correo, telefono").eq("activo", True).execute()
        return random.choice(res.data) if res.data else None
    except Exception: return None