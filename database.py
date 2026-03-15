from supabase import create_client, Client
import config
import utils
from datetime import datetime
import random

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
COLUMNAS_PERMITIDAS = "id,clave,nombre,municipio,colonia,precio,subtipoPropiedad,tipoOperacion,descripcion,m2T,m2C,recamaras,banios,mapa_url,latitud,longitud,url_ficha"

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
        return []

def buscar_propiedades(tipo_inmueble, tipo_operacion, zona, presupuesto, mostrar_mix_general=False, tipo_credito=None, orden_precio=None):
    try:
        presupuesto_busqueda = (presupuesto * 1.2) if presupuesto else 1000000000
        
        def aplicar_filtros_base(q):
            if tipo_operacion: q = q.ilike("tipoOperacion", f"%{tipo_operacion}%")
            if tipo_inmueble: q = q.ilike("subtipoPropiedad", f"%{tipo_inmueble[:4]}%") 
            if tipo_credito == "infonavit": q = q.ilike("descripcion", "%infonavit%")
            elif tipo_credito == "fovissste": q = q.ilike("descripcion", "%fovissste%")
            elif tipo_credito == "bancario": q = q.or_("descripcion.ilike.*bancario*,descripcion.ilike.*credito*,descripcion.ilike.*crédito*")
            elif tipo_credito == "general": q = q.or_("descripcion.ilike.*infonavit*,descripcion.ilike.*fovissste*,descripcion.ilike.*bancario*,descripcion.ilike.*credito*,descripcion.ilike.*crédito*")
            return q

        query = aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS))
        
        # 🗺️ TRADUCTOR DE QRO
        zona_limpia = zona.lower() if zona else ""
        if zona_limpia in ["qro", "queretaro", "querétaro"]:
            zona_busqueda = "municipio.ilike.*queretaro*,municipio.ilike.*querétaro*,municipio.ilike.*qro*,colonia.ilike.*queretaro*,colonia.ilike.*querétaro*"
            query = query.or_(zona_busqueda)
        elif zona and zona_limpia != "sugerencias":
            zona_busqueda = f"municipio.ilike.*{zona}*,colonia.ilike.*{zona}*,nombre.ilike.*{zona}*"
            query = query.or_(zona_busqueda)

        query = query.lte("precio", presupuesto_busqueda)

        # 🎲 LÓGICA DE ORDEN O RULETA
        if orden_precio in ["desc", "asc"] or presupuesto:
            # Si hay orden explícito o dio presupuesto, ordenamos por precio
            orden_descendente = True if (orden_precio == "desc" or presupuesto) else False
            if orden_precio == "asc": orden_descendente = False
            query = query.order("precio", desc=orden_descendente).limit(4)
            propiedades = query.execute().data
        else:
            # Si solo quiere "ver opciones", traemos 20 y elegimos 4 al azar
            query = query.limit(20)
            resultados = query.execute().data
            if resultados:
                propiedades = random.sample(resultados, min(4, len(resultados)))
            else:
                propiedades = []

        return propiedades
    except Exception as e:
        print(f"[ERROR DB BUSQUEDA] {e}")
        return []

def guardar_mapa_generado(id_propiedad, url_mapa):
    try: supabase.table("propiedades").update({"mapa_url": url_mapa}).eq("id", id_propiedad).execute()
    except Exception: pass

def obtener_asesor_aleatorio():
    try:
        res = supabase.table("asesores").select("id, nombre, correo, telefono").eq("activo", True).execute()
        return random.choice(res.data) if res.data else None
    except Exception: return None