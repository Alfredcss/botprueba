import database
import json

propiedades = database.buscar_propiedades(None, None, "San Juan", None, recamaras=4, banios=3)[0]

print(f"Total encontradas con rec>=4 y ban>=3 en San Juan: {len(propiedades)}")
for p in propiedades:
    print(f"Clave: {p['clave']}, Rec: {p['recamaras']}, Ban: {p['banios']}, Desc: {p['descripcion'][:50]}...")

# Ahora vamos a buscar TODO en San Juan y ver cuantas mencionan 4 recamaras en la descripcion
todas_sj = database.buscar_propiedades(None, None, "San Juan", None, None)[0]
candidatas = []
for p in todas_sj:
    desc = str(p.get('descripcion', '')).lower()
    if '4' in desc and 'rec' in desc and '3' in desc and 'bañ' in desc:
        candidatas.append(p)

print(f"\nTotal candidatas potenciales por descripcion textual: {len(candidatas)}")
for p in candidatas:
    print(f"Clave: {p.get('clave')}, DB_Rec: {p.get('recamaras')}, DB_Ban: {p.get('banios')}")
