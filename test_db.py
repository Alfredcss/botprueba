import database
import json

propiedades = database.buscar_por_clave("609813")
print("Propiedad Lomas de Guadalupe:")
for p in propiedades:
    print(p.get("municipio"), p.get("colonia"))

all_props = database.buscar_propiedades(None, None, None, None, None)[0]
print("\nMunicipios en la base de datos (con sample size):")
municipios = [p.get("municipio") for p in all_props]
from collections import Counter
print(Counter(municipios))

print("\nBuscando 'San Juan':")
res_sj = database.buscar_propiedades(None, None, "San Juan", None, None)[0]
print("Hits:", len(res_sj))
for p in res_sj:
    print(p.get("clave"), p.get("municipio"), p.get("precio"))

print("\nBuscando 'San Juan del Río':")
res_sjr = database.buscar_propiedades(None, None, "San Juan del Río", None, None)[0]
print("Hits:", len(res_sjr))

print("\nBuscando 'San Juan del Rio':")
res_sjrx = database.buscar_propiedades(None, None, "San Juan del Rio", None, None)[0]
print("Hits:", len(res_sjrx))
