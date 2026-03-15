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
            if tipo_credito == "infonavit": q = q.ilike("descripcion", "%infonavit%")
            elif tipo_credito == "fovissste": q = q.ilike("descripcion", "%fovissste%")
            elif tipo_credito == "bancario": q = q.or_("descripcion.ilike.*bancario*,descripcion.ilike.*credito*,descripcion.ilike.*crédito*")
            return q

        def aplicar_zona(q):
            if not zona or zona.lower().strip() == "sugerencias": return q
            z_lower = zona.lower().strip()
            
            # Limpiamos basura (por si la IA no lo hizo)
            for b in ["colonia ", "fraccionamiento ", "barrio ", "zona ", "en "]:
                z_lower = z_lower.replace(b, "")
            z_lower = z_lower.strip()
            
            # Si tiene coma, separamos Municipio y Colonia
            if "," in z_lower:
                partes = z_lower.split(",")
                ciudad = partes[0].strip()
                col = partes[1].strip()
                
                # Buscamos ciudad
                if ciudad in ["qro", "queretaro", "querétaro"]: q = q.or_("municipio.ilike.*queretaro*,municipio.ilike.*querétaro*")
                elif ciudad in ["sjr", "san juan", "san juan del rio", "san juan del río"]: q = q.ilike("municipio", "%san juan%")
                elif ciudad in ["tequis", "tx", "tequisquiapan"]: q = q.ilike("municipio", "%tequisquiapan%")
                else: q = q.ilike("municipio", f"%{ciudad}%")
                
                # Buscamos colonia
                if col: q = q.ilike("colonia", f"%{col}%")
                return q
            else:
                # Si no hay coma, buscamos en ambos lados usando * como comodín
                c = z_lower
                if c in ["qro", "queretaro", "querétaro"]: return q.or_("municipio.ilike.*queretaro*,municipio.ilike.*querétaro*")
                elif c in ["sjr", "san juan", "san juan del rio", "san juan del río"]: return q.ilike("municipio", "%san juan%")
                elif c in ["tequis", "tx", "tequisquiapan"]: return q.ilike("municipio", "%tequisquiapan%")
                else:
                    return q.or_(f"municipio.ilike.*{c}*,colonia.ilike.*{c}*,nombre.ilike.*{c}*")

        # FASE 1: BÚSQUEDA ESTRICTA
        q1 = aplicar_zona(aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)))
        q1 = q1.lte("precio", presupuesto_busqueda)
        
        if orden_precio in ["desc", "asc"] or (presupuesto and presupuesto != 999999999):
            orden_descendente = True if (orden_precio == "desc" or presupuesto) else False
            if orden_precio == "asc": orden_descendente = False
            propiedades = q1.order("precio", desc=orden_descendente).limit(4).execute().data
        else:
            resultados = q1.limit(20).execute().data
            propiedades = random.sample(resultados, min(4, len(resultados))) if resultados else []

        # FASE 2: RESCATE 
        if not propiedades and zona:
            # 1. Quitamos límite de precio
            q2 = aplicar_zona(aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS)))
            rescate = q2.order("precio", desc=False).limit(4).execute().data
            
            # 2. Quitamos restricción de "casas" (Si pide casa en Palmillas y solo hay terreno, le mostrará el terreno)
            if not rescate:
                q_tipo = aplicar_zona(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS))
                rescate = q_tipo.order("precio", desc=False).limit(4).execute().data

            # 3. Si la colonia no existe, buscamos en la ciudad entera
            if not rescate and "," in zona.lower():
                ciudad_sola = zona.split(",")[0].strip()
                q3 = aplicar_filtros_base(supabase.table("propiedades").select(COLUMNAS_PERMITIDAS))
                if "qro" in ciudad_sola or "queretaro" in ciudad_sola: q3 = q3.or_("municipio.ilike.*queretaro*,municipio.ilike.*querétaro*")
                elif "sjr" in ciudad_sola or "san juan" in ciudad_sola: q3 = q3.ilike("municipio", "%san juan%")
                elif "tequis" in ciudad_sola or "tx" in ciudad_sola: q3 = q3.ilike("municipio", "%tequisquiapan%")
                else: q3 = q3.ilike("municipio", f"%{ciudad_sola}%")
                rescate = q3.order("precio", desc=False).limit(4).execute().data
                
            propiedades = rescate

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